"""The intake pipeline: limits, drafting, approval, and the audit trail.

These tests never call the model. The agent is replaced with a stub so the
rules around it — turn caps, wish caps, what gets stored, what gets logged —
can be checked quickly and without spending tokens. The two end-to-end intakes
against the real model are recorded in harness.md and screenshots/.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import config, db, intake_api, main, seed
from backend.agents import audit, intake
from backend.models import (
    AgentCallLog,
    Category,
    DraftWish,
    IntakeStatus,
    Occasion,
    RequestStatus,
    RequestType,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
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

def test_approval_stores_wishes_as_pending_review(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "coat"})

    body = client.post("/api/intake/approve", json={
        "session_id": session_id, "wishes": [COAT.model_dump(mode="json")],
    }).json()

    assert body["approved"] == 1
    assert body["status"] == "pending_review"
    assert body["duration_seconds"] >= 0

    with db.connect(config.DB_PATH) as conn:
        stored = [r for r in db.list_requests(conn, RequestStatus.PENDING_REVIEW)
                  if r.family_alias == "Family A04"]
        session = db.get_intake_session(conn, session_id)
    assert len(stored) == 1
    assert stored[0].zip == "06511"                       # taken from the family record
    assert session.status is IntakeStatus.APPROVED
    assert session.duration_seconds is not None


def test_nothing_goes_public_at_this_stage(client, monkeypatch):
    monkeypatch.setattr(intake_api, "run_turn", _stub_turn("Got it.", [COAT], done=True))
    session_id = client.post("/api/intake/start", json={"family_alias": "Family A04"}).json()["session_id"]
    client.post("/api/intake/message", json={"session_id": session_id, "message": "coat"})

    with db.connect(config.DB_PATH) as conn:
        before = len(db.list_requests(conn, RequestStatus.OPEN))
    client.post("/api/intake/approve", json={
        "session_id": session_id, "wishes": [COAT.model_dump(mode="json")],
    })
    with db.connect(config.DB_PATH) as conn:
        after = len(db.list_requests(conn, RequestStatus.OPEN))
    assert before == after


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

def test_a_missing_deadline_becomes_thirty_days_out():
    request = intake_api._to_request(COAT, "Family A04", "06511")
    assert request.deadline == date.today() + timedelta(days=30)


def test_a_missing_cost_is_filled_from_the_price_guide():
    request = intake_api._to_request(COAT, "Family A04", "06511")
    assert request.budget_min_usd is not None and request.budget_max_usd is not None


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
