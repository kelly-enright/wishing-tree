"""The weekly rhythm: when a donor drops off, and when a family receives.

Every region has one drop-off window and one delivery window a week. A donation
reaches a family on the first delivery day on or after the drop-off, so what
"in time" means is the *delivery* date, not the drop-off date.

All of this is arithmetic over the region config. No model is involved, so a
date the app shows a donor is one it can defend.
"""

from __future__ import annotations

from datetime import date, timedelta

from backend import config
from backend.models import Region, Weekday

WEEKDAY_INDEX: dict[Weekday, int] = {
    Weekday.MONDAY: 0, Weekday.TUESDAY: 1, Weekday.WEDNESDAY: 2, Weekday.THURSDAY: 3,
    Weekday.FRIDAY: 4, Weekday.SATURDAY: 5, Weekday.SUNDAY: 6,
}


def next_weekday(start: date, day: Weekday) -> date:
    """The first date on or after `start` that falls on `day`."""
    return start + timedelta(days=(WEEKDAY_INDEX[day] - start.weekday()) % 7)


def previous_weekday(start: date, day: Weekday) -> date:
    """The last date on or before `start` that falls on `day`."""
    return start - timedelta(days=(start.weekday() - WEEKDAY_INDEX[day]) % 7)


def next_dropoff(today: date | None = None, region: Region | None = None) -> date:
    """The next drop-off a donor could make.

    Today's own window is not offered: a donor reading this at 9am on a
    Thursday might make it, and one reading it at 9pm will not. The next week's
    window is a date the app can stand behind.
    """
    region = region or config.get_region()
    return next_weekday((today or date.today()) + timedelta(days=1),
                        region.dropoff_window.day)


def delivery_for(dropoff: date, region: Region | None = None) -> date:
    """When a family receives something dropped off on `dropoff`."""
    region = region or config.get_region()
    return next_weekday(dropoff, region.delivery_window.day)


def dropoff_before(
    deadline: date | None, today: date | None = None, region: Region | None = None
) -> dict:
    """The latest drop-off whose delivery still lands on or before `deadline`.

    Returns the next available drop-off when there is no deadline, and says so
    rather than inventing urgency. When no drop-off can arrive in time it says
    that too, and offers the soonest one anyway — a late donation is usually
    still wanted, and that is the family's call to make, not the app's.
    """
    region = region or config.get_region()
    today = today or date.today()
    soonest = next_dropoff(today, region)
    soonest_delivery = delivery_for(soonest, region)

    if deadline is None:
        return {
            "dropoff_date": soonest.isoformat(),
            "delivery_date": soonest_delivery.isoformat(),
            "arrives_in_time": True,
            "time_sensitive": False,
            "reason": "no deadline on this wish, so the next drop-off is fine",
            "hub_name": region.hub_name,
            "hub_address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        }

    # Work back from the last delivery that still makes the deadline.
    last_delivery = previous_weekday(deadline, region.delivery_window.day)
    if last_delivery < soonest_delivery:
        return {
            "dropoff_date": soonest.isoformat(),
            "delivery_date": soonest_delivery.isoformat(),
            "arrives_in_time": False,
            "time_sensitive": True,
            "reason": (
                f"no drop-off can arrive by {deadline.isoformat()}; the soonest "
                f"delivery is {soonest_delivery.isoformat()}"
            ),
            "hub_name": region.hub_name,
            "hub_address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        }

    latest = previous_weekday(last_delivery, region.dropoff_window.day)
    if latest < soonest:
        latest, last_delivery = soonest, soonest_delivery

    return {
        "dropoff_date": latest.isoformat(),
        "delivery_date": last_delivery.isoformat(),
        "arrives_in_time": True,
        "time_sensitive": True,
        "reason": (
            f"dropping off on {latest.isoformat()} is delivered "
            f"{last_delivery.isoformat()}, before the {deadline.isoformat()} deadline"
        ),
        "hub_name": region.hub_name,
        "hub_address": region.hub_address,
        "dropoff_window": region.dropoff_window.label(),
        "delivery_window": region.delivery_window.label(),
    }
