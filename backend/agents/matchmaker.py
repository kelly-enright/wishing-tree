"""The Matchmaker: ranks open wishes for one donor.

What this agent is given is deliberately thin. `search_open_wishes` returns
`public_card()` shapes — the same thing a donor sees on the wall — so there is
no family contact detail anywhere in its context, and nothing for it to leak.

The fairness work is split between the prompt and the data. The prompt says to
rank on urgency and waiting time and to ignore how a wish is written. The tool
makes that possible by handing over `days_until_deadline` and `days_waiting`
as numbers, so the model does not have to infer either from prose. And the
descriptions it reads have already been rewritten into one neutral format by
the Privacy & Safety agent, so there is little tone left to be swayed by.

Dates are never the model's to invent: `next_dropoff_before` computes them from
the region's schedule, and the agent is told to pass them through unchanged.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from pydantic_ai import Agent, CachePoint, RunContext
from pydantic_ai.messages import ModelMessage, ToolCallPart
from pydantic_ai.settings import ModelSettings

from backend import accounts, config, db, scheduling, text
from backend.agents import audit, budget
from backend.agents.model import build_model
from backend.models import (
    AgentCallLog,
    Category,
    Donor,
    MatchmakerResult,
    RequestType,
)

AGENT_NAME = "matchmaker"
PROMPT_PATH = config.PROMPTS_DIR / "matchmaker_agent.md"

_INTERNAL_TOOLS = {"final_result"}


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def prompt_version() -> str:
    return audit.prompt_version(system_prompt())


@dataclass
class MatchDeps:
    donor_alias: str
    session_id: str
    today: date | None = None
    # A granter who is also a neighbor: their own wishes never become
    # candidates, so the model is never asked to rank them.
    own_aliases: list[str] = field(default_factory=list)
    candidate_ids: list[int] = field(default_factory=list)
    truncated: bool = False


@lru_cache(maxsize=1)
def matchmaker_agent() -> Agent:
    agent = Agent(
        build_model(),
        output_type=MatchmakerResult,
        deps_type=MatchDeps,
        system_prompt=system_prompt(),
        model_settings=ModelSettings(max_tokens=config.MAX_OUTPUT_TOKENS_MATCHMAKER),
        retries=2,
    )

    @agent.system_prompt
    def todays_date(ctx: RunContext[MatchDeps]) -> str:
        today = ctx.deps.today or date.today()
        return (
            f"Today's date is {today.isoformat()}. "
            f"Return at most {config.MAX_MATCHES_RETURNED} matches."
        )

    @agent.tool
    def search_open_wishes(
        ctx: RunContext[MatchDeps],
        zip: str | None = None,
        max_cost: float | None = None,
        categories: list[str] | None = None,
        request_type: str | None = None,
    ) -> dict:
        """Open wishes matching a donor's constraints.

        `zip` is read as *the donor's area*, not an exact postcode match: it
        resolves to the region that covers it, and every open wish in that
        region is eligible. A donor in 06512 driving to the hub in 06511 is
        the normal case, and matching zip-for-zip returned nothing at all.

        Returns the donor-visible shape of each wish and nothing more, with
        `days_until_deadline` and `days_waiting` precomputed so ranking is done
        on numbers rather than on how a wish reads.
        """
        today = ctx.deps.today or date.today()
        limit = config.MATCHMAKER_CANDIDATE_LIMIT

        region = config.region_for_zip(zip) if zip else None
        area = region.zip_codes if region else None

        with db.connect() as conn:
            # Fetch one past the limit, so truncation can be reported honestly.
            found = db.list_open_wishes(
                conn,
                zip_codes=area,
                max_cost_usd=max_cost,
                categories=categories or None,
                request_type=request_type,
                limit=None if limit is None else limit + 1,
                exclude_family_aliases=ctx.deps.own_aliases,
            )

        truncated = limit is not None and len(found) > limit
        if truncated:
            found = found[:limit]

        ctx.deps.candidate_ids = [w.id for w in found if w.id]
        ctx.deps.truncated = truncated

        return {
            "count": len(found),
            "truncated": truncated,
            "candidate_limit": limit,
            "area": region.name if region else "all regions",
            "wishes": [w.public_card(today) for w in found],
        }

    @agent.tool
    def next_dropoff_before(
        ctx: RunContext[MatchDeps], deadline: str | None = None
    ) -> dict:
        """The latest drop-off whose delivery still makes a deadline.

        Pass the wish's deadline as YYYY-MM-DD, or nothing when it has none.
        Computed from the region's weekly schedule, not estimated.
        """
        parsed = date.fromisoformat(deadline) if deadline else None
        return scheduling.dropoff_before(parsed, ctx.deps.today or date.today())

    return agent


def build_input(donor: Donor, filters: dict | None = None) -> str:
    """What the donor is asking for. No contact details are included."""
    chosen = filters or {}
    categories = chosen.get("categories") or [
        c.value for c in donor.preferred_categories
    ]
    return (
        "Find the best open wishes for this donor.\n\n"
        f"  alias: {donor.alias}\n"
        f"  zip: {donor.zip}\n"
        f"  budget per wish: ${donor.budget_usd:,.0f}\n"
        f"  preferred categories: {', '.join(categories) if categories else 'any'}\n"
        f"  prefers: {donor.preference.value} wishes\n"
        + (f"  filter — maximum cost: ${chosen['max_cost_usd']:,.0f}\n"
           if chosen.get("max_cost_usd") else "")
        + (f"  filter — wish type: {chosen['request_type']}\n"
           if chosen.get("request_type") else "")
        + "\nSearch, then rank. Call next_dropoff_before for every wish you return."
    )


def _tool_names(messages: list[ModelMessage]) -> list[str]:
    names: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart) and part.tool_name not in _INTERNAL_TOOLS:
                if part.tool_name not in names:
                    names.append(part.tool_name)
    return names


def enforce(result: MatchmakerResult, deps: MatchDeps) -> tuple[MatchmakerResult, list[str]]:
    """Drop anything the agent returned that search did not offer.

    The prompt says to rank only what the tool returned. This makes it true: an
    invented or stale wish id cannot reach a donor, and a wish that was claimed
    while the model was thinking is dropped rather than offered twice.
    """
    enforced: list[str] = []
    candidates = set(deps.candidate_ids)
    kept = []

    with db.connect() as conn:
        for match in result.matches:
            if match.request_id not in candidates:
                enforced.append(f"dropped wish #{match.request_id}: not in the search results")
                continue
            wish = db.get_request(conn, match.request_id)
            if wish is None or wish.status.value != "open":
                enforced.append(f"dropped wish #{match.request_id}: no longer open")
                continue
            kept.append(match)

    if len(kept) > config.MAX_MATCHES_RETURNED:
        enforced.append(
            f"trimmed to {text.counted(config.MAX_MATCHES_RETURNED, 'match', 'matches')}"
        )
        kept = kept[: config.MAX_MATCHES_RETURNED]

    return MatchmakerResult(matches=kept, note=result.note), enforced


async def find_matches(
    donor: Donor,
    session_id: str,
    filters: dict | None = None,
    today: date | None = None,
) -> tuple[MatchmakerResult, list[str], AgentCallLog]:
    """Rank open wishes for one donor. Returns the result, what code enforced,
    and the audit record."""
    budget.guard(session_id)

    agent = matchmaker_agent()
    with db.connect() as conn:
        own = accounts.own_family_aliases(conn, donor.contact_email.lower())
    deps = MatchDeps(donor_alias=donor.alias, session_id=session_id, today=today,
                     own_aliases=own)
    started = time.perf_counter()
    call = AgentCallLog(
        agent=AGENT_NAME,
        model=config.MODEL_NAME,
        operation="find_matches",
        session_id=session_id,
        prompt_version=prompt_version(),
    )

    try:
        result = await agent.run([CachePoint(), build_input(donor, filters)], deps=deps)
    except Exception as exc:                        # noqa: BLE001
        call.ok = False
        call.error = f"{type(exc).__name__}: {exc}"
        call.latency_ms = int((time.perf_counter() - started) * 1000)
        audit.record(call)
        raise

    usage = result.usage
    cached = usage.cache_read_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    call.input_tokens = config.split_input_tokens(
        usage.input_tokens or 0, cached, cache_write
    )
    call.cached_input_tokens = cached
    call.cache_write_tokens = cache_write
    call.output_tokens = usage.output_tokens or 0
    call.latency_ms = int((time.perf_counter() - started) * 1000)
    call.tools_called = _tool_names(result.new_messages())
    call.estimated_cost_usd = config.estimate_cost_usd(
        call.input_tokens, cached, call.output_tokens, cache_write
    )

    final, enforced = enforce(result.output, deps)
    call.input_summary = (
        f"donor {donor.alias}, ${donor.budget_usd:,.0f} budget, "
        f"{text.counted(len(deps.candidate_ids), 'candidate')}"
        + (", truncated" if deps.truncated else "")
    )
    call.output_summary = "; ".join(
        part for part in (
            f"{text.counted(len(final.matches), 'match', 'matches')} returned",
            f"code pass: {text.counted(len(enforced), 'change')}" if enforced else "",
        ) if part
    )
    audit.record(call)

    return final, enforced, call
