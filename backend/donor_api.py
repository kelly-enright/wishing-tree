"""The donor side: the wish wall, the Matchmaker, and granting a wish.

Everything a donor can reach returns `public_card()` shapes. A family's street
address and phone number are not filtered out of these responses — they are
never put in, because the card is built by naming the fields a donor may see.

Granting is the one place in the app where two people can want the same thing
at the same time. It is settled in SQLite with a conditional UPDATE, not in
Python, so the second donor is told the wish is gone rather than both being
told they got it.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Response

from backend import badges, config, db, scheduling
from backend.agents import budget
from backend.agents.budget import BudgetExceeded
from backend.agents.matchmaker import find_matches
from backend.models import (
    Category,
    GrantRequest,
    Occasion,
    PledgeStatus,
    RequestStatus,
    RequestType,
)

router = APIRouter(prefix="/api")


def _donor_or_404(alias: str):
    with db.connect() as conn:
        donor = db.get_donor(conn, alias)
    if donor is None:
        raise HTTPException(status_code=404, detail=f"No donor with alias {alias!r}.")
    return donor


def _match_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"match-{stamp}-{uuid.uuid4().hex[:6]}"


# --------------------------------------------------------------------------
# The wish wall
# --------------------------------------------------------------------------

@router.get("/wishes")
def wish_wall(
    category: list[Category] | None = Query(default=None),
    occasion: Occasion | None = None,
    request_type: RequestType | None = None,
    max_cost_usd: float | None = None,
    zip: str | None = None,
) -> dict:
    """Every open wish, filtered. Cards only — no contact details exist here."""
    today = date.today()
    with db.connect() as conn:
        wishes = db.list_open_wishes(
            conn,
            zip_code=zip,
            max_cost_usd=max_cost_usd,
            categories=[c.value for c in category] if category else None,
            request_type=request_type.value if request_type else None,
            occasion=occasion.value if occasion else None,
        )
    region = config.get_region()
    return {
        "count": len(wishes),
        "wishes": badges.decorate([w.public_card(today) for w in wishes], today),
        "region": {
            "name": region.name,
            "hub_name": region.hub_name,
            "hub_address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        },
        "filters": {
            "categories": [c.value for c in Category],
            "occasions": [o.value for o in Occasion],
            "request_types": [t.value for t in RequestType],
        },
    }


# --------------------------------------------------------------------------
# Matchmaking
# --------------------------------------------------------------------------

@router.post("/match")
async def match_wishes(body: dict) -> dict:
    """Ask the Matchmaker to rank open wishes for one donor."""
    donor = _donor_or_404(body.get("donor_alias", ""))
    session_id = body.get("session_id") or _match_session_id()
    filters = {
        "max_cost_usd": body.get("max_cost_usd"),
        "request_type": body.get("request_type"),
        "categories": body.get("categories"),
    }

    try:
        result, enforced, _call = await find_matches(donor, session_id, filters)
    except BudgetExceeded as limit:
        return {
            "session_id": session_id,
            "matches": [],
            "note": limit.friendly,
            "budget_scope": limit.scope,
            "usage": _usage(session_id),
        }
    except Exception as exc:                        # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail="The matchmaker could not answer just then. Please try again.",
        ) from exc

    today = date.today()
    with db.connect() as conn:
        cards = {}
        for match in result.matches:
            wish = db.get_request(conn, match.request_id)
            if wish:
                card = wish.public_card(today)
                card["badges"] = badges.badges_for(card, today)
                cards[match.request_id] = card

    return {
        "session_id": session_id,
        "matches": [
            {
                **match.model_dump(mode="json"),
                "wish": cards.get(match.request_id),
            }
            for match in result.matches
            if match.request_id in cards
        ],
        "note": result.note,
        "enforced": enforced,
        "candidate_limit": config.MATCHMAKER_CANDIDATE_LIMIT,
        "usage": _usage(session_id),
    }


def _usage(session_id: str) -> dict:
    with db.connect() as conn:
        usage = db.session_usage(conn, session_id)
    usage["prices_are_placeholders"] = config.PRICES_ARE_PLACEHOLDERS
    usage["model"] = config.MODEL_NAME
    return usage


# --------------------------------------------------------------------------
# Granting
# --------------------------------------------------------------------------

@router.post("/grant")
def grant_wish(body: GrantRequest) -> dict:
    """Claim a wish for one donor and hand back the logistics.

    Rent and utility wishes never pass through the hub: the money goes to the
    landlord or the provider, which is simulated in this MVP. Everything else
    is dropped at the hub in the weekly window.
    """
    donor = _donor_or_404(body.donor_alias)
    region = config.get_region()
    today = date.today()

    with db.connect() as conn:
        wish = db.get_request(conn, body.request_id)
        if wish is None:
            raise HTTPException(status_code=404, detail="That wish no longer exists.")
        if wish.status is not RequestStatus.OPEN:
            raise HTTPException(
                status_code=409,
                detail="Someone else has already granted this wish. "
                       "Have a look at what else is on the wall.",
            )

        schedule = scheduling.dropoff_before(wish.deadline, today, region)

        # A donor who picked a window on the confirmation screen gets that one,
        # as long as it is a real drop-off day that has not passed.
        chosen = body.dropoff_date
        if chosen is not None:
            valid = {date.fromisoformat(c["dropoff_date"])
                     for c in _dropoff_choices(wish, today, region)}
            if chosen not in valid:
                raise HTTPException(
                    status_code=422,
                    detail="That drop-off day isn't one we're running. "
                           "Please pick one from the list.",
                )
            schedule = {
                **schedule,
                "dropoff_date": chosen.isoformat(),
                "delivery_date": scheduling.delivery_for(chosen, region).isoformat(),
            }
            schedule["arrives_in_time"] = (
                wish.deadline is None
                or date.fromisoformat(schedule["delivery_date"]) <= wish.deadline
            )

        pledge = db.claim_wish(
            conn,
            request_id=wish.id,
            donor_alias=donor.alias,
            dropoff=date.fromisoformat(schedule["dropoff_date"]),
            delivery=date.fromisoformat(schedule["delivery_date"]),
        )
        if pledge is None:
            raise HTTPException(
                status_code=409,
                detail="Someone else got there first. "
                       "Have a look at what else is on the wall.",
            )
        conn.commit()
        granted = db.get_request(conn, wish.id)

    paid_direct = wish.category is Category.RENT_UTILITIES
    return {
        "granted": True,
        "wish": granted.public_card(today),
        "pledge": pledge.model_dump(mode="json"),
        "paid_directly_to_provider": paid_direct,
        "logistics": (
            {
                "kind": "direct_payment",
                "headline": "Paid directly to provider (simulated)",
                "detail": (
                    "Rent and utility help never passes through a person. "
                    "Wishing Tree pays the landlord or the utility company "
                    "directly. No payment is actually made in this MVP."
                ),
                "delivery_date": schedule["delivery_date"],
            }
            if paid_direct
            else {
                "kind": "hub_dropoff",
                "headline": f"Drop off at {region.hub_name}",
                "hub_name": region.hub_name,
                "hub_address": region.hub_address,
                "dropoff_date": schedule["dropoff_date"],
                "dropoff_window": region.dropoff_window.label(),
                "delivery_date": schedule["delivery_date"],
                "delivery_window": region.delivery_window.label(),
            }
        ),
        "arrives_in_time": schedule["arrives_in_time"],
        "schedule_note": schedule["reason"],
    }


@router.get("/donors/{alias}/pledges")
def donor_pledges(alias: str) -> dict:
    """What this donor has claimed, with each wish's public card."""
    donor = _donor_or_404(alias)
    today = date.today()
    with db.connect() as conn:
        pledges = [p for p in db.list_pledges(conn) if p.donor_alias == donor.alias]
        rows = []
        for pledge in pledges:
            wish = db.get_request(conn, pledge.request_id)
            rows.append({
                "pledge": pledge.model_dump(mode="json"),
                "wish": wish.public_card(today) if wish else None,
            })
    return {"count": len(rows), "pledges": rows}


# --------------------------------------------------------------------------
# Before a wish locks
# --------------------------------------------------------------------------

def _what_to_bring(wish) -> dict:
    """Exactly what a donor is agreeing to buy."""
    if wish.request_type is RequestType.SPECIFIC:
        return {
            "kind": "specific",
            "headline": "Bring this exact item",
            "item": wish.item_description,
            "brand": wish.brand,
            "size": wish.size,
            "color": wish.color,
            "link": wish.product_link,
            "substitute_ok": wish.open_to_substitute,
            "substitute_note": (
                "A similar substitute is fine if the exact one isn't available."
                if wish.open_to_substitute
                else "This family asked for this item specifically — please don't "
                     "substitute."
            ),
        }
    return {
        "kind": "flexible",
        "headline": "You choose — here's what matters",
        "item": wish.item_description,
        "essentials": wish.size_preferences or wish.size,
        "substitute_ok": True,
        "substitute_note": "Anything that fits the description works.",
    }


def _dropoff_choices(wish, today: date, region) -> list[dict]:
    """Every upcoming drop-off whose delivery still arrives in time.

    A donor with two weeks of notice should be able to say "the week after
    next", rather than being handed one date and left to make it work.
    """
    choices = []
    for dropoff in badges.upcoming_dropoffs(4, today, region):
        delivery = scheduling.delivery_for(dropoff, region)
        in_time = wish.deadline is None or delivery <= wish.deadline
        if not in_time and choices:
            break
        choices.append({
            "dropoff_date": dropoff.isoformat(),
            "delivery_date": delivery.isoformat(),
            "arrives_in_time": in_time,
            "label": dropoff.strftime("%A, %B %-d"),
        })
    return choices


@router.get("/grant/options")
def grant_options(request_id: int, donor_alias: str) -> dict:
    """Everything the confirmation screen needs before anything locks."""
    donor = _donor_or_404(donor_alias)
    region = config.get_region()
    today = date.today()

    with db.connect() as conn:
        wish = db.get_request(conn, request_id)
    if wish is None:
        raise HTTPException(status_code=404, detail="That wish no longer exists.")
    if wish.status is not RequestStatus.OPEN:
        raise HTTPException(
            status_code=409,
            detail="Someone else has already granted this wish. "
                   "Have a look at what else is on the tree.",
        )

    card = wish.public_card(today)
    card["badges"] = badges.badges_for(card, today, region)
    paid_direct = wish.category is Category.RENT_UTILITIES

    return {
        "wish": card,
        "donor_alias": donor.alias,
        "what_to_bring": None if paid_direct else _what_to_bring(wish),
        "estimated_cost_usd": wish.cost_ceiling_usd(),
        "cost_is_estimate": wish.cost_is_estimate,
        "paid_directly_to_provider": paid_direct,
        "direct_payment_note": (
            "Wishing Tree pays the landlord or the utility company directly — "
            "never the family, and never you to them. A coordinator will email "
            "you how to pay. No payment is actually taken in this MVP."
            if paid_direct else None
        ),
        "dropoff_choices": [] if paid_direct else _dropoff_choices(wish, today, region),
        "hub": {
            "name": region.hub_name,
            "address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        },
    }


# --------------------------------------------------------------------------
# What a donor has taken on
# --------------------------------------------------------------------------

DONOR_STATUS = {
    "pledged": "Granted",
    "dropped_off": "Dropped off — thank you, it's on its way",
    "delivered": "Delivered",
    "missed": "Missed",
    "released": "Released back to the tree",
    "canceled": "Canceled",
}

DIRECT_STATUS = {
    "pledged": "We'll email you how to pay",
    "delivered": "Paid",
}


@router.get("/donors/{alias}/granted")
def donor_granted(alias: str) -> dict:
    """A donor's own wishes, with friendly statuses and this week's drop-off.

    Carries the wish card and nothing else about the family — no name, no
    address, no contact of any kind.
    """
    donor = _donor_or_404(alias)
    region = config.get_region()
    today = date.today()
    week_end = today + timedelta(days=7)

    rows, this_week = [], []
    with db.connect() as conn:
        for pledge in db.list_pledges(conn):
            if pledge.donor_alias != donor.alias:
                continue
            wish = db.get_request(conn, pledge.request_id)
            if wish is None:
                continue

            paid_direct = wish.category is Category.RENT_UTILITIES
            key = pledge.status.value
            label = (DIRECT_STATUS.get(key) if paid_direct else None) or DONOR_STATUS[key]

            row = {
                "pledge_id": pledge.id,
                "wish": wish.public_card(today),
                "status": key,
                "label": label,
                "paid_directly_to_provider": paid_direct,
                "dropoff_date": pledge.dropoff_date.isoformat(),
                "delivery_date": pledge.delivery_date.isoformat(),
                "dropoff_window": region.dropoff_window.label(),
                "hub_name": region.hub_name,
                "hub_address": region.hub_address,
                "can_release": pledge.status is PledgeStatus.PLEDGED,
            }
            rows.append(row)

            if (pledge.status is PledgeStatus.PLEDGED and not paid_direct
                    and today <= pledge.dropoff_date <= week_end):
                this_week.append(row)

    order = ["pledged", "dropped_off", "delivered", "released", "missed", "canceled"]
    rows.sort(key=lambda r: (order.index(r["status"]), r["dropoff_date"]))

    return {
        "count": len(rows),
        "granted": rows,
        "this_week": this_week,
        "hub": {"name": region.hub_name, "address": region.hub_address,
                "dropoff_window": region.dropoff_window.label()},
    }


@router.post("/pledges/{pledge_id}/release")
def release_pledge(pledge_id: int, donor_alias: str) -> dict:
    """A donor who cannot make it says so, and the wish goes straight back.

    Recorded as `released`, not `missed`. Someone who tells you in advance has
    done the right thing, and the run sheet should not read as if they let a
    family down.
    """
    donor = _donor_or_404(donor_alias)

    with db.connect() as conn:
        pledge = db.get_pledge(conn, pledge_id)
        if pledge is None:
            raise HTTPException(status_code=404, detail="That pledge no longer exists.")
        if pledge.donor_alias != donor.alias:
            raise HTTPException(status_code=403, detail="That isn't yours to release.")
        if pledge.status is not PledgeStatus.PLEDGED:
            raise HTTPException(
                status_code=409,
                detail="This one has already moved on — nothing to release.",
            )

        db.set_pledge_status(conn, pledge_id, PledgeStatus.RELEASED)
        conn.commit()
        wish = db.get_request(conn, pledge.request_id)

    return {
        "released": True,
        "wish_id": pledge.request_id,
        "wish_status": wish.status.value if wish else None,
        "message": "Released. It's back on the tree for another neighbor — "
                   "thank you for telling us rather than leaving it.",
    }


# --------------------------------------------------------------------------
# A calendar file for the drop-off
# --------------------------------------------------------------------------

def _ics_escape(text: str) -> str:
    """Escape the four characters an .ics line cannot carry raw."""
    return (
        text.replace("\\", r"\\")
        .replace(",", r"\,")
        .replace(";", r"\;")
        .replace("\n", r"\n")
    )


@router.get("/pledges/{pledge_id}/calendar.ics")
def pledge_calendar(pledge_id: int, donor_alias: str) -> Response:
    """An .ics for the drop-off window, built here.

    No calendar service is involved: this is a few lines of text with the
    right field names, which is all an .ics is. Times are floating local —
    the window is 4-7pm wherever the donor's calendar thinks it is, which is
    the same 4-7pm the hub is open.
    """
    donor = _donor_or_404(donor_alias)
    region = config.get_region()

    with db.connect() as conn:
        pledge = db.get_pledge(conn, pledge_id)
        if pledge is None:
            raise HTTPException(status_code=404, detail="That pledge no longer exists.")
        if pledge.donor_alias != donor.alias:
            raise HTTPException(status_code=403, detail="That isn't yours.")
        wish = db.get_request(conn, pledge.request_id)

    day = pledge.dropoff_date.strftime("%Y%m%d")
    start = f"{day}T{region.dropoff_window.start.strftime('%H%M%S')}"
    end = f"{day}T{region.dropoff_window.end.strftime('%H%M%S')}"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    summary = "Wishing Tree drop-off"
    description = (
        f"Bring: {wish.item_description}" if wish else "Wishing Tree drop-off"
    ) + f"\nDelivered to the family on {pledge.delivery_date.isoformat()}."

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Wishing Tree//Drop-off//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:wishing-tree-pledge-{pledge_id}@wishingtree.local",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{start}",
        f"DTEND:{end}",
        f"SUMMARY:{_ics_escape(summary)}",
        f"LOCATION:{_ics_escape(region.hub_name + ', ' + region.hub_address)}",
        f"DESCRIPTION:{_ics_escape(description)}",
        "BEGIN:VALARM",
        "TRIGGER:-P1D",
        "ACTION:DISPLAY",
        "DESCRIPTION:Wishing Tree drop-off tomorrow",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    body = "\r\n".join(lines) + "\r\n"

    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="wishing-tree-dropoff-{day}.ics"',
        },
    )
