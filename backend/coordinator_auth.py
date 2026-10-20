"""The admin passcode gate.

A correct passcode issues a short-lived token, held in memory so it dies with
the process. Admin-only data is served against that token, which is what makes those
endpoints closed on the server rather than merely hidden in the interface —
the run sheet is the one screen in this app that shows a family's street
address, so a hidden route would not be enough.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from backend import config

TOKEN_TTL = timedelta(hours=8)

_TOKENS: dict[str, datetime] = {}


def issue_token(passcode: str) -> str:
    """Check the passcode and hand back a token, or refuse."""
    if not secrets.compare_digest(passcode.strip(), config.COORDINATOR_PASSCODE):
        raise HTTPException(status_code=401, detail="That passcode is not right.")

    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    _TOKENS[token] = now
    for issued, when in list(_TOKENS.items()):
        if now - when > TOKEN_TTL:
            _TOKENS.pop(issued, None)
    return token


def require_coordinator(x_coordinator_token: str | None = Header(default=None)) -> None:
    issued = _TOKENS.get(x_coordinator_token or "")
    if issued is None or datetime.now(timezone.utc) - issued > TOKEN_TTL:
        raise HTTPException(
            status_code=401,
            detail="Admin access has expired. Enter the passcode again.",
        )


def clear() -> None:
    """For tests."""
    _TOKENS.clear()
