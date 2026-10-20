"""The audit trail: one record per model call.

Every call any agent makes is written twice:

  - to `output/audit_trail.json`, append-only, one JSON object per line
  - to the `agent_calls` table, so the app can total a session for the
    token panel without reading a file

JSON Lines rather than one JSON array, because a run can append without first
reading and rewriting everything before it. The file is opened in append mode
and never in write mode. `read_all()` reads it back.

This is the evidence behind the tokenomics section of the report: input tokens,
cached input tokens and output tokens are recorded separately because they are
priced separately.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from backend import config, db
from backend.models import AgentCallLog

_lock = threading.Lock()


def now() -> datetime:
    return datetime.now(timezone.utc)


def prompt_version(text: str) -> str:
    """Short stable hash of a prompt, so a record says which prompt produced it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def append_jsonl(entry: dict, path: Path | None = None) -> None:
    """Append one record. Never truncates; creates the file if missing."""
    target = Path(path or config.AUDIT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, default=str, ensure_ascii=False)
    with _lock:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def record(call: AgentCallLog, conn: sqlite3.Connection | None = None) -> None:
    """Write one call to both the trail file and the database."""
    entry = call.model_dump(mode="json")
    entry["total_tokens"] = call.total_tokens
    append_jsonl(entry)

    if conn is not None:
        db.insert_agent_call(call, conn)
        return
    with db.connect() as own:
        db.insert_agent_call(call, own)
        own.commit()


def read_all(path: Path | None = None) -> list[dict]:
    """Read the trail back, tolerating a trailing partial line."""
    target = Path(path or config.AUDIT_PATH)
    if not target.exists():
        return []
    out: list[dict] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def totals(path: Path | None = None) -> dict:
    """Whole-project totals, for the report."""
    rows = read_all(path)
    return {
        "calls": len(rows),
        "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
        "cached_input_tokens": sum(r.get("cached_input_tokens", 0) for r in rows),
        "cache_write_tokens": sum(r.get("cache_write_tokens", 0) for r in rows),
        "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
        "cost_usd": sum(r.get("estimated_cost_usd") or 0 for r in rows),
        "prices_are_placeholders": config.PRICES_ARE_PLACEHOLDERS,
    }
