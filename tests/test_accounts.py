"""Accounts: what is stored, who can see what, and how guessing is slowed.

The tests here are mostly about things *not* happening — a password not being
stored, an email not being returned, one person not reaching another's data.
Those are the failures nobody notices until it matters.
"""

import re
import time

import pytest
from fastapi.testclient import TestClient

from backend import accounts, config, coordinator_auth, db, main, seed
from helpers import email_for, sign_in, sign_out


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit_trail.json")
    seed.seed(config.DB_PATH)
    coordinator_auth.clear()
    return TestClient(main.app)


def admin(client):
    token = client.post("/api/coordinator/unlock",
                        json={"passcode": config.COORDINATOR_PASSCODE}).json()["token"]
    return {"X-Coordinator-Token": token}


NEW_ACCOUNT = {
    "zip": "06511",
    "contact_address": "4 Nightingale Ct, New Haven, CT 06511",
    "contact_email": "wren@example.com",
    "password": "a long enough password",
}


# --------------------------------------------------------------------------
# What is stored
# --------------------------------------------------------------------------

def test_a_password_is_never_stored_in_readable_form(client):
    client.post("/api/families", json=NEW_ACCOUNT)

    with db.connect(config.DB_PATH) as conn:
        row = conn.execute(
            "SELECT password_hash FROM accounts WHERE email = ?",
            (NEW_ACCOUNT["contact_email"],),
        ).fetchone()

    assert row is not None
    assert NEW_ACCOUNT["password"] not in row["password_hash"]
    assert row["password_hash"].startswith("$2b$")          # bcrypt, salt included


def test_the_whole_database_holds_no_readable_password(client):
    """Not just the accounts table: no column anywhere has it."""
    client.post("/api/families", json=NEW_ACCOUNT)

    with db.connect(config.DB_PATH) as conn:
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            dumped = str(list(conn.execute(f"SELECT * FROM {table}")))
            assert NEW_ACCOUNT["password"] not in dumped, table
            assert config.DEMO_PASSWORD not in dumped, table


def test_two_accounts_with_one_password_do_not_share_a_hash(client):
    """Salted, so the hashes say nothing about which passwords match."""
    with db.connect(config.DB_PATH) as conn:
        hashes = [r["password_hash"] for r in conn.execute(
            "SELECT password_hash FROM accounts")]
    assert len(hashes) == len(set(hashes))


def test_signing_up_never_returns_the_password(client):
    response = client.post("/api/families", json=NEW_ACCOUNT)
    assert response.status_code == 201
    assert NEW_ACCOUNT["password"] not in response.text
    assert "password" not in response.json()


def test_the_production_work_factor_is_not_the_test_one():
    """conftest lowers the cost for speed. The real default stays high."""
    import importlib
    fresh = importlib.reload(config)
    assert fresh.BCRYPT_ROUNDS == 12


# --------------------------------------------------------------------------
# What a stranger can see
# --------------------------------------------------------------------------

PUBLIC = [
    "/api/stats", "/api/wishes", "/api/accounts", "/api/service-area",
    "/api/retailers", "/api/health",
]


@pytest.mark.parametrize("path", PUBLIC)
def test_no_public_endpoint_leaks_an_email_or_a_hash(client, path):
    body = client.get(path).text
    assert "@" not in body or "example.com" not in body
    assert "$2b$" not in body
    assert "password" not in body.lower()


def test_the_demo_account_list_is_aliases_only(client):
    """It exists so nobody has to sign up to try the app. It must not become
    a directory of who lives where."""
    body = client.get("/api/accounts").json()
    text = str(body)
    with db.connect(config.DB_PATH) as conn:
        for row in conn.execute("SELECT contact_email, contact_address FROM families"):
            assert row["contact_email"] not in text
            assert row["contact_address"] not in text


def test_a_session_cookie_is_not_readable_by_scripts(client):
    client.post("/api/auth/login", json={
        "email": email_for("Neighbor A04"), "password": config.DEMO_PASSWORD,
    })
    header = client.cookies.jar._cookies  # noqa: SLF001
    raw = str(client.post("/api/auth/login", json={
        "email": email_for("Neighbor A04"), "password": config.DEMO_PASSWORD,
    }).headers.get("set-cookie", ""))
    assert "HttpOnly" in raw
    assert "SameSite=lax" in raw or "samesite=lax" in raw.lower()
    assert header is not None


def test_the_session_token_itself_is_not_stored(client):
    """Only a hash of it, so a copy of the table cannot be replayed."""
    client.post("/api/auth/login", json={
        "email": email_for("Neighbor A04"), "password": config.DEMO_PASSWORD,
    })
    token = client.cookies.get(accounts.COOKIE_NAME)
    assert token
    with db.connect(config.DB_PATH) as conn:
        stored = [r["token_hash"] for r in conn.execute("SELECT token_hash FROM sessions")]
    assert stored
    assert token not in stored


# --------------------------------------------------------------------------
# A session sees only its own account
# --------------------------------------------------------------------------

def test_a_neighbor_cannot_read_another_neighbors_wishes(client):
    sign_in(client, "Neighbor A04")
    mine = client.get("/api/families/Neighbor A04/wishes")
    theirs = client.get("/api/families/Neighbor A07/wishes")
    assert mine.status_code == 200
    assert theirs.status_code == 403


def test_a_granter_cannot_read_another_granters_list(client):
    sign_in(client, "Granter D01")
    assert client.get("/api/donors/Granter D01/granted").status_code == 200
    assert client.get("/api/donors/Granter D02/granted").status_code == 403


def test_a_granter_cannot_reach_the_neighbor_side(client):
    sign_in(client, "Granter D01")
    assert client.get("/api/families/Neighbor A04/wishes").status_code == 403


def test_signed_out_means_signed_out(client):
    sign_in(client, "Neighbor A04")
    assert client.get("/api/families/Neighbor A04/wishes").status_code == 200
    sign_out(client)
    assert client.get("/api/families/Neighbor A04/wishes").status_code == 401


def test_an_unknown_alias_answers_like_somebody_elses(client):
    """So the error cannot be used to find out who has an account."""
    sign_in(client, "Neighbor A04")
    unknown = client.get("/api/families/Neighbor Z99/wishes")
    other = client.get("/api/families/Neighbor A07/wishes")
    assert unknown.status_code == other.status_code == 403
    assert unknown.json()["detail"] == other.json()["detail"]


# --------------------------------------------------------------------------
# Logging in
# --------------------------------------------------------------------------

def test_the_right_password_works_and_the_wrong_one_does_not(client):
    email = email_for("Neighbor A04")
    good = client.post("/api/auth/login", json={"email": email, "password": config.DEMO_PASSWORD})
    assert good.status_code == 200
    assert good.json()["alias"] == "Neighbor A04"

    sign_out(client)
    bad = client.post("/api/auth/login", json={"email": email, "password": "not it"})
    assert bad.status_code == 401


def test_a_wrong_password_and_an_unknown_email_read_the_same(client):
    """Neither answer says whether that address has an account."""
    wrong = client.post("/api/auth/login", json={
        "email": email_for("Neighbor A04"), "password": "not it"})
    missing = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "not it"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_repeated_failures_are_slowed_down(client):
    """Five free tries, then a delay that doubles. Measured on the function
    rather than the clock, so the suite does not have to sit through it."""
    email = email_for("Neighbor A04")
    accounts.reset_throttle()

    for _ in range(accounts.FREE_ATTEMPTS):
        assert accounts.failure_delay(email) == 0
        accounts.record_failure(email)

    first = accounts.failure_delay(email)
    assert first > 0
    accounts.record_failure(email)
    assert accounts.failure_delay(email) > first

    for _ in range(20):
        accounts.record_failure(email)
    assert accounts.failure_delay(email) == accounts.MAX_DELAY


def test_the_delay_is_actually_applied_on_a_login(client):
    email = email_for("Neighbor A04")
    for _ in range(accounts.FREE_ATTEMPTS + 1):
        client.post("/api/auth/login", json={"email": email, "password": "not it"})

    started = time.monotonic()
    client.post("/api/auth/login", json={"email": email, "password": "not it"})
    assert time.monotonic() - started >= 0.4


def test_a_good_login_clears_the_record(client):
    email = email_for("Neighbor A04")
    for _ in range(3):
        client.post("/api/auth/login", json={"email": email, "password": "not it"})
    client.post("/api/auth/login", json={"email": email, "password": config.DEMO_PASSWORD})
    assert accounts.failure_delay(email) == 0


def test_a_short_password_is_refused(client):
    response = client.post("/api/families", json={**NEW_ACCOUNT, "password": "short"})
    assert response.status_code == 400
    assert "at least" in response.json()["detail"]


# --------------------------------------------------------------------------
# One email, two sides
# --------------------------------------------------------------------------

def _both_sides(client):
    """Sign up as a neighbor, then as a granter on the same email."""
    client.post("/api/families", json=NEW_ACCOUNT)
    client.post("/api/donors", json={
        **NEW_ACCOUNT, "contact_address": "9 Rookery Ln, New Haven, CT 06511",
        "budget_usd": 80, "preferred_categories": ["clothing"], "preference": "either",
    })
    sign_out(client)


def test_one_email_can_hold_both_sides(client):
    _both_sides(client)
    body = client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"],
    }).json()
    assert body["must_choose"] is True
    assert {r["role"] for r in body["roles"]} == {"family", "donor"}
    assert body["role"] is None            # nothing chosen yet


def test_choosing_a_side_and_switching_later(client):
    _both_sides(client)
    client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"]})

    chosen = client.post("/api/auth/side", json={"role": "donor"}).json()
    assert chosen["role"] == "donor"
    assert client.get(f"/api/donors/{chosen['alias']}/granted").status_code == 200

    back = client.post("/api/auth/side", json={"role": "family"}).json()
    assert back["role"] == "family"
    assert client.get(f"/api/families/{back['alias']}/wishes").status_code == 200


def test_a_side_you_do_not_have_is_refused(client):
    client.post("/api/families", json=NEW_ACCOUNT)
    assert client.post("/api/auth/side", json={"role": "donor"}).status_code == 403


def test_a_second_signup_cannot_change_the_first_password(client):
    """Otherwise knowing an email would be enough to take over an account."""
    client.post("/api/families", json=NEW_ACCOUNT)
    sign_out(client)

    hijack = client.post("/api/donors", json={
        **NEW_ACCOUNT, "password": "a completely different password",
        "contact_address": "9 Rookery Ln, New Haven, CT 06511",
        "budget_usd": 80, "preferred_categories": ["clothing"], "preference": "either",
    })
    assert hijack.status_code == 409

    still_works = client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"]})
    assert still_works.status_code == 200


# --------------------------------------------------------------------------
# Nobody grants their own wish
# --------------------------------------------------------------------------

def _own_wish_id(client):
    """Put a wish on the tree belonging to NEW_ACCOUNT's neighbor side."""
    from datetime import date, timedelta
    from backend.models import Category, Occasion, Request, RequestStatus, RequestType

    with db.connect(config.DB_PATH) as conn:
        alias = conn.execute(
            "SELECT alias FROM families WHERE contact_email = ?",
            (NEW_ACCOUNT["contact_email"],)).fetchone()["alias"]
        wish = Request(
            family_alias=alias,
            category=Category.CLOTHING,
            request_type=RequestType.FLEXIBLE,
            item_description="Winter coat for a child, size 8",
            occasion=Occasion.EVERYDAY,
            zip=NEW_ACCOUNT["zip"],
            status=RequestStatus.OPEN,
            deadline=date.today() + timedelta(days=20),
            budget_min_usd=30.0,
            budget_max_usd=50.0,
        )
        wish_id = db.insert_request(wish, conn)
        conn.commit()
    return wish_id, alias


def test_your_own_wish_is_not_on_your_tree(client):
    _both_sides(client)
    wish_id, alias = _own_wish_id(client)

    client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"]})
    client.post("/api/auth/side", json={"role": "donor"})

    on_my_tree = client.get("/api/wishes").json()["wishes"]
    assert wish_id not in [w["id"] for w in on_my_tree]
    assert alias not in [w["family_alias"] for w in on_my_tree]


def test_somebody_elses_tree_still_has_it(client):
    """The wish is hidden from its own author, not withdrawn from the tree."""
    _both_sides(client)
    wish_id, _alias = _own_wish_id(client)

    sign_in(client, "Granter D01")
    assert wish_id in [w["id"] for w in client.get("/api/wishes").json()["wishes"]]


def test_granting_your_own_wish_is_refused_at_the_endpoint(client):
    """The tree hides it; this is what holds if the API is called directly."""
    _both_sides(client)
    wish_id, _alias = _own_wish_id(client)

    body = client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"]}).json()
    client.post("/api/auth/side", json={"role": "donor"})
    granter = next(r["alias"] for r in body["roles"] if r["role"] == "donor")

    refused = client.post("/api/grant", json={
        "donor_alias": granter, "request_id": wish_id})
    assert refused.status_code == 409
    assert "your own wish" in refused.json()["detail"]


# --------------------------------------------------------------------------
# Resetting a password
# --------------------------------------------------------------------------

def test_a_coordinator_issues_a_code_and_the_person_sets_their_own_password(client):
    client.post("/api/families", json=NEW_ACCOUNT)
    sign_out(client)

    issued = client.post("/api/coordinator/reset-password", headers=admin(client),
                         json={"alias": "Neighbor A59"})
    assert issued.status_code == 200
    code = issued.json()["code"]
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", code)
    assert NEW_ACCOUNT["password"] not in issued.text

    done = client.post("/api/auth/reset", json={
        "email": NEW_ACCOUNT["contact_email"], "code": code,
        "password": "a brand new password",
    })
    assert done.status_code == 200

    assert client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": "a brand new password",
    }).status_code == 200
    assert client.post("/api/auth/login", json={
        "email": NEW_ACCOUNT["contact_email"], "password": NEW_ACCOUNT["password"],
    }).status_code == 401


def test_a_reset_code_works_once(client):
    client.post("/api/families", json=NEW_ACCOUNT)
    sign_out(client)
    code = client.post("/api/coordinator/reset-password", headers=admin(client),
                       json={"alias": "Neighbor A59"}).json()["code"]

    first = client.post("/api/auth/reset", json={
        "email": NEW_ACCOUNT["contact_email"], "code": code, "password": "first new one"})
    second = client.post("/api/auth/reset", json={
        "email": NEW_ACCOUNT["contact_email"], "code": code, "password": "second new one"})
    assert first.status_code == 200
    assert second.status_code == 400


def test_a_reset_code_is_not_stored_in_the_clear(client):
    client.post("/api/families", json=NEW_ACCOUNT)
    code = client.post("/api/coordinator/reset-password", headers=admin(client),
                       json={"alias": "Neighbor A59"}).json()["code"]
    with db.connect(config.DB_PATH) as conn:
        stored = [r["code_hash"] for r in conn.execute(
            "SELECT code_hash FROM password_resets")]
    assert stored and code not in stored


def test_only_an_admin_can_issue_a_reset_code(client):
    sign_in(client, "Neighbor A04")
    assert client.post("/api/coordinator/reset-password",
                       json={"alias": "Neighbor A07"}).status_code == 401


def test_a_reset_signs_out_whoever_was_in_there(client):
    """Resetting is also what you do when you fear somebody else is."""
    client.post("/api/families", json=NEW_ACCOUNT)        # leaves them signed in
    assert client.get("/api/families/Neighbor A59/wishes").status_code == 200

    code = client.post("/api/coordinator/reset-password", headers=admin(client),
                       json={"alias": "Neighbor A59"}).json()["code"]
    client.post("/api/auth/reset", json={
        "email": NEW_ACCOUNT["contact_email"], "code": code, "password": "a new one again"})

    assert client.get("/api/families/Neighbor A59/wishes").status_code == 401


# --------------------------------------------------------------------------
# The demo shortcut
# --------------------------------------------------------------------------

def test_continue_as_logs_in_for_real(client):
    """It goes through a session like anyone else, not around one."""
    response = client.post("/api/auth/demo", json={"alias": "Neighbor A04"})
    assert response.status_code == 200
    assert response.json()["alias"] == "Neighbor A04"
    assert client.get("/api/families/Neighbor A04/wishes").status_code == 200


def test_the_shortcut_stops_working_once_a_password_is_set(client):
    """The guard that keeps a demo convenience from becoming a back door.

    A seeded account is reachable because its password is the published demo
    one. The moment somebody sets their own, the shortcut must refuse — so it
    can never be used to walk into a real person's account.
    """
    assert client.post("/api/auth/demo", json={"alias": "Neighbor A04"}).status_code == 200

    code = client.post("/api/coordinator/reset-password", headers=admin(client),
                       json={"alias": "Neighbor A04"}).json()["code"]
    client.post("/api/auth/reset", json={
        "email": email_for("Neighbor A04"), "code": code,
        "password": "a password of my own",
    })

    refused = client.post("/api/auth/demo", json={"alias": "Neighbor A04"})
    assert refused.status_code == 403
    assert "password of its own" in refused.json()["detail"]


def test_the_demo_list_still_carries_no_email(client):
    """The shortcut resolves the alias on the server precisely so the browser
    never needs one. The list it is driven from must stay alias-only."""
    listed = client.get("/api/accounts").text
    assert "@" not in listed
    assert email_for("Neighbor A04") not in listed


def test_an_unknown_demo_alias_is_refused(client):
    assert client.post("/api/auth/demo", json={"alias": "Neighbor Z99"}).status_code == 404


# --------------------------------------------------------------------------
# A first name is the most identifying thing anyone gives us
# --------------------------------------------------------------------------

NAMED = {**NEW_ACCOUNT, "first_name": "Marisol", "contact_email": "marisol@example.com"}


def test_a_name_reaches_no_public_endpoint(client):
    client.post("/api/families", json=NAMED)
    sign_out(client)

    for path in PUBLIC + ["/api/wishes?category=clothing"]:
        assert NAMED["first_name"] not in client.get(path).text, path


def test_no_seeded_name_is_anywhere_public(client):
    """The seed gives a few people names. None may surface."""
    with db.connect(config.DB_PATH) as conn:
        names = [r["first_name"] for r in conn.execute(
            "SELECT first_name FROM families WHERE first_name IS NOT NULL")]
        names += [r["first_name"] for r in conn.execute(
            "SELECT first_name FROM donors WHERE first_name IS NOT NULL")]
    assert names, "the seed should carry some names to make this test mean something"

    sign_in(client, "Granter D01")
    for path in ("/api/wishes", "/api/accounts", "/api/stats",
                 "/api/donors/Granter D01/granted"):
        body = client.get(path).text
        for name in names:
            assert name not in body, f"{path} shows {name!r}"


def test_a_wish_card_never_carries_a_name(client):
    """The card is what a granter sees and what every agent is handed."""
    with db.connect(config.DB_PATH) as conn:
        named = conn.execute(
            "SELECT alias, first_name FROM families WHERE first_name IS NOT NULL"
        ).fetchone()
        wishes = db.list_open_wishes(conn)

    cards = [w.public_card() for w in wishes if w.family_alias == named["alias"]]
    assert cards, "the named neighbor should have an open wish to check"
    for card in cards:
        assert named["first_name"] not in str(card)
        assert "first_name" not in card


def test_a_person_sees_their_own_name_and_nobody_elses(client):
    client.post("/api/families", json=NAMED)
    me = client.get("/api/auth/me").json()
    assert me["first_name"] == "Marisol"

    sign_in(client, "Granter D01")
    theirs = client.get("/api/auth/me").json()
    assert theirs["first_name"] != "Marisol"


def test_the_admin_run_sheet_shows_names(client):
    """The one screen where staff may see one, so delivery day is human."""
    wish = client.get("/api/wishes").json()["wishes"]
    sign_in(client, "Granter D01")
    first = next(w for w in wish)
    client.post("/api/grant", json={
        "donor_alias": "Granter D01", "request_id": first["id"]})

    sheet = client.get("/api/coordinator/run-sheet", headers=admin(client)).json()
    assert "donor_name" in sheet["dropoffs"][0]
    names = [row.get("donor_name") for row in sheet["dropoffs"]]
    assert any(names), "at least one seeded granter has a name"


def test_a_name_is_never_sent_to_an_agent(client):
    """Agents are handed `public_card()` shapes and an alias. Neither can
    carry a name, which is what makes this structural rather than a promise."""
    from backend.agents.intake import IntakeDeps

    fields = set(IntakeDeps.__dataclass_fields__)
    assert "first_name" not in fields
    for field in fields:
        assert "name" not in field or field in {"family_alias"}, field
