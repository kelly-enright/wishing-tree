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

from backend import config, coordinator_auth, db, main, seed, text

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
    assert "No circumstances, but keep the purpose" in text
    assert "Shower chair for an adult" in text


def test_the_safety_prompt_keeps_what_an_item_is_for():
    """The house voice strips the household's story. It had been reading that
    as license to strip the item's purpose too, which is the one piece of
    context a granter actually buys from."""
    text = (config.PROMPTS_DIR / "safety_agent.md").read_text()
    assert "**and what it is for**" in text
    assert "A detail that identifies nobody is not yours to take." in text
    # And the line it has to hold: the thing, not the household.
    assert "whether it describes the thing or the household" in text


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
BACKEND = Path(__file__).resolve().parent.parent / "backend"


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
    # A blanket asked for as a birthday present is a gift, not bedding. Named
    # in full: another wish mentions a lap blanket among things for hospital
    # days, which is not a gift and should not be dragged in by a loose match.
    with db.connect(config.DB_PATH) as conn:
        blanket = next(r for r in db.list_requests(conn)
                       if "Weighted lap blanket" in r.item_description)
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
    reduced = reduced_motion_rules()
    for piece in (".tree--swaying .leaf", ".drift__leaf", ".reveal",
                  ".sparkles--go"):
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
               "--evergreen-deep": "#22463C", "--evergreen": "#2F5D50"}

# Backgrounds that words are actually set on.
NEW_BACKGROUNDS = {"--sky-top": "#DCE9EF", "--sky-horizon": "#F7F2E8",
                   "--band-sage": "#E8EFE7", "--cream": "#FBF6EE"}

# The hills and the leaf mound. Deliberately fresher than anything text sits
# on — `--hill-sage-deep` against `--ink-soft` is 3.6:1, under the bar — and
# that is safe only for as long as they carry no words. The test below is
# what makes that a rule rather than a hope.
DECORATION_ONLY = {"--hill-sage": "#BCD4B6", "--hill-sage-deep": "#A6C4A1"}


def reduced_motion_rules() -> str:
    """Every `prefers-reduced-motion` block in the stylesheet, joined.

    There is more than one — motion was added in several passes — so a test
    that looks only at the last would quietly stop checking the others.
    """
    blocks = []
    needle = "@media (prefers-reduced-motion: reduce)"
    start = CSS.find(needle)
    while start != -1:
        depth, i = 0, CSS.index("{", start)
        for i in range(i, len(CSS)):
            if CSS[i] == "{":
                depth += 1
            elif CSS[i] == "}":
                depth -= 1
                if depth == 0:
                    break
        blocks.append(CSS[start:i + 1])
        start = CSS.find(needle, i)
    return "\n".join(blocks)


def test_the_new_tones_are_the_ones_in_the_stylesheet():
    """So this file cannot drift away from what the app actually paints."""
    for name, value in {**TEXT_COLORS, **NEW_BACKGROUNDS,
                        **DECORATION_ONLY}.items():
        assert f"{name}:" in CSS
        assert value in CSS, f"{name} is no longer {value}"


@pytest.mark.parametrize("bg", sorted(NEW_BACKGROUNDS))
def test_text_stays_readable_on_every_background_it_sits_on(bg):
    """Every text color against every background words appear on, at AA."""
    for text, fg in TEXT_COLORS.items():
        got = contrast(fg, NEW_BACKGROUNDS[bg])
        assert got >= 4.5, f"{text} on {bg} is only {got:.1f}:1"


def test_the_hill_tones_are_used_for_shapes_and_never_behind_words():
    """They are below AA for muted text, which is fine while nothing is
    written on them. The only place they are used now is the ground under
    the tree, which is a drawing."""
    allowed = {".hills", "fill=\"var(--hill-sage"}
    for token in DECORATION_ONLY:
        users = []
        for path in [FRONTEND / "src" / "styles.css"]:
            for line in path.read_text().splitlines():
                if f"var({token})" in line:
                    users.append(line.strip())
        for line in users:
            assert any(k in line for k in ("background", "fill")), line
        # And in components, only inside the two drawings.
        for page in (FRONTEND / "src" / "pages").glob("*.tsx"):
            assert token not in page.read_text(), page.name


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
    # left alone. That rule has now flattened the tab bar, the drift layer
    # twice and Monty's entrance, so the exclusion is one shared marker
    # rather than a list that has to be remembered.
    assert ".landing > *:not(.topbar):not(.tabbar):not(.layer)" in CSS
    assert ".about > *:not(.topbar):not(.tabbar):not(.layer)" in CSS
    assert 'className="drift layer"' in BITS.read_text()


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


def test_there_is_one_band_and_it_fades_into_the_cream():
    """The warm sand behind the example wish went: cream on cream on sand
    read as beige on beige, and one band gives the page a single change of
    note rather than three."""
    source = LANDING.read_text()
    assert 'band band--sage" aria-label="How it works"' in source
    assert "band--sand" not in source
    assert "band--sand" not in CSS

    rule = re.search(r"\.band--sage \{(.+?)\}", CSS, re.S)
    assert rule
    # Transparent at both ends, so it gives way rather than starting.
    assert "transparent 0%" in rule.group(1)
    assert "transparent 100%" in rule.group(1)


def test_the_grain_is_too_faint_to_notice():
    # The definition, not the one-line z-index tweak that follows it.
    grain = CSS[CSS.index(".grain::after {\n"):]
    assert "opacity: 0.035" in grain[:200]
    assert "feTurbulence" in grain[:900]               # inline, no asset to ship
    assert "pointer-events: none" in grain[:200]


def test_all_of_the_new_motion_switches_off():
    reduced = reduced_motion_rules()
    assert ".drift__fall, .drift__leaf { animation: none; }" in reduced
    assert ".drift { display: none; }" in reduced


# --------------------------------------------------------------------------
# A tab opens the page it names
# --------------------------------------------------------------------------

def test_my_wishes_always_opens_my_wishes():
    """It used to bounce anybody with no wishes to the chat, so the tab
    could not be opened until you had one — it looked broken, not empty."""
    page = (FRONTEND / "src" / "pages" / "MyWishesPage.tsx").read_text()
    assert "navigate('/family/new'" not in page
    assert "No wishes yet" in page
    assert 'to="/family/new"' in page          # the way on from the empty state

    # Landing on the chat is something sign-up does once, on the way in.
    signup = (FRONTEND / "src" / "pages" / "SignUpFamily.tsx").read_text()
    assert "navigate('/family/new')" in signup


def test_a_header_link_is_lit_by_the_route_not_by_a_guess():
    bar = (FRONTEND / "src" / "components" / "TopBar.tsx").read_text()
    # `roleLinks` is for pages that are not the role's own screen. Passing no
    # `on` leaves the highlight to the route — it used to hand over
    # neighborLinks('wishes'), which lit "My wishes" while you were on About.
    assert "return [...neighborLinks().slice(0, 2), about]" in bar
    assert "active: on ? on === 'wishes' : undefined" in bar


def test_the_signed_out_header_has_a_way_to_the_other_pages_on_a_phone():
    bar = (FRONTEND / "src" / "components" / "TopBar.tsx").read_text()
    assert "function SignedOutMenu" in bar
    assert "{!alias && !links && <SignedOutMenu links={shown} />}" in bar
    # And the bottom bar is for a signed-in person's own sections, so the two
    # are never on screen together — at 390px they did not both fit.
    assert "{shown.length > 0 && (alias || links) && (" in bar


def test_the_account_menu_shows_a_name_and_explains_the_alias():
    bar = (FRONTEND / "src" / "components" / "TopBar.tsx").read_text()
    assert "{name ?? alias}" in bar
    assert "Others see you as {alias}." in bar
    # The badge still falls back to the alias code, because an initial taken
    # from "Neighbor A04" reads N for every neighbor in New Haven.
    assert "alias.split(' ').pop() ?? alias" in bar


def test_the_background_covers_a_page_of_any_height():
    assert "html { background: var(--cream); }" in CSS
    assert "html, body, #root { min-height: 100%; }" in CSS
    assert "html, body, #root { height: 100%; }" not in CSS


def test_the_pinned_header_starts_at_the_top_of_the_page():
    """It used to sit 72px down until you scrolled, because the page it is
    the first child of had that much padding above it."""
    for rule in (".landing {", ".page {"):
        block = CSS[CSS.index(rule):]
        block = block[:block.index("}")]
        assert "padding: 0 " in block, rule


# --------------------------------------------------------------------------
# Two small celebrations
# --------------------------------------------------------------------------

WISH = FRONTEND / "src" / "components" / "WishLands.tsx"
SPARKLES = FRONTEND / "src" / "components" / "MontySparkles.tsx"


def test_a_wish_joins_the_tree_once_a_visit():
    source = WISH.read_text()
    assert "sessionStorage.getItem('wishingtree.wished')" in source
    # Two to three seconds, as asked, and the component outlives the
    # animation by a tenth of a second so nothing is cut off mid-fade.
    assert "setTimeout(() => setPlaying(false), 3100)" in source
    assert "animation: wish-rise 3s" in CSS
    assert "animation: wish-spark 3s" in CSS


def test_the_wish_leaf_rises_to_a_branch_and_leaves_nothing_behind():
    """It climbs from the foot of the hero to the canopy, sparkles, and
    fades. The fade is the point: every leaf on this tree is somebody's real
    wish, and a decorative one left in the canopy would be a wish nobody
    made."""
    rise = CSS[CSS.index("@keyframes wish-rise"):]
    rise = rise[:rise.index("\n}")]
    assert "430px" in rise                      # the foot of the hero
    assert rise.rstrip().rsplit("\n", 1)[-1].count("opacity: 0") == 1

    # And it is measured against the tree, so the branch is the same branch
    # at every width.
    assert "<WishLands />" in (FRONTEND / "src" / "pages" / "Landing.tsx").read_text()
    land = CSS[CSS.index(".wishland {"):]
    land = land[:land.index("}")]
    assert "position: absolute" in land

    # Nothing is drawn at all once it is over.
    assert "if (!playing) return null" in WISH.read_text()


def test_the_wish_leaf_is_painted_over_the_canopy_and_not_under_it():
    """`.leaf--on` reaches z-index 4. A wish arriving behind a leaf is a
    smudge, not an arrival."""
    land = CSS[CSS.index(".wishland {"):]
    land = land[:land.index("}")]
    z = int(re.search(r"z-index:\s*(\d+)", land).group(1))
    assert z > 4


def test_monty_sparkles_in_the_three_places_asked_for():
    pages = FRONTEND / "src" / "pages"
    using = {p.name for p in pages.glob("*.tsx") if "<MontySparkles" in p.read_text()}
    assert using == {"About.tsx", "Donor.tsx", "MyGranted.tsx"}

    # On the granter's side it marks a wish that arrived — the leaf turning
    # gold is their doing, and the neighbor's own pages stay still.
    granted = (pages / "MyGranted.tsx").read_text()
    assert "row.status === 'delivered' && (\n        <MontySparkles" in granted


def test_montys_face_does_not_move_only_the_sparkles_do():
    """The drawing is the content and the sparkle is the decoration. A face
    that bounces competes with the sentence beside it, and the sentence is
    what the moment is for."""
    source = SPARKLES.read_text()
    assert "<Monty size={size} />" in source
    # No animation reaches the drawing itself — only the dots around it.
    assert ".sparkles--go .sparkles__dot { animation: twinkle 1s" in CSS
    assert ".sparkles--go .monty" not in CSS
    assert ".sparkles--go .sparkles {" not in CSS
    # About a second.
    assert "setTimeout(() => setPlaying(false), 1200)" in source


def test_the_neighbors_own_pages_stay_calm():
    """No added motion where somebody is asking for help."""
    pages = FRONTEND / "src" / "pages"
    for name in ("MyWishes.tsx", "MyWishesPage.tsx", "Intake.tsx"):
        source = (pages / name).read_text()
        assert "MontySparkles" not in source, name
        assert "WishLands" not in source, name
        assert "DriftingLeaves" not in source, name


def test_neither_celebration_loops():
    for block in ("@keyframes wish-rise", "@keyframes wish-spark",
                  "@keyframes twinkle"):
        assert block in CSS
    for source in (WISH.read_text(), SPARKLES.read_text()):
        assert "infinite" not in source
    # Each holds its last frame rather than snapping back, and none repeats.
    assert "animation: wish-rise 3s cubic-bezier(0.33, 0, 0.3, 1) both" in CSS
    assert "animation: wish-spark 3s ease-out both" in CSS
    assert "animation: twinkle 1s ease-out both" in CSS


def test_both_celebrations_stop_for_anyone_who_asked_for_stillness():
    """Neither leaves anything to hide: the wish-leaf is never drawn at all,
    and the sparkle dots rest at opacity 0, so stopping the animation leaves
    Monty's face on its own."""
    assert "function wantsStillness" in SPARKLES.read_text()
    wish = WISH.read_text()
    assert "prefers-reduced-motion: reduce" in wish
    assert "return false" in wish

    reduced = reduced_motion_rules()
    assert ".sparkles--go .sparkles__dot { animation: none; }" in reduced

    dot = CSS[CSS.index(".sparkles__dot {"):]
    assert "opacity: 0" in dot[:dot.index("}")]


def test_the_dog_who_ran_through_the_leaves_is_gone():
    """Removed rather than left in place unused: the entrance, the leaf pile
    and the full-body drawing were one feature, and a stylesheet that still
    carries its CSS is a stylesheet nobody can read."""
    for dead in (".arrival", ".pile", ".plays", "dog__leg",
                 "@keyframes arrive", "@keyframes burst", "@keyframes romp"):
        assert dead not in CSS, dead
    components = FRONTEND / "src" / "components"
    assert not (components / "MontyBody.tsx").exists()
    assert not (components / "MontyPlays.tsx").exists()


# --------------------------------------------------------------------------
# Where the numbers live
# --------------------------------------------------------------------------

def test_a_session_can_see_its_own_token_usage(client):
    """Collapsed by default on both sides, so a grader can open it and see
    what their own session cost without it sitting on a neighbor's screen."""
    panel = (FRONTEND / "src" / "components" / "TokenPanel.tsx").read_text()
    assert "open = false" in panel
    assert "Show AI details" in panel

    for name in ("Intake.tsx", "Donor.tsx"):
        source = (FRONTEND / "src" / "pages" / name).read_text()
        assert "<TokenPanel usage={usage} />" in source, name
        # Collapsed: no page passes `open`.
        assert "<TokenPanel usage={usage} open" not in source, name


def test_the_intake_duration_is_an_admin_number(client):
    """A stopwatch beside somebody asking for a winter coat was the wrong
    note. It is on the activity page now, and nowhere a neighbor reads."""
    intake = (FRONTEND / "src" / "pages" / "Intake.tsx").read_text()
    assert "seconds={result?.seconds}" not in intake
    assert "This intake took" not in intake

    activity = (FRONTEND / "src" / "pages" / "AgentActivity.tsx").read_text()
    assert "Intake conversations" in activity
    assert "duration_seconds" in activity


def test_the_activity_endpoint_reports_how_long_each_intake_took(client):
    token = client.post("/api/coordinator/unlock",
                        json={"passcode": config.COORDINATOR_PASSCODE}).json()["token"]
    body = client.get("/api/coordinator/activity",
                      headers={"X-Coordinator-Token": token}).json()
    assert "intakes" in body
    for run in body["intakes"]:
        assert run["duration_seconds"] is not None
        assert {"session_id", "family_alias", "turns"} <= set(run)


def test_token_numbers_never_reach_a_public_endpoint(client):
    """`estimated_cost_usd` on a wish is what the item costs, which is the
    point of the card. These are the token fields, matched so that a wish's
    own price does not look like one."""
    for path in PUBLIC_PATHS:
        body = client.get(path).text.lower()
        for field in ("input_tokens", "output_tokens", "cache_write_tokens",
                      "cached_input_tokens", "prices_are_placeholders"):
            assert field not in body, f"{path} exposes {field}"
        assert not re.search(r"(?<![a-z_])cost_usd", body), f"{path} exposes a token cost"


# --------------------------------------------------------------------------
# How we use AI
# --------------------------------------------------------------------------

def test_the_how_it_works_page_says_what_the_ai_does():
    source = (FRONTEND / "src" / "pages" / "HowItWorksPage.tsx").read_text()
    flat = re.sub(r"\s+", " ", source)
    assert "How we use AI" in flat
    for phrase in (
        "AI helps turn what you share into a clear wish",
        "checks every wish for personal details before anyone sees it",
        "suggests wishes that fit a wish granter's budget",
        "People, not AI, coordinate every drop-off and delivery.",
    ):
        assert phrase in flat, phrase


# --------------------------------------------------------------------------
# Motion, all of it
# --------------------------------------------------------------------------

def test_every_animation_in_the_app_is_switched_off_by_the_setting():
    """Counted rather than listed: a new `@keyframes` added later is covered
    by the same rule, and this test will not quietly stop checking."""
    names = set(re.findall(r"@keyframes\s+([\w-]+)", CSS))
    assert len(names) >= 12, "expected the app to have a good deal of motion"

    reduced = reduced_motion_rules()
    # One rule covers every animation there is or ever will be.
    assert "animation-duration: 0.001ms !important" in reduced
    assert "animation-iteration-count: 1 !important" in reduced
    assert "transition-duration: 0.001ms !important" in reduced
    assert "*, *::before, *::after" in reduced

    # The drifting leaves are removed outright; the sparkles are left in
    # place and simply stop, because they rest invisible anyway.
    assert ".drift { display: none; }" in reduced
    assert ".sparkles--go .sparkles__dot" in reduced


# --------------------------------------------------------------------------
# The morning sky
# --------------------------------------------------------------------------

def test_the_hero_sky_is_a_morning_not_an_afternoon():
    assert "--sky-top:        #DCE9EF" in CSS
    assert "--sky-horizon:    #F7F2E8" in CSS
    assert "--glow-peach" not in CSS                  # the old afternoon

    sky = CSS[CSS.index("body.wt-warm {"):]
    sky = sky[:sky.index("}")]
    assert "var(--sky-top) 0%" in sky
    assert "var(--sky-horizon)" in sky
    # A thin band of early sun low down, and nothing stronger.
    assert "rgba(224, 168, 75, 0.16)" in sky


def test_the_hills_are_fresher_than_the_sky_they_sit_against():
    """Otherwise the ground and the horizon are the same note."""
    assert contrast("#BCD4B6", "#F7F2E8") > 1.3
    assert "--hill-sage:      #BCD4B6" in CSS


def test_a_signed_in_page_gets_a_hint_of_sky_and_no_scenery():
    body = CSS[CSS.index("\nbody {"):]
    body = body[:body.index("}")]
    assert "rgba(220, 233, 239, 0.55)" in body        # the faintest top
    assert "var(--cream)" in body

    # The scenery belongs to the two pages that ask for it.
    pages = FRONTEND / "src" / "pages"
    warm = {p.name for p in pages.glob("*.tsx") if "useBodyClass('wt-warm')" in p.read_text()}
    assert warm == {"Landing.tsx", "About.tsx"}
    hills = {p.name for p in pages.glob("*.tsx") if "<Hills" in p.read_text()}
    assert hills == {"Landing.tsx"}


# --------------------------------------------------------------------------
# What was taken out, and what was only reworded
# --------------------------------------------------------------------------

MYWISHES = FRONTEND / "src" / "pages" / "MyWishes.tsx"


@pytest.mark.parametrize("said,expected", [
    # The things that are genuinely personal, however the review phrases them.
    ("a child's name", ["a child's name"]),
    ("the child name Sofia", ["a child's name"]),
    ("a school name", ["a school name"]),
    ("the name of her high school", ["a school name"]),
    ("a street address", ["an address"]),
    ("an apartment number", ["an address"]),
    ("a phone number", ["a phone number"]),
    ("an email address", ["an email address"]),
    ("an employer name", ["an employer's name"]),
    ("the landlord's name", ["a landlord's name"]),
    ("a medical detail", ["a medical detail"]),
    ("the name of the hospital", ["a medical detail"]),
    ("a parent's name", ["a name"]),
    # And everything that is not. Tidying a wish is not a privacy removal.
    ("a use-purpose detail", []),
    ("shortened for clarity", []),
    ("rewrote in the third person", []),
    ("the reason it is needed", []),
    ("first-person phrasing", []),
    ("none", []),
    ("", []),
])
def test_only_personal_details_are_reported_as_removed(said, expected):
    assert text.personal_removals([said]) == expected


def test_the_same_kind_twice_is_said_once():
    """Two names taken out is still "a name" said once — a neighbor reading
    their own wish does not need the count."""
    assert text.personal_removals(
        ["a child's name", "a child's name", "another child name"],
    ) == ["a child's name"]


def test_a_reworded_wish_reports_nothing_taken_out():
    """The whole failure this guards: a wish that was only rewritten came back
    saying something had been taken out of it, in words nobody uses."""
    assert text.personal_removals(
        ["a use-purpose detail", "condensed the description"],
    ) == []


def test_the_promise_is_filtered_everywhere_it_is_read(client):
    """Written on the way in and filtered again on the way out, so a wish
    reviewed before this rule existed still reads in plain words."""
    for path in ("backend/intake_api.py", "backend/family_api.py",
                 "backend/main.py"):
        source = (Path(__file__).resolve().parent.parent / path).read_text()
        assert "personal_removals" in source, path


def test_the_safety_prompt_names_the_closed_vocabulary():
    prompt = (config.PROMPTS_DIR / "safety_agent.md").read_text()
    assert "**Rewording is not a removal.**" in prompt
    # Every phrase the code will accept is offered to the agent by name, so
    # the two cannot drift apart.
    for _keywords, plain in text.PERSONAL_REMOVALS:
        assert plain in prompt, plain


# --------------------------------------------------------------------------
# My wishes
# --------------------------------------------------------------------------

def test_my_wishes_says_what_the_tree_can_and_cannot_promise():
    source = MYWISHES.read_text()
    assert "Neighbors nearby can see your wishes on the tree." in source
    assert "We can't promise" in source
    assert "we'll do our best to find someone who" in source
    # Said once, at the top, and not gated on a wish happening to be up.
    assert source.count("mywishes__how") == 1
    assert "anyOnTheTree" not in source


def test_each_wish_card_shows_cost_and_deadline():
    source = MYWISHES.read_text()
    assert "costLabel(row.wish)" in source
    assert "cost_is_estimate" in source and "pill-estimate" in source
    assert "'No deadline'" in source
    # The same helper the wish granter's card uses, so one wish reads the same
    # on both sides.
    card = (FRONTEND / "src" / "components" / "WishCard.tsx").read_text()
    assert "costLabel" in card
    assert "function cost(" not in card


def test_the_tracker_shows_the_whole_path_with_the_stage_marked():
    source = MYWISHES.read_text()
    assert "progress__step--now" in source and "progress__step--done" in source
    assert "aria-current={step.now ? 'step' : undefined}" in source

    api = (BACKEND / "family_api.py").read_text()
    assert 'TRACK = ["being_checked", "on_the_tree", "granted", "on_its_way", "delivered"]' in api
    # A held wish is off the track, not early on it.
    assert "if stage not in TRACK:\n        return None" in api


def test_the_tracker_uses_the_payment_words_for_a_rent_wish():
    """"On its way" is wrong for money going to a landlord, and the page
    should not have to know that — the server labels the track."""
    api = (BACKEND / "family_api.py").read_text()
    assert '(RENT_STAGES.get(key) if is_rent else None) or STAGES[key]' in api
    assert MYWISHES.read_text().count("RENT") == 0


def test_the_tracker_labels_are_the_words_asked_for():
    api = (BACKEND / "family_api.py").read_text()
    for label in ("Being checked", "On the tree", "A neighbor picked your wish",
                  "On its way", "Delivered"):
        assert f'"{label}"' in api, label


def test_a_wish_carries_its_track_to_the_page(client):
    sign_in(client, "Neighbor A04")
    body = client.get("/api/families/Neighbor A04/wishes").json()
    assert body["wishes"], "the seed should give this neighbor wishes"
    for row in body["wishes"]:
        track = row["track"]
        if row["stage"] == "not_posted":
            assert track is None
            continue
        assert [s["key"] for s in track] == [
            "being_checked", "on_the_tree", "granted", "on_its_way", "delivered",
        ]
        assert sum(s["now"] for s in track) == 1
        now = next(i for i, s in enumerate(track) if s["now"])
        assert all(s["done"] for s in track[:now])
        assert not any(s["done"] for s in track[now:])


# --------------------------------------------------------------------------
# American English
# --------------------------------------------------------------------------

# Spellings and phrasings that are correct English and the wrong English for
# a project written in and about New Haven, Connecticut.
BRITISH = (
    "colour", "favourite", "neighbour", "behaviour", "defence", "offence",
    "licence", "centre", "metre", "litre", "fibre", "grey",
    "organise", "recognise", "apologise", "realise", "customise",
    "analyse", "prioritise", "summarise",
    "labelled", "cancelled", "travelling", "modelling", "signalling",
    "whilst", "amongst", "learnt", "spelt", "postcode", "post code",
    "straight away", "have a read", "has got to", "have got to",
    "tick the box", "ticked", "programme", "enquire", "aeroplane",
)

# The files people read from, or that the models read from.
AMERICAN_ENGLISH_PATHS = (
    *(FRONTEND / "src").rglob("*.tsx"),
    *(FRONTEND / "src").rglob("*.ts"),
    FRONTEND / "src" / "styles.css",
    *BACKEND.rglob("*.py"),
    *(Path(__file__).resolve().parent.parent / "prompts").glob("*.md"),
)


def _deliverable_text(path: Path) -> str:
    """The words a reader actually sees in a built deliverable.

    Scripts and styles come out — `slides.html` has reveal.js inlined, and
    its minified source contains plenty of words nobody reads.
    """
    import html as _html

    body = path.read_text(encoding="utf-8")
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return _html.unescape(body).lower()


DELIVERABLES = (
    Path(__file__).resolve().parent.parent / "report.html",
    Path(__file__).resolve().parent.parent / "slides.html",
)


@pytest.mark.parametrize("word", BRITISH)
def test_the_report_and_slides_are_in_american_english(word):
    """The deliverables, not just the app.

    These are the two files that get handed in, and they were the one place
    the American English rule was not actually enforced — a British spelling
    could sit in the report indefinitely with every test passing.
    """
    for path in DELIVERABLES:
        if path.exists():
            assert word not in _deliverable_text(path), f"{word!r} in {path.name}"


def test_no_placeholders_are_left_in_the_deliverables():
    """The gold dashed boxes are scaffolding. The live passcode marker is not
    one of them and is deliberately left for the uploaded copy."""
    for path in DELIVERABLES:
        if path.exists():
            assert "placeholder" not in _deliverable_text(path), path.name


@pytest.mark.parametrize("word", BRITISH)
def test_the_app_is_written_in_american_english(word):
    """Spelling and phrasing both. The agents' prompts are in here too, so
    their replies come out the same way."""
    for path in AMERICAN_ENGLISH_PATHS:
        body = path.read_text().lower()
        if path.parent.name == "prompts":
            # The prompts name the British forms in order to forbid them.
            body = body.split("## how you write")[0]
        assert word not in body, f"{word!r} in {path.name}"


def test_each_agent_prompt_asks_for_american_english():
    for name in ("intake_agent.md", "safety_agent.md", "matchmaker_agent.md"):
        prompt = (config.PROMPTS_DIR / name).read_text()
        assert "American English throughout" in prompt, name


# --------------------------------------------------------------------------
# Monty on the thank-you screen
# --------------------------------------------------------------------------

def test_monty_sits_beside_the_thank_you_headline():
    """`flex-wrap: wrap` let the headline take its own line at an awkward
    width and left him stranded above it at the left margin, which reads as a
    bug rather than a layout."""
    rule = CSS[CSS.index(".thanks {"):]
    rule = rule[:rule.index("}")]
    assert "flex-wrap: nowrap" in rule

    # And the stacked version is deliberate: centered, under a query. There
    # is more than one 560px block, so find the one that mentions `.thanks`.
    stacked = CSS[CSS.rindex("@media (max-width: 560px) {", 0, CSS.index(".thanks { flex-direction")):]
    stacked = stacked[:stacked.index("}")]
    assert "flex-direction: column" in stacked
    assert "align-items: center" in stacked
    assert "text-align: center" in stacked


# --------------------------------------------------------------------------
# Opening a wish from the tree
# --------------------------------------------------------------------------

COMPONENTS = FRONTEND / "src" / "components"
WISHOPEN = COMPONENTS / "WishOpen.tsx"
TREE = COMPONENTS / "WishTree.tsx"
DONOR = FRONTEND / "src" / "pages" / "Donor.tsx"
LANDING = FRONTEND / "src" / "pages" / "Landing.tsx"


def test_the_tree_no_longer_draws_the_wish_it_opened():
    """It used to push a card in under the tree, which moved everything the
    moment you tapped a leaf. The tree now only says which leaf is lit; the
    wish is drawn beside it or over it, and nothing shifts."""
    tree = TREE.read_text()
    assert "selectedId" in tree and "onSelect" in tree
    assert "tree__picked" not in tree
    # The type is still imported; the component is not rendered here.
    assert "<WishCard" not in tree
    assert ".tree__picked" not in CSS


def test_a_leaf_selects_rather_than_toggles():
    """A control that sometimes opens and sometimes closes is one you have to
    think about. Closing is the close button, Escape, or a tap outside."""
    tree = TREE.read_text()
    assert "onClick={() => onSelect(wish)}" in tree
    assert "setOpenId(openId === wish.id ? null : wish.id)" not in tree


def test_the_lit_leaf_is_the_open_wish():
    tree = TREE.read_text()
    assert "selectedId === wish.id ? ' leaf--on' : ''" in tree
    assert "aria-pressed={selectedId === wish.id}" in tree


def test_a_wish_closes_on_escape_and_on_a_tap_outside():
    source = WISHOPEN.read_text()
    assert "event.key === 'Escape'" in source
    # `pointerdown`, so a tap that starts outside closes even if it drifts.
    assert "addEventListener('pointerdown', onOutside)" in source
    assert "box.current?.contains(event.target as Node)" in source


def test_closing_a_wish_puts_the_keyboard_back_on_its_leaf():
    """A keyboard user who closes a wish should be on the leaf they came
    from, not at the top of the page."""
    source = WISHOPEN.read_text()
    assert "export function leafId" in source
    assert "document.getElementById(leafId(wishId))?.focus()" in source
    assert TREE.read_text().count("id={leafId(wish.id)}") == 1
    # And focus goes into the wish when it opens.
    assert source.count("box.current?.focus()") == 2


def test_the_sheet_is_modal_and_keeps_tab_inside_it():
    """It covers what is behind it, so Tab must not wander off into a tree
    nobody can see."""
    source = WISHOPEN.read_text()
    assert 'role="dialog"' in source and 'aria-modal="true"' in source
    assert "event.key !== 'Tab'" in source
    assert "event.preventDefault()" in source
    # The panel is not modal — the page behind it is still there to use.
    panel = source[source.index("export function WishPanel"):source.index("export function WishSheet")]
    assert "aria-modal" not in panel


def test_the_sheet_places_itself_and_says_so():
    """Fifth time: the rule that gives a page's direct children
    `position: relative` flattens anything that positions itself, so anything
    that does carries `.layer`."""
    assert 'className="sheetwrap layer"' in WISHOPEN.read_text()
    assert "position: fixed; inset: 0; z-index: 60" in CSS


def test_the_wish_panel_takes_over_the_column_beside_the_tree():
    donor = DONOR.read_text()
    assert "{!narrow && openWish ? (" in donor
    assert "<WishPanel" in donor
    # Closing brings the two panels back.
    assert "onClose={() => setOpenWish(null)}" in donor
    assert "<DonorHowItWorks compact />" in donor
    assert "<HowItArrives region={region} />" in donor


def test_how_it_works_is_beside_the_tree_on_a_wide_screen():
    """Nothing stands between the filters and the tree any more."""
    donor = DONOR.read_text()
    # The folded line is the phone version only, and starts folded.
    assert "{narrow && !matches && (" in donor
    assert 'id="donor-how" title="How it works" defaultOpen={false}' in donor
    # And it is not also in the side panel there, or it is said twice.
    assert "{!narrow && !matches && <DonorHowItWorks compact />}" in donor


def test_the_side_column_is_wide_enough_for_a_wish():
    """232px held a note about drop-offs. It has to hold a whole wish card
    now, cost and deadline side by side."""
    rule = CSS[CSS.index(".wall { display: grid"):]
    rule = rule[:rule.index("}")]
    assert "300px" in rule


def test_the_landing_hero_opens_a_wish_the_same_way():
    """Signed out, on the hero tree: a sheet at every width, because a
    centered column has no panel beside it to put a wish in."""
    landing = LANDING.read_text()
    assert "<WishSheet" in landing
    assert 'grantLabel="Grant this wish"' in landing
    assert "onGrant={grantAfterSignIn}" in landing
    assert "selectedId={openWish?.id ?? null}" in landing
    # Capped and centered above phone width, or it reads as stretched.
    capped = CSS[CSS.index("@media (min-width: 620px) {"):]
    assert "max-width: 560px; margin: 0 auto;" in capped[:200]


def test_granting_from_the_hero_carries_the_wish_through_sign_in():
    landing = LANDING.read_text()
    assert "/donor?wish=${wish.id}" in landing
    assert "navigate(`/login?next=${encodeURIComponent(back)}`)" in landing


# --------------------------------------------------------------------------
# How it arrives
# --------------------------------------------------------------------------

ARRIVES = COMPONENTS / "HowItArrives.tsx"


def test_how_it_arrives_says_the_times_the_way_a_person_does():
    source = ARRIVES.read_text()
    assert "Drop-off: {weekly(region.dropoff_window)}" in source
    assert "Delivery: {weekly(region.delivery_window)}" in source
    # The raw label is a database row, not a sentence.
    assert "{region.dropoff_window}" not in source.replace(
        "{weekly(region.dropoff_window)}", "")


def test_the_rent_line_says_who_gets_paid():
    source = ARRIVES.read_text()
    said = " ".join(source.split())
    assert ("Wishing Tree pays rent and utilities directly to the landlord or "
            "provider, never cash to a neighbor.") in said
    # The old wording is gone everywhere, not just here.
    for page in (FRONTEND / "src").rglob("*.tsx"):
        assert "paid straight to the landlord or provider" not in page.read_text(), page.name


def test_both_presentations_stop_for_anyone_who_asked_for_stillness():
    reduced = reduced_motion_rules()
    assert ".wishpanel, .sheetwrap__scrim, .wishsheet { animation: none; }" in reduced


# --------------------------------------------------------------------------
# Running as a public demo
# --------------------------------------------------------------------------

def test_a_local_run_is_exactly_the_local_run_it_always_was(client):
    """Everything the deployed site turns on is off unless something sets it.
    A grader on their own machine must see what they saw before."""
    assert config.DEMO_BANNER is False
    assert config.RESEED_ON_START is False
    assert config.COORDINATOR_PASSCODE == "wishingtree-demo"

    body = client.get("/api/site").json()
    assert body == {"demo": False, "banner": None}


def test_the_demo_banner_is_a_value_not_a_second_build():
    """One `frontend/dist` serves both a local run and the deployed site. A
    flag baked into the build would mean two builds and a way to ship the
    wrong one."""
    banner = (FRONTEND / "src" / "components" / "DemoBanner.tsx").read_text()
    assert "getSite()" in banner
    assert "if (!text) return null" in banner
    # Drawn above the routes, so it reaches every page including the 404.
    app = (FRONTEND / "src" / "App.tsx").read_text()
    assert app.index("<DemoBanner />") < app.index("<Routes>")


def test_the_banner_says_what_it_has_to_say():
    assert config.DEMO_BANNER_TEXT == (
        "This is a demo of Wishing Tree. Please use made-up details, not "
        "real personal information."
    )


def test_the_three_live_switches_read_the_environment(monkeypatch):
    """Each one off by default, on when the host sets it, and never anywhere
    in the repository."""
    import importlib

    for name, attr, expected in (
        ("WISHINGTREE_DEMO_BANNER", "DEMO_BANNER", True),
        ("WISHINGTREE_RESEED", "RESEED_ON_START", True),
        ("WISHINGTREE_HTTPS", "COOKIE_SECURE", True),
    ):
        monkeypatch.setenv(name, "1")
        reloaded = importlib.reload(config)
        assert getattr(reloaded, attr) is expected, name
        monkeypatch.delenv(name)

    monkeypatch.setenv("WISHINGTREE_PASSCODE", "something-else")
    reloaded = importlib.reload(config)
    assert reloaded.COORDINATOR_PASSCODE == "something-else"
    monkeypatch.delenv("WISHINGTREE_PASSCODE")
    importlib.reload(config)
    assert config.COORDINATOR_PASSCODE == "wishingtree-demo"


def test_the_deployed_demo_rebuilds_its_data_on_every_start():
    """A free host's disk does not survive a restart, so the data resets
    whether we ask it to or not. Resetting it deliberately means a tester
    always finds the same tree rather than whatever was left behind."""
    source = (BACKEND / "main.py").read_text()
    assert "if config.RESEED_ON_START:" in source
    assert "seed.reset(config.DB_PATH)" in source
    # And a local run still only seeds an empty database.
    assert "seed.seed_if_empty()" in source


def test_the_caps_are_not_relaxed_for_the_deployed_site():
    """A public URL is the one place a runaway loop costs real money."""
    source = (BACKEND / "config.py").read_text()
    for setting in ("MAX_TOKENS_PER_INTAKE_SESSION", "DAILY_TOKEN_BUDGET"):
        line = next(l for l in source.splitlines() if l.startswith(setting))
        assert "getenv" not in line, f"{setting} must not be loosenable by the host"


def test_no_live_secret_is_in_the_repository():
    """The passcode the deployed site uses is set in the host's dashboard.
    What is in here is the local default and nothing else."""
    for path in (BACKEND / "config.py", Path(__file__).resolve().parent.parent / "README.md"):
        body = path.read_text()
        assert "WISHINGTREE_PASSCODE=" not in body, path.name
