"""What a family sees about a delivery on its way to them.

A family can confirm the window they were offered, or say it does not work.
There is no self-service rescheduling: saying it does not work flags the
pledge, and a coordinator gets in touch. A new date is a promise to a person,
and a person should be the one to make it.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from backend import config, db
from backend.models import PledgeStatus, WindowAnswer, WindowResponse

router = APIRouter(prefix="/api/families")

RESCHEDULE_MESSAGE = (
    "Thanks for telling us. A Wishing Tree coordinator will get in touch to "
    "sort out another time — you don't need to do anything else."
)

CONFIRMED_MESSAGE = "Thanks — we'll see you then."


@router.get("/{alias}/deliveries")
def family_deliveries(alias: str) -> dict:
    """Wishes on their way to this family, with the window to confirm."""
    with db.connect() as conn:
        family = db.get_family(conn, alias)
        if family is None:
            raise HTTPException(status_code=404, detail=f"No family with alias {alias!r}.")

        region = config.get_region(family.region_slug)
        today = date.today()
        rows = []
        for pledge in db.pledges_for_family(conn, alias):
            if pledge.status in (PledgeStatus.CANCELLED, PledgeStatus.MISSED):
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
def respond_to_window(body: WindowAnswer) -> dict:
    """The family confirms the window, or says it does not work."""
    if body.response is WindowResponse.PENDING:
        raise HTTPException(status_code=422, detail="Choose confirm or doesn't work.")

    with db.connect() as conn:
        pledge = db.get_pledge(conn, body.pledge_id)
        if pledge is None:
            raise HTTPException(status_code=404, detail="That delivery no longer exists.")

        wish = db.get_request(conn, pledge.request_id)
        if wish is None or wish.family_alias != body.family_alias:
            # A pledge belongs to one family; nobody else may answer for them.
            raise HTTPException(status_code=403, detail="That delivery is not yours.")

        db.set_window_response(conn, body.pledge_id, body.response)
        conn.commit()

    confirmed = body.response is WindowResponse.CONFIRMED
    return {
        "pledge_id": body.pledge_id,
        "window_response": body.response.value,
        "message": CONFIRMED_MESSAGE if confirmed else RESCHEDULE_MESSAGE,
        "coordinator_will_contact": not confirmed,
    }
