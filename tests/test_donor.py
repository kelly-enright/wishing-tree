"""The donor side: the wall, the schedule, ranking, and claiming a wish.

The Matchmaker's judgment is not tested here — the recorded end-to-end run in
harness.md is the evidence for that. What is tested is everything that has to
hold whatever it answers: what a donor can see, what the schedule says, what
the code throws away, and what happens when two donors want the same wish.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import config, db, donor_api, main, scheduling, seed
from backend.agents import matchmaker
from backend.agents.matchmaker import MatchDeps
from backend.models import (
    Category,
    MatchmakerResult,
    Occasion,
    Request,
    RequestStatus,
    RequestType,
    WishMatch,
)

TUESDAY = date(2026, 10, 20)        # the week these tests reason about


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
    seed.seed(config.DB_PATH)
    return TestClient(main.app)


# --------------------------------------------------------------------------
# The weekly schedule
# --------------------------------------------------------------------------

def test_the_next_dropoff_is_the_coming_thursday():
    assert scheduling.next_dropoff(TUESDAY) == date(2026, 10, 22)


def test_todays_own_window_is_never_offered():
    """A donor reading this on Thursday evening cannot make Thursday."""
    thursday = date(2026, 10, 22)
    assert scheduling.next_dropoff(thursday) == date(2026, 10, 29)


def test_a_dropoff_is_delivered_the_following_saturday():
    assert scheduling.delivery_for(date(2026, 10, 22)) == date(2026, 10, 24)


def test_the_latest_dropoff_that_still_makes_a_deadline_is_chosen():
    """Not the soonest — the latest that still arrives, so donors have time."""
    result = scheduling.dropoff_before(date(2026, 11, 21), TUESDAY)
    assert result["dropoff_date"] == "2026-11-19"
    assert result["delivery_date"] == "2026-11-21"
    assert result["arrives_in_time"] is True


def test_no_deadline_is_not_treated_as_urgent():
    result = scheduling.dropoff_before(None, TUESDAY)
    assert result["time_sensitive"] is False
    assert result["arrives_in_time"] is True
    assert "no deadline" in result["reason"]


def test_a_deadline_nothing_can_reach_is_said_plainly():
    result = scheduling.dropoff_before(date(2026, 10, 21), TUESDAY)
    assert result["arrives_in_time"] is False
    assert result["dropoff_date"] == "2026-10-22"      # offered anyway
    assert "no drop-off can arrive" in result["reason"]


def test_the_schedule_comes_from_region_config():
    region = config.get_region()
    result = scheduling.dropoff_before(None, TUESDAY, region)
    assert result["hub_name"] == region.hub_name
    assert result["dropoff_window"] == region.dropoff_window.label()


# --------------------------------------------------------------------------
# The wish wall
# --------------------------------------------------------------------------

def test_the_wall_shows_only_open_wishes(client):
    body = client.get("/api/wishes").json()
    assert body["count"] > 0
    assert {w["status"] for w in body["wishes"]} == {"open"}


def test_the_wall_carries_no_contact_details(client):
    text = client.get("/api/wishes").text
    with db.connect(config.DB_PATH) as conn:
        families = db.list_families(conn)
    for family in families:
        assert family.contact_address not in text
        assert family.contact_email not in text
        if family.contact_phone:
            assert family.contact_phone not in text
    assert "contact_address" not in text
    assert "contact_email" not in text
    assert "555-" not in text
    assert "@example.com" not in text


def test_filters_narrow_the_wall(client):
    everything = client.get("/api/wishes").json()["count"]
    clothing = client.get("/api/wishes?category=clothing").json()
    assert 0 < clothing["count"] < everything
    assert {w["category"] for w in clothing["wishes"]} == {"clothing"}

    cheap = client.get("/api/wishes?max_cost_usd=50").json()
    assert all(w["cost_ceiling_usd"] <= 50 for w in cheap["wishes"])

    specific = client.get("/api/wishes?request_type=specific").json()
    assert {w["request_type"] for w in specific["wishes"]} == {"specific"}


def test_wishes_without_a_deadline_sort_last_on_the_wall(client):
    with db.connect(config.DB_PATH) as conn:
        db.insert_request(
            Request(family_alias="Neighbor A04", category=Category.OTHER,
                    request_type=RequestType.FLEXIBLE, item_description="No date given.",
                    occasion=Occasion.EVERYDAY, zip="06511", budget_min_usd=20.0,
                    status=RequestStatus.OPEN),
            conn,
        )
        conn.commit()
    wishes = client.get("/api/wishes").json()["wishes"]
    assert wishes[-1]["deadline"] is None
    assert wishes[-1]["deadline_label"] == "No deadline"
    assert wishes[-1]["days_until_deadline"] is None


def test_a_card_reports_waiting_time_for_fair_ranking(client):
    wishes = client.get("/api/wishes").json()["wishes"]
    assert all(w["days_waiting"] >= 0 for w in wishes)


# --------------------------------------------------------------------------
# The candidate limit
# --------------------------------------------------------------------------

def test_the_candidate_limit_caps_what_the_search_tool_returns(client, monkeypatch):
    monkeypatch.setattr(config, "MATCHMAKER_CANDIDATE_LIMIT", 3)
    with db.connect(config.DB_PATH) as conn:
        found = db.list_open_wishes(conn, limit=config.MATCHMAKER_CANDIDATE_LIMIT)
    assert len(found) == 3


def test_the_limit_can_be_turned_off_to_pass_every_open_wish(client, monkeypatch):
    monkeypatch.setattr(config, "MATCHMAKER_CANDIDATE_LIMIT", None)
    with db.connect(config.DB_PATH) as conn:
        everything = db.list_open_wishes(conn, limit=None)
        total = len(db.list_requests(conn, RequestStatus.OPEN))
    assert len(everything) == total


# --------------------------------------------------------------------------
# What the code throws away after the Matchmaker answers
# --------------------------------------------------------------------------

def _match(request_id: int) -> WishMatch:
    return WishMatch(
        request_id=request_id, reason="within budget",
        dropoff_date=date(2026, 10, 22), delivery_date=date(2026, 10, 24),
    )


def test_a_wish_the_search_never_returned_is_dropped(client):
    deps = MatchDeps(donor_alias="Granter D01", session_id="s", candidate_ids=[1, 2])
    result = MatchmakerResult(matches=[_match(1), _match(999)])
    final, enforced = matchmaker.enforce(result, deps)

    assert [m.request_id for m in final.matches] == [1]
    assert any("not in the search results" in e for e in enforced)


def test_a_wish_claimed_while_the_model_was_thinking_is_dropped(client):
    with db.connect(config.DB_PATH) as conn:
        open_wish = db.list_open_wishes(conn, limit=1)[0]
        db.update_request_status(conn, open_wish.id, RequestStatus.GRANTED)
        conn.commit()

    deps = MatchDeps(donor_alias="Granter D01", session_id="s",
                     candidate_ids=[open_wish.id])
    final, enforced = matchmaker.enforce(MatchmakerResult(matches=[_match(open_wish.id)]), deps)

    assert final.matches == []
    assert any("no longer open" in e for e in enforced)


def test_more_than_five_matches_are_trimmed(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_MATCHES_RETURNED", 5)
    with db.connect(config.DB_PATH) as conn:
        ids = [w.id for w in db.list_open_wishes(conn, limit=7)]

    deps = MatchDeps(donor_alias="Granter D01", session_id="s", candidate_ids=ids)
    final, enforced = matchmaker.enforce(
        MatchmakerResult(matches=[_match(i) for i in ids]), deps
    )
    assert len(final.matches) == 5
    assert any("trimmed" in e for e in enforced)


def test_the_matchmaker_is_never_given_contact_details(client):
    """Its search tool returns the same card a donor sees, and nothing else."""
    with db.connect(config.DB_PATH) as conn:
        wish = db.list_open_wishes(conn, limit=1)[0]
        family = db.get_family(conn, wish.family_alias)
    card = str(wish.public_card())
    assert family.contact_address not in card
    assert family.contact_phone not in card


# --------------------------------------------------------------------------
# Granting
# --------------------------------------------------------------------------

def _first_open(client, category: str | None = None) -> dict:
    url = "/api/wishes" + (f"?category={category}" if category else "")
    return client.get(url).json()["wishes"][0]


def test_granting_locks_the_wish_and_creates_a_pledge(client):
    wish = _first_open(client)
    body = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()

    assert body["granted"] is True
    assert body["wish"]["status"] == "granted"

    with db.connect(config.DB_PATH) as conn:
        stored = db.get_request(conn, wish["id"])
        pledge = db.get_pledge_for_request(conn, wish["id"])
    assert stored.status is RequestStatus.GRANTED
    assert pledge is not None
    assert pledge.donor_alias == "Granter D01"
    assert pledge.delivery_date >= pledge.dropoff_date


def test_a_second_donor_cannot_claim_the_same_wish(client):
    wish = _first_open(client)
    first = client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": wish["id"]})
    second = client.post("/api/grant", json={"donor_alias": "Granter D02", "request_id": wish["id"]})

    assert first.status_code == 200
    assert second.status_code == 409
    assert "just granted this one" in second.json()["detail"]

    with db.connect(config.DB_PATH) as conn:
        pledges = [p for p in db.list_pledges(conn) if p.request_id == wish["id"]]
    assert len(pledges) == 1              # exactly one donor holds it


def test_a_granted_wish_leaves_the_wall(client):
    wish = _first_open(client)
    client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": wish["id"]})
    remaining = {w["id"] for w in client.get("/api/wishes").json()["wishes"]}
    assert wish["id"] not in remaining


def test_an_item_wish_goes_through_the_hub(client):
    wish = _first_open(client, "clothing")
    body = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()

    assert body["paid_directly_to_provider"] is False
    logistics = body["logistics"]
    assert logistics["kind"] == "hub_dropoff"
    assert logistics["hub_name"] == config.get_region().hub_name
    assert "165 Whitney Ave" in logistics["hub_address"]
    assert logistics["dropoff_window"] == config.get_region().dropoff_window.label()


def test_a_rent_wish_skips_the_hub_and_is_paid_to_the_provider(client):
    wish = _first_open(client, "rent_utilities")
    body = client.post("/api/grant", json={
        "donor_alias": "Granter D06", "request_id": wish["id"],
    }).json()

    assert body["paid_directly_to_provider"] is True
    logistics = body["logistics"]
    assert logistics["kind"] == "direct_payment"
    assert logistics["headline"] == "Paid straight to the provider (simulated)"
    assert "hub_address" not in logistics


def test_the_drop_off_offered_is_the_one_the_schedule_chose(client):
    wish = _first_open(client)
    expected = scheduling.dropoff_before(
        date.fromisoformat(wish["deadline"]) if wish["deadline"] else None
    )
    body = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    assert body["logistics"]["dropoff_date"] == expected["dropoff_date"]


def test_granting_a_missing_wish_is_404(client):
    response = client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": 99999})
    assert response.status_code == 404


def test_an_unknown_donor_cannot_grant(client):
    wish = _first_open(client)
    response = client.post("/api/grant", json={"donor_alias": "Nobody", "request_id": wish["id"]})
    assert response.status_code == 404


def test_a_donor_can_see_what_they_claimed(client):
    wish = _first_open(client)
    client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": wish["id"]})
    body = client.get("/api/donors/Granter D01/pledges").json()
    assert any(row["wish"]["id"] == wish["id"] for row in body["pledges"])


def test_a_donor_zip_means_their_region_not_their_postcode(client):
    """Donations all pass through one hub, so a donor can grant anywhere in
    the region. Matching zip-for-zip returned almost nothing."""
    region = config.region_for_zip("06511")
    with db.connect(config.DB_PATH) as conn:
        across_region = db.list_open_wishes(conn, zip_codes=region.zip_codes)
        same_postcode = db.list_open_wishes(conn, zip_code="06511")
    assert len(across_region) > len(same_postcode)


def test_the_service_area_is_new_haven_city_only(client):
    """Six city zips. The neighboring towns are a later expansion."""
    body = client.get("/api/service-area").json()
    assert body["zip_codes"] == ["06510", "06511", "06513", "06515", "06519", "06520"]
    assert "New Haven" in body["notice"]

    assert client.get("/api/service-area?zip=06511").json()["covered"] is True
    for outside in ("06512", "06514", "06516", "06517", "06518", "06525", "90210"):
        answer = client.get(f"/api/service-area?zip={outside}").json()
        assert answer["covered"] is False, outside
        assert "coming soon" in answer["message"]


def test_every_seeded_person_is_inside_the_service_area(client):
    region = config.get_region()
    with db.connect(config.DB_PATH) as conn:
        people = [*db.list_families(conn), *db.list_donors(conn)]
    outside = [p.alias for p in people if p.zip not in region.zip_codes]
    assert outside == []
