"""The words the app uses.

Tone is not decoration here. Someone asking for help reads these strings on a
hard day, and a single "beneficiary" undoes a lot of careful work. These tests
hold the vocabulary in place so it cannot drift back.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import config, coordinator_auth, db, main, seed

# Words that describe people from a distance. None of them belongs in
# anything a person using Wishing Tree reads.
BANNED = [
    "needy", "less fortunate", "beneficiary", "beneficiaries",
    "recipient", "charity case", "underprivileged", "the poor",
    "save a family", "deserving",
]

# "donor" is a perfectly good word; it is just not the one we show. Internal
# code keeps it — these tests only look at what reaches a person.
NEVER_SHOWN = ["donor", "donors", "Donor", "Donors"]

# JSON field names and the `role` discriminator the frontend routes on are
# code: nothing draws them. Blank them out before reading a response, so the
# test judges the words people see and not the plumbing underneath them.
FIELD_NAME = re.compile(r'"[a-z_]+"\s*:')
ROLE_VALUE = re.compile(r'"role"\s*:\s*"[a-z]+"')


def prose(response) -> str:
    """What is left of a response once the machine-readable parts are gone."""
    return FIELD_NAME.sub('"k":', ROLE_VALUE.sub('"role":"x"', response.text))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
    seed.seed(config.DB_PATH)
    coordinator_auth.clear()
    return TestClient(main.app)


# --------------------------------------------------------------------------
# Aliases
# --------------------------------------------------------------------------

def test_people_are_neighbors_and_granters(client):
    with db.connect(config.DB_PATH) as conn:
        families = db.list_families(conn)
        donors = db.list_donors(conn)

    assert all(f.alias.startswith("Neighbor ") for f in families)
    assert all(d.alias.startswith("Granter ") for d in donors)
    assert not any("Family" in f.alias for f in families)
    assert not any("Donor" in d.alias for d in donors)


def test_a_new_signup_gets_a_neighbor_alias(client):
    body = client.post("/api/families", json={
        "zip": "06511", "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
        "contact_email": "new@example.com",
    }).json()
    assert body["alias"].startswith("Neighbor ")

    granter = client.post("/api/donors", json={
        "zip": "06511", "contact_address": "9 Rookery Ln, New Haven, CT 06511",
        "contact_email": "give@example.com", "budget_usd": 60,
        "preferred_categories": ["clothing"], "preference": "either",
    }).json()
    assert granter["alias"].startswith("Granter ")


# --------------------------------------------------------------------------
# What reaches a person
# --------------------------------------------------------------------------

PUBLIC_PATHS = [
    "/api/stats", "/api/service-area", "/api/service-area?zip=06511",
    "/api/service-area?zip=90210", "/api/retailers", "/api/accounts",
    "/api/wishes", "/api/wishes?category=clothing",
    "/api/families/Neighbor A04/wishes",
    "/api/families/Neighbor A04/deliveries",
    "/api/donors/Granter D01/granted",
]


@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_no_public_response_says_donor(client, path):
    body = prose(client.get(path))
    for word in NEVER_SHOWN:
        assert not re.search(rf"\b{word}\b", body), f"{path} says {word!r}"


@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_no_public_response_uses_a_banned_word(client, path):
    body = prose(client.get(path)).lower()
    for word in BANNED:
        assert word not in body, f"{path} says {word!r}"


def test_the_out_of_area_message_is_a_not_yet(client):
    message = client.get("/api/service-area?zip=90210").json()["message"]
    assert "yet" in message
    assert "coming soon" in message
    assert "sorry" in message.lower()


def test_nothing_claims_a_rate_of_wishes_granted(client):
    """We cannot back up "most wishes get granted", so we never say it."""
    for path in PUBLIC_PATHS:
        body = prose(client.get(path)).lower()
        for claim in ("most wishes", "% of wishes", "guaranteed", "we promise"):
            assert claim not in body, f"{path} claims {claim!r}"


# --------------------------------------------------------------------------
# The prompts the agents write from
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["intake_agent", "safety_agent", "matchmaker_agent"])
def test_a_prompt_only_says_a_banned_word_to_forbid_it(name):
    """Every prompt names some of these words — that is how an instruction not
    to use them gets written. What matters is that the sentence around the word
    is a prohibition and not an example of how to talk."""
    text = (config.PROMPTS_DIR / f"{name}.md").read_text().lower()
    for paragraph in re.split(r"\n\s*\n", text):
        for word in BANNED:
            if word in paragraph:
                assert any(stop in paragraph for stop in ("never", "not ", "no ", "don't")), (
                    f"{name} uses {word!r} outside a prohibition:\n{paragraph.strip()}"
                )


def test_the_intake_prompt_carries_the_voice_guide():
    text = (config.PROMPTS_DIR / "intake_agent.md").read_text()
    assert "Dignity, never pity" in text
    assert "Never ask for their story" in text
    assert "never quote a rate" in text
    assert "Call them neighbors, never donors" in text


# --------------------------------------------------------------------------
# The counter on the landing page
# --------------------------------------------------------------------------

def test_the_granted_counter_is_real(client):
    before = client.get("/api/stats").json()["wishes_granted"]
    wish = client.get("/api/wishes").json()["wishes"][0]
    client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    })
    assert client.get("/api/stats").json()["wishes_granted"] == before + 1


def test_the_counter_does_not_double_count_a_regranted_wish(client):
    """A wish released and granted again was still one wish granted."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    first = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    after_one = client.get("/api/stats").json()["wishes_granted"]

    client.post(f"/api/pledges/{first['pledge']['id']}/release?donor_alias=Granter D01")
    client.post("/api/grant", json={
        "donor_alias": "Granter D02", "request_id": wish["id"],
    })
    assert client.get("/api/stats").json()["wishes_granted"] == after_one


def test_the_landing_line_names_the_real_region(client):
    body = client.get("/api/stats").json()
    assert body["line"] == "Every wish on this tree is from someone in New Haven."
    assert body["wishes_open"] == len(client.get("/api/wishes").json()["wishes"])
