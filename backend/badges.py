"""The gentle badges on a wish card.

Computed from the same two numbers the Matchmaker ranks on —
`days_until_deadline` and `days_waiting` — so a donor reading the wall and the
agent ranking it are looking at the same facts. Thresholds live in
`config.py`, not in the interface.

No red URGENT. Every wish on this wall matters to somebody, and shouting about
one quietly says the others can wait. A wish that needs a donor soon says so
with a date; a wish that has been passed over says so with a number of weeks.
"""

from __future__ import annotations

from datetime import date, timedelta

from backend import config, scheduling
from backend.models import Region


def upcoming_dropoffs(
    count: int, today: date | None = None, region: Region | None = None
) -> list[date]:
    """The next `count` drop-off dates, soonest first."""
    region = region or config.get_region()
    today = today or date.today()
    dates: list[date] = []
    cursor = scheduling.next_dropoff(today, region)
    for _ in range(count):
        dates.append(cursor)
        cursor = scheduling.next_dropoff(cursor, region)
    return dates


def badges_for(card: dict, today: date | None = None,
               region: Region | None = None) -> list[dict]:
    """Badges for one `public_card()` shape."""
    today = today or date.today()
    out: list[dict] = []

    deadline = card.get("deadline")
    if deadline:
        horizon = upcoming_dropoffs(config.URGENCY_DROPOFFS_AHEAD, today, region)[-1]
        if date.fromisoformat(deadline) <= horizon:
            out.append({
                "kind": "needed_by",
                "label": f"Needed by {deadline}",
                "detail": "This one has to arrive before a date your neighbor gave us.",
            })

    waiting = card.get("days_waiting", 0)
    if waiting > config.WAITING_BADGE_DAYS:
        weeks = waiting // 7
        out.append({
            "kind": "waiting",
            "label": f"Waiting {weeks} week{'' if weeks == 1 else 's'}",
            "detail": "No neighbor has picked this one up yet.",
        })

    return out


def decorate(cards: list[dict], today: date | None = None) -> list[dict]:
    """Add badges to every card in a list, in place."""
    region = config.get_region()
    today = today or date.today()
    for card in cards:
        card["badges"] = badges_for(card, today, region)
    return cards
