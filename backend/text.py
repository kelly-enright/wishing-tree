"""Wording helpers.

Small, but the app writes to families having a hard week, so "1 wish(es) went
back on the wall" is not good enough. Every count the app says out loud goes
through here.
"""

from __future__ import annotations


def plural(count: int, singular: str, many: str | None = None) -> str:
    """Just the noun: `plural(1, "wish", "wishes")` -> "wish"."""
    return singular if count == 1 else (many or f"{singular}s")


def counted(count: int, singular: str, many: str | None = None) -> str:
    """The number and the noun: `counted(2, "wish", "wishes")` -> "2 wishes"."""
    return f"{count} {plural(count, singular, many)}"


def verb(count: int, singular: str, many: str) -> str:
    """Agreement for the verb: `verb(1, "is", "are")` -> "is"."""
    return singular if count == 1 else many
