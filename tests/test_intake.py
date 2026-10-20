"""The intake pipeline: limits, drafting, approval, and the audit trail.

These tests never call the model. The agent is replaced with a stub so the
rules around it — turn caps, wish caps, what gets stored, what gets logged —
can be checked quickly and without spending tokens. The two end-to-end intakes
against the real model are recorded in harness.md and screenshots/.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend import config, db, intake_api, main, seed
from backend.agents import audit, intake, safety
from backend.models import (
    AgentCallLog,
    Category,
    CleanedWish,
    DraftWish,
    IntakeStatus,
    Occasion,
    RequestStatus,
    RequestType,
    SafetyReview,
)


def _stub_review(approved: bool = True):
    """Stands in for the Privacy & Safety agent, so approving costs nothing."""
    async def fake(request, session_id):
        call = AgentCallLog(
            agent="safety", model=config.MODEL_NAME, operation="review_wish",
            session_id=session_id, request_id=request.id,
            input_tokens=50, cached_input_tokens=800, output_tokens=40, latency_ms=5,
        )
        audit.record(call)
        review = SafetyReview(
            approved=approved,
            cleaned=CleanedWish(item_description=request.item_description,
                                size=request.size, product_link=request.product_link),
            removed=[], flags=[],
            note_to_family="Looks good." if approved else "Held for a coordinator.",
        )
        return review, [], call
    return fake


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
    monkeypatch.setattr(safety, "review_wish", _stub_review(True))
    seed.seed(config.DB_PATH)
    intake_api._HISTORY.clear()
    return TestClient(main.app)


def _stub_turn(message: str, wishes: list[DraftWish], done: bool = False):
    """Stands in for the model: same signature, no network."""
    async def fake(deps, text, history=None):
        call = AgentCallLog(
            agent="intake", model=config.MODEL_NAME, operation="draft_wishes",
            session_id=deps.session_id, input_tokens=100,
            cached_input_tokens=900, output_tokens=50, latency_ms=10,
            tools_called=["get_categories_and_occasions"],
            estimated_cost_usd=config.estimate_cost_usd(100, 900, 50),
        )
        audit.record(call)
        from backend.models import IntakeReply
        return IntakeReply(message=message, draft_wishes=wishes, done=done), [], call
    return fake


COAT = DraftWish(
    category=Category.CLOTHING,
    request_type=RequestType.FLEXIBLE,
    item_description="Winter coat for an 8-year-old, for walking to school.",
    occasion=Occasion.EVERYDAY,
    size="Boys 8",
)


# --------------------------------------------------------------------------
# The agent is never handed contact details
# --------------------------------------------------------------------------

def test_the_agent_deps_carry_no_address_or_phone():
    """Structural guarantee: there is nowhere to put them."""
    fields = set(intake.IntakeDeps.__dataclass_fields__)
    assert fields == {"family_alias", "family_id", "session_id", "blocked_lookups"}


def test_a_family_address_never_appears_in_the_agent_prompt():
    prompt = intake.system_prompt()
    assert "address" in prompt.lower()          # it is mentioned as forbidden
    assert "Larkspur" not in prompt             # no seeded address is in it


# --------------------------------------------------------------------------
# Starting an intake
# --------------------------------------------------------------------------

def test_start_creates_a_session_and_greets_without_a_model_call(client):
    body = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()
    assert body["session_id"].startswith("intake-")
    assert body["at_wish_cap"] is False
    assert body["usage"]["calls"] == 0        # the greeting is free


def test_a_family_at_the_wish_cap_cannot_start(client):
    """Family A07 has four open wishes; add one more and the cap is reached."""
    with db.connect(config.DB_PATH) as conn:
        extra = db.list_requests(conn)[0]
        extra.family_alias = "Family A07"
        extra.status = RequestStatus.OPEN
        db.insert_request(extra, conn)
        conn.commit()
        assert db.open_wish_count(conn, "Family A07") == config.MAX_OPEN_WISHES_PER_FAMILY

    body = client.post("/api/intake/start", json={"family_alias": "Family A07"}).json()
    assert body["at_wish_cap"] is True
    assert body["session_id"] is None
    assert "most we can show" in body["message"]


def test_an_unknown_family_is_404(client):
    assert client.post("/api/intake/start", json={"family_alias": "Nobody"}).status_code == 404


# --------------------------------------------------------------------------
# Chatting
# --------------------------------------------------------------------------

def test_a_turn_returns_drafts_and_counts_tokens(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]

    turn = client.post("/api/intake/message",
                       json={"session_id": session_id, "message": "He needs a coat."}).json()
    assert turn["done"] is True
    assert len(turn["draft_wishes"]) == 1
    assert turn["turns_used"] == 1
    assert turn["turns_remaining"] == config.MAX_INTAKE_TURNS - 1
    assert turn["usage"]["calls"] == 1
    assert turn["usage"]["cached_input_tokens"] == 900


def test_the_turn_cap_stops_the_chat_without_spending_a_call(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("ok", []))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]

    with db.connect(config.DB_PATH) as conn:
        session = db.get_intake_session(conn, session_id)
        session.turns = config.MAX_INTAKE_TURNS
        db.update_intake_session(session, conn)
        conn.commit()

    turn = client.post("/api/intake/message",
                       json={"session_id": session_id, "message": "one more"}).json()
    assert turn["limit_reached"] is True
    assert turn["usage"]["calls"] == 0          # no model call was made
    assert "put together what we have" in turn["message"]


def test_an_overlong_message_is_refused(client):
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    response = client.post("/api/intake/message",
                           json={"session_id": session_id, "message": "x" * 2001})
    assert response.status_code == 422


def test_an_expired_session_is_404(client):
    response = client.post("/api/intake/message",
                           json={"session_id": "intake-nope", "message": "hello"})
    assert response.status_code == 404


# --------------------------------------------------------------------------
# Approval
# --------------------------------------------------------------------------

def test_approval_publishes_through_the_safety_review(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "coat"})

    body = client.post("/api/intake/approve", json={
        "session_id": session_id, "wishes": [COAT.model_dump(mode="json")],
    }).json()

    assert body["approved"] == 1
    assert body["published"] == 1
    assert body["held"] == 0
    assert body["duration_seconds"] >= 0
    assert body["outcomes"][0]["note_to_family"]

    new_id = body["outcomes"][0]["request_id"]
    with db.connect(config.DB_PATH) as conn:
        stored = [r for r in db.list_requests(conn) if r.id == new_id][0]
        session = db.get_intake_session(conn, session_id)
    assert stored.status is RequestStatus.OPEN            # published by the review
    assert stored.zip == "06511"                          # taken from the family record
    assert session.status is IntakeStatus.APPROVED
    assert session.duration_seconds is not None


def test_a_rejected_wish_stays_hidden_and_the_family_is_told_why(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    monkeypatch.setattr(safety, "review_wish", _stub_review(False))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "coat"})

    body = client.post("/api/intake/approve", json={
        "session_id": session_id, "wishes": [COAT.model_dump(mode="json")],
    }).json()

    assert body["published"] == 0 and body["held"] == 1
    assert "coordinator" in body["outcomes"][0]["note_to_family"].lower()

    new_id = body["outcomes"][0]["request_id"]
    with db.connect(config.DB_PATH) as conn:
        stored = [r for r in db.list_requests(conn) if r.id == new_id][0]
    assert stored.status is RequestStatus.PENDING_REVIEW   # still hidden


def test_a_wish_is_never_public_before_the_review_runs(client, monkeypatch):
    """Approving stores it; only the safety review can make it open."""
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "coat"})

    seen: list[str] = []

    async def failing_review(request, session_id):
        with db.connect(config.DB_PATH) as conn:
            stored = [r for r in db.list_requests(conn) if r.id == request.id][0]
        seen.append(stored.status.value)
        raise RuntimeError("reviewer unavailable")

    monkeypatch.setattr(safety, "review_wish", failing_review)
    body = client.post("/api/intake/approve", json={
        "session_id": session_id, "wishes": [COAT.model_dump(mode="json")],
    }).json()

    assert seen == ["pending_review"]        # not public while being reviewed
    assert body["published"] == 0            # and a failed review publishes nothing


def test_approving_more_than_the_cap_is_refused(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("ok", [COAT]))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    too_many = [COAT.model_dump(mode="json")] * 6
    response = client.post("/api/intake/approve",
                           json={"session_id": session_id, "wishes": too_many})
    assert response.status_code == 409


# --------------------------------------------------------------------------
# Draft -> Request conversion
# --------------------------------------------------------------------------

def test_a_missing_deadline_stays_missing():
    """Never make up a detail. No date given means no date stored."""
    request = intake_api._to_request(COAT, "Family A04", "06511")
    assert request.deadline is None
    assert request.deadline_label() == "No deadline"
    assert request.days_until_deadline() is None


def test_a_deadline_the_family_gave_is_kept():
    draft = COAT.model_copy(update={"deadline": date(2026, 12, 1)})
    request = intake_api._to_request(draft, "Family A04", "06511")
    assert request.deadline == date(2026, 12, 1)
    assert request.deadline_label() == "2026-12-01"


def test_a_missing_cost_is_filled_from_the_price_guide_and_marked_as_an_estimate():
    request = intake_api._to_request(COAT, "Family A04", "06511")
    assert request.budget_min_usd is not None and request.budget_max_usd is not None
    assert request.cost_is_estimate is True


def test_a_cost_the_family_gave_is_not_marked_as_an_estimate():
    draft = COAT.model_copy(update={"estimated_cost_usd": 30.0})
    request = intake_api._to_request(draft, "Family A04", "06511")
    assert request.estimated_cost_usd == 30.0
    assert request.cost_is_estimate is False


def test_a_specific_wish_with_no_link_becomes_flexible():
    draft = COAT.model_copy(update={"request_type": RequestType.SPECIFIC, "product_link": None})
    assert intake_api._to_request(draft, "Family A04", "06511").request_type is RequestType.FLEXIBLE


def test_a_specific_wish_keeps_its_link():
    draft = COAT.model_copy(update={
        "request_type": RequestType.SPECIFIC,
        "product_link": "https://www.target.com/p/coat/-/A-1",
        "estimated_cost_usd": 45.0,
    })
    request = intake_api._to_request(draft, "Family A04", "06511")
    assert request.request_type is RequestType.SPECIFIC
    assert request.product_link.startswith("https://www.target.com")


# --------------------------------------------------------------------------
# Price guide matching
# --------------------------------------------------------------------------

@pytest.mark.parametrize("probe,expected", [
    ("boys winter coat", "children's winter coat"),
    ("work shoes", "work shoes, non-slip"),
    ("backpack for school", "backpack"),
    ("diapers", "diapers, one month"),
])
def test_family_wording_finds_the_right_price_guide_entry(probe, expected):
    entries = intake._price_guide()
    best = max(entries, key=lambda e: intake._match_score(probe, e["item"]))
    assert best["item"] == expected


def test_nonsense_does_not_match_anything():
    entries = [e for e in intake._price_guide() if e["category"] == "clothing"]
    best = max(intake._match_score("xylophone repair", e["item"]) for e in entries)
    assert best < 0.45


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------

def test_every_call_is_written_to_the_trail_and_the_table(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("ok", [COAT]))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "hello"})

    rows = audit.read_all(config.AUDIT_PATH)
    assert len(rows) == 1
    assert rows[0]["session_id"] == session_id
    assert rows[0]["agent"] == "intake"
    assert rows[0]["total_tokens"] == 1050

    with db.connect(config.DB_PATH) as conn:
        calls = db.list_agent_calls(conn, session_id)
    assert len(calls) == 1
    assert calls[0]["cached_input_tokens"] == 900


def test_the_trail_separates_cached_from_uncached_input(client, monkeypatch):
    """They are priced differently, so they are never summed into one number."""
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("ok", []))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "hi"})

    usage = client.get(f"/api/intake/usage/{session_id}").json()
    assert usage["input_tokens"] == 100
    assert usage["cached_input_tokens"] == 900
    assert usage["prices_are_placeholders"] is True


def test_the_trail_is_append_only(tmp_path):
    path = tmp_path / "trail.json"
    for i in range(3):
        audit.append_jsonl({"n": i}, path)
    assert [r["n"] for r in audit.read_all(path)] == [0, 1, 2]
