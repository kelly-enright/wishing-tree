"""The rules the structured types enforce on their own."""

from datetime import date, time

import pytest
from pydantic import ValidationError

from backend.models import (
    Category,
    Family,
    Occasion,
    Request,
    RequestStatus,
    RequestType,
    Weekday,
    Window,
)


def _specific(**overrides) -> dict:
    base = dict(
        family_alias="Family A04",
        category=Category.CLOTHING,
        request_type=RequestType.SPECIFIC,
        item_description="Winter coat",
        deadline=date(2026, 12, 1),
        occasion=Occasion.EVERYDAY,
        zip="06511",
        estimated_cost_usd=42.0,
        product_link="https://www.target.com/p/x/-/A-1",
    )
    base.update(overrides)
    return base


def test_a_specific_wish_needs_a_product_link():
    with pytest.raises(ValidationError):
        Request(**_specific(product_link=None))


def test_a_flexible_wish_must_not_carry_a_product_link():
    with pytest.raises(ValidationError):
        Request(**_specific(request_type=RequestType.FLEXIBLE))


def test_a_wish_needs_a_cost_or_a_range():
    with pytest.raises(ValidationError):
        Request(**_specific(estimated_cost_usd=None))


def test_a_range_alone_is_enough():
    wish = Request(**_specific(
        request_type=RequestType.FLEXIBLE, product_link=None,
        estimated_cost_usd=None, budget_min_usd=40.0, budget_max_usd=70.0,
    ))
    assert wish.cost_ceiling_usd() == 70.0


def test_a_backwards_budget_range_is_rejected():
    with pytest.raises(ValidationError):
        Request(**_specific(budget_min_usd=90.0, budget_max_usd=20.0))


def test_zip_codes_must_be_five_digits():
    with pytest.raises(ValidationError):
        Request(**_specific(zip="0651"))


def test_a_window_must_end_after_it_starts():
    with pytest.raises(ValidationError):
        Window(day=Weekday.THURSDAY, start=time(19, 0), end=time(16, 0))


def test_a_family_public_view_drops_the_contact_details():
    family = Family(
        alias="Family A04", zip="06511",
        contact_address="118 Larkspur St, New Haven, CT 06511",
        contact_phone="(203) 555-0104",
    )
    public = family.public_view()
    assert public == {"alias": "Family A04", "zip": "06511", "region_slug": "new_haven"}
    assert "Larkspur" not in str(public)
    assert "555" not in str(public)


def test_default_status_is_draft_until_the_family_approves():
    assert Request(**_specific()).status is RequestStatus.DRAFT
