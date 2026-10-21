"""What a family sees about a delivery on its way to them.

A family can confirm the window they were offered, or say it does not work.
There is no self-service rescheduling: saying it does not work flags the
pledge, and a coordinator gets in touch. A new date is a promise to a person,
and a person should be the one to make it.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from backend import accounts, config, db, text
from backend.models import (
    Category,
    PledgeStatus,
    RequestStatus,
    WindowAnswer,
    WindowResponse,
)

router = APIRouter(prefix="/api/families")

RESCHEDULE_MESSAGE = (
    "Thanks for telling us. A coordinator will get in touch to find another "
    "time. Nothing else for you to do."
)

CONFIRMED_MESSAGE = "Thanks — we'll see you then."


@router.get("/{alias}/deliveries")
def family_deliveries(
    alias: str,
    session: accounts.Session = Depends(accounts.require("family")),
) -> dict:
    accounts.owns(session, alias)
    """Wishes on their way to this family, with the window to confirm."""
    with db.connect() as conn:
        family = db.get_family(conn, alias)
        if family is None:
            raise HTTPException(status_code=404, detail=f"We couldn't find a neighbor with the alias {alias!r}.")

        region = config.get_region(family.region_slug)
        today = date.today()
        rows = []
        for pledge in db.pledges_for_family(conn, alias):
            if pledge.status in (PledgeStatus.CANCELED, PledgeStatus.MISSED,
                                 PledgeStatus.RELEASED):
                continue
            wish = db.get_request(conn, pledge.request_id)
            if wish is None:
                continue
            rows.append({
                "pledge_id": pledge.id,
                "wish": wish.public_card(today),
                "delivery_date": pledge.delivery_date.isoformat(),
                "delivery_window": region.delivery_window.label(),
                "status": pledge.delivery_status(),
                "window_response": pledge.window_response.value,
                # Rent and utilities never arrive at a door.
                "paid_directly_to_provider": wish.category.value == "rent_utilities",
            })

    return {"count": len(rows), "deliveries": rows}


@router.post("/deliveries/respond")
def respond_to_window(
    body: WindowAnswer,
    session: accounts.Session = Depends(accounts.require("family")),
) -> dict:
    """The family confirms the window, or says it does not work."""
    accounts.owns(session, body.family_alias)
    if body.response is WindowResponse.PENDING:
        raise HTTPException(status_code=422, detail="Choose confirm or doesn't work.")

    with db.connect() as conn:
        pledge = db.get_pledge(conn, body.pledge_id)
        if pledge is None:
            raise HTTPException(status_code=404, detail="That delivery no longer exists.")

        wish = db.get_request(conn, pledge.request_id)
        if wish is None or wish.family_alias != body.family_alias:
            # A pledge belongs to one family; nobody else may answer for them.
            raise HTTPException(status_code=403, detail="That delivery isn't yours.")

        db.set_window_response(conn, body.pledge_id, body.response)
        conn.commit()

    confirmed = body.response is WindowResponse.CONFIRMED
    return {
        "pledge_id": body.pledge_id,
        "window_response": body.response.value,
        "message": CONFIRMED_MESSAGE if confirmed else RESCHEDULE_MESSAGE,
        "coordinator_will_contact": not confirmed,
    }


# --------------------------------------------------------------------------
# My wishes — where a family follows what happened to each one
# --------------------------------------------------------------------------
# Nothing here says anything about a donor. A family sees the state of their
# own wish and the date it arrives; who granted it is not theirs to know, and
# a donor who changes their mind should not become a person a family is
# waiting on by name.

# These read alongside what the wish granter is told, and the two sides must
# never contradict each other: while a granter sees "Ready to drop off", the
# neighbor sees "A neighbor picked your wish", not "Granted". Nothing here
# says a wish arrived until it has.
STAGES = {
    "being_checked": "Being checked",
    "on_the_tree": "On the tree",
    "granted": "A neighbor picked your wish",
    "on_its_way": "On its way",
    "delivered": "Delivered",
    "not_posted": "Not on the tree yet",
}

# Rent and utilities move as a payment, not a parcel.
RENT_STAGES = {
    "granted": "A neighbor picked your wish",
    "on_its_way": "Payment on the way",
    "delivered": "Paid",
}

RENT_NOTE = (
    "A coordinator will email you to confirm the amount and who to pay. The "
    "payment goes straight to your landlord or the utility company — never "
    "to you, and never through this app."
)


def _stage_for(wish, pledge, review) -> tuple[str, str, bool]:
    """The stage, the line under it, and whether this wish was dropped once."""
    status = wish.status.value
    # A donor who missed the window and one who said in advance they couldn't
    # come are the same thing from here: the wish is back up, and the family
    # is not told which it was.
    dropped_once = pledge is not None and pledge.status in (
        PledgeStatus.MISSED, PledgeStatus.RELEASED
    )

    direct = wish.category is Category.RENT_UTILITIES

    if status == "delivered":
        return "delivered", ("The payment has been made." if direct
                             else "This one arrived."), False
    if status == "dropped_off":
        if direct:
            return "on_its_way", "The payment is on its way to the provider.", False
        return ("on_its_way",
                "It's at the hub. We bring it to you on the next delivery day.",
                False)
    if status == "granted":
        if direct:
            return ("granted",
                    "A neighbor picked your wish. A coordinator will be in touch "
                    "about the payment.", False)
        return "granted", "A neighbor picked your wish. Here's when it arrives.", False
    if status == "open":
        if dropped_once:
            # Deliberately says nothing about why. A family does not need to
            # carry a stranger's change of plans, and "someone couldn't make
            # it" invites a disappointment that the wish going straight back
            # up has already answered.
            return "on_the_tree", "Still looking for the right neighbor.", True
        return ("on_the_tree",
                "Up on the tree where neighbors can see it. We can't promise "
                "someone will grant it, but we'll do our best to find a "
                "neighbor who can help.", False)
    if status == "pending_review":
        if review is not None and not review["approved"]:
            # Our sentence for this reason, never the agent's own wording.
            kinds = [flag.get("kind") for flag in (review.get("flags") or [])]
            return "not_posted", text.held_reason(kinds), False
        return ("being_checked",
                "We're checking this for anything that shouldn't be public. "
                "It only takes a moment.", False)
    return "being_checked", "Just submitted.", False


@router.get("/{alias}/wishes")
def family_wishes(
    alias: str,
    session: accounts.Session = Depends(accounts.require("family")),
) -> dict:
    accounts.owns(session, alias)
    """Every wish this family has posted, and where each one has got to."""
    today = date.today()
    with db.connect() as conn:
        family = db.get_family(conn, alias)
        if family is None:
            raise HTTPException(status_code=404, detail=f"We couldn't find a neighbor with the alias {alias!r}.")

        region = config.get_region(family.region_slug)
        rows = []
        for wish in db.list_requests(conn):
            if wish.family_alias != alias or wish.status is RequestStatus.DRAFT:
                continue

            pledge = db.get_pledge_for_request(conn, wish.id)
            review = db.get_safety_review(conn, wish.id)
            stage, detail, still_looking = _stage_for(wish, pledge, review)
            is_rent = wish.category is Category.RENT_UTILITIES

            delivery = None
            if stage in ("granted", "on_its_way") and pledge is not None and not is_rent:
                delivery = {
                    "pledge_id": pledge.id,
                    "date": pledge.delivery_date.isoformat(),
                    "window": region.delivery_window.label(),
                    "window_response": pledge.window_response.value,
                }

            rows.append({
                "wish": wish.public_card(today),
                "stage": stage,
                "label": (RENT_STAGES.get(stage) if is_rent else None) or STAGES[stage],
                "detail": detail,
                "still_looking": still_looking,
                "delivery": delivery,
                "direct_payment": is_rent,
                "direct_payment_note": RENT_NOTE if is_rent else None,
                "removed_before_posting": review["removed"] if review else [],
            })

    order = ["granted", "on_its_way", "being_checked", "on_the_tree",
             "not_posted", "delivered"]
    rows.sort(key=lambda r: order.index(r["stage"]))
    return {
        "count": len(rows),
        "wishes": rows,
        "stages": STAGES,
        "open_wish_cap": config.MAX_OPEN_WISHES_PER_FAMILY,
    }
