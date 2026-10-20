"""Intake endpoints: the chat, the approval screen, and the token panel.

Conversation history lives in memory for the life of the server process. That
is enough for the MVP — an intake is one sitting — and it keeps the family's
words out of the database, where only the approved, neutrally written wishes
end up.

The first message is a fixed greeting rather than a model call. It would cost
a full turn to have the agent say hello, and it would say roughly the same
thing every time.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage

from backend import config, db
from backend.agents.intake import IntakeDeps, _price_guide, run_turn
from backend.models import (
    DraftWish,
    IntakeSession,
    IntakeStatus,
    Request,
    RequestStatus,
    RequestType,
)

router = APIRouter(prefix="/api/intake")

GREETING = (
    "Hi — I'm here to help you put together your wishes. "
    "Tell me what's going on and what would help most right now. "
    "You don't need to share your address, phone number or anyone's name here."
)

LIMIT_MESSAGE = (
    "We've covered a lot here, so I'll stop and put together what we have. "
    "You can look through the wishes on the next screen, change anything that "
    "isn't right, and start a new chat later if you need to add more."
)

WISH_CAP_MESSAGE = (
    "You already have {used} wishes on the wall, which is the most we can show "
    "at once ({cap}). Once one of them is granted, come back and we'll add the "
    "next one."
)

# session_id -> conversation so far
_HISTORY: dict[str, list[ModelMessage]] = {}


# --------------------------------------------------------------------------
# Request / response bodies
# --------------------------------------------------------------------------

class StartIntake(BaseModel):
    family_alias: str


class IntakeMessage(BaseModel):
    session_id: str
    message: str


class ApproveIntake(BaseModel):
    session_id: str
    wishes: list[DraftWish]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{config.INTAKE_SESSION_PREFIX}-{stamp}-{uuid.uuid4().hex[:6]}"


def _family_or_404(alias: str):
    with db.connect() as conn:
        family = db.get_family(conn, alias)
    if family is None:
        raise HTTPException(status_code=404, detail=f"No family with alias {alias!r}.")
    return family


def _session_or_404(session_id: str) -> IntakeSession:
    with db.connect() as conn:
        session = db.get_intake_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="That intake session has expired.")
    return session


def _usage(session_id: str) -> dict:
    with db.connect() as conn:
        usage = db.session_usage(conn, session_id)
    usage["prices_are_placeholders"] = config.PRICES_ARE_PLACEHOLDERS
    usage["model"] = config.MODEL_NAME
    return usage


def _category_range(category: str) -> tuple[float, float] | None:
    entries = [e for e in _price_guide() if e["category"] == category]
    if not entries:
        return None
    return (
        min(e["range_usd"][0] for e in entries),
        max(e["range_usd"][1] for e in entries),
    )


def _to_request(draft: DraftWish, family_alias: str, zip_code: str) -> Request:
    """Turn an approved draft into a storable wish, filling only what is missing.

    Nothing here invents a detail the family might disagree with: a missing
    deadline becomes 30 days out, and a missing cost becomes the price guide's
    range for that category. Both are visible and editable on the approval
    screen before this runs.
    """
    kind = draft.request_type
    link = draft.product_link
    if kind is RequestType.SPECIFIC and not link:
        kind = RequestType.FLEXIBLE        # a specific wish with no link is flexible
    if kind is RequestType.FLEXIBLE:
        link = None

    low, high = draft.budget_min_usd, draft.budget_max_usd
    if draft.estimated_cost_usd is None and low is None and high is None:
        fallback = _category_range(draft.category.value)
        if fallback:
            low, high = fallback

    return Request(
        family_alias=family_alias,
        category=draft.category,
        request_type=kind,
        item_description=draft.item_description,
        deadline=draft.deadline or (date.today() + timedelta(days=30)),
        occasion=draft.occasion,
        zip=zip_code,
        status=RequestStatus.PENDING_REVIEW,
        estimated_cost_usd=draft.estimated_cost_usd,
        budget_min_usd=low,
        budget_max_usd=high,
        product_link=link,
        brand=draft.brand if kind is RequestType.SPECIFIC else None,
        size=draft.size,
        color=draft.color if kind is RequestType.SPECIFIC else None,
        open_to_substitute=draft.open_to_substitute,
        size_preferences=draft.size_preferences,
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.post("/start", status_code=201)
def start_intake(body: StartIntake) -> dict:
    family = _family_or_404(body.family_alias)

    with db.connect() as conn:
        used = db.open_wish_count(conn, family.alias)
    cap = config.MAX_OPEN_WISHES_PER_FAMILY
    if used >= cap:
        return {
            "session_id": None,
            "message": WISH_CAP_MESSAGE.format(used=used, cap=cap),
            "at_wish_cap": True,
            "open_wishes": used,
            "maximum": cap,
        }

    session = IntakeSession(session_id=_new_session_id(), family_alias=family.alias)
    with db.connect() as conn:
        db.insert_intake_session(session, conn)
        conn.commit()
    _HISTORY[session.session_id] = []

    return {
        "session_id": session.session_id,
        "message": GREETING,
        "at_wish_cap": False,
        "open_wishes": used,
        "maximum": cap,
        "turns_remaining": config.MAX_INTAKE_TURNS,
        "usage": _usage(session.session_id),
    }


@router.post("/message")
async def intake_message(body: IntakeMessage) -> dict:
    session = _session_or_404(body.session_id)
    if session.status is not IntakeStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="This intake is already finished.")

    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Say something first.")
    if len(text) > config.MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"That message is longer than {config.MAX_MESSAGE_CHARS} characters. "
                   "Could you shorten it?",
        )

    # The turn cap is enforced before any model call, so hitting it costs nothing.
    if session.turns >= config.MAX_INTAKE_TURNS:
        session.status = IntakeStatus.LIMIT_REACHED
        with db.connect() as conn:
            db.update_intake_session(session, conn)
            conn.commit()
        return {
            "message": LIMIT_MESSAGE,
            "draft_wishes": [],
            "done": True,
            "limit_reached": True,
            "turns_used": session.turns,
            "turns_remaining": 0,
            "usage": _usage(session.session_id),
        }

    family = _family_or_404(session.family_alias)
    deps = IntakeDeps(
        family_alias=family.alias,
        family_id=family.id or 0,
        session_id=session.session_id,
    )

    try:
        reply, history, _call = await run_turn(
            deps, text, _HISTORY.get(session.session_id, [])
        )
    except Exception as exc:                       # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail="The assistant could not answer just then. Please try again.",
        ) from exc

    _HISTORY[session.session_id] = history
    session.turns += 1
    with db.connect() as conn:
        db.update_intake_session(session, conn)
        conn.commit()

    return {
        "message": reply.message,
        "draft_wishes": [w.model_dump(mode="json") for w in reply.draft_wishes],
        "done": reply.done,
        "limit_reached": False,
        "turns_used": session.turns,
        "turns_remaining": max(0, config.MAX_INTAKE_TURNS - session.turns),
        "blocked_lookups": deps.blocked_lookups,
        "usage": _usage(session.session_id),
    }


@router.post("/approve")
def approve_intake(body: ApproveIntake) -> dict:
    session = _session_or_404(body.session_id)
    family = _family_or_404(session.family_alias)

    with db.connect() as conn:
        used = db.open_wish_count(conn, family.alias)
    remaining = max(0, config.MAX_OPEN_WISHES_PER_FAMILY - used)
    if len(body.wishes) > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"You can post {remaining} more wish(es) right now. "
                   f"Please remove some before approving.",
        )

    saved = []
    with db.connect() as conn:
        for draft in body.wishes:
            request = _to_request(draft, family.alias, family.zip)
            request.id = db.insert_request(request, conn)
            saved.append(request)

        session.approved_at = datetime.now(timezone.utc)
        session.status = IntakeStatus.APPROVED
        session.duration_seconds = (
            session.approved_at - session.started_at
        ).total_seconds()
        db.update_intake_session(session, conn)
        conn.commit()

    _HISTORY.pop(session.session_id, None)

    return {
        "approved": len(saved),
        "status": RequestStatus.PENDING_REVIEW.value,
        "duration_seconds": round(session.duration_seconds, 1),
        "turns_used": session.turns,
        "wishes": [r.model_dump(mode="json") for r in saved],
        "usage": _usage(session.session_id),
    }


@router.get("/usage/{session_id}")
def intake_usage(session_id: str) -> dict:
    return _usage(session_id)
