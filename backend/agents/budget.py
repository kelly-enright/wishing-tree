"""Token spending limits, enforced on the server.

Two caps, both from config.py:

  - per session  (`MAX_TOKENS_PER_INTAKE_SESSION`)
  - per day, across the whole app (`DAILY_TOKEN_BUDGET`)

They are checked in `guard()`, which every agent calls immediately before it
touches the model. That is the only place a model call can start from, so there
is nothing a browser can send — no header, no field, no replayed request — that
skips the check. The numbers come from the `agent_calls` table, which only the
server writes.

A tripped cap raises `BudgetExceeded`, carrying a message written for the
person on the screen rather than for a log.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from backend import config, db


class BudgetExceeded(RuntimeError):
    """Raised instead of making a model call. `.friendly` is user-facing."""

    def __init__(self, friendly: str, scope: str, used: int, cap: int):
        super().__init__(f"{scope} token budget exceeded: {used}/{cap}")
        self.friendly = friendly
        self.scope = scope
        self.used = used
        self.cap = cap


def session_tokens(conn: sqlite3.Connection, session_id: str) -> int:
    row = conn.execute(
        """SELECT COALESCE(SUM(input_tokens + cached_input_tokens
                                + cache_write_tokens + output_tokens), 0) AS n
             FROM agent_calls WHERE session_id = ?""",
        (session_id,),
    ).fetchone()
    return int(row["n"])


def tokens_today(conn: sqlite3.Connection, day: str | None = None) -> int:
    today = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        """SELECT COALESCE(SUM(input_tokens + cached_input_tokens
                                + cache_write_tokens + output_tokens), 0) AS n
             FROM agent_calls WHERE substr(timestamp, 1, 10) = ?""",
        (today,),
    ).fetchone()
    return int(row["n"])


def status(session_id: str | None = None) -> dict:
    """What is left, for the token panel and the activity page."""
    with db.connect() as conn:
        daily = tokens_today(conn)
        used = session_tokens(conn, session_id) if session_id else 0
    return {
        "session_tokens": used,
        "session_cap": config.MAX_TOKENS_PER_INTAKE_SESSION,
        "daily_tokens": daily,
        "daily_cap": config.DAILY_TOKEN_BUDGET,
        "session_remaining": max(0, config.MAX_TOKENS_PER_INTAKE_SESSION - used),
        "daily_remaining": max(0, config.DAILY_TOKEN_BUDGET - daily),
    }


def guard(session_id: str | None = None) -> None:
    """Raise BudgetExceeded rather than start a model call that breaches a cap."""
    with db.connect() as conn:
        daily = tokens_today(conn)
        if daily >= config.DAILY_TOKEN_BUDGET:
            raise BudgetExceeded(
                "Wishing Tree is busy right now. Nothing you did caused this — "
                "try again tomorrow, or tell a coordinator.",
                scope="daily", used=daily, cap=config.DAILY_TOKEN_BUDGET,
            )

        if session_id is None:
            return

        used = session_tokens(conn, session_id)
        if used >= config.MAX_TOKENS_PER_INTAKE_SESSION:
            raise BudgetExceeded(
                "We need to stop here for now. Everything you've told me is safe — "
                "check your wishes on the next screen and post them, and start "
                "a new chat any time.",
                scope="session", used=used, cap=config.MAX_TOKENS_PER_INTAKE_SESSION,
            )
