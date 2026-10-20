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
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from backend import config, db, scheduling
from backend.agents import budget
from backend.agents.budget import BudgetExceeded
from backend.agents.matchmaker import find_matches
from backend.models import Category, GrantRequest, Occasion, RequestStatus, RequestType

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
        "wishes": [w.public_card(today) for w in wishes],
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
                cards[match.request_id] = wish.public_card(today)

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
