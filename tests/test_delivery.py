"""Delivery confirmation, the coordinator's run sheet, and the privacy line.

No agents in any of this. It is database logic, and it is tested as such.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import config, coordinator_auth, db, main, seed
from backend.coordinator_api import week_bounds
from backend.models import (
    Category,
    Occasion,
    Pledge,
    PledgeStatus,
    Request,
    RequestStatus,
    RequestType,
    WindowResponse,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
    seed.seed(config.DB_PATH)
    coordinator_auth.clear()
    return TestClient(main.app)


def _token(client) -> dict:
    token = client.post("/api/coordinator/unlock",
                        json={"passcode": config.COORDINATOR_PASSCODE}).json()["token"]
    return {"X-Coordinator-Token": token}


def _grant_first_open(client, donor="Donor D01", category: str | None = None) -> dict:
    url = "/api/wishes" + (f"?category={category}" if category else "")
    wish = client.get(url).json()["wishes"][0]
    body = client.post("/api/grant", json={
        "donor_alias": donor, "request_id": wish["id"],
    }).json()
    return body


# --------------------------------------------------------------------------
# THE PRIVACY LINE
# --------------------------------------------------------------------------

def test_no_public_api_response_ever_contains_an_address_or_a_phone(client):
    """The rule the whole app rests on, checked against every public endpoint.

    Not a spot check: it walks every seeded family and donor, and looks for
    their actual address and phone in the raw response body of every endpoint
    a signed-out visitor, a family or a donor can reach.
    """
    with db.connect(config.DB_PATH) as conn:
        people = [*db.list_families(conn), *db.list_donors(conn)]
        granted = _grant_first_open(client)

    public_endpoints = [
        "/api/health",
        "/api/accounts",
        "/api/accounts/family/Family A04",
        "/api/accounts/donor/Donor D01",
        "/api/wishes",
        "/api/wishes?category=clothing",
        "/api/wishes?max_cost_usd=50",
        "/api/wishes?request_type=specific",
        "/api/donors/Donor D01/pledges",
        "/api/families/Family A04/deliveries",
        f"/api/families/{granted['wish']['family_alias']}/deliveries",
    ]

    for path in public_endpoints:
        body = client.get(path).text
        assert "contact_address" not in body, path
        assert "contact_phone" not in body, path
        assert "family_address" not in body, path
        assert "family_phone" not in body, path
        assert "donor_address" not in body, path
        assert "donor_phone" not in body, path
        for person in people:
            assert person.contact_address not in body, f"{path} leaked an address"
            assert person.contact_phone not in body, f"{path} leaked a phone number"


def test_the_grant_response_carries_no_contact_details(client):
    with db.connect(config.DB_PATH) as conn:
        people = [*db.list_families(conn), *db.list_donors(conn)]
    wish = client.get("/api/wishes").json()["wishes"][0]
    body = client.post("/api/grant", json={
        "donor_alias": "Donor D01", "request_id": wish["id"],
    }).text
    for person in people:
        assert person.contact_address not in body
        assert person.contact_phone not in body


def test_contact_details_do_appear_on_the_coordinator_run_sheet(client):
    """The other half of the rule: the coordinator has to be able to deliver."""
    _grant_first_open(client)
    sheet = client.get("/api/coordinator/run-sheet", headers=_token(client)).json()

    rows = [*sheet["dropoffs"], *sheet["deliveries"]]
    assert rows, "expected something scheduled this week"
    assert any(
        row.get("donor_address") or row.get("family_address") for row in rows
    )
    assert any(
        row.get("donor_phone") or row.get("family_phone") for row in rows
    )


# --------------------------------------------------------------------------
# The family confirming a window
# --------------------------------------------------------------------------

def test_a_family_sees_what_is_coming_with_its_window(client):
    granted = _grant_first_open(client)
    alias = granted["wish"]["family_alias"]

    body = client.get(f"/api/families/{alias}/deliveries").json()
    mine = [d for d in body["deliveries"] if d["wish"]["id"] == granted["wish"]["id"]]
    assert len(mine) == 1
    assert mine[0]["window_response"] == "pending"
    assert mine[0]["delivery_window"] == config.get_region().delivery_window.label()


def test_confirming_the_window(client):
    granted = _grant_first_open(client)
    alias = granted["wish"]["family_alias"]
    pledge_id = granted["pledge"]["id"]

    body = client.post("/api/families/deliveries/respond", json={
        "family_alias": alias, "pledge_id": pledge_id, "response": "confirmed",
    }).json()

    assert body["window_response"] == "confirmed"
    assert body["coordinator_will_contact"] is False

    with db.connect(config.DB_PATH) as conn:
        pledge = db.get_pledge(conn, pledge_id)
    assert pledge.window_response is WindowResponse.CONFIRMED
    assert pledge.family_confirmed_delivery is True


def test_saying_it_does_not_work_hands_it_to_a_coordinator(client):
    """No self-service rescheduling: it is flagged, and a person follows up."""
    granted = _grant_first_open(client)
    alias = granted["wish"]["family_alias"]
    pledge_id = granted["pledge"]["id"]

    body = client.post("/api/families/deliveries/respond", json={
        "family_alias": alias, "pledge_id": pledge_id, "response": "needs_reschedule",
    }).json()

    assert body["coordinator_will_contact"] is True
    assert "coordinator will get in touch" in body["message"]
    # No new date is offered anywhere in the answer.
    assert "delivery_date" not in body

    with db.connect(config.DB_PATH) as conn:
        pledge = db.get_pledge(conn, pledge_id)
    assert pledge.window_response is WindowResponse.NEEDS_RESCHEDULE
    assert pledge.delivery_date == date.fromisoformat(granted["pledge"]["delivery_date"])


def test_one_family_cannot_answer_for_another(client):
    granted = _grant_first_open(client)
    other = "Family A19" if granted["wish"]["family_alias"] != "Family A19" else "Family A04"

    response = client.post("/api/families/deliveries/respond", json={
        "family_alias": other, "pledge_id": granted["pledge"]["id"], "response": "confirmed",
    })
    assert response.status_code == 403


def test_pending_is_not_an_answer(client):
    granted = _grant_first_open(client)
    response = client.post("/api/families/deliveries/respond", json={
        "family_alias": granted["wish"]["family_alias"],
        "pledge_id": granted["pledge"]["id"], "response": "pending",
    })
    assert response.status_code == 422


# --------------------------------------------------------------------------
# The run sheet
# --------------------------------------------------------------------------

def test_the_run_sheet_needs_the_coordinator_token(client):
    assert client.get("/api/coordinator/run-sheet").status_code == 401
    assert client.get("/api/coordinator/run-sheet",
                      headers={"X-Coordinator-Token": "nope"}).status_code == 401


def test_a_week_runs_monday_to_sunday():
    start, end = week_bounds(date(2026, 10, 22))     # a Thursday
    assert start == date(2026, 10, 19)
    assert end == date(2026, 10, 25)
    assert start.weekday() == 0 and end.weekday() == 6


def test_the_run_sheet_can_step_week_by_week(client):
    headers = _token(client)
    this_week = client.get("/api/coordinator/run-sheet", headers=headers).json()
    assert this_week["is_this_week"] is True

    nxt = client.get(f"/api/coordinator/run-sheet?week_of={this_week['next_week']}",
                     headers=headers).json()
    assert nxt["is_this_week"] is False
    assert nxt["week_start"] == this_week["next_week"]
    assert nxt["previous_week"] == this_week["week_start"]


def test_a_malformed_week_is_rejected(client):
    assert client.get("/api/coordinator/run-sheet?week_of=last-tuesday",
                      headers=_token(client)).status_code == 422


def test_rent_wishes_sit_in_their_own_section(client):
    granted = _grant_first_open(client, donor="Donor D06", category="rent_utilities")
    sheet = client.get("/api/coordinator/run-sheet", headers=_token(client)).json()

    direct = [p for p in sheet["direct_payments"] if p["pledge_id"] == granted["pledge"]["id"]]
    assert len(direct) == 1
    assert direct[0]["amount_usd"] > 0

    # and nowhere else
    assert granted["pledge"]["id"] not in [d["pledge_id"] for d in sheet["dropoffs"]]
    for delivery in sheet["deliveries"]:
        assert granted["pledge"]["id"] not in delivery["pledge_ids"]


def test_several_wishes_for_one_family_are_one_delivery_row(client):
    """The coordinator makes one trip, so the sheet shows one stop."""
    wishes = client.get("/api/wishes?category=clothing").json()["wishes"]
    with db.connect(config.DB_PATH) as conn:
        alias = wishes[0]["family_alias"]
        extra = Request(
            family_alias=alias, category=Category.GIFTS, request_type=RequestType.FLEXIBLE,
            item_description="A second thing for the same household.",
            occasion=Occasion.EVERYDAY, zip=wishes[0]["zip"],
            deadline=date.fromisoformat(wishes[0]["deadline"]) if wishes[0]["deadline"] else None,
            budget_min_usd=20.0, budget_max_usd=40.0, status=RequestStatus.OPEN,
        )
        extra.id = db.insert_request(extra, conn)
        conn.commit()

    first = client.post("/api/grant", json={
        "donor_alias": "Donor D01", "request_id": wishes[0]["id"]}).json()
    second = client.post("/api/grant", json={
        "donor_alias": "Donor D04", "request_id": extra.id}).json()

    sheet = client.get("/api/coordinator/run-sheet", headers=_token(client)).json()
    rows = [d for d in sheet["deliveries"] if d["family_alias"] == alias]

    # One stop, however many wishes arrive on it — this family may already have
    # had something scheduled for the same day from the seed data.
    assert len(rows) == 1
    assert first["pledge"]["id"] in rows[0]["pledge_ids"]
    assert second["pledge"]["id"] in rows[0]["pledge_ids"]
    assert len(rows[0]["items"]) == len(rows[0]["pledge_ids"]) >= 2


def test_the_sheet_counts_what_is_waiting_on_a_family(client):
    granted = _grant_first_open(client)
    headers = _token(client)

    before = client.get("/api/coordinator/run-sheet", headers=headers).json()
    assert before["counts"]["awaiting_confirmation"] >= 1

    client.post("/api/families/deliveries/respond", json={
        "family_alias": granted["wish"]["family_alias"],
        "pledge_id": granted["pledge"]["id"], "response": "needs_reschedule",
    })
    after = client.get("/api/coordinator/run-sheet", headers=headers).json()
    assert after["counts"]["needs_reschedule"] >= 1


# --------------------------------------------------------------------------
# One click on the run sheet
# --------------------------------------------------------------------------

def test_marking_a_dropoff_moves_the_wish_too(client):
    granted = _grant_first_open(client)
    client.post("/api/coordinator/pledge-status", headers=_token(client), json={
        "pledge_ids": [granted["pledge"]["id"]], "status": "dropped_off",
    })
    with db.connect(config.DB_PATH) as conn:
        wish = db.get_request(conn, granted["wish"]["id"])
        pledge = db.get_pledge(conn, granted["pledge"]["id"])
    assert wish.status is RequestStatus.DROPPED_OFF
    assert pledge.status is PledgeStatus.DROPPED_OFF


def test_marking_delivered(client):
    granted = _grant_first_open(client)
    client.post("/api/coordinator/pledge-status", headers=_token(client), json={
        "pledge_ids": [granted["pledge"]["id"]], "status": "delivered",
    })
    with db.connect(config.DB_PATH) as conn:
        wish = db.get_request(conn, granted["wish"]["id"])
    assert wish.status is RequestStatus.DELIVERED


def test_a_missed_dropoff_puts_the_wish_back_on_the_wall(client):
    """The family must not quietly go without because a donor did not turn up."""
    granted = _grant_first_open(client)
    wish_id = granted["wish"]["id"]
    assert wish_id not in {w["id"] for w in client.get("/api/wishes").json()["wishes"]}

    body = client.post("/api/coordinator/pledge-status", headers=_token(client), json={
        "pledge_ids": [granted["pledge"]["id"]], "status": "missed",
    }).json()

    assert body["reopened_wishes"] == [wish_id]
    assert "back on the wall" in body["note"]
    assert wish_id in {w["id"] for w in client.get("/api/wishes").json()["wishes"]}

    with db.connect(config.DB_PATH) as conn:
        assert db.get_pledge(conn, granted["pledge"]["id"]).status is PledgeStatus.MISSED


def test_a_reopened_wish_can_be_granted_by_someone_else(client):
    granted = _grant_first_open(client)
    client.post("/api/coordinator/pledge-status", headers=_token(client), json={
        "pledge_ids": [granted["pledge"]["id"]], "status": "missed",
    })
    again = client.post("/api/grant", json={
        "donor_alias": "Donor D02", "request_id": granted["wish"]["id"],
    })
    assert again.status_code == 200
    assert again.json()["granted"] is True


def test_one_click_can_move_a_whole_delivery(client):
    wishes = client.get("/api/wishes").json()["wishes"][:2]
    ids = []
    for wish, donor in zip(wishes, ["Donor D01", "Donor D04"]):
        body = client.post("/api/grant", json={
            "donor_alias": donor, "request_id": wish["id"],
        }).json()
        ids.append(body["pledge"]["id"])

    client.post("/api/coordinator/pledge-status", headers=_token(client), json={
        "pledge_ids": ids, "status": "delivered",
    })
    with db.connect(config.DB_PATH) as conn:
        for pledge_id in ids:
            assert db.get_pledge(conn, pledge_id).status is PledgeStatus.DELIVERED


def test_updating_an_unknown_pledge_is_404(client):
    response = client.post("/api/coordinator/pledge-status", headers=_token(client),
                           json={"pledge_ids": [99999], "status": "delivered"})
    assert response.status_code == 404


def test_a_status_click_needs_the_token(client):
    granted = _grant_first_open(client)
    response = client.post("/api/coordinator/pledge-status",
                           json={"pledge_ids": [granted["pledge"]["id"]], "status": "delivered"})
    assert response.status_code == 401


# --------------------------------------------------------------------------
# A whole week
# --------------------------------------------------------------------------

def test_a_full_week_several_grants_one_missed_and_deliveries_done(client):
    """The scenario the problem asks for, start to finish."""
    headers = _token(client)
    wishes = client.get("/api/wishes").json()["wishes"][:4]
    donors = ["Donor D01", "Donor D03", "Donor D04", "Donor D07"]

    granted = []
    for wish, donor in zip(wishes, donors):
        granted.append(client.post("/api/grant", json={
            "donor_alias": donor, "request_id": wish["id"],
        }).json())

    # Every family confirms except one, who cannot make it.
    for item in granted[:-1]:
        client.post("/api/families/deliveries/respond", json={
            "family_alias": item["wish"]["family_alias"],
            "pledge_id": item["pledge"]["id"], "response": "confirmed",
        })
    client.post("/api/families/deliveries/respond", json={
        "family_alias": granted[-1]["wish"]["family_alias"],
        "pledge_id": granted[-1]["pledge"]["id"], "response": "needs_reschedule",
    })

    # One donor does not turn up; the rest drop off and are delivered.
    missed = granted[1]
    client.post("/api/coordinator/pledge-status", headers=headers, json={
        "pledge_ids": [missed["pledge"]["id"]], "status": "missed",
    })
    delivered_ids = [g["pledge"]["id"] for g in granted if g is not missed]
    client.post("/api/coordinator/pledge-status", headers=headers, json={
        "pledge_ids": delivered_ids, "status": "delivered",
    })

    with db.connect(config.DB_PATH) as conn:
        assert db.get_request(conn, missed["wish"]["id"]).status is RequestStatus.OPEN
        for item in granted:
            if item is missed:
                continue
            assert db.get_request(conn, item["wish"]["id"]).status is RequestStatus.DELIVERED

    # The missed wish is back on the wall for someone else.
    assert missed["wish"]["id"] in {w["id"] for w in client.get("/api/wishes").json()["wishes"]}


def test_a_missed_dropoff_leaves_the_delivery_round(client):
    """It stays in the drop-off list so the coordinator sees what happened,
    but there is nothing to deliver, so it must not sit in a delivery round."""
    granted = _grant_first_open(client)
    headers = _token(client)
    pledge_id = granted["pledge"]["id"]

    before = client.get("/api/coordinator/run-sheet", headers=headers).json()
    assert any(pledge_id in row["pledge_ids"] for row in before["deliveries"])

    client.post("/api/coordinator/pledge-status", headers=headers,
                json={"pledge_ids": [pledge_id], "status": "missed"})

    after = client.get("/api/coordinator/run-sheet", headers=headers).json()
    assert not any(pledge_id in row["pledge_ids"] for row in after["deliveries"])
    assert any(row["pledge_id"] == pledge_id and row["status"] == "missed"
               for row in after["dropoffs"])


def test_a_missed_wish_is_not_on_the_family_s_coming_to_you_list(client):
    """Nothing is coming; the wish is back on the wall instead."""
    granted = _grant_first_open(client)
    alias = granted["wish"]["family_alias"]
    client.post("/api/coordinator/pledge-status", headers=_token(client),
                json={"pledge_ids": [granted["pledge"]["id"]], "status": "missed"})

    deliveries = client.get(f"/api/families/{alias}/deliveries").json()["deliveries"]
    assert granted["pledge"]["id"] not in [d["pledge_id"] for d in deliveries]
