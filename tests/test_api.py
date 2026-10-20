"""The three ways into the app, and the privacy rules around them.

The app has no passwords in the MVP: signing up creates a record and returns an
alias, and the browser remembers the alias. The one exception is the
coordinator, whose screens show home addresses and so sit behind a passcode.
"""

import pytest
from fastapi.testclient import TestClient

from backend import config, db, main, seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client over an isolated, seeded database."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    seed.seed(db_path)
    return TestClient(main.app)


# --------------------------------------------------------------------------
# Family sign-up
# --------------------------------------------------------------------------

def test_family_signup_creates_a_record_and_returns_an_alias(client):
    response = client.post("/api/families", json={
        "zip": "06511",
        "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
        "contact_phone": "(203) 555-0191",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "family"
    assert body["alias"] == "Family A59"   # next free alias after the seeded set
    assert body["zip"] == "06511"


def test_signup_response_never_echoes_the_contact_details(client):
    """The address and phone go to the database, not back to the browser."""
    response = client.post("/api/families", json={
        "zip": "06511",
        "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
        "contact_phone": "(203) 555-0191",
    })
    text = response.text
    assert "Nightingale" not in text
    assert "555-0191" not in text


def test_the_contact_details_are_stored_for_the_coordinator(client):
    client.post("/api/families", json={
        "zip": "06511",
        "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
        "contact_phone": "(203) 555-0191",
    })
    with db.connect(config.DB_PATH) as conn:
        family = db.get_family(conn, "Family A59")
    assert family is not None
    assert family.contact_address.startswith("4 Nightingale Ct")
    assert family.contact_phone == "(203) 555-0191"


def test_two_signups_get_different_aliases(client):
    form = {
        "zip": "06511",
        "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
        "contact_phone": "(203) 555-0191",
    }
    first = client.post("/api/families", json=form).json()
    second = client.post("/api/families", json=form).json()
    assert first["alias"] != second["alias"]


def test_a_zip_outside_the_region_is_refused_with_a_useful_message(client):
    response = client.post("/api/families", json={
        "zip": "90210",
        "contact_address": "1 Palm Dr, Beverly Hills, CA 90210",
        "contact_phone": "(310) 555-0100",
    })
    assert response.status_code == 400
    assert "New Haven" in response.json()["detail"]


def test_a_malformed_zip_is_rejected(client):
    response = client.post("/api/families", json={
        "zip": "651", "contact_address": "somewhere", "contact_phone": "2035550100",
    })
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Donor sign-up
# --------------------------------------------------------------------------

def test_donor_signup_stores_preferences(client):
    response = client.post("/api/donors", json={
        "zip": "06517",
        "contact_address": "12 Rookery Ln, Hamden, CT 06517",
        "contact_phone": "(203) 555-0292",
        "budget_usd": 150,
        "preferred_categories": ["clothing", "food"],
        "preference": "flexible",
    })
    assert response.status_code == 201
    assert response.json()["alias"] == "Donor D09"

    with db.connect(config.DB_PATH) as conn:
        donor = db.get_donor(conn, "Donor D09")
    assert donor.budget_usd == 150
    assert [c.value for c in donor.preferred_categories] == ["clothing", "food"]
    assert donor.preference.value == "flexible"


# --------------------------------------------------------------------------
# "Continue as..." list
# --------------------------------------------------------------------------

def test_accounts_lists_every_seeded_family_and_donor(client):
    body = client.get("/api/accounts").json()
    assert len(body["families"]) == 15
    assert len(body["donors"]) == 8
    assert body["families"][0]["alias"].startswith("Family ")


def test_the_accounts_list_leaks_no_address_or_phone(client):
    """This list is open in the demo, so it must carry aliases and zips only."""
    text = client.get("/api/accounts").text
    with db.connect(config.DB_PATH) as conn:
        families = db.list_families(conn)
        donors = db.list_donors(conn)
    for person in [*families, *donors]:
        assert person.contact_address not in text
        assert person.contact_phone not in text
    assert "555-" not in text
    assert "contact_address" not in text


def test_a_remembered_alias_can_be_confirmed(client):
    assert client.get("/api/accounts/family/Family A27").status_code == 200
    assert client.get("/api/accounts/family/Family Z99").status_code == 404


# --------------------------------------------------------------------------
# Coordinator passcode
# --------------------------------------------------------------------------

def test_the_right_passcode_unlocks(client):
    response = client.post(
        "/api/coordinator/unlock", json={"passcode": config.COORDINATOR_PASSCODE}
    )
    assert response.status_code == 200
    assert response.json()["unlocked"] is True


@pytest.mark.parametrize("passcode", ["", "wrong", "wishingtree", "WISHINGTREE-DEMO"])
def test_a_wrong_passcode_is_refused(client, passcode):
    response = client.post("/api/coordinator/unlock", json={"passcode": passcode})
    assert response.status_code == 401


def test_the_passcode_is_checked_on_the_server_not_shipped_to_the_browser():
    """The passcode must not appear anywhere in the built frontend."""
    dist = config.FRONTEND_DIST
    if not dist.exists():
        pytest.skip("frontend not built")
    for path in dist.rglob("*"):
        if path.is_file() and path.suffix in {".js", ".css", ".html"}:
            assert config.COORDINATOR_PASSCODE not in path.read_text(errors="ignore")
