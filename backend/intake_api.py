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
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage

from backend import config, db, text
from backend.agents import budget, safety
from backend.agents.budget import BudgetExceeded
from backend.agents.intake import IntakeDeps, _price_guide, run_turn
from backend.models import (
    DraftWish,
    Request,
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
    """Turn an approved draft into a storable wish.

    A missing deadline stays missing. Giving a wish a date the family never
    said would break the rule the whole intake runs on, and would hand the
    Matchmaker urgency that nobody asked for.

    A missing cost is filled from the price guide, because a donor needs some
    idea of the amount — but it is marked `cost_is_estimate`, so every screen
    can say so, and the family can type over it on the approval screen first.
    """
    kind = draft.request_type
    link = draft.product_link
    if kind is RequestType.SPECIFIC and not link:
        kind = RequestType.FLEXIBLE        # a specific wish with no link is flexible
    if kind is RequestType.FLEXIBLE:
        link = None

    low, high = draft.budget_min_usd, draft.budget_max_usd
    estimated = False
    if draft.estimated_cost_usd is None and low is None and high is None:
        fallback = _category_range(draft.category.value)
        if fallback:
            low, high = fallback
            estimated = True

    return Request(
        family_alias=family_alias,
        category=draft.category,
        request_type=kind,
        item_description=draft.item_description,
        deadline=draft.deadline,
        occasion=draft.occasion,
        zip=zip_code,
        status=RequestStatus.PENDING_REVIEW,
        estimated_cost_usd=draft.estimated_cost_usd,
        budget_min_usd=low,
        budget_max_usd=high,
        cost_is_estimate=estimated,
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
    except BudgetExceeded as limit:
        session.status = IntakeStatus.LIMIT_REACHED
        with db.connect() as conn:
            db.update_intake_session(session, conn)
            conn.commit()
        return {
            "message": limit.friendly,
            "draft_wishes": [],
            "done": True,
            "limit_reached": True,
            "budget_scope": limit.scope,
            "turns_used": session.turns,
            "turns_remaining": 0,
            "usage": _usage(session.session_id),
        }
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
async def approve_intake(body: ApproveIntake) -> dict:
    session = _session_or_404(body.session_id)
    family = _family_or_404(session.family_alias)

    with db.connect() as conn:
        used = db.open_wish_count(conn, family.alias)
    remaining = max(0, config.MAX_OPEN_WISHES_PER_FAMILY - used)
    if len(body.wishes) > remaining:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You can post {text.counted(remaining, 'more wish', 'more wishes')} "
                f"right now. Please remove "
                f"{text.plural(len(body.wishes) - remaining, 'one', 'some')} "
                f"before approving."
                if remaining
                else "You have as many wishes on the wall as we can show at once. "
                     "Once one of them is granted, come back and add the next."
            ),
        )

    saved = []
    with db.connect() as conn:
        for draft in body.wishes:
            request = _to_request(draft, family.alias, family.zip)
            request.id = db.insert_request(request, conn)
            saved.append(request)
        conn.commit()

    # Every approved wish goes through the Privacy & Safety agent before anyone
    # else can see it. A review that fails leaves the wish hidden, which is the
    # safe direction to fail in.
    outcomes = []
    for request in saved:
        outcomes.append(await _review_and_publish(request, session.session_id))

    with db.connect() as conn:
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
        "published": sum(1 for o in outcomes if o["published"]),
        "held": sum(1 for o in outcomes if not o["published"]),
        "duration_seconds": round(session.duration_seconds, 1),
        "turns_used": session.turns,
        "outcomes": outcomes,
        "usage": _usage(session.session_id),
        "budget": budget.status(session.session_id),
    }


@router.get("/usage/{session_id}")
def intake_usage(session_id: str) -> dict:
    return _usage(session_id)


# --------------------------------------------------------------------------
# Publishing, which only happens through the safety review
# --------------------------------------------------------------------------

async def _review_and_publish(request: Request, session_id: str) -> dict:
    """Review one wish, then publish it or leave it hidden.

    There is no other path to `open`. A wish becomes public here or not at all,
    and every outcome — including a failed review — is recorded.
    """
    try:
        review, enforced, _call = await safety.review_wish(request, session_id)
    except BudgetExceeded as limit:
        # Written for this moment, not reused from the chat: by now the family
        # has approved, and what is waiting is the review, not more talking.
        return {
            "request_id": request.id,
            "published": False,
            "description": request.item_description,
            "removed": [],
            "flags": [],
            "enforced": [],
            "note_to_family": (
                "Wishing Tree has reached its daily limit for AI usage, so the "
                "safety check on this one has to wait. Your wish is saved and "
                "nothing is lost — it will go up once the limit resets."
            ),
            "budget_scope": limit.scope,
        }
    except Exception:                               # noqa: BLE001
        return {
            "request_id": request.id,
            "published": False,
            "description": request.item_description,
            "removed": [],
            "flags": [],
            "enforced": [],
            "note_to_family": (
                "We could not finish the safety check on this one just now. "
                "It is saved and a coordinator will look at it."
            ),
        }

    cleaned = safety.apply_to_request(request, review)
    cleaned.status = (
        RequestStatus.OPEN if review.approved else RequestStatus.PENDING_REVIEW
    )

    with db.connect() as conn:
        db.update_request_content(conn, cleaned)
        db.insert_safety_review(
            conn,
            request_id=request.id,
            approved=review.approved,
            removed=review.removed,
            flags=[f.model_dump(mode="json") for f in review.flags],
            enforced=enforced,
            note_to_family=review.note_to_family,
            session_id=session_id,
        )
        conn.commit()

    return {
        "request_id": request.id,
        "published": review.approved,
        "description": cleaned.item_description,
        "removed": review.removed,
        "flags": [f.model_dump(mode="json") for f in review.flags],
        "enforced": enforced,
        "note_to_family": review.note_to_family,
    }
