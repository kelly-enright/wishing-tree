"""The coordinator's weekly run sheet.

This is the only screen in Wishing Tree that shows a family's street address
and phone number, and the only API that returns them. It is behind the
coordinator token, and every other view is built from `public_card()` shapes
that have no such fields to begin with.

No agents here. One week of pledges, three sections, and a button per row.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend import accounts, config, db, text
from backend.coordinator_auth import require_coordinator
from backend.models import Category, PledgeStatus

router = APIRouter(prefix="/api/coordinator", dependencies=[Depends(require_coordinator)])


class StatusClick(BaseModel):
    """One button on the run sheet. Several ids when a family's delivery is
    several wishes at once."""

    pledge_ids: list[int]
    status: PledgeStatus


def week_bounds(anchor: date | None = None) -> tuple[date, date]:
    """Monday to Sunday containing `anchor`."""
    day = anchor or date.today()
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


@router.get("/run-sheet")
def run_sheet(week_of: str | None = None) -> dict:
    """One week: who is dropping off, what goes out, and what is paid directly.

    `week_of` is any date in the week, so the interface can step back and
    forward a week at a time without knowing where weeks begin.
    """
    try:
        anchor = date.fromisoformat(week_of) if week_of else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="week_of must be YYYY-MM-DD.") from None

    start, end = week_bounds(anchor)
    region = config.get_region()
    today = date.today()

    dropoffs: list[dict] = []
    direct_payments: list[dict] = []
    delivery_groups: dict[tuple[str, str], dict] = {}

    with db.connect() as conn:
        for pledge in db.pledges_in_week(conn, start, end):
            wish = db.get_request(conn, pledge.request_id)
            if wish is None:
                continue
            donor = db.get_donor(conn, pledge.donor_alias)
            family = db.get_family(conn, wish.family_alias)

            if wish.category is Category.RENT_UTILITIES:
                direct_payments.append({
                    "pledge_id": pledge.id,
                    "family_alias": wish.family_alias,
                    "family_email": family.contact_email if family else None,
                    "donor_alias": pledge.donor_alias,
                    "item": wish.item_description,
                    "amount_usd": wish.cost_ceiling_usd(),
                    "pay_by": pledge.delivery_date.isoformat(),
                    "status": pledge.status.value,
                    "note": "Email the neighbor to confirm the amount and who to pay. "
                            "Paid to the landlord or provider, never to the "
                            "neighbor. Simulated in this demo.",
                })
                continue

            if start <= pledge.dropoff_date <= end:
                dropoffs.append({
                    "pledge_id": pledge.id,
                    "donor_alias": pledge.donor_alias,
                    # Coordinator-only, and only here.
                    "donor_name": donor.first_name if donor else None,
                    "donor_address": donor.contact_address if donor else None,
                    "donor_email": donor.contact_email if donor else None,
                    "donor_phone": donor.contact_phone if donor else None,
                    "item": wish.item_description,
                    "dropoff_date": pledge.dropoff_date.isoformat(),
                    "status": pledge.dropoff_status(),
                    "pledge_status": pledge.status.value,
                })

            # A missed or canceled drop-off still belongs in the drop-off
            # list, so the coordinator can see what happened — but there is
            # nothing to deliver, so it must not sit in a delivery round.
            if pledge.status in (PledgeStatus.MISSED, PledgeStatus.RELEASED,
                                 PledgeStatus.CANCELED):
                continue

            if start <= pledge.delivery_date <= end:
                key = (wish.family_alias, pledge.delivery_date.isoformat())
                group = delivery_groups.setdefault(key, {
                    "family_alias": wish.family_alias,
                    # Coordinator-only, and only here.
                    "family_name": family.first_name if family else None,
                    "family_address": family.contact_address if family else None,
                    "family_email": family.contact_email if family else None,
                    "family_phone": family.contact_phone if family else None,
                    "delivery_date": pledge.delivery_date.isoformat(),
                    "pledge_ids": [],
                    "items": [],
                    "confirmed": True,
                    "window_responses": [],
                    "status": "delivered",
                })
                group["pledge_ids"].append(pledge.id)
                group["items"].append(wish.item_description)
                group["window_responses"].append(pledge.window_response.value)
                group["confirmed"] = group["confirmed"] and pledge.family_confirmed_delivery
                if pledge.delivery_status() != "delivered":
                    group["status"] = "scheduled"

    deliveries = sorted(delivery_groups.values(), key=lambda g: g["delivery_date"])

    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "is_this_week": week_bounds(today)[0] == start,
        "previous_week": (start - timedelta(days=7)).isoformat(),
        "next_week": (start + timedelta(days=7)).isoformat(),
        "hub": {
            "name": region.hub_name,
            "address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        },
        "dropoffs": dropoffs,
        "deliveries": deliveries,
        "direct_payments": direct_payments,
        "counts": {
            "dropoffs": len(dropoffs),
            "deliveries": len(deliveries),
            "direct_payments": len(direct_payments),
            "awaiting_confirmation": sum(
                1 for g in deliveries if not g["confirmed"] and g["status"] == "scheduled"
            ),
            "needs_reschedule": sum(
                1 for g in deliveries if "needs_reschedule" in g["window_responses"]
            ),
        },
    }


@router.post("/pledge-status")
def update_status(body: StatusClick) -> dict:
    """Move one or more pledges, and their wishes with them.

    A missed drop-off puts the wish back on the wall as `open`, so another
    donor can grant it rather than the family quietly going without.
    """
    if not body.pledge_ids:
        raise HTTPException(status_code=422, detail="No pledge given.")

    updated = []
    with db.connect() as conn:
        for pledge_id in body.pledge_ids:
            pledge = db.set_pledge_status(conn, pledge_id, body.status)
            if pledge is None:
                raise HTTPException(
                    status_code=404, detail=f"No pledge with id {pledge_id}."
                )
            wish = db.get_request(conn, pledge.request_id)
            updated.append({
                "pledge_id": pledge_id,
                "pledge_status": pledge.status.value,
                "wish_id": pledge.request_id,
                "wish_status": wish.status.value if wish else None,
            })
        conn.commit()

    reopened = [u["wish_id"] for u in updated if u["wish_status"] == "open"]
    return {
        "updated": updated,
        "reopened_wishes": reopened,
        "note": (
            f"{text.counted(len(reopened), 'wish', 'wishes')} went back on the "
            f"tree for another neighbor."
            if reopened else ""
        ),
    }


class ResetRequest(BaseModel):
    alias: str


@router.post("/reset-password")
def reset_password(body: ResetRequest) -> dict:
    """Issue a one-time code so somebody can set a new password.

    No email is sent, because Wishing Tree sends none: a coordinator reads
    the code out, or hands it over on delivery day. Staff never see or choose
    the password itself — the code only buys the chance to set one, it expires
    within the hour, and it works once.
    """
    alias = body.alias.strip()
    with db.connect() as conn:
        table = "families" if alias.startswith("Neighbor") else "donors"
        row = conn.execute(
            f"SELECT contact_email FROM {table} WHERE alias = ?", (alias,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404, detail=f"We couldn't find a neighbor with the alias {alias!r}.")
        email = row["contact_email"].lower()
        if not accounts.account_exists(conn, email):
            raise HTTPException(
                status_code=409,
                detail=f"{alias} has no login yet, so there is no password to reset.",
            )
        code = accounts.issue_reset_code(conn, email)
        conn.commit()

    return {
        "alias": alias,
        "code": code,
        "expires_in_minutes": int(accounts.RESET_TTL.total_seconds() // 60),
        "how": ("Read this code out to them. They go to Log in, choose "
                "“Forgot your password?”, and set a new one with it. "
                "It works once and expires within the hour."),
    }
