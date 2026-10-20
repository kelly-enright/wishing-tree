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

def _admin(client):
    token = client.post("/api/coordinator/unlock",
                        json={"passcode": config.COORDINATOR_PASSCODE}).json()["token"]
    return {"X-Coordinator-Token": token}


def _move(client, pledge_id, status):
    return client.post("/api/coordinator/pledge-status", headers=_admin(client),
                       json={"pledge_ids": [pledge_id], "status": status})


def test_the_counter_moves_only_when_a_wish_arrives(client):
    """"Granted" on the landing page means a neighbor has the thing. Claiming
    it and dropping it at the hub are both still on the way."""
    before = client.get("/api/stats").json()["wishes_granted"]
    wish = client.get("/api/wishes").json()["wishes"][0]
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    assert client.get("/api/stats").json()["wishes_granted"] == before

    _move(client, granted["pledge"]["id"], "dropped_off")
    assert client.get("/api/stats").json()["wishes_granted"] == before

    _move(client, granted["pledge"]["id"], "delivered")
    assert client.get("/api/stats").json()["wishes_granted"] == before + 1


def test_the_counter_does_not_double_count_a_regranted_wish(client):
    """A wish released, granted again and delivered is one wish granted."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    first = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    before = client.get("/api/stats").json()["wishes_granted"]

    client.post(f"/api/pledges/{first['pledge']['id']}/release?donor_alias=Granter D01")
    second = client.post("/api/grant", json={
        "donor_alias": "Granter D02", "request_id": wish["id"],
    }).json()
    _move(client, second["pledge"]["id"], "delivered")
    assert client.get("/api/stats").json()["wishes_granted"] == before + 1


def test_the_landing_line_names_the_real_region(client):
    body = client.get("/api/stats").json()
    assert body["line"] == "Every wish on this tree is from someone in New Haven."
    assert body["wishes_open"] == len(client.get("/api/wishes").json()["wishes"])


# --------------------------------------------------------------------------
# The two sides of one wish
# --------------------------------------------------------------------------

def _stage(client, alias, request_id):
    wishes = client.get(f"/api/families/{alias}/wishes").json()["wishes"]
    return next(w for w in wishes if w["wish"]["id"] == request_id)


def test_the_two_sides_never_contradict_each_other(client):
    """While a granter is told the wish is ready to drop off, the neighbor
    must not be told it was granted. Granted means it arrived."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    alias = wish["family_alias"]
    granted = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()
    pledge = granted["pledge"]["id"]

    def granter_label():
        rows = client.get("/api/donors/Granter D01/granted").json()["granted"]
        return next(r for r in rows if r["pledge_id"] == pledge)["label"]

    assert granter_label() == "Ready to drop off"
    assert _stage(client, alias, wish["id"])["label"] == "A neighbor picked your wish"

    _move(client, pledge, "dropped_off")
    assert granter_label() == "Dropped off, thank you!"
    assert _stage(client, alias, wish["id"])["label"] == "On its way"

    _move(client, pledge, "delivered")
    assert granter_label() == "Delivered, wish granted!"
    assert _stage(client, alias, wish["id"])["label"] == "Delivered"


def test_nothing_says_granted_before_a_wish_arrives(client):
    wish = client.get("/api/wishes").json()["wishes"][0]
    alias = wish["family_alias"]
    pledge = client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": wish["id"],
    }).json()["pledge"]["id"]

    for stage in ("pledged", "dropped_off"):
        if stage != "pledged":
            _move(client, pledge, stage)
        seen = _stage(client, alias, wish["id"])
        assert "granted" not in seen["label"].lower(), seen["label"]
        assert "granted" not in seen["detail"].lower(), seen["detail"]


# --------------------------------------------------------------------------
# Seeded wishes read like published ones
# --------------------------------------------------------------------------

FIRST_PERSON = [" i ", " my ", " we ", " our ", " us ", "i'm ", "i've ", "my "]
RELATIONSHIPS = ["my son", "my daughter", "my mother", "my grandson", "her brother",
                 "my kids", "my child", "her mother", "my husband", "my wife"]


def test_no_seeded_wish_speaks_in_the_first_person(client):
    """Seed data has to look exactly like what the Safety agent publishes,
    or the screenshots in the report show something the app never produces."""
    with db.connect(config.DB_PATH) as conn:
        for request in db.list_requests(conn):
            text = f" {request.item_description.lower()} "
            for word in FIRST_PERSON:
                assert word not in text, f"{request.item_description!r} says {word!r}"
            for phrase in RELATIONSHIPS:
                assert phrase not in text, f"{request.item_description!r} says {phrase!r}"


def test_no_seeded_wish_explains_itself(client):
    """A granter needs to know what to bring, not why it is needed."""
    with db.connect(config.DB_PATH) as conn:
        for request in db.list_requests(conn):
            text = request.item_description.lower()
            for giveaway in (" so i ", " so he ", " so she ", " because ", " after "):
                assert giveaway not in f" {text} ", request.item_description


def test_the_safety_prompt_asks_for_the_published_form():
    text = (config.PROMPTS_DIR / "safety_agent.md").read_text()
    assert "No first person" in text
    assert "No relationships" in text
    assert "No reasons and no circumstances" in text
    assert "Shower chair for an adult" in text


# --------------------------------------------------------------------------
# Dates, as a person reads them
# --------------------------------------------------------------------------

ISO = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")

# What the admin run sheet is allowed to keep: it is a working document,
# scanned in columns, and ISO sorts and lines up.
ADMIN_PATHS = ("/api/coordinator/",)


def test_no_date_a_person_reads_is_still_iso(client):
    """Dates reach the browser as ISO — that is the right shape for data.
    What matters is that no composed *sentence* carries one."""
    for path in PUBLIC_PATHS:
        body = client.get(path).json()
        for text in _sentences(body):
            assert not ISO.search(text), f"{path} shows an ISO date: {text!r}"


def _sentences(node):
    """Every string in a response that reads as prose rather than as data."""
    DATA_FIELDS = {
        "deadline", "dropoff_date", "delivery_date", "created_at", "updated_at",
        "week_start", "week_end", "previous_week", "next_week", "pay_by",
        "deadline_label", "date",
    }
    if isinstance(node, dict):
        for key, value in node.items():
            if key in DATA_FIELDS:
                continue
            yield from _sentences(value)
    elif isinstance(node, list):
        for item in node:
            yield from _sentences(item)
    elif isinstance(node, str):
        yield node


def test_the_deadline_badge_reads_like_a_date(client):
    wishes = client.get("/api/wishes").json()["wishes"]
    labels = [b["label"] for w in wishes for b in (w.get("badges") or [])
              if b["kind"] == "needed_by"]
    assert labels, "no deadline badges in the seed to check"
    for label in labels:
        assert not ISO.search(label), label
        assert label.startswith("Needed by ")


def test_the_run_sheet_may_keep_its_compact_dates(client):
    """Stated as a rule so it is a decision rather than an oversight."""
    token = client.post("/api/coordinator/unlock",
                        json={"passcode": config.COORDINATOR_PASSCODE}).json()["token"]
    sheet = client.get("/api/coordinator/run-sheet",
                       headers={"X-Coordinator-Token": token}).json()
    assert sheet["week_start"]
    assert ISO.fullmatch(sheet["week_start"])


# --------------------------------------------------------------------------
# The visual refresh — the parts that can be checked without a browser
# --------------------------------------------------------------------------

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def test_the_fonts_are_served_by_this_app():
    """Self-hosted, so the app looks the same with no internet and opening it
    sends nothing to a third party."""
    css = (FRONTEND / "src" / "styles.css").read_text()
    assert "fonts.googleapis.com" not in css
    assert "fonts.gstatic.com" not in css
    for family in ("fraunces-latin.woff2", "inter-latin.woff2"):
        assert f"/fonts/{family}" in css
        assert (FRONTEND / "public" / "fonts" / family).exists()
    assert (FRONTEND / "public" / "fonts" / "LICENSE").exists()


def test_the_built_app_carries_the_fonts_and_the_favicon():
    """The built frontend is what ships, so the files have to be in it."""
    dist = FRONTEND / "dist"
    assert (dist / "favicon.svg").exists()
    for family in ("fraunces-latin.woff2", "inter-latin.woff2"):
        assert (dist / "fonts" / family).exists()
    index = (dist / "index.html").read_text()
    assert 'rel="icon"' in index
    assert "favicon.svg" in index


def test_the_favicon_is_the_tree_not_the_scaffold():
    """The file started life as a framework placeholder in purple."""
    svg = (FRONTEND / "public" / "favicon.svg").read_text()
    assert "#2F5D50" in svg and "#E0A84B" in svg      # evergreen and gold
    assert "863bff" not in svg.lower()                 # the old purple


def test_motion_is_switched_off_for_anyone_who_asks():
    css = (FRONTEND / "src" / "styles.css").read_text()
    block = css[css.index("@media (prefers-reduced-motion: reduce)"):]
    assert "animation-duration: 0.001ms !important" in block
    assert "transition-duration: 0.001ms !important" in block


def test_a_leaf_does_not_use_transform_for_its_position():
    """Position lives in `translate`/`rotate` so hover and the arrival
    animation can use `transform` without knocking leaves off the tree."""
    tree = (FRONTEND / "src" / "components" / "WishTree.tsx").read_text()
    seat = tree[tree.index("const style = {"): tree.index("const style = {") + 400]
    assert "translate:" in seat and "rotate:" in seat
    assert "transform:" not in seat


def test_the_promise_button_says_it_is_a_promise():
    for rel in ("src/components/WishCard.tsx", "src/pages/GrantConfirm.tsx"):
        text = (FRONTEND / rel).read_text()
        assert "I'll grant this wish" in text
        assert "'Grant this wish'" not in text
