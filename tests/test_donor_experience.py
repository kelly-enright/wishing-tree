"""The donor side added in Problem 10: badges, confirmation, release, calendar."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import badges, config, coordinator_auth, db, main, seed
from backend.models import (
    Category,
    Occasion,
    PledgeStatus,
    Request,
    RequestStatus,
    RequestType,
)

TUESDAY = date(2026, 10, 20)


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


# --------------------------------------------------------------------------
# Badges
# --------------------------------------------------------------------------

def test_needed_by_appears_only_within_the_next_two_dropoffs():
    soon, later = badges.upcoming_dropoffs(2, TUESDAY)
    assert soon == date(2026, 10, 22) and later == date(2026, 10, 29)

    inside = badges.badges_for({"deadline": later.isoformat(), "days_waiting": 0}, TUESDAY)
    assert [b["kind"] for b in inside] == ["needed_by"]

    outside = badges.badges_for(
        {"deadline": (later + timedelta(days=1)).isoformat(), "days_waiting": 0}, TUESDAY
    )
    assert outside == []


def test_waiting_appears_after_the_threshold():
    assert badges.badges_for({"deadline": None, "days_waiting": 14}, TUESDAY) == []
    assert badges.badges_for({"deadline": None, "days_waiting": 8}, TUESDAY) == []

    # The threshold is 14 days, so the first badge a wish can earn is two
    # weeks. There is no "Waiting 1 week" state, by construction.
    waiting = badges.badges_for({"deadline": None, "days_waiting": 15}, TUESDAY)
    assert waiting[0]["label"] == "Waiting 2 weeks"
    assert badges.badges_for({"deadline": None, "days_waiting": 29}, TUESDAY)[0]["label"] == "Waiting 4 weeks"


def test_a_wish_with_no_deadline_only_gets_the_waiting_badge():
    got = badges.badges_for({"deadline": None, "days_waiting": 30}, TUESDAY)
    assert [b["kind"] for b in got] == ["waiting"]


def test_the_thresholds_come_from_config(monkeypatch):
    monkeypatch.setattr(config, "WAITING_BADGE_DAYS", 3)
    got = badges.badges_for({"deadline": None, "days_waiting": 4}, TUESDAY)
    assert got and got[0]["kind"] == "waiting"


def test_no_badge_shouts():
    """Gentle by design: a date and a count, never a red URGENT."""
    everything = badges.badges_for({"deadline": "2026-10-22", "days_waiting": 40}, TUESDAY)
    for badge in everything:
        assert "urgent" not in badge["label"].lower()
        assert badge["label"] == badge["label"].strip()
        assert not badge["label"].isupper()


def test_the_wall_carries_badges(client):
    wishes = client.get("/api/wishes").json()["wishes"]
    assert all("badges" in w for w in wishes)
    assert any(w["badges"] for w in wishes)


# --------------------------------------------------------------------------
# The confirmation screen
# --------------------------------------------------------------------------

def _first_open(client, category: str | None = None) -> dict:
    url = "/api/wishes" + (f"?category={category}" if category else "")
    return client.get(url).json()["wishes"][0]


def test_a_specific_wish_says_exactly_what_to_bring(client):
    wish = _first_open(client, "clothing")
    while wish["request_type"] != "specific":
        rest = [w for w in client.get("/api/wishes?request_type=specific").json()["wishes"]]
        wish = rest[0]
        break

    body = client.get(
        f"/api/grant/options?request_id={wish['id']}&donor_alias=Granter D01"
    ).json()
    bring = body["what_to_bring"]
    assert bring["kind"] == "specific"
    assert bring["item"]
    assert "similar" in bring["substitute_note"].lower()
    assert body["estimated_cost_usd"] > 0


def test_a_flexible_wish_says_what_matters(client):
    flexible = client.get("/api/wishes?request_type=flexible").json()["wishes"][0]
    body = client.get(
        f"/api/grant/options?request_id={flexible['id']}&donor_alias=Granter D01"
    ).json()
    assert body["what_to_bring"]["kind"] == "flexible"
    assert body["what_to_bring"]["substitute_ok"] is True


def test_a_rent_wish_confirms_the_amount_and_who_pays(client):
    rent = _first_open(client, "rent_utilities")
    body = client.get(
        f"/api/grant/options?request_id={rent['id']}&donor_alias=Granter D06"
    ).json()
    assert body["paid_directly_to_provider"] is True
    assert body["what_to_bring"] is None
    assert body["dropoff_choices"] == []
    assert "coordinator will email" in body["direct_payment_note"]
    assert "directly" in body["direct_payment_note"]


def test_the_options_offer_every_dropoff_that_still_arrives(client):
    far = client.get("/api/wishes").json()["wishes"]
    distant = max(far, key=lambda w: w["days_until_deadline"] or 0)
    body = client.get(
        f"/api/grant/options?request_id={distant['id']}&donor_alias=Granter D01"
    ).json()
    assert len(body["dropoff_choices"]) > 1
    assert all(c["arrives_in_time"] for c in body["dropoff_choices"])


def test_a_donor_can_pick_a_later_dropoff(client):
    far = client.get("/api/wishes").json()["wishes"]
    distant = max(far, key=lambda w: w["days_until_deadline"] or 0)
    options = client.get(
        f"/api/grant/options?request_id={distant['id']}&donor_alias=Granter D01"
    ).json()
    second = options["dropoff_choices"][1]["dropoff_date"]

    body = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": distant["id"], "dropoff_date": second,
    }).json()
    assert body["logistics"]["dropoff_date"] == second


def test_a_dropoff_day_we_do_not_run_is_refused(client):
    wish = _first_open(client)
    response = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
        "dropoff_date": "2026-10-21",          # a Wednesday
    })
    assert response.status_code == 422
    assert "isn't one we're running" in response.json()["detail"]


def test_options_refuse_a_wish_someone_else_took(client):
    wish = _first_open(client)
    client.post("/api/grant", json={"donor_alias": "Granter D02", "request_id": wish["id"]})
    response = client.get(
        f"/api/grant/options?request_id={wish['id']}&donor_alias=Granter D01"
    )
    assert response.status_code == 409


# --------------------------------------------------------------------------
# My granted wishes
# --------------------------------------------------------------------------

def test_granted_list_has_friendly_statuses_and_no_family_details(client):
    wish = _first_open(client)
    client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": wish["id"]})

    body = client.get("/api/donors/Granter D01/granted").json()
    assert body["granted"]
    labels = {row["label"] for row in body["granted"]}
    assert "Ready to drop off" in labels
    # A wish just claimed is coming up, not yet granted.
    assert {r["pledge_id"] for r in body["coming_up"]} == {
        r["pledge_id"] for r in body["granted"] if r["status"] == "pledged"
    }

    with db.connect(config.DB_PATH) as conn:
        families = db.list_families(conn)
    text = str(body)
    for family in families:
        assert family.contact_address not in text
        assert family.contact_email not in text


def test_a_rent_pledge_reads_differently(client):
    rent = _first_open(client, "rent_utilities")
    client.post("/api/grant", json={"donor_alias": "Granter D06", "request_id": rent["id"]})
    body = client.get("/api/donors/Granter D06/granted").json()
    row = [r for r in body["granted"] if r["wish"]["id"] == rent["id"]][0]
    assert row["label"] == "We'll email you how to pay"


def test_a_dropoff_this_week_shows_in_the_banner(client):
    wish = _first_open(client)
    client.post("/api/grant", json={"donor_alias": "Granter D01", "request_id": wish["id"]})
    body = client.get("/api/donors/Granter D01/granted").json()
    assert body["this_week"], "expected the coming drop-off in the banner"


# --------------------------------------------------------------------------
# Releasing
# --------------------------------------------------------------------------

def test_releasing_puts_the_wish_straight_back(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    pledge_id = granted["pledge"]["id"]

    body = client.post(f"/api/pledges/{pledge_id}/release?donor_alias=Granter D01").json()
    assert body["released"] is True
    assert body["wish_status"] == "open"
    assert wish["id"] in {w["id"] for w in client.get("/api/wishes").json()["wishes"]}


def test_a_release_is_not_a_missed_dropoff(client):
    """Someone who tells you in advance has done the right thing."""
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    client.post(f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D01")

    with db.connect(config.DB_PATH) as conn:
        pledge = db.get_pledge(conn, granted["pledge"]["id"])
    assert pledge.status is PledgeStatus.RELEASED
    assert pledge.status is not PledgeStatus.MISSED

    sheet = client.get("/api/coordinator/run-sheet", headers=_token(client)).json()
    row = [d for d in sheet["dropoffs"] if d["pledge_id"] == granted["pledge"]["id"]][0]
    assert row["status"] == "released"


def test_a_released_wish_leaves_the_delivery_round(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    client.post(f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D01")

    sheet = client.get("/api/coordinator/run-sheet", headers=_token(client)).json()
    for delivery in sheet["deliveries"]:
        assert granted["pledge"]["id"] not in delivery["pledge_ids"]


def test_the_family_is_not_told_why_a_wish_came_back(client):
    """Only 'Still looking for the right neighbor.'"""
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    client.post(f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D01")

    rows = client.get(f"/api/families/{wish['family_alias']}/wishes").json()["wishes"]
    row = [r for r in rows if r["wish"]["id"] == wish["id"]][0]
    assert row["detail"] == "Still looking for the right neighbor."
    assert "couldn't" not in row["detail"]
    assert "donor" not in str(row).lower()


def test_only_the_donor_who_granted_it_can_release_it(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    response = client.post(
        f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D02"
    )
    assert response.status_code == 403


def test_releasing_twice_is_refused(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    url = f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D01"
    assert client.post(url).status_code == 200
    assert client.post(url).status_code == 409


# --------------------------------------------------------------------------
# The calendar file
# --------------------------------------------------------------------------

def test_the_calendar_file_is_a_real_ics(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    pledge_id = granted["pledge"]["id"]

    response = client.get(f"/api/pledges/{pledge_id}/calendar.ics?donor_alias=Granter D01")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert ".ics" in response.headers["content-disposition"]

    body = response.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert body.strip().endswith("END:VCALENDAR")
    for field in ("DTSTART:", "DTEND:", "SUMMARY:", "LOCATION:", "UID:", "BEGIN:VALARM"):
        assert field in body

    day = granted["pledge"]["dropoff_date"].replace("-", "")
    region = config.get_region()
    assert f"DTSTART:{day}T{region.dropoff_window.start.strftime('%H%M%S')}" in body
    assert region.hub_name.replace(",", "\\,") in body or region.hub_name in body


def test_the_calendar_file_carries_no_family_details(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    body = client.get(
        f"/api/pledges/{granted['pledge']['id']}/calendar.ics?donor_alias=Granter D01"
    ).text

    with db.connect(config.DB_PATH) as conn:
        families = db.list_families(conn)
    for family in families:
        assert family.contact_address not in body
        assert family.contact_email not in body


def test_someone_elses_calendar_is_refused(client):
    wish = _first_open(client)
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    response = client.get(
        f"/api/pledges/{granted['pledge']['id']}/calendar.ics?donor_alias=Granter D02"
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# The gold leaves
# --------------------------------------------------------------------------

def test_the_wall_reports_recently_granted_wishes(client):
    body = client.get("/api/wishes").json()
    assert body["granted_window_days"] == config.GRANTED_LEAF_DAYS
    assert body["recently_granted"], "expected some gold leaves from the seed"


def test_a_gold_leaf_carries_only_an_id_and_a_category(client):
    """A granted wish is nobody's to read any more — the leaf is just a shape."""
    body = client.get("/api/wishes").json()
    for leaf in body["recently_granted"]:
        assert set(leaf) == {"id", "category"}


def _deliver(client, pledge_id, status="delivered"):
    """Drive a pledge forward the way the admin does, from the run sheet."""
    return client.post(
        "/api/coordinator/pledge-status",
        headers=_token(client),
        json={"pledge_ids": [pledge_id], "status": status},
    )


def test_a_claimed_wish_is_not_gold_until_it_arrives(client):
    """Gold means granted, and granted means the neighbor has it. A wish
    someone has claimed is a promise made, not a promise kept."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()

    after = client.get("/api/wishes").json()
    assert wish["id"] not in {w["id"] for w in after["wishes"]}      # off the tree
    assert wish["id"] not in {g["id"] for g in after["recently_granted"]}  # not gold

    _deliver(client, granted["pledge"]["id"], "dropped_off")
    assert wish["id"] not in {
        g["id"] for g in client.get("/api/wishes").json()["recently_granted"]
    }

    _deliver(client, granted["pledge"]["id"], "delivered")
    assert wish["id"] in {
        g["id"] for g in client.get("/api/wishes").json()["recently_granted"]
    }


def test_old_grants_fall_off_the_tree(client):
    """The tree remembers a month, not forever.

    Ages one pledge past the window rather than moving the window, because
    what matters is that an old grant drops off, not that a zero-day window
    returns nothing.
    """
    wish = client.get("/api/wishes").json()["wishes"][0]
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    pledge_id = granted["pledge"]["id"]
    _deliver(client, pledge_id, "delivered")

    assert wish["id"] in {g["id"] for g in client.get("/api/wishes").json()["recently_granted"]}

    # Dated on the delivery, which is when the wish actually arrived.
    old = (date.today() - timedelta(days=config.GRANTED_LEAF_DAYS + 1)).isoformat()
    with db.connect(config.DB_PATH) as conn:
        conn.execute("UPDATE pledges SET delivery_date = ? WHERE id = ?", (old, pledge_id))
        conn.commit()

    assert wish["id"] not in {g["id"] for g in client.get("/api/wishes").json()["recently_granted"]}


def test_a_released_wish_is_not_a_gold_leaf(client):
    wish = client.get("/api/wishes").json()["wishes"][0]
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    client.post(f"/api/pledges/{granted['pledge']['id']}/release?donor_alias=Granter D01")

    after = client.get("/api/wishes").json()
    assert wish["id"] not in {g["id"] for g in after["recently_granted"]}
    assert wish["id"] in {w["id"] for w in after["wishes"]}        # back on the tree


# --------------------------------------------------------------------------
# The three stages, and what "granted" is allowed to mean
# --------------------------------------------------------------------------

def _granted_rows(client, alias="Granter D01"):
    return client.get(f"/api/donors/{alias}/granted").json()


def test_a_wish_walks_the_three_stages(client):
    wish = _first_open(client)
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()["pledge"]["id"]

    def row():
        body = _granted_rows(client)
        return next(r for r in body["granted"] if r["pledge_id"] == pledge)

    assert row()["label"] == "Ready to drop off"
    assert row()["section"] == "coming_up"

    _deliver(client, pledge, "dropped_off")
    assert row()["label"] == "Dropped off, thank you!"
    assert row()["section"] == "granted"

    _deliver(client, pledge, "delivered")
    assert row()["label"] == "Delivered, wish granted!"
    assert row()["section"] == "granted"


def test_rent_never_says_drop_off(client):
    """Nobody carries a rent payment to the hub, so nothing says they did."""
    rent = next(w for w in client.get("/api/wishes").json()["wishes"]
                if w["category"] == "rent_utilities")
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": rent["id"],
    }).json()["pledge"]["id"]

    def row():
        return next(r for r in _granted_rows(client)["granted"]
                    if r["pledge_id"] == pledge)

    assert row()["label"] == "We'll email you how to pay"
    _deliver(client, pledge, "dropped_off")
    assert row()["label"] == "Payment received, thank you!"
    _deliver(client, pledge, "delivered")
    assert row()["label"] == "Paid to provider, wish granted!"

    for stage in _granted_rows(client)["granted"]:
        if stage["paid_directly_to_provider"]:
            assert "drop" not in stage["label"].lower()


def test_coming_up_holds_what_has_not_arrived_yet(client):
    wish = _first_open(client)
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()["pledge"]["id"]

    body = _granted_rows(client)
    assert pledge in {r["pledge_id"] for r in body["coming_up"]}
    assert pledge not in {r["pledge_id"] for r in body["already_granted"]}

    _deliver(client, pledge, "delivered")
    body = _granted_rows(client)
    assert pledge not in {r["pledge_id"] for r in body["coming_up"]}
    assert pledge in {r["pledge_id"] for r in body["already_granted"]}


def test_a_released_wish_leaves_the_granters_page(client):
    wish = _first_open(client)
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()["pledge"]["id"]
    client.post(f"/api/pledges/{pledge}/release?donor_alias=Granter D01")

    body = _granted_rows(client)
    assert pledge not in {r["pledge_id"] for r in body["granted"]}
    assert pledge not in {r["pledge_id"] for r in body["coming_up"]}
    assert pledge not in {r["pledge_id"] for r in body["already_granted"]}


def test_a_missed_dropoff_leaves_the_granters_page_too(client):
    """It is back on the tree for someone else. Showing it here would only
    be a reminder of something they did not do."""
    wish = _first_open(client)
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()["pledge"]["id"]
    _deliver(client, pledge, "missed")

    body = _granted_rows(client)
    assert pledge not in {r["pledge_id"] for r in body["granted"]}
    assert pledge not in {r["pledge_id"] for r in body["coming_up"]}


def test_the_hub_address_is_linked_to_a_map(client):
    wish = _first_open(client)
    client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    })
    body = _granted_rows(client)
    assert body["hub"]["maps_url"].startswith("https://www.google.com/maps/")
    assert "New+Haven" in body["hub"]["maps_url"]
