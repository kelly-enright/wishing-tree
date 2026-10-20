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


class WindowResponse(str, Enum):
    """What the family said about the delivery window they were offered.

    There is no self-service rescheduling: a family that cannot make the window
    says so, and a coordinator gets in touch. A date is a promise to a person,
    and a person should make it.
    """

    PENDING = "pending"                    # not asked, or not answered yet
    CONFIRMED = "confirmed"
    NEEDS_RESCHEDULE = "needs_reschedule"  # waiting on the coordinator


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
    deadline: date | None = None
    occasion: Occasion
    zip: str
    status: RequestStatus = RequestStatus.DRAFT

    # Estimated cost, or a range. A specific wish usually has a point estimate;
    # a flexible one usually has a range. At least one is required.
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    budget_min_usd: float | None = Field(default=None, ge=0)
    budget_max_usd: float | None = Field(default=None, ge=0)

    # True when the cost came from the price guide rather than the family, so
    # every screen can label it as an estimate rather than a stated price.
    cost_is_estimate: bool = False

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

    def days_waiting(self, today: date | None = None) -> int:
        """How long this wish has been up. Fairness input: a wish that has
        waited counts for something, independently of how it is written."""
        return ((today or date.today()) - self.created_at.date()).days

    def public_card(self, today: date | None = None) -> dict:
        """Everything a donor may see, and nothing else.

        Built by listing fields rather than by removing them, so a new column
        on `Request` cannot leak onto the wish wall by default.
        """
        return {
            "id": self.id,
            "family_alias": self.family_alias,
            "category": self.category.value,
            "occasion": self.occasion.value,
            "request_type": self.request_type.value,
            "item_description": self.item_description,
            "zip": self.zip,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "deadline_label": self.deadline_label(),
            "days_until_deadline": self.days_until_deadline(today),
            "days_waiting": self.days_waiting(today),
            "estimated_cost_usd": self.estimated_cost_usd,
            "budget_min_usd": self.budget_min_usd,
            "budget_max_usd": self.budget_max_usd,
            "cost_ceiling_usd": self.cost_ceiling_usd(),
            "cost_is_estimate": self.cost_is_estimate,
            "product_link": self.product_link,
            "brand": self.brand,
            "size": self.size,
            "color": self.color,
            "open_to_substitute": self.open_to_substitute,
            "size_preferences": self.size_preferences,
            "status": self.status.value,
        }

    def days_until_deadline(self, today: date | None = None) -> int | None:
        """None when the family gave no date. A missing deadline is not urgent
        and is not overdue; it is simply unknown."""
        if self.deadline is None:
            return None
        return (self.deadline - (today or date.today())).days

    def deadline_label(self) -> str:
        """What every screen shows. Never invents a date."""
        return self.deadline.isoformat() if self.deadline else "No deadline"


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
    window_response: WindowResponse = WindowResponse.PENDING
    status: PledgeStatus = PledgeStatus.PLEDGED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _delivery_after_dropoff(self) -> "Pledge":
        if self.delivery_date < self.dropoff_date:
            raise ValueError("delivery_date cannot be before dropoff_date")
        return self

    @property
    def family_confirmed_delivery(self) -> bool:
        return self.window_response is WindowResponse.CONFIRMED

    def dropoff_status(self) -> str:
        """What the run sheet shows in the drop-off column."""
        if self.status is PledgeStatus.MISSED:
            return "missed"
        if self.status in (PledgeStatus.DROPPED_OFF, PledgeStatus.DELIVERED):
            return "dropped off"
        return "scheduled"

    def delivery_status(self) -> str:
        """What the run sheet shows in the delivery column."""
        return "delivered" if self.status is PledgeStatus.DELIVERED else "scheduled"


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
    # The four buckets the course's billing convention prices separately.
    # `input_tokens` is UNCACHED input: the API's figure minus the cached and
    # cache-write parts, so no token is charged twice.
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    ok: bool = True
    error: str | None = None
    session_id: str | None = None
    tools_called: list[str] = Field(default_factory=list)

    # Shape, never content. These are shown on the coordinator's activity page,
    # so neither may ever contain a family's words: an unmatched school name or
    # employer would otherwise leak through a summary. Intake records the size
    # of what went in, not what it said.
    input_summary: str = ""
    output_summary: str = ""

    request_id: int | None = None
    prompt_version: str | None = None
    estimated_cost_usd: float | None = None

    @property
    def total_input_tokens(self) -> int:
        """What the API reported as input, reassembled from the three buckets."""
        return self.input_tokens + self.cached_input_tokens + self.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.output_tokens


# --------------------------------------------------------------------------
# Sign-up and session types
# --------------------------------------------------------------------------
# A family's and a donor's address and phone arrive through these plain forms.
# They are stored for the coordinator and never sent to a model.

class FamilySignUp(BaseModel):
    zip: str
    contact_address: str = Field(min_length=4)
    contact_phone: str = Field(min_length=7)

    @field_validator("zip")
    @classmethod
    def _five_digit_zip(cls, z: str) -> str:
        if not (len(z) == 5 and z.isdigit()):
            raise ValueError("zip code must be five digits")
        return z


class DonorSignUp(BaseModel):
    zip: str
    contact_address: str = Field(min_length=4)
    contact_phone: str = Field(min_length=7)
    budget_usd: float = Field(ge=0)
    preferred_categories: list[Category] = Field(default_factory=list)
    preference: DonorPreference = DonorPreference.EITHER

    @field_validator("zip")
    @classmethod
    def _five_digit_zip(cls, z: str) -> str:
        if not (len(z) == 5 and z.isdigit()):
            raise ValueError("zip code must be five digits")
        return z


class CoordinatorUnlock(BaseModel):
    passcode: str


class AccountSummary(BaseModel):
    """One row of the demo "Continue as..." list.

    Aliases and zips only. Contact details never appear in this shape, which is
    what lets the list be public in the demo without leaking anything.
    """

    role: str          # "family" | "donor"
    alias: str
    zip: str
    detail: str = ""   # e.g. "3 wishes" or "$75 budget"


# --------------------------------------------------------------------------
# Intake — what the agent returns, and the session it runs in
# --------------------------------------------------------------------------

class DraftWish(BaseModel):
    """One wish as the Intake agent drafts it, before the family approves.

    Looser than `Request` on purpose: a draft is allowed to have gaps. The
    agent is told to leave a field empty rather than invent a value, so empty
    fields here are a feature. The gaps are filled on the approval screen,
    by the family, and only then does this become a `Request`.
    """

    category: Category
    request_type: RequestType = RequestType.FLEXIBLE
    item_description: str = Field(max_length=400)  # mirrors config.MAX_DESCRIPTION_CHARS
    occasion: Occasion = Occasion.EVERYDAY

    deadline: date | None = None
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    budget_min_usd: float | None = Field(default=None, ge=0)
    budget_max_usd: float | None = Field(default=None, ge=0)

    product_link: str | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    open_to_substitute: bool = True

    size_preferences: str | None = None


class IntakeReply(BaseModel):
    """The Intake agent's structured answer on every turn."""

    message: str = Field(description="what the family sees in the chat")
    draft_wishes: list[DraftWish] = Field(default_factory=list)
    done: bool = False


class IntakeStatus(str, Enum):
    ACTIVE = "active"
    APPROVED = "approved"
    LIMIT_REACHED = "limit_reached"
    ABANDONED = "abandoned"


class IntakeSession(BaseModel):
    """One family's intake chat, from first message to approval."""

    session_id: str
    family_alias: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None
    turns: int = 0
    status: IntakeStatus = IntakeStatus.ACTIVE
    duration_seconds: float | None = None


# --------------------------------------------------------------------------
# Privacy & Safety review
# --------------------------------------------------------------------------

class SafetyFlagKind(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    CASH_REQUEST = "cash_request"
    SCAM = "scam"
    POLICY_VIOLATION = "policy_violation"


class SafetyFlag(BaseModel):
    kind: SafetyFlagKind
    reason: str = Field(max_length=200)


class CleanedWish(BaseModel):
    """The parts of a wish the reviewer is allowed to rewrite."""

    item_description: str = Field(max_length=400)
    size: str | None = None
    color: str | None = None
    brand: str | None = None
    size_preferences: str | None = None
    product_link: str | None = None


class SafetyReview(BaseModel):
    """What the Privacy & Safety agent returns for one wish.

    `removed` names the *kinds* of things taken out ("a child's name"), never
    the values. It is read by the family and shown in the coordinator's
    activity log, so it must be safe to display.
    """

    approved: bool
    cleaned: CleanedWish
    removed: list[str] = Field(default_factory=list)
    flags: list[SafetyFlag] = Field(default_factory=list)
    note_to_family: str = Field(max_length=400)

    def flag_kinds(self) -> set[SafetyFlagKind]:
        return {f.kind for f in self.flags}


class WishAmounts(BaseModel):
    """What `check_wish_limits` is asked about."""

    category: Category
    estimated_cost_usd: float | None = None
    budget_min_usd: float | None = None
    budget_max_usd: float | None = None


# --------------------------------------------------------------------------
# Matchmaking and granting
# --------------------------------------------------------------------------

class WishMatch(BaseModel):
    """One ranked wish, as the Matchmaker returns it."""

    request_id: int
    reason: str = Field(max_length=200, description="one line, for the donor")
    dropoff_date: date
    delivery_date: date
    arrives_in_time: bool = True


class MatchmakerResult(BaseModel):
    """The Matchmaker's structured answer for one donor."""

    matches: list[WishMatch] = Field(default_factory=list)
    note: str = Field(default="", max_length=300)


class GrantRequest(BaseModel):
    donor_alias: str
    request_id: int


class DonorFilters(BaseModel):
    """What a donor asks the wish wall or the Matchmaker for."""

    zip: str | None = None
    max_cost_usd: float | None = Field(default=None, ge=0)
    categories: list[Category] = Field(default_factory=list)
    request_type: RequestType | None = None
    occasion: Occasion | None = None


# --------------------------------------------------------------------------
# The coordinator's run sheet
# --------------------------------------------------------------------------

class WindowAnswer(BaseModel):
    """A family answering the delivery window they were offered."""

    family_alias: str
    pledge_id: int
    response: WindowResponse


class StatusUpdate(BaseModel):
    """One click on the run sheet."""

    pledge_id: int
    status: PledgeStatus
