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


def test_phone_numbers_are_all_in_the_fiction_range(tmp_path):
    """555-01xx is reserved for fiction, so no seeded number can reach a person."""
    path = _seeded(tmp_path)
    with db.connect(path) as conn:
        numbers = [f.contact_phone for f in db.list_families(conn)]
        numbers += [d.contact_phone for d in db.list_donors(conn)]
    assert all("555-01" in n or "555-02" in n for n in numbers)


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
