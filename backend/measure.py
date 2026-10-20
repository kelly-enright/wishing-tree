"""Token measurement against the real model.

    ./.venv/bin/python -m backend.measure

Runs three experiments and writes `output/tokenomics.md`:

  B. ten intakes, ten safety reviews and ten matchmaker runs, to get a cost
     per run for each agent and per whole journey
  C. the matchmaker with the candidate limit at 15 and with no limit, on the
     same donors, to see what the extra context buys
  D. ten intakes at the default output cap and ten at a tighter one, to see
     whether capping output saves money without making wishes worse

Two things keep this honest:

  - It runs against its own database (`data/measure.db`), so a benchmark burst
    never spends the operational daily token budget or touches real data.
  - The daily cap is raised for the duration, in that database only. Sixty
    calls in three minutes is not a day of normal use, and the app's own cap
    is left exactly as it is.

Everything still lands in the shared audit trail, tagged with `measure-`
session ids, so the raw records can be checked against this file.
"""

from __future__ import annotations

import asyncio
import json
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from backend import config, db, seed
from backend.agents import intake as intake_mod
from backend.agents import matchmaker as match_mod
from backend.agents import model as model_mod
from backend.agents import safety as safety_mod
from backend.agents.intake import IntakeDeps
from backend.models import AgentCallLog, Request

MEASURE_DB = config.DATA_DIR / "measure.db"
REPORT_PATH = config.OUTPUT_DIR / "tokenomics.md"
RAW_PATH = config.OUTPUT_DIR / "tokenomics_runs.json"

CONCURRENCY = 4

# --------------------------------------------------------------------------
# Ten intakes: five that name an exact item, five that describe a need
# --------------------------------------------------------------------------

@dataclass
class Scenario:
    key: str
    family: str
    kind: str          # "specific" | "flexible"
    first: str
    follow_up: str


SCENARIOS: list[Scenario] = [
    Scenario("coat", "Family A04", "flexible",
             "My son needs a winter coat for school, he's 8.",
             "Boys size 8, and no date in particular."),
    Scenario("backpack", "Family A07", "specific",
             "My daughter needs this backpack for school: "
             "https://www.target.com/p/kids-backpack-17in/-/A-54110298 "
             "— she's in 4th grade and would like the blue one.",
             "That's everything, thanks."),
    Scenario("groceries", "Family A12", "flexible",
             "We're short on groceries this month, there are four of us.",
             "No allergies, but no pork please. That's all."),
    Scenario("shoes", "Family A15", "specific",
             "I start a kitchen job next month and need non-slip work shoes, "
             "these ones: https://www.walmart.com/ip/slip-resistant-work-shoe/118920334",
             "Women's 9, and I need them by the 10th of November."),
    Scenario("electric", "Family A19", "flexible",
             "We got a shutoff notice on the electric bill, due the 3rd of next month.",
             "It's United Illuminating. That's the only thing."),
    Scenario("uniform", "Family A23", "flexible",
             "Both my kids have grown out of their school clothes.",
             "Boys 10 and girls 7. Nothing urgent."),
    Scenario("blazer", "Family A27", "specific",
             "I have an interview and need a blazer, this one would work: "
             "https://www.oldnavy.com/product/womens-classic-blazer-p-8814402",
             "Women's 12, charcoal, and the interview is on the 5th of November."),
    Scenario("diapers", "Family A31", "flexible",
             "We need diapers and wipes for a 14-month-old.",
             "Size 4. No particular date."),
    Scenario("supplies", "Family A34", "specific",
             "My son needs the 6th grade supply list, this set covers it: "
             "https://www.staples.com/kindergarten-supply-bundle/product_24119087",
             "Nothing else, thank you."),
    Scenario("meals", "Family A38", "flexible",
             "I'm recovering from surgery and can't stand at the stove.",
             "Soft foods, no allergies. That's it."),
]


def _row(call: AgentCallLog, **extra) -> dict:
    return {
        "agent": call.agent,
        "input_tokens": call.input_tokens,
        "cached_input_tokens": call.cached_input_tokens,
        "cache_write_tokens": call.cache_write_tokens,
        "output_tokens": call.output_tokens,
        "total_tokens": call.total_tokens,
        "latency_ms": call.latency_ms,
        "cost_usd": call.estimated_cost_usd or 0.0,
        **extra,
    }


# --------------------------------------------------------------------------
# Experiments
# --------------------------------------------------------------------------

async def one_intake(scenario: Scenario, label: str, gate: asyncio.Semaphore) -> dict:
    """One intake, up to two turns: the opening message, then a follow-up if
    the agent asked for one. That is what a real intake looks like."""
    async with gate:
        deps = IntakeDeps(family_alias=scenario.family, family_id=1,
                          session_id=f"measure-{label}-{scenario.key}")
        calls: list[AgentCallLog] = []

        reply, history, call = await intake_mod.run_turn(deps, scenario.first)
        calls.append(call)

        if not reply.done:
            reply, history, call = await intake_mod.run_turn(
                deps, scenario.follow_up, history
            )
            calls.append(call)

        wishes = reply.draft_wishes
        return {
            "scenario": scenario.key,
            "kind": scenario.kind,
            "turns": len(calls),
            "wishes": len(wishes),
            "done": reply.done,
            "reply_chars": len(reply.message),
            # Quality signals, for the output-cap experiment.
            "wishes_with_cost": sum(
                1 for w in wishes
                if w.estimated_cost_usd is not None or w.budget_min_usd is not None
            ),
            "wishes_with_size": sum(1 for w in wishes if w.size or w.size_preferences),
            "wishes_with_deadline": sum(1 for w in wishes if w.deadline),
            "descriptions": [w.item_description for w in wishes],
            "drafts": [w.model_dump(mode="json") for w in wishes],
            "calls": [_row(c) for c in calls],
            "cost_usd": sum(c.estimated_cost_usd or 0 for c in calls),
            "total_tokens": sum(c.total_tokens for c in calls),
            "output_tokens": sum(c.output_tokens for c in calls),
        }


async def one_review(request: Request, label: str, gate: asyncio.Semaphore) -> dict:
    async with gate:
        final, enforced, call = await safety_mod.review_wish(
            request, f"measure-{label}-{request.id}"
        )
        return {
            "request_id": request.id,
            "category": request.category.value,
            "approved": final.approved,
            "removed": len(final.removed),
            "flags": [f.kind.value for f in final.flags],
            "code_pass_changes": len(enforced),
            **_row(call),
        }


async def one_match(donor, label: str, limit: int | None,
                    gate: asyncio.Semaphore) -> dict:
    async with gate:
        original = config.MATCHMAKER_CANDIDATE_LIMIT
        config.MATCHMAKER_CANDIDATE_LIMIT = limit
        try:
            result, enforced, call = await match_mod.find_matches(
                donor, f"measure-{label}-{donor.alias.replace(' ', '')}"
            )
        finally:
            config.MATCHMAKER_CANDIDATE_LIMIT = original

        return {
            "donor": donor.alias,
            "candidate_limit": limit if limit is not None else "all",
            "matches": [m.request_id for m in result.matches],
            "match_count": len(result.matches),
            "code_pass_changes": len(enforced),
            **_row(call),
        }


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------

def average(rows: list[dict], field: str) -> float:
    values = [r[field] for r in rows if r.get(field) is not None]
    return statistics.mean(values) if values else 0.0


def summarize(rows: list[dict], per_call: bool = True) -> dict:
    flat = []
    for row in rows:
        flat.extend(row["calls"]) if "calls" in row else flat.append(row)
    source = flat if per_call else rows
    return {
        "runs": len(rows),
        "calls": len(flat) if flat else len(rows),
        "input": average(source, "input_tokens"),
        "cached": average(source, "cached_input_tokens"),
        "cache_write": average(source, "cache_write_tokens"),
        "output": average(source, "output_tokens"),
        "total": average(source, "total_tokens"),
        "latency_ms": average(source, "latency_ms"),
        "cost_usd": average(source, "cost_usd"),
        "cost_per_run_usd": statistics.mean(
            [r.get("cost_usd", 0) for r in rows]
        ) if rows else 0.0,
    }


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

async def run_all() -> dict:
    gate = asyncio.Semaphore(CONCURRENCY)

    with db.connect(MEASURE_DB) as conn:
        open_wishes = db.list_open_wishes(conn, limit=10)
        donors = db.list_donors(conn)[:5]

    print(f"  B1. ten intakes at the default output cap "
          f"({config.MAX_OUTPUT_TOKENS_INTAKE})…")
    intakes_default = await asyncio.gather(
        *(one_intake(s, "intake-default", gate) for s in SCENARIOS)
    )

    print("  B2. ten safety reviews…")
    reviews = await asyncio.gather(
        *(one_review(w, "review", gate) for w in open_wishes)
    )

    print("  B3. ten matchmaker runs…")
    match_runs = await asyncio.gather(
        *(one_match(d, "match", config.MATCHMAKER_CANDIDATE_LIMIT, gate)
          for d in donors * 2)
    )

    print("  C.  the same five donors, limit 15 then no limit…")
    matches_15 = await asyncio.gather(
        *(one_match(d, "limit15", 15, gate) for d in donors)
    )
    matches_all = await asyncio.gather(
        *(one_match(d, "limitall", None, gate) for d in donors)
    )

    tight = 700
    print(f"  D.  ten intakes at a tighter output cap ({tight})…")
    original_cap = config.MAX_OUTPUT_TOKENS_INTAKE
    config.MAX_OUTPUT_TOKENS_INTAKE = tight
    intake_mod.intake_agent.cache_clear()
    try:
        intakes_tight = await asyncio.gather(
            *(one_intake(s, "intake-tight", gate) for s in SCENARIOS),
            return_exceptions=True,
        )
    finally:
        config.MAX_OUTPUT_TOKENS_INTAKE = original_cap
        intake_mod.intake_agent.cache_clear()

    failures = [r for r in intakes_tight if isinstance(r, Exception)]
    intakes_tight = [r for r in intakes_tight if not isinstance(r, Exception)]

    return {
        "intakes_default": list(intakes_default),
        "reviews": list(reviews),
        "matches": list(match_runs),
        "limit_15": list(matches_15),
        "limit_all": list(matches_all),
        "intakes_tight": intakes_tight,
        "tight_cap": tight,
        "default_cap": original_cap,
        "tight_failures": [f"{type(e).__name__}: {e}" for e in failures],
    }


def main() -> None:
    config.require_api_key()

    # Its own database, and headroom for a benchmark burst. The app's own
    # daily cap is untouched; see the module docstring.
    original_db, original_daily = config.DB_PATH, config.DAILY_TOKEN_BUDGET
    config.DB_PATH = MEASURE_DB
    config.DAILY_TOKEN_BUDGET = 50_000_000
    if MEASURE_DB.exists():
        MEASURE_DB.unlink()
    seed.seed(MEASURE_DB)

    started = datetime.now(timezone.utc)
    print(f"Measuring against {config.MODEL_NAME} — this spends real tokens.")
    try:
        data = asyncio.run(run_all())
    finally:
        config.DB_PATH, config.DAILY_TOKEN_BUDGET = original_db, original_daily

    data["run_at"] = started.isoformat(timespec="seconds")
    data["model"] = config.MODEL_NAME
    data["prices"] = {
        "input": config.PRICE_PER_MILLION_INPUT_USD,
        "cached_input": config.PRICE_PER_MILLION_CACHED_INPUT_USD,
        "cache_write": config.PRICE_PER_MILLION_CACHE_WRITE_USD,
        "output": config.PRICE_PER_MILLION_OUTPUT_USD,
    }

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nRaw runs -> {RAW_PATH}")

    from backend.tokenomics_report import write_report
    write_report(data, REPORT_PATH)
    print(f"Report   -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
