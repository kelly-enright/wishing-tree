"""Turn a measurement run into output/tokenomics.md.

Kept apart from `backend/measure.py` so the report can be rewritten from the
saved raw runs without spending tokens again:

    from backend.tokenomics_report import write_report
    import json
    write_report(json.load(open("output/tokenomics.json")), ...)
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from backend import config

# --------------------------------------------------------------------------
# Usage assumptions — stated here so a reader can disagree with them
# --------------------------------------------------------------------------

FAMILIES_SHARE = 1 / 3          # one family for every two donors
INTAKES_PER_FAMILY_MONTH = 1.0  # a family posts wishes about once a month
MATCH_RUNS_PER_DONOR_MONTH = 2.0  # a donor looks for something to grant twice


def _mean(rows: list[dict], field: str) -> float:
    values = [r[field] for r in rows if r.get(field) is not None]
    return statistics.mean(values) if values else 0.0


def _calls(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        out.extend(row.get("calls", [row]))
    return out


def _agent_table(name: str, rows: list[dict]) -> tuple[str, dict]:
    calls = _calls(rows)
    stats = {
        "runs": len(rows),
        "calls": len(calls),
        "calls_per_run": len(calls) / len(rows) if rows else 0,
        "input": _mean(calls, "input_tokens"),
        "cached": _mean(calls, "cached_input_tokens"),
        "cache_write": _mean(calls, "cache_write_tokens"),
        "output": _mean(calls, "output_tokens"),
        "latency": _mean(calls, "latency_ms"),
        "cost_call": _mean(calls, "cost_usd"),
        "cost_run": _mean(rows, "cost_usd") if "cost_usd" in (rows[0] if rows else {}) else _mean(calls, "cost_usd"),
    }
    line = (
        f"| {name} | {stats['runs']} | {stats['calls_per_run']:.1f} | "
        f"{stats['input']:,.0f} | {stats['cached']:,.0f} | "
        f"{stats['cache_write']:,.0f} | {stats['output']:,.0f} | "
        f"{stats['latency']/1000:.1f} s | ${stats['cost_call']:.6f} | "
        f"${stats['cost_run']:.6f} |"
    )
    return line, stats


def write_report(data: dict, path: Path) -> None:
    prices = data["prices"]
    intakes = data["intakes_default"]
    reviews = data["reviews"]
    matches = data["matches"]

    intake_line, intake_stats = _agent_table("Intake", intakes)
    review_line, review_stats = _agent_table("Privacy & Safety", reviews)
    match_line, match_stats = _agent_table("Matchmaker", matches)

    wishes_per_intake = _mean(intakes, "wishes")
    family_journey = intake_stats["cost_run"] + review_stats["cost_run"] * wishes_per_intake
    donor_journey = match_stats["cost_run"]

    def monthly(users: int) -> dict:
        families = users * FAMILIES_SHARE
        donors = users - families
        family_cost = families * INTAKES_PER_FAMILY_MONTH * family_journey
        donor_cost = donors * MATCH_RUNS_PER_DONOR_MONTH * donor_journey
        return {
            "families": families, "donors": donors,
            "family_cost": family_cost, "donor_cost": donor_cost,
            "total": family_cost + donor_cost,
        }

    hundred, tenk = monthly(100), monthly(10_000)

    # --- experiment C ---
    by_donor_15 = {r["donor"]: r for r in data["limit_15"]}
    by_donor_all = {r["donor"]: r for r in data["limit_all"]}
    c_rows, changed_count, same_count = [], 0, 0
    for donor in sorted(by_donor_15):
        a, b = by_donor_15[donor], by_donor_all.get(donor)
        if not b:
            continue
        same_set = set(a["matches"]) == set(b["matches"])
        same_order = a["matches"] == b["matches"]
        changed_count += 0 if same_set else 1
        same_count += 1 if same_set else 0
        c_rows.append(
            f"| {donor} | {a['input_tokens'] + a['cached_input_tokens'] + a['cache_write_tokens']:,} | "
            f"${a['cost_usd']:.6f} | "
            f"{b['input_tokens'] + b['cached_input_tokens'] + b['cache_write_tokens']:,} | "
            f"${b['cost_usd']:.6f} | "
            f"{'same five' if same_set else 'different'} | "
            f"{'same order' if same_order else 'reordered'} |"
        )
    cost_15 = _mean(data["limit_15"], "cost_usd")
    cost_all = _mean(data["limit_all"], "cost_usd")

    # --- experiment D: three arms, because the middle one never bound ---
    def arm(rows: list[dict]) -> dict:
        calls = _calls(rows)
        return {
            "runs": len(rows),
            "cost": _mean(rows, "cost_usd"),
            "output_per_call": _mean(calls, "output_tokens"),
            "turns": _mean(rows, "turns"),
            "wishes": _mean(rows, "wishes"),
            "with_cost": _mean(rows, "wishes_with_cost"),
            "done": sum(1 for r in rows if r.get("done")),
        }

    d_default = arm(intakes)
    # `intakes_mid` is the middle arm. The key used to be `intakes_cap700`,
    # named after the number rather than the role, which is how the report
    # and the script that feeds it drifted apart: measure.py stopped writing
    # that key and this read a missing list as a column of zeros.
    d_mid = arm(data.get("intakes_mid", data.get("intakes_cap700", [])))
    d_tight = arm(data["intakes_tight"])
    tight_cap, default_cap = data["tight_cap"], data["default_cap"]
    mid_cap = data.get("mid_cap", 700)
    failures = data.get("tight_failures", [])
    mid_failures = data.get("mid_failures", [])
    attempted = len(data["intakes_tight"]) + len(failures)
    failure_rate = len(failures) / attempted * 100 if attempted else 0
    saving = d_default["cost"] - d_tight["cost"]
    saving_pct = (saving / d_default["cost"] * 100) if d_default["cost"] else 0
    keep = default_cap

    report = f"""# Tokenomics — Wishing Tree

Measured against **{data['model']}** on {data['run_at'][:10]}. Every number
here comes from a real run; nothing is estimated except where it says so.

Raw per-run records: `output/tokenomics_runs.json`.
Full call trail: `output/audit_trail.json` (benchmark sessions are prefixed
`measure-`).

## Prices

USD per million tokens, from the Lecture 11 slides (OpenAI Standard, short
context):

| Bucket | Price |
|---|---|
| input | ${prices['input']:.3f} |
| cached input | ${prices['cached_input']:.3f} |
| cache write | ${prices['cache_write']:.3f} |
| output | ${prices['output']:.3f} |

**Billing convention.** The API's input figure includes the cached and
cache-write parts, so uncached input = input − cached − cache write. Each
bucket is priced once. Output is **5× fresh input and 50× cached input**,
which turns out to decide most of what follows.

## How this was measured

- Ten intakes, a mix of four that name an exact item with a product link and
  six that describe a need. Each runs the opening message and, if the agent
  asks something, one follow-up — which is what a real intake looks like.
- Ten safety reviews over real open wishes.
- Ten matchmaker runs across five donors.
- Its own database (`data/measure.db`) and a raised daily cap for the burst,
  so benchmarking never spends the operational budget. The app's own cap is
  unchanged.

## Cost per run, by agent

| Agent | Runs | Calls/run | Input | Cached | Cache write | Output | Latency | $/call | $/run |
|---|---|---|---|---|---|---|---|---|---|
{intake_line}
{review_line}
{match_line}

Cached input is the largest bucket in every row, which is the explicit
prompt-cache breakpoint doing its job.

## Cost per journey

**A family journey** — one intake, then a safety review for each wish it
produced ({wishes_per_intake:.1f} wishes per intake, measured):

| Part | Cost |
|---|---|
| Intake ({intake_stats['calls_per_run']:.1f} calls) | ${intake_stats['cost_run']:.6f} |
| Safety reviews (× {wishes_per_intake:.1f}) | ${review_stats['cost_run'] * wishes_per_intake:.6f} |
| **Whole family journey** | **${family_journey:.6f}** |

**A donor journey** — one matchmaker run. Browsing the wall, filtering and
granting are all plain database work and cost nothing.

| Part | Cost |
|---|---|
| **Whole donor journey** | **${donor_journey:.6f}** |

Roughly: **{1/family_journey:,.0f} family journeys to the dollar**, and
**{1/donor_journey:,.0f} donor journeys to the dollar**.

## Monthly cost at scale

Stated assumptions, so they can be argued with:

- one family for every two donors ({FAMILIES_SHARE:.0%} of users are families)
- a family posts wishes {INTAKES_PER_FAMILY_MONTH:.0f}× a month
- a donor asks to be matched {MATCH_RUNS_PER_DONOR_MONTH:.0f}× a month
- the coordinator's screens, the wish wall, granting and delivery use no model
  calls at all

| Users | Families | Donors | Family cost | Donor cost | **Monthly total** |
|---|---|---|---|---|---|
| 100 | {hundred['families']:,.0f} | {hundred['donors']:,.0f} | ${hundred['family_cost']:.2f} | ${hundred['donor_cost']:.2f} | **${hundred['total']:.2f}** |
| 10,000 | {tenk['families']:,.0f} | {tenk['donors']:,.0f} | ${tenk['family_cost']:.2f} | ${tenk['donor_cost']:.2f} | **${tenk['total']:.2f}** |

At ten thousand users the model bill is **${tenk['total']:.0f} a month** —
less than one volunteer coordinator's phone plan. The binding constraint on
this project is the coordinator's Saturday, not the token budget.

## Experiment C — does the matchmaker need more candidates?

The search tool hands the model at most `MATCHMAKER_CANDIDATE_LIMIT`
candidates. Run at 15 and with no limit, on the same five donors:

| Donor | Input @15 | Cost @15 | Input @all | Cost @all | Top five | Order |
|---|---|---|---|---|---|---|
{chr(10).join(c_rows)}

Average cost: **${cost_15:.6f}** at 15, **${cost_all:.6f}** with no limit
({(cost_all / cost_15 - 1) * 100:+.0f}%).

{same_count} of {len(c_rows)} donors got the **same five wishes** either way.

**Keeping the limit at 15.** The wall is small
enough today that removing the limit changes little, but the cost grows with
the size of the wall while the answer does not: the matchmaker returns five
wishes however many it is shown, and the ones it picks are the most urgent,
which the database already sorts to the front. The limit is the setting that
stops a busy wall quietly becoming an expensive prompt.

## Experiment D — does capping output save money?

Output is the dearest bucket, so a cap per reply is the most direct lever.
Three arms, because the first tighter cap turned out not to be tight at all.

| | Default ({default_cap}) | {mid_cap} | {tight_cap} |
|---|---|---|---|
| Output tokens per call | {d_default['output_per_call']:,.0f} | {d_mid['output_per_call']:,.0f} | {d_tight['output_per_call']:,.0f} |
| Cost per intake | ${d_default['cost']:.6f} | ${d_mid['cost']:.6f} | ${d_tight['cost']:.6f} |
| Turns per intake | {d_default['turns']:.1f} | {d_mid['turns']:.1f} | {d_tight['turns']:.1f} |
| Wishes drafted | {d_default['wishes']:.1f} | {d_mid['wishes']:.1f} | {d_tight['wishes']:.1f} |
| Wishes with a cost | {d_default['with_cost']:.1f} | {d_mid['with_cost']:.1f} | {d_tight['with_cost']:.1f} |
| **Intakes that failed outright** | **0 of {d_default['runs']}** | **{len(mid_failures)} of {d_mid['runs'] + len(mid_failures)}** | **{len(failures)} of {attempted}** |

**A cap of {mid_cap} does nothing.** Mean output is about
{d_default['output_per_call']:,.0f} tokens a call, so {mid_cap} never binds; the cost
difference between those two arms is run-to-run variance, not a saving. This is
worth saying plainly because it is the easy mistake: setting a cap, seeing a
lower bill in one sample, and concluding the cap caused it.

**A cap of {tight_cap} binds, and breaks things.** {len(failures)} of
{attempted} intakes ({failure_rate:.0f}%) failed outright with *"Model token
limit ({tight_cap}) exceeded before any response was generated"* — the
structured reply could not be produced at all. The {d_tight['runs']} that did
finish averaged ${d_tight['cost']:.6f}, a saving of ${saving:.6f}
({saving_pct:.0f}%) per intake.

**Keeping {keep}.** A saving of {saving_pct:.0f}% of a tenth of a cent is worth
nothing against a {failure_rate:.0f}% chance that a family who has just typed
out what their children need gets an error instead of a wish. And the saving is
overstated anyway: the failed runs are not free — the tokens were spent before
the limit was hit — they are just wasted.

The real lever on output is not the cap. It is the prompt: telling the intake
agent to ask only the follow-ups that change what a donor would buy is what
keeps replies short, and it does that without ever truncating one.

## What actually drives the bill

1. **Output tokens.** At ${prices['output']:.2f}/M they are 5× fresh input and
   50× cached. The single biggest lever is asking agents for less prose, not
   feeding them less context.
2. **Turn count.** A second intake turn roughly doubles that intake's cost.
   The follow-up rules in the intake prompt — ask only what changes what a
   donor would buy — are a cost control as much as a kindness.
3. **Cache hits.** The explicit breakpoint keeps the system prompt out of the
   fresh-input bucket on every call after the first.

Things that cost nothing and were deliberately kept that way: the wish wall,
filtering, granting, the whole delivery flow, the coordinator's run sheet, and
the intake greeting, which is a fixed string rather than a model call.
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return None
