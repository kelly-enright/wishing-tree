"""Every tunable setting for Wishing Tree, in one place.

Nothing else in this project hard-codes a model name, a region, a limit, a
price, or a retailer domain. Adding a second city is an edit to REGIONS here —
no code changes anywhere else.

.env lookup (required by the course run rules): this repo's own folder first,
then the folder one level above it, because the teaching staff keep their .env
one level up. The nearest file wins. If PORTKEY_API_KEY is in neither, the app
stops with a message naming both paths it looked in.
"""

from __future__ import annotations

import os
from datetime import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from backend.models import Region, Weekday, Window

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

DB_PATH = DATA_DIR / "wishing_tree.db"
PRICE_GUIDE_PATH = DATA_DIR / "price_guide.json"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
HARNESS_PATH = OUTPUT_DIR / "harness.md"

# --------------------------------------------------------------------------
# .env lookup — repo folder first, then one level above
# --------------------------------------------------------------------------

ENV_SEARCH_PATHS: list[Path] = [PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"]


def load_env(search_paths: list[Path] | None = None) -> list[Path]:
    """Load .env files in priority order. Returns the ones that existed.

    Loaded with override=False and nearest-first, so a key set in the repo's
    own .env beats the same key one level up, and a key already exported in
    the shell beats both.
    """
    found: list[Path] = []
    for candidate in search_paths or ENV_SEARCH_PATHS:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            found.append(candidate)
    return found


def require_api_key(search_paths: list[Path] | None = None) -> str:
    """Return PORTKEY_API_KEY, or stop with a message that says what to do."""
    paths = search_paths or ENV_SEARCH_PATHS
    load_env(paths)
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        looked = "\n".join(f"  - {p}" for p in paths)
        raise RuntimeError(
            "PORTKEY_API_KEY is not set.\n"
            "Wishing Tree looked for a .env file in these places, nearest first:\n"
            f"{looked}\n"
            "Copy .env.example to one of them and fill in PORTKEY_API_KEY, "
            "or export the key in your shell, then start the app again."
        )
    return key


def api_key_status(search_paths: list[Path] | None = None) -> tuple[bool, str]:
    """Non-raising form, for a health check that should not take the app down."""
    try:
        require_api_key(search_paths)
    except RuntimeError as exc:
        return False, str(exc)
    return True, "PORTKEY_API_KEY found"


# --------------------------------------------------------------------------
# Model — one model for this whole project
# --------------------------------------------------------------------------

load_env()

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PORTKEY_PROVIDER = "openai"

# --------------------------------------------------------------------------
# Regions — add a city here and the app follows; no code changes needed
# --------------------------------------------------------------------------

REGIONS: list[Region] = [
    Region(
        slug="new_haven",
        name="New Haven, CT",
        zip_codes=[
            "06510", "06511", "06512", "06513", "06514", "06515", "06516",
            "06517", "06518", "06519", "06520", "06524", "06525",
        ],
        hub_name="Yale School of Management",
        hub_address="165 Whitney Ave, New Haven, CT 06511",
        dropoff_window=Window(day=Weekday.THURSDAY, start=time(16, 0), end=time(19, 0)),
        delivery_window=Window(day=Weekday.SATURDAY, start=time(10, 0), end=time(13, 0)),
        active=True,
    ),
]

DEFAULT_REGION_SLUG = "new_haven"


def get_region(slug: str = DEFAULT_REGION_SLUG) -> Region:
    for region in REGIONS:
        if region.slug == slug:
            return region
    raise KeyError(f"no region configured with slug {slug!r}")


def active_regions() -> list[Region]:
    return [r for r in REGIONS if r.active]


def region_for_zip(zip_code: str) -> Region | None:
    for region in active_regions():
        if region.covers(zip_code):
            return region
    return None


# --------------------------------------------------------------------------
# Retailer allowlist — the Privacy & Safety agent checks links against this
# --------------------------------------------------------------------------
# Product links are checked as strings only. No agent and no part of this app
# ever fetches a product URL, so a hostile link cannot run anything.

RETAILER_ALLOWLIST: frozenset[str] = frozenset({
    "amazon.com",
    "target.com",
    "walmart.com",
    "costco.com",
    "bestbuy.com",
    "staples.com",
    "officedepot.com",
    "oldnavy.com",
    "gap.com",
    "uniqlo.com",
    "kohls.com",
    "macys.com",
    "jcpenney.com",
    "dsw.com",
    "carters.com",
    "ikea.com",
    "cvs.com",
    "walgreens.com",
    "stopandshop.com",
    "shoprite.com",
})


def is_allowed_retailer(url: str | None) -> bool:
    """True only for an https link whose host is on the allowlist.

    Deliberately strict: https only, no embedded credentials, and the host must
    be an allowlisted domain or a subdomain of one.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme != "https" or "@" in (parsed.netloc or ""):
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in RETAILER_ALLOWLIST)


# --------------------------------------------------------------------------
# Coordinator passcode
# --------------------------------------------------------------------------
# The coordinator's screens are the only ones that show a family's street
# address and phone number, so they sit behind a shared passcode. This is a
# demo gate, not authentication: there are no user passwords in the MVP, and
# the passcode is checked on the server, never in the browser.

COORDINATOR_PASSCODE = "wishingtree-demo"

# --------------------------------------------------------------------------
# Limits — app behaviour
# --------------------------------------------------------------------------

MAX_OPEN_WISHES_PER_FAMILY = 5     # stops one family filling the wall
MAX_INTAKE_TURNS = 20              # family messages in one intake before it must wrap up
MAX_WISHES_PER_INTAKE = 5          # wishes the intake agent may draft in one session
INTAKE_SESSION_PREFIX = "intake"   # session ids look like intake-20261020-a3f9c1
MAX_MATCHES_RETURNED = 10          # ranked wishes the matchmaker returns to a donor
MAX_MESSAGE_CHARS = 2_000          # longest family message accepted into intake
MAX_DESCRIPTION_CHARS = 400        # longest wish description shown publicly

AGENT_TIMEOUT_S = 60.0             # wall clock for one agent run
HTTP_TIMEOUT_S = 45.0              # per model request
HTTP_MAX_RETRIES = 1               # a wedged call is not worth retrying three times

# --------------------------------------------------------------------------
# Token budgets — the overspending guard
# --------------------------------------------------------------------------

MAX_TOKENS_PER_INTAKE_SESSION = 20_000
MAX_TOKENS_PER_REVIEW = 4_000
MAX_TOKENS_PER_MATCH_RUN = 8_000
DAILY_TOKEN_BUDGET = 500_000       # across the whole app

# --------------------------------------------------------------------------
# Prices — PLACEHOLDERS
# --------------------------------------------------------------------------
# >>> KELLY: fill these three in before writing the tokenomics section. <<<
# They are USD per MILLION tokens for gpt-6-luna. Until they are real, every
# cost this app reports is 0.00 and PRICES_ARE_PLACEHOLDERS stays True, so no
# placeholder number can quietly end up in the report.

PRICE_PER_MILLION_INPUT_USD: float = 0.00         # PLACEHOLDER
PRICE_PER_MILLION_CACHED_INPUT_USD: float = 0.00  # PLACEHOLDER
PRICE_PER_MILLION_OUTPUT_USD: float = 0.00        # PLACEHOLDER

PRICES_ARE_PLACEHOLDERS: bool = (
    PRICE_PER_MILLION_INPUT_USD == 0.0
    and PRICE_PER_MILLION_CACHED_INPUT_USD == 0.0
    and PRICE_PER_MILLION_OUTPUT_USD == 0.0
)


def estimate_cost_usd(
    input_tokens: int = 0,
    cached_input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """Cost of one call. Returns 0.0 while the prices above are placeholders."""
    return (
        input_tokens * PRICE_PER_MILLION_INPUT_USD
        + cached_input_tokens * PRICE_PER_MILLION_CACHED_INPUT_USD
        + output_tokens * PRICE_PER_MILLION_OUTPUT_USD
    ) / 1_000_000
