"""The seed data is synthetic, complete, and safe to publish."""

from backend import db, seed
from backend.config import is_allowed_retailer
from backend.models import Category, Occasion, RequestType


def _seeded(tmp_path):
    path = tmp_path / "wishing_tree.db"
    seed.seed(path)
    return path


def test_counts_match_the_brief(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        counts = db.counts(conn)
    assert counts["families"] == 15
    assert counts["requests"] == 40
    assert counts["donors"] == 8


def test_every_category_and_occasion_appears(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        requests = db.list_requests(conn)
    assert {r.category for r in requests} == set(Category)
    assert {r.occasion for r in requests} == set(Occasion)


def test_roughly_half_the_wishes_are_specific(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        requests = db.list_requests(conn)
    specific = sum(r.request_type is RequestType.SPECIFIC for r in requests)
    assert 0.4 <= specific / len(requests) <= 0.6


def test_every_product_link_is_on_the_allowlist(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        requests = db.list_requests(conn)
    links = [r.product_link for r in requests if r.request_type is RequestType.SPECIFIC]
    assert links and all(is_allowed_retailer(link) for link in links)


def test_every_family_has_at_least_one_wish(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        families = {f.alias for f in db.list_families(conn)}
        asked = {r.family_alias for r in db.list_requests(conn)}
    assert families == asked


def test_contact_details_cannot_reach_a_real_person(tmp_path):
    """555-01xx is reserved for fiction and example.com reaches nobody."""
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        people = [*db.list_families(conn), *db.list_donors(conn)]

    numbers = [p.contact_phone for p in people if p.contact_phone]
    assert numbers, "expected at least some phone numbers"
    assert all("555-01" in n or "555-02" in n for n in numbers)
    assert all(p.contact_email.endswith("@example.com") for p in people)

    # And phone really is optional in the seed, so the UI path gets exercised.
    assert any(p.contact_phone is None for p in people)


def test_every_claimed_wish_has_a_pledge(tmp_path):
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        claimed = [r for r in db.list_requests(conn)
                   if r.status.value in {"granted", "dropped_off", "delivered"}]
        pledged_ids = {p.request_id for p in db.list_pledges(conn)}
    assert {r.id for r in claimed} == pledged_ids


def test_seeding_twice_does_not_duplicate(tmp_path):
    path = _seeded(tmp_path)
    seed.seed_if_empty(path)
    with db.connect(path) as conn:
        assert db.counts(conn)["requests"] == 40


def test_a_wish_with_no_deadline_survives_a_round_trip(tmp_path):
    """Optional deadlines have to store and read back as empty, not as today."""
    from backend.models import Category, Occasion, Request, RequestType

    path = _seeded(tmp_path)
    wish = Request(
        family_alias="Neighbor A04",
        category=Category.CLOTHING,
        request_type=RequestType.FLEXIBLE,
        item_description="Warm layers for a child.",
        occasion=Occasion.EVERYDAY,
        zip="06511",
        budget_min_usd=30.0,
        budget_max_usd=60.0,
        cost_is_estimate=True,
    )
    with db.connect(path) as conn:
        new_id = db.insert_request(wish, conn)
        conn.commit()
        stored = [r for r in db.list_requests(conn) if r.id == new_id][0]

    assert stored.deadline is None
    assert stored.deadline_label() == "No deadline"
    assert stored.cost_is_estimate is True


def test_wishes_without_a_deadline_sort_after_those_with_one(tmp_path):
    from backend.models import Category, Occasion, Request, RequestType

    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        db.insert_request(
            Request(
                family_alias="Neighbor A04", category=Category.OTHER,
                request_type=RequestType.FLEXIBLE, item_description="No date given.",
                occasion=Occasion.EVERYDAY, zip="06511", budget_min_usd=10.0,
            ),
            conn,
        )
        conn.commit()
        ordered = db.list_requests(conn)

    assert ordered[-1].deadline is None
    assert ordered[0].deadline is not None
