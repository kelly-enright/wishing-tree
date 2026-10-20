"""Re-cost every recorded call at the current prices.

`output/audit_trail.json` is append-only: it is the raw record of what each
call actually used, and nothing rewrites it. Prices change, though — they were
placeholders until the Lecture 11 figures arrived — so cost is treated as
derived rather than stored.

This module reads the trail, applies the four prices in `config.py`, and writes
`output/tokenomics.json`: per-call costs, per-session costs, and totals. It
also updates `estimated_cost_usd` on the `agent_calls` rows, which is a table
and may be corrected in place.

    ./.venv/bin/python -m backend.tokenomics
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from backend import config, db
from backend.agents import audit

OUTPUT_PATH = config.OUTPUT_DIR / "tokenomics.json"


def _buckets(record: dict) -> tuple[int, int, int, int]:
    """The four priced buckets of one call.

    Records written before explicit caching have no `cache_write_tokens`. That
    is not a gap in the data: under implicit caching the API reported no
    cache-write tokens, so zero is the true figure for those calls.
    """
    return (
        int(record.get("input_tokens", 0)),
        int(record.get("cached_input_tokens", 0)),
        int(record.get("cache_write_tokens", 0)),
        int(record.get("output_tokens", 0)),
    )


def cost_of(record: dict) -> float:
    uncached, cached, write, output = _buckets(record)
    return config.estimate_cost_usd(uncached, cached, output, write)


def recost(trail_path: Path | None = None) -> dict:
    """Cost every call in the trail, grouped by session and by agent."""
    records = audit.read_all(trail_path)

    calls = []
    by_session: dict[str, dict] = defaultdict(
        lambda: {"calls": 0, "input": 0, "cached": 0, "cache_write": 0,
                 "output": 0, "cost_usd": 0.0, "agents": set()}
    )
    by_agent: dict[str, dict] = defaultdict(
        lambda: {"calls": 0, "input": 0, "cached": 0, "cache_write": 0,
                 "output": 0, "cost_usd": 0.0}
    )

    for record in records:
        uncached, cached, write, output = _buckets(record)
        cost = cost_of(record)
        session = record.get("session_id") or "(none)"
        agent = record.get("agent", "unknown")

        calls.append({
            "timestamp": record.get("timestamp"),
            "session_id": session,
            "agent": agent,
            "operation": record.get("operation"),
            "request_id": record.get("request_id"),
            "input_tokens": uncached,
            "cached_input_tokens": cached,
            "cache_write_tokens": write,
            "output_tokens": output,
            "total_tokens": uncached + cached + write + output,
            "latency_ms": record.get("latency_ms", 0),
            "cost_usd": round(cost, 8),
            "ok": record.get("ok", True),
        })

        for bucket, key in ((by_session[session], "agents"), (by_agent[agent], None)):
            bucket["calls"] += 1
            bucket["input"] += uncached
            bucket["cached"] += cached
            bucket["cache_write"] += write
            bucket["output"] += output
            bucket["cost_usd"] += cost
            if key:
                bucket["agents"].add(agent)

    for bucket in by_session.values():
        bucket["agents"] = sorted(bucket["agents"])
        bucket["cost_usd"] = round(bucket["cost_usd"], 8)
    for bucket in by_agent.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 8)

    total_input = sum(c["input_tokens"] for c in calls)
    total_cached = sum(c["cached_input_tokens"] for c in calls)
    total_write = sum(c["cache_write_tokens"] for c in calls)
    total_output = sum(c["output_tokens"] for c in calls)
    all_input = total_input + total_cached + total_write

    return {
        "prices_per_million_usd": {
            "input": config.PRICE_PER_MILLION_INPUT_USD,
            "cached_input": config.PRICE_PER_MILLION_CACHED_INPUT_USD,
            "cache_write": config.PRICE_PER_MILLION_CACHE_WRITE_USD,
            "output": config.PRICE_PER_MILLION_OUTPUT_USD,
        },
        "billing_convention": (
            "uncached input = input - cached - cache_write; each bucket priced once"
        ),
        "model": config.MODEL_NAME,
        "totals": {
            "calls": len(calls),
            "input_tokens": total_input,
            "cached_input_tokens": total_cached,
            "cache_write_tokens": total_write,
            "output_tokens": total_output,
            "total_tokens": all_input + total_output,
            "cache_hit_rate": round(total_cached / all_input, 4) if all_input else 0.0,
            "cost_usd": round(sum(c["cost_usd"] for c in calls), 8),
        },
        "by_agent": dict(by_agent),
        "by_session": dict(by_session),
        "calls": calls,
    }


def update_database_costs() -> int:
    """Correct `estimated_cost_usd` on stored calls at the current prices."""
    changed = 0
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM agent_calls"):
            cost = config.estimate_cost_usd(
                row["input_tokens"], row["cached_input_tokens"],
                row["output_tokens"], row["cache_write_tokens"],
            )
            conn.execute(
                "UPDATE agent_calls SET estimated_cost_usd = ? WHERE id = ?",
                (cost, row["id"]),
            )
            changed += 1
        conn.commit()
    return changed


def main() -> None:
    report = recost()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = update_database_costs()

    totals = report["totals"]
    print(f"Re-costed {totals['calls']} calls from the trail -> {OUTPUT_PATH}")
    print(f"Updated {rows} agent_calls rows in the database")
    print()
    print(f"  input         {totals['input_tokens']:>8,}")
    print(f"  cached        {totals['cached_input_tokens']:>8,}")
    print(f"  cache write   {totals['cache_write_tokens']:>8,}")
    print(f"  output        {totals['output_tokens']:>8,}")
    print(f"  cache hit     {totals['cache_hit_rate']:>8.1%}")
    print(f"  cost          ${totals['cost_usd']:>8.4f}")


if __name__ == "__main__":
    main()
