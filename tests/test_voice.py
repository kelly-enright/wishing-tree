"""The words the app uses.

Tone is not decoration here. Someone asking for help reads these strings on a
hard day, and a single "beneficiary" undoes a lot of careful work. These tests
hold the vocabulary in place so it cannot drift back.
"""

import re
from pathlib import Path

import pytest

from helpers import grant_as, sign_in
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
    return sign_in(TestClient(main.app), 'Neighbor A04')


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
    "password": "a-good-long-password",
    }).json()
    assert body["alias"].startswith("Neighbor ")

    granter = client.post("/api/donors", json={
        "zip": "06511", "contact_address": "9 Rookery Ln, New Haven, CT 06511",
        "contact_email": "give@example.com", "budget_usd": 60,
        "password": "a-good-long-password",
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
    granted = grant_as(client, "Granter D01", wish["id"]).json()
    assert client.get("/api/stats").json()["wishes_granted"] == before

    _move(client, granted["pledge"]["id"], "dropped_off")
    assert client.get("/api/stats").json()["wishes_granted"] == before

    _move(client, granted["pledge"]["id"], "delivered")
    assert client.get("/api/stats").json()["wishes_granted"] == before + 1


def test_the_counter_does_not_double_count_a_regranted_wish(client):
    """A wish released, granted again and delivered is one wish granted."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    first = grant_as(client, "Granter D01", wish["id"]).json()
    before = client.get("/api/stats").json()["wishes_granted"]

    client.post(f"/api/pledges/{first['pledge']['id']}/release?donor_alias=Granter D01")
    second = grant_as(client, "Granter D02", wish["id"]).json()
    _move(client, second["pledge"]["id"], "delivered")
    assert client.get("/api/stats").json()["wishes_granted"] == before + 1


def test_the_landing_line_names_the_real_region(client):
    body = client.get("/api/stats").json()
    assert body["line"] == "Every wish on this tree is from someone in New Haven."
    # Counted for somebody with no wishes of their own. A neighbor's own
    # wishes are kept off their tree, so for them the two would differ — see
    # test_accounts.py, where that is the point rather than a nuisance.
    sign_in(client, "Granter D01")
    assert body["wishes_open"] == len(client.get("/api/wishes").json()["wishes"])


# --------------------------------------------------------------------------
# The two sides of one wish
# --------------------------------------------------------------------------

def _stage(client, alias, request_id):
    """What the neighbor is told about one wish. Signs in as them to ask,
    because this endpoint now answers only to the account that owns it."""
    sign_in(client, alias)
    wishes = client.get(f"/api/families/{alias}/wishes").json()["wishes"]
    return next(w for w in wishes if w["wish"]["id"] == request_id)


def test_the_two_sides_never_contradict_each_other(client):
    """While a granter is told the wish is ready to drop off, the neighbor
    must not be told it was granted. Granted means it arrived."""
    wish = client.get("/api/wishes").json()["wishes"][0]
    alias = wish["family_alias"]
    granted = grant_as(client, "Granter D01", wish["id"]).json()
    pledge = granted["pledge"]["id"]

    def granter_label():
        # _stage() signs in as the neighbor, so come back as the granter.
        sign_in(client, "Granter D01")
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
    pledge = grant_as(client, "Granter D01", wish["id"]).json()["pledge"]["id"]

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


# --------------------------------------------------------------------------
# No page is a dead end
# --------------------------------------------------------------------------

PAGES = sorted((FRONTEND / "src" / "pages").glob("*.tsx"))

# Two of these are not pages in their own right: FormShell wraps the sign-up
# forms and is rendered inside them, and GrantConfirm is a step shown within
# the granter's page. Both sit under a bar drawn by their parent.
NOT_A_PAGE = {"FormShell.tsx", "GrantConfirm.tsx", "MyWishes.tsx",
              "MyGranted.tsx", "RunSheet.tsx", "AgentActivity.tsx",
              "WishReview.tsx"}


@pytest.mark.parametrize("page", [p for p in PAGES if p.name not in NOT_A_PAGE],
                         ids=lambda p: p.name)
def test_every_page_draws_the_navigation_bar(page):
    """Including the landing page, About, and the screens after a wish is
    granted. Whatever brought somebody to a page, there is a way on from it."""
    source = page.read_text()
    # A page either draws the bar itself or sits inside FormShell, which does.
    assert "<TopBar" in source or "<FormShell" in source, f"{page.name} has no navigation"
    assert "page__nav" not in source, f"{page.name} still uses the old bare header"


def test_the_login_page_offers_staff_a_way_in():
    source = (FRONTEND / "src" / "pages" / "LogIn.tsx").read_text()
    assert "Admin sign-in" in source
    assert 'to="/coordinator"' in source


def test_the_footer_is_one_component_used_everywhere():
    """Rather than a copy per page, which is how two of them end up differing."""
    footer = (FRONTEND / "src" / "components" / "Footer.tsx").read_text()
    assert 'to="/about"' in footer and 'to="/coordinator"' in footer
    for name in ("Landing.tsx", "About.tsx", "LogIn.tsx", "HowItWorksPage.tsx"):
        source = (FRONTEND / "src" / "pages" / name).read_text()
        assert "<Footer />" in source, name


def test_the_about_page_can_be_left():
    source = (FRONTEND / "src" / "pages" / "About.tsx").read_text()
    assert "backlink" in source


# --------------------------------------------------------------------------
# Household, and the category definitions the agent works from
# --------------------------------------------------------------------------

def test_household_exists_everywhere_a_category_has_to(client):
    """A category that the backend knows and the frontend cannot draw is a
    wish that renders as a blank leaf."""
    from backend.models import Category
    assert Category.HOUSEHOLD.value == "household"

    tree = (FRONTEND / "src" / "components" / "WishTree.tsx").read_text()
    icons = (FRONTEND / "src" / "components" / "CategoryIcon.tsx").read_text()
    api = (FRONTEND / "src" / "api.ts").read_text()
    assert "household: '#5B7C99'" in tree          # its own leaf color
    assert "household: Lamp" in icons              # its own icon
    assert "household: 'Household'" in api         # its own filter chip


def test_every_category_can_be_drawn(client):
    """Each value the server can send has a color and an icon on the client."""
    from backend.models import Category
    tree = (FRONTEND / "src" / "components" / "WishTree.tsx").read_text()
    icons = (FRONTEND / "src" / "components" / "CategoryIcon.tsx").read_text()
    for category in Category:
        assert f"{category.value}:" in tree, category.value
        assert f"{category.value}:" in icons, category.value


def test_the_seed_puts_home_things_in_household(client):
    with db.connect(config.DB_PATH) as conn:
        household = [r.item_description for r in db.list_requests(conn)
                     if r.category.value == "household"]
    assert any("Shower chair" in d for d in household)
    assert any("Sheets, towels" in d for d in household)
    # A blanket asked for as a birthday present is a gift, not bedding.
    with db.connect(config.DB_PATH) as conn:
        blanket = next(r for r in db.list_requests(conn)
                       if "lap blanket" in r.item_description)
    assert blanket.category.value == "gifts"


def _flat(path) -> str:
    """Prose with its line wrapping removed, so a phrase that happens to
    break across two lines still matches."""
    return re.sub(r"\s+", " ", path.read_text())


def test_the_prompt_carries_the_definitions_verbatim():
    text = _flat(config.PROMPTS_DIR / "intake_agent.md")
    for phrase in (
        "Always paid by Wishing Tree directly to the provider",
        "soap, shampoo, toothpaste, deodorant, period products",
        "backpacks, notebooks, pens, calculators",
        "lamps, bedding, towels, kitchenware, small furniture",
        "home safety or accessibility items such as a shower chair",
        "only when nothing above fits",
    ):
        assert phrase in text, phrase


def test_the_prompt_says_a_wish_needs_a_cost():
    text = _flat(config.PROMPTS_DIR / "intake_agent.md")
    assert "About how much is it on the store page?" in text
    assert "Target or" in text and "Walmart" in text
    assert "Never leave it empty" in text


def test_the_price_guide_grew_where_it_was_asked_to():
    import json
    guide = json.loads(config.PRICE_GUIDE_PATH.read_text())
    counts: dict[str, int] = {}
    for item in guide["items"]:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    assert counts.get("household", 0) >= 15
    assert counts.get("clothing", 0) >= 15
    review = (config.OUTPUT_DIR / "price_guide_review.md").read_text()
    assert "## Household" in review
    assert f"**{len(guide['items'])} entries**" in review


def test_the_matchmaker_is_told_not_to_say_zero_days():
    text = _flat(config.PROMPTS_DIR / "matchmaker_agent.md")
    assert "waiting 0 days" in text          # named, in order to forbid it
    assert "seven days or more" in text


# --------------------------------------------------------------------------
# A neighbor never reads the agent's own words
# --------------------------------------------------------------------------

def test_a_held_wish_says_what_to_change_in_our_words(client):
    from backend import text as copy
    cash = copy.held_reason(["cash_request"])
    assert "Wishing Tree never does that" in cash
    assert "rent or utilities" in cash

    # Every flag kind has a line of its own, so none falls through to a
    # shrug. The default exists for a review that raised nothing at all.
    from backend.models import SafetyFlagKind
    for kind in SafetyFlagKind:
        assert copy.held_reason([kind.value]) != copy.HELD_DEFAULT, kind


def test_the_approval_response_carries_no_agent_prose(client):
    """`note_to_family` is still written and still stored for the activity
    log. It simply never reaches the person who made the wish."""
    import inspect
    from backend import intake_api
    source = inspect.getsource(intake_api)
    returns = source[source.index("def _review_and_publish"):]
    assert '"held_reason"' in returns
    assert '"note_to_family": review.note_to_family' not in returns


# --------------------------------------------------------------------------
# The two neighbor pages
# --------------------------------------------------------------------------

def test_my_wishes_and_make_a_wish_are_separate_pages():
    app = (FRONTEND / "src" / "App.tsx").read_text()
    assert 'path="/family" element={<MyWishesPage />}' in app
    assert 'path="/family/new" element={<Intake />}' in app

    wishes = (FRONTEND / "src" / "pages" / "MyWishesPage.tsx").read_text()
    chat = (FRONTEND / "src" / "pages" / "Intake.tsx").read_text()
    assert "neighborLinks('wishes')" in wishes
    assert "neighborLinks('new')" in chat
    # Neither page renders the other's half.
    assert "startIntake" not in wishes
    assert "<MyWishes" not in chat


def test_the_chat_greeting_is_the_one_that_was_asked_for():
    from backend import intake_api
    assert intake_api.GREETING.startswith("Hi neighbor, I'm so glad you're here.")
    assert "a coat for a growing kid" in intake_api.GREETING
    assert "No need to share your address" in intake_api.GREETING


def test_the_chat_keeps_the_keyboard_open():
    """A disabled input loses focus, and a phone closes the keyboard with it."""
    chat = (FRONTEND / "src" / "pages" / "Intake.tsx").read_text()
    composer = chat[chat.index('className="composer"'):]
    composer = composer[:composer.index("</form>")]
    assert "readOnly={busy}" in composer
    assert "disabled={busy}" not in composer
    assert "box.current?.focus()" in chat


def test_the_message_counter_waits_until_it_matters():
    chat = (FRONTEND / "src" / "pages" / "Intake.tsx").read_text()
    assert "turnsLeft <= 5" in chat


def test_the_privacy_badge_is_not_shown_before_the_check_runs():
    review = (FRONTEND / "src" / "pages" / "WishReview.tsx").read_text()
    assert "checked={false}" in review
    card = (FRONTEND / "src" / "components" / "WishCard.tsx").read_text()
    assert "checked = true" in card


def test_a_wish_without_a_cost_cannot_be_posted():
    review = (FRONTEND / "src" / "pages" / "WishReview.tsx").read_text()
    assert "missingCost" in review
    assert "disabled={busy || missingCost.length > 0}" in review


# --------------------------------------------------------------------------
# The landing page, and the first impression
# --------------------------------------------------------------------------

LANDING = FRONTEND / "src" / "pages" / "Landing.tsx"
BITS = FRONTEND / "src" / "components" / "LandingBits.tsx"


def test_the_doors_say_who_they_are_for():
    source = LANDING.read_text()
    assert "If you could use a hand" in source
    assert "If you'd like to help" in source
    assert "'For neighbors'" not in source


def test_the_demo_shortcut_and_the_footer_say_what_was_asked():
    assert ("Continue as an existing neighbor or wish granter, without signing up."
            in LANDING.read_text())
    footer = (FRONTEND / "src" / "components" / "Footer.tsx").read_text()
    assert "Wishing Tree pays rent and utilities directly to the landlord or provider" \
        in re.sub(r"\s+", " ", footer)


def test_the_footer_reads_the_week_as_a_standing_arrangement():
    """"Thursdays 4-7 PM", not "Thursday 4:00 PM-7:00 PM"."""
    footer = (FRONTEND / "src" / "components" / "Footer.tsx").read_text()
    assert "function recurring" in footer
    assert "${day}s ${hours(windowLabel)}" in footer


def test_the_hero_shows_the_real_tree(client):
    """Real leaves, real gold, from the same endpoint a granter reads."""
    source = LANDING.read_text()
    assert "<WishTree" in source
    assert "getWishes(EMPTY_FILTERS)" in source
    assert "swaying" in source and "compact" in source
    # And that endpoint answers a stranger, which is what makes it possible.
    body = client.get("/api/wishes").json()
    assert body["count"] > 0


def test_the_example_wish_is_a_real_one_and_a_steady_one():
    """The oldest open wish: real, so nothing is invented, and the same one
    between two page loads."""
    source = LANDING.read_text()
    assert "days_waiting" in source
    assert "Here's what a wish looks like" in source


def test_a_signed_out_visitor_is_invited_rather_than_blocked():
    """Tapping a leaf leads somewhere they can finish, carrying the wish."""
    source = LANDING.read_text()
    assert 'grantLabel="Grant this wish"' in source      # not "I'll grant"
    assert "/donor?wish=${wish.id}" in source
    assert "/login?next=" in source

    login = (FRONTEND / "src" / "pages" / "LogIn.tsx").read_text()
    assert "get('next')" in login
    assert "take you straight back to that wish" in login

    donor = (FRONTEND / "src" / "pages" / "Donor.tsx").read_text()
    assert "get('wish')" in donor
    assert "setConfirming(found)" in donor
    # And the id is dropped afterwards, so a refresh does not reopen it.
    assert "navigate('/donor', { replace: true })" in donor


def test_the_signed_out_header_puts_the_two_ways_in_on_the_right():
    bar = (FRONTEND / "src" / "components" / "TopBar.tsx").read_text()
    right = bar[bar.index('className="topbar__right"'):]
    right = right[:right.index("{alias && (")]
    assert 'to="/login"' in right
    assert 'btn btn--primary btn--small' in right        # Create account, filled
    # And the current page's link is lit, without each page being told to.
    assert "const here = useLocation().pathname" in bar
    assert "link.active ?? (link.to ? here === link.to : false)" in bar


# --------------------------------------------------------------------------
# Motion, and turning it off
# --------------------------------------------------------------------------

def test_every_piece_of_landing_motion_can_be_switched_off():
    css = (FRONTEND / "src" / "styles.css").read_text()
    reduced = css[css.rindex("@media (prefers-reduced-motion: reduce)"):]
    for piece in (".tree--swaying .leaf", ".drift__leaf", ".reveal"):
        assert piece in reduced, piece
    assert ".drift { display: none; }" in reduced


def test_the_count_up_and_the_reveal_respect_the_setting():
    bits = BITS.read_text()
    # Both check the preference themselves rather than relying on CSS alone,
    # because both change what is in the DOM, not just how it moves.
    assert bits.count("prefers-reduced-motion: reduce") >= 2
    assert "setShown(to)" not in bits or "useState(to)" in bits


def test_nothing_on_the_landing_page_flashes():
    """Slow is the whole brief. Nothing under two seconds, except the two
    hover lifts and the fade-in, which are responses to an action."""
    css = (FRONTEND / "src" / "styles.css").read_text()
    sway = css[css.index(".tree--swaying .leaf {"):]
    assert "7s" in sway[:120]
    glint = css[css.index("@keyframes glint"):]
    assert "0%, 92%, 100% { opacity: 0; }" in glint      # dark 92% of the time
    # The drift's own timings moved onto the elements when it was made
    # visible; `test_the_falling_leaves_are_actually_visible_now` checks them.
    drift = css[css.index(".drift__leaf {"):]
    assert "opacity: 0.18" in drift[:300]


# --------------------------------------------------------------------------
# About
# --------------------------------------------------------------------------

def test_kelly_comes_first_on_the_about_page():
    source = (FRONTEND / "src" / "pages" / "About.tsx").read_text()
    assert source.index("Hi, I'm Kelly.") < source.index("Why Wishing Tree exists")
    assert '<h1 className="page__title">Hi, I\'m Kelly.</h1>' in source
    assert "Who I am" not in source


def test_the_closing_line_moved_to_the_end_unchanged():
    source = (FRONTEND / "src" / "pages" / "About.tsx").read_text()
    flat = re.sub(r"\s+", " ", source)
    line = ("Wishing Tree is starting in New Haven, and I'm the first coordinator, "
            "so if your wish is granted, I may be the one who brings it to your door.")
    assert line in flat
    assert flat.count("I'm the first coordinator") == 1      # moved, not copied
    assert source.index("about__closing") > source.index("How we protect privacy")


def test_no_other_about_wording_changed():
    """The rest of that page is Kelly's, word for word."""
    flat = re.sub(r"\s+", " ", (FRONTEND / "src" / "pages" / "About.tsx").read_text())
    for sentence in (
        "For seven years, I volunteered at a soup kitchen.",
        "Need doesn't keep a calendar.",
        "Wishing Tree is that bridge: the giving tree, online and all year round,",
        "Neighbors are never shown by name or address.",
        "I'm Kelly, an MBA student at Yale School of Management.",
    ):
        assert sentence in flat, sentence


# --------------------------------------------------------------------------
# Warmth: the glow, the hills, the bands, the grain
# --------------------------------------------------------------------------

CSS = (FRONTEND / "src" / "styles.css").read_text()


def _hex_luminance(value: str) -> float:
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(fg: str, bg: str) -> float:
    light, dark = sorted((_hex_luminance(fg), _hex_luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


TEXT_COLORS = {"--ink": "#2B2B2B", "--ink-soft": "#5F5A53",
               "--evergreen-deep": "#22463C"}
NEW_BACKGROUNDS = {"--glow-peach": "#F8E6D2", "--band-sage": "#E8EFE7",
                   "--band-sand": "#F6EBDA", "--hill-sage": "#C9D7C6"}


def test_the_new_tones_are_the_ones_in_the_stylesheet():
    """So this file cannot drift away from what the app actually paints."""
    for name, value in {**TEXT_COLORS, **NEW_BACKGROUNDS}.items():
        assert f"{name}:" in CSS
        assert value in CSS, f"{name} is no longer {value}"


@pytest.mark.parametrize("bg", sorted(NEW_BACKGROUNDS))
def test_text_stays_readable_on_every_warm_background(bg):
    """Every text color against every new background, at the AA bar of 4.5."""
    for text, fg in TEXT_COLORS.items():
        got = contrast(fg, NEW_BACKGROUNDS[bg])
        assert got >= 4.5, f"{text} on {bg} is only {got:.1f}:1"


def test_the_falling_leaves_are_actually_visible_now():
    bits = BITS.read_text()
    assert bits.count("animationDuration") == 18        # nine leaves, fall and spin
    block = CSS[CSS.index(".drift__leaf {"):]
    assert "opacity: 0.18" in block[:300]

    # Fifteen to twenty-five seconds each, as asked.
    import re as _re
    seconds = [float(s) for s in _re.findall(r"animationDuration: '(\d+(?:\.\d+)?)s'", bits)]
    falls = [s for s in seconds if s >= 15]
    assert len(falls) == 9
    assert all(15 <= s <= 25 for s in falls), falls


def test_the_leaves_sway_and_spin_as_well_as_fall():
    assert "@keyframes fall" in CSS
    sway = CSS[CSS.index("@keyframes sway-fall"):]
    assert "translateX(-16px) rotate(0deg)" in sway[:260]
    assert "rotate(300deg)" in sway[:400]


def test_the_leaves_are_only_on_the_two_pages_that_asked_for_them():
    pages = FRONTEND / "src" / "pages"
    with_leaves = {p.name for p in pages.glob("*.tsx")
                   if "<DriftingLeaves" in p.read_text()}
    assert with_leaves == {"Landing.tsx", "About.tsx"}

    warm = {p.name for p in pages.glob("*.tsx") if "useBodyClass('wt-warm')" in p.read_text()}
    assert warm == {"Landing.tsx", "About.tsx"}


def test_the_leaves_never_sit_on_top_of_anything():
    block = CSS[CSS.index(".drift {"):]
    assert "pointer-events: none" in block[:200]
    assert "z-index: 0" in block[:200]
    # And the content is lifted above them, with the self-positioning pieces
    # left alone — the bug that flattened the tab bar twice.
    assert ".landing > *:not(.topbar):not(.tabbar):not(.drift)" in CSS
    assert ".about > *:not(.topbar):not(.tabbar):not(.drift)" in CSS


def test_the_landing_page_has_one_logo_not_two():
    source = LANDING.read_text()
    assert "hero__logo" not in source
    assert "<Logo" not in source                      # the header carries it
    assert '<h1 className="hero__tagline">' in source  # the tagline is the headline


def test_the_tree_is_planted():
    assert "export function Hills" in BITS.read_text()
    assert 'hills={<Hills />}' in LANDING.read_text()
    # Inside the canvas, where the ground is, not under the caption.
    tree = (FRONTEND / "src" / "components" / "WishTree.tsx").read_text()
    canvas = tree[tree.index('className="tree__canvas"'):]
    assert "{hills}" in canvas[:160]
    # And the flat shadow gives way, or it reads as a puddle on the grass.
    assert "{!hills && (" in tree


def test_nothing_decorative_widens_the_page():
    """Both bugs this problem produced: a 300%-wide hill and an absolutely
    positioned glow, each of which gave the page a sideways scrollbar."""
    hills = CSS[CSS.index(".hills {"):]
    assert "width: 100vw" in hills[:420]
    assert "width: 300%" not in CSS
    # The glow is painted on the body, which is the size of the window.
    assert "body.wt-warm {" in CSS
    assert ".about::before" not in CSS


def test_the_bands_alternate_and_fade_into_each_other():
    source = LANDING.read_text()
    assert 'band band--sage" aria-label="How it works"' in source
    assert 'band band--sand" aria-label="An example wish"' in source
    # Each selector appears twice — once for the shared full-bleed layout,
    # once for its own gradient. It is the gradient we are checking.
    for band in ("band--sage", "band--sand"):
        rule = re.search(rf"\.{band} \{{\s*background:(.+?)\}}", CSS, re.S)
        assert rule, band
        # Transparent at both ends, so one gives way to the next.
        assert "transparent 0%" in rule.group(1)
        assert "transparent 100%" in rule.group(1)


def test_the_grain_is_too_faint_to_notice():
    # The definition, not the one-line z-index tweak that follows it.
    grain = CSS[CSS.index(".grain::after {\n"):]
    assert "opacity: 0.035" in grain[:200]
    assert "feTurbulence" in grain[:900]               # inline, no asset to ship
    assert "pointer-events: none" in grain[:200]


def test_all_of_the_new_motion_switches_off():
    reduced = CSS[CSS.rindex("@media (prefers-reduced-motion: reduce)"):]
    assert ".drift__fall, .drift__leaf { animation: none; }" in reduced
    assert ".drift { display: none; }" in reduced
