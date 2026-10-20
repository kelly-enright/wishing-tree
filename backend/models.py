"""Structured types for Wishing Tree.

Every structured object in this project is defined here as a Pydantic model, so
the agents added in later problems can return these types directly and the API
and the database speak the same shapes.

This module imports nothing from the rest of the project. `backend/config.py`
imports *from* here (for the typed region list), never the other way round.

Privacy note: a family's and a donor's street address and phone number are
coordinator-only. Every model that holds them exposes `public_view()`, which is
the only shape allowed to reach the wish wall, a donor, or an AI agent.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


# --------------------------------------------------------------------------
# Enumerations — the vocabulary of the app
# --------------------------------------------------------------------------

class Category(str, Enum):
    """What a wish is for."""

    RENT_UTILITIES = "rent_utilities"
    ESSENTIALS = "essentials"          # hygiene, diapers
    CLOTHING = "clothing"
    SCHOOL_SUPPLIES = "school_supplies"
    GIFTS = "gifts"
    FOOD = "food"
    OTHER = "other"


class Occasion(str, Enum):
    """Why a wish is happening now. Drives urgency, not eligibility."""

    HOLIDAY = "holiday"
    BIRTHDAY = "birthday"
    BACK_TO_SCHOOL = "back_to_school"
    JOB_INTERVIEW = "job_interview"
    EMERGENCY = "emergency"
    EVERYDAY = "everyday"


class RequestType(str, Enum):
    SPECIFIC = "specific"    # an exact item, with a product link
    FLEXIBLE = "flexible"    # a described need, essentials only


class RequestStatus(str, Enum):
    """The life of one wish, in order."""

    DRAFT = "draft"                    # intake agent drafted it, family has not approved
    PENDING_REVIEW = "pending_review"  # family approved, privacy & safety agent has not cleared it
    OPEN = "open"                      # public on the wish wall
    GRANTED = "granted"                # a donor pledged it
    DROPPED_OFF = "dropped_off"        # donor left it at the hub
    DELIVERED = "delivered"            # coordinator delivered it to the family
    MISSED = "missed"                  # deadline passed with no donor


class DonorPreference(str, Enum):
    SPECIFIC = "specific"
    FLEXIBLE = "flexible"
    EITHER = "either"


class PledgeStatus(str, Enum):
    PLEDGED = "pledged"
    DROPPED_OFF = "dropped_off"
    DELIVERED = "delivered"
    MISSED = "missed"          # donor did not make the drop-off window
    CANCELLED = "cancelled"


class Weekday(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# --------------------------------------------------------------------------
# Region — configuration, so a new city needs no code change
# --------------------------------------------------------------------------

class Window(BaseModel):
    """A recurring weekly time window."""

    day: Weekday
    start: time
    end: time

    @model_validator(mode="after")
    def _end_after_start(self) -> "Window":
        if self.end <= self.start:
            raise ValueError(f"window end {self.end} must be after start {self.start}")
        return self

    def label(self) -> str:
        """e.g. 'Thursday 4:00-7:00 PM' — for the UI and the run sheet."""
        def fmt(t: time) -> str:
            hour = t.hour % 12 or 12
            suffix = "AM" if t.hour < 12 else "PM"
            return f"{hour}:{t.minute:02d} {suffix}"
        return f"{self.day.value.capitalize()} {fmt(self.start)}-{fmt(self.end)}"


class Region(BaseModel):
    """One city Wishing Tree operates in. New cities are added in config.py."""

    slug: str
    name: str
    zip_codes: list[str]
    hub_name: str
    hub_address: str
    dropoff_window: Window
    delivery_window: Window
    active: bool = True

    @field_validator("zip_codes")
    @classmethod
    def _five_digit_zips(cls, zips: list[str]) -> list[str]:
        for z in zips:
            if not (len(z) == 5 and z.isdigit()):
                raise ValueError(f"zip code {z!r} must be five digits")
        return zips

    def covers(self, zip_code: str) -> bool:
        return zip_code in self.zip_codes


# --------------------------------------------------------------------------
# People — families and donors
# --------------------------------------------------------------------------

class Family(BaseModel):
    """A household asking for help.

    `alias` is the only name that is ever public. `contact_address` and
    `contact_phone` are collected in a plain form, never sent to a model, and
    shown only on the coordinator's run sheet.
    """

    id: int | None = None
    alias: str = Field(description="public label, e.g. 'Family A27'")
    zip: str
    region_slug: str = "new_haven"

    # Coordinator-only, never public, never sent to an agent.
    contact_address: str
    contact_phone: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("zip")
    @classmethod
    def _five_digit_zip(cls, z: str) -> str:
        if not (len(z) == 5 and z.isdigit()):
            raise ValueError(f"zip code {z!r} must be five digits")
        return z

    def public_view(self) -> dict:
        """The only shape allowed off the coordinator's screen."""
        return {"alias": self.alias, "zip": self.zip, "region_slug": self.region_slug}


class Donor(BaseModel):
    """Someone offering to grant wishes."""

    id: int | None = None
    alias: str
    zip: str
    region_slug: str = "new_haven"

    # Coordinator-only.
    contact_address: str
    contact_phone: str

    budget_usd: float = Field(ge=0, description="what this donor can spend per wish")
    preferred_categories: list[Category] = Field(default_factory=list)
    preference: DonorPreference = DonorPreference.EITHER

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("zip")
    @classmethod
    def _five_digit_zip(cls, z: str) -> str:
        if not (len(z) == 5 and z.isdigit()):
            raise ValueError(f"zip code {z!r} must be five digits")
        return z

    def public_view(self) -> dict:
        return {
            "alias": self.alias,
            "zip": self.zip,
            "budget_usd": self.budget_usd,
            "preferred_categories": [c.value for c in self.preferred_categories],
            "preference": self.preference.value,
        }


# --------------------------------------------------------------------------
# Request — a "wish" in the interface, a "request" in the code
# --------------------------------------------------------------------------

class Request(BaseModel):
    """One need. Specific wishes name an exact item; flexible ones describe it."""

    id: int | None = None
    family_alias: str
    category: Category
    request_type: RequestType
    item_description: str
    deadline: date
    occasion: Occasion
    zip: str
    status: RequestStatus = RequestStatus.DRAFT

    # Estimated cost, or a range. A specific wish usually has a point estimate;
    # a flexible one usually has a range. At least one is required.
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    budget_min_usd: float | None = Field(default=None, ge=0)
    budget_max_usd: float | None = Field(default=None, ge=0)

    # Specific wishes only.
    product_link: str | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    open_to_substitute: bool = False

    # Flexible wishes only.
    size_preferences: str | None = Field(
        default=None, description="just the essentials, e.g. 'boys 4T, warm layers'"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("zip")
    @classmethod
    def _five_digit_zip(cls, z: str) -> str:
        if not (len(z) == 5 and z.isdigit()):
            raise ValueError(f"zip code {z!r} must be five digits")
        return z

    @model_validator(mode="after")
    def _shape_matches_type(self) -> "Request":
        if self.request_type is RequestType.SPECIFIC:
            if not self.product_link:
                raise ValueError("a specific wish needs a product_link")
        else:
            if self.product_link:
                raise ValueError("a flexible wish must not carry a product_link")

        if self.budget_min_usd is not None and self.budget_max_usd is not None:
            if self.budget_max_usd < self.budget_min_usd:
                raise ValueError("budget_max_usd must be >= budget_min_usd")

        has_point = self.estimated_cost_usd is not None
        has_range = self.budget_min_usd is not None or self.budget_max_usd is not None
        if not (has_point or has_range):
            raise ValueError("a wish needs an estimated cost or a budget range")
        return self

    def cost_ceiling_usd(self) -> float:
        """The most this wish is expected to cost — used to match donor budgets."""
        if self.budget_max_usd is not None:
            return self.budget_max_usd
        if self.estimated_cost_usd is not None:
            return self.estimated_cost_usd
        return self.budget_min_usd or 0.0

    def days_until_deadline(self, today: date | None = None) -> int:
        return (self.deadline - (today or date.today())).days


# --------------------------------------------------------------------------
# Pledge — a donor granting one wish
# --------------------------------------------------------------------------

class Pledge(BaseModel):
    """A donor has claimed a wish and picked a weekly drop-off."""

    id: int | None = None
    request_id: int
    donor_alias: str
    dropoff_date: date
    delivery_date: date
    family_confirmed_delivery: bool = False
    status: PledgeStatus = PledgeStatus.PLEDGED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _delivery_after_dropoff(self) -> "Pledge":
        if self.delivery_date < self.dropoff_date:
            raise ValueError("delivery_date cannot be before dropoff_date")
        return self


# --------------------------------------------------------------------------
# AgentCallLog — one row per model call, the evidence for tokenomics
# --------------------------------------------------------------------------

class AgentCallLog(BaseModel):
    """One AI call, appended to output/audit_trail.json.

    Token counts are recorded separately for input, cached input and output
    because they are priced differently; the tokenomics section of the report
    is computed from these rows, not from estimates.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str                      # intake | safety | matchmaker
    model: str
    operation: str                  # e.g. 'draft_wishes', 'review_request'
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    ok: bool = True
    error: str | None = None
    request_id: int | None = None
    prompt_version: str | None = None
    estimated_cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.cached_input_tokens + self.output_tokens
