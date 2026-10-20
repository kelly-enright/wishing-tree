"""Deterministic safety checks, written once and used twice.

The Privacy & Safety agent gets these as tools, so it can look things up while
it reasons. The publishing code then runs the same functions itself, on the
agent's own output, before a wish is allowed to go public. If the agent skips a
tool, misreads a result, or is talked out of using one, the second pass still
runs — it is plain Python and there is no prompt in it.

What this module can and cannot do:

  - Phone numbers, email addresses and street addresses are patterns, and
    patterns catch them reliably. Those are enforced in code.
  - Names, schools, employers and medical specifics are not patterns. Those are
    the agent's job, and the code pass cannot back them up except where a
    person announces one ("my name is ...").

Nothing here fetches a URL. A link is checked as a string, and only as a string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend import config

# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\d)"
    r"|(?<!\d)\d{10}(?!\d)"
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_STREET_WORDS = (
    r"St|Street|Ave|Avenue|Rd|Road|Ln|Lane|Dr|Drive|Ct|Court|Blvd|Boulevard|"
    r"Way|Ter|Terrace|Pl|Place|Row|Walk|Bend|Sq|Square|Gate|Hall|Hwy|Highway|"
    r"Cir|Circle|Pkwy|Parkway|Trail|Trl"
)
_ADDRESS = re.compile(
    rf"\b\d{{1,5}}\s+(?:[A-Za-z][A-Za-z.'\-]*\s+){{0,3}}(?:{_STREET_WORDS})\b\.?",
    re.IGNORECASE,
)
_UNIT = re.compile(r"\b(?:Apt|Apartment|Unit|Suite|Ste)\.?\s*#?\s*[A-Za-z0-9\-]{1,6}\b",
                   re.IGNORECASE)

# Deliberately NOT case-insensitive on the captured name: requiring capitals is
# what stops "I am struggling" being read as a name. The lead-in phrase allows
# either case, because it may start a sentence.
_SELF_NAMED = re.compile(
    r"\b(?:[Mm]y name is|[Ii] am|[Ii]'m|[Tt]his is|[Ww]e are|[Cc]all me|"
    r"[Hh]er name is|[Hh]is name is|[Tt]heir name is|[Mm]y (?:son|daughter|child) "
    r"(?:is )?(?:called )?)\s*"
    r"([A-Z][a-z'\-]+(?:\s+[A-Z][a-z'\-]+){0,2})",
)

# Phrases that are an attempt to steer the reviewer rather than describe a need.
_INJECTION = [
    (re.compile(r"\bignore\s+(?:all\s+|any\s+|your\s+|the\s+)?(?:previous\s+|prior\s+|above\s+)?(?:instructions?|rules?|prompts?)\b", re.I),
     "asks the reviewer to ignore its instructions"),
    (re.compile(r"\bdisregard\s+(?:all\s+|any\s+|your\s+|the\s+)?(?:previous\s+|prior\s+|above\s+)?(?:instructions?|rules?)\b", re.I),
     "asks the reviewer to disregard its rules"),
    (re.compile(r"\b(?:system|developer)\s+(?:prompt|message|mode)\b", re.I),
     "refers to the system prompt"),
    (re.compile(r"\byou\s+are\s+now\b|\bact\s+as\s+(?:a|an|the)\b|\bpretend\s+(?:to\s+be|you)\b", re.I),
     "tries to reassign the reviewer's role"),
    (re.compile(r"\bmark\s+(?:this|it)\s+(?:as\s+)?(?:urgent|approved|verified|priority)\b", re.I),
     "instructs the reviewer how to label the wish"),
    (re.compile(r"\b(?:approve|publish)\s+(?:this|it)\s+(?:immediately|now|without)\b", re.I),
     "instructs the reviewer to publish without checking"),
    (re.compile(r"\boverride\b.{0,20}\b(?:rules?|limits?|checks?)\b", re.I),
     "asks to override a limit"),
]

# Asking for money to change hands directly, which Wishing Tree does not do.
_CASH = [
    (re.compile(r"\b(?:cash|venmo|cashapp|cash app|zelle|paypal|wire|gift ?card code|western union)\b", re.I),
     "asks for money or a transfer between people"),
    (re.compile(r"\bsend\s+(?:me\s+)?(?:the\s+)?money\b", re.I),
     "asks for money to be sent"),
]

_SCAM = [
    (re.compile(r"\b(?:bitcoin|crypto|btc|eth|wallet address|gift card number)\b", re.I),
     "asks for an untraceable payment"),
    (re.compile(r"\b(?:ssn|social security number|bank account number|routing number|pin number)\b", re.I),
     "asks for a sensitive financial identifier"),
]


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    kind: str       # phone | email | address | unit | self_named
    text: str       # the matched text, for redaction — never shown to a donor
    start: int
    end: int

    def label(self) -> str:
        """What a human sees. Says what was found, never what it was."""
        return {
            "phone": "a phone number",
            "email": "an email address",
            "address": "a street address",
            "unit": "an apartment or unit number",
            "self_named": "a person's name",
        }.get(self.kind, self.kind)


_REPLACEMENTS = {
    "phone": "[phone removed]",
    "email": "[email removed]",
    "address": "[address removed]",
    "unit": "",
    "self_named": "[name removed]",
}


def find_contact_details(text: str) -> list[Finding]:
    """Every phone number, email, street address or self-announced name."""
    if not text:
        return []

    found: list[Finding] = []
    for pattern, kind in (
        (_EMAIL, "email"),
        (_PHONE, "phone"),
        (_ADDRESS, "address"),
        (_UNIT, "unit"),
    ):
        for match in pattern.finditer(text):
            found.append(Finding(kind, match.group(0), match.start(), match.end()))

    for match in _SELF_NAMED.finditer(text):
        found.append(Finding("self_named", match.group(1), match.start(1), match.end(1)))

    # Longest first, so overlapping matches redact cleanly.
    found.sort(key=lambda f: (f.start, -(f.end - f.start)))
    kept: list[Finding] = []
    for finding in found:
        if any(finding.start >= k.start and finding.end <= k.end for k in kept):
            continue
        kept.append(finding)
    return kept


def redact(text: str) -> tuple[str, list[str]]:
    """Return the text with contact details replaced, and what was removed."""
    findings = find_contact_details(text)
    if not findings:
        return text, []

    cleaned = text
    for finding in sorted(findings, key=lambda f: f.start, reverse=True):
        cleaned = cleaned[: finding.start] + _REPLACEMENTS[finding.kind] + cleaned[finding.end :]
    cleaned = _tidy(cleaned)
    return cleaned, [f.label() for f in findings]


def _tidy(text: str) -> str:
    """Clean up the punctuation a removal leaves behind."""
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)   # " ," -> ","
    text = re.sub(r",\s*([.;:])", r"\1", text)      # ", ." -> "."
    text = re.sub(r"([,.;:])\1+", r"\1", text)      # ".." -> "."
    return text.strip()


def scrub(text: str, limit: int = 240) -> str:
    """Safe for the coordinator's activity log: redacted and shortened."""
    cleaned, _ = redact(text or "")
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"


# --------------------------------------------------------------------------
# Link, value and intent checks
# --------------------------------------------------------------------------

def check_link(url: str | None) -> dict:
    """Is this link allowed? Checked as a string. Nothing is ever fetched."""
    if not url:
        return {"has_link": False, "allowed": True, "reason": "no link on this wish"}

    allowed = config.is_allowed_retailer(url)
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return {
        "has_link": True,
        "allowed": allowed,
        "host": host or "unreadable",
        "reason": (
            f"{host} is on the retailer allowlist"
            if allowed
            else f"{host or 'that link'} is not on the retailer allowlist, "
                 f"or the link is not https"
        ),
        "note": "checked as text only; this app never opens a product link",
    }


def check_value(
    category: str,
    estimated_cost_usd: float | None = None,
    budget_min_usd: float | None = None,
    budget_max_usd: float | None = None,
) -> dict:
    """Is the amount asked for within the cap for this category?"""
    cap = config.wish_value_cap(category)
    amount = budget_max_usd if budget_max_usd is not None else estimated_cost_usd
    if amount is None:
        amount = budget_min_usd

    if amount is None:
        return {"within_limit": True, "cap_usd": cap, "amount_usd": None,
                "reason": "no amount on this wish"}

    within = amount <= cap
    return {
        "within_limit": within,
        "cap_usd": cap,
        "amount_usd": amount,
        "reason": (
            f"${amount:,.0f} is within the ${cap:,.0f} cap for {category}"
            if within
            else f"${amount:,.0f} is over the ${cap:,.0f} cap for {category}"
        ),
    }


def _matches(text: str, rules: list[tuple[re.Pattern, str]]) -> list[str]:
    return [reason for pattern, reason in rules if pattern.search(text or "")]


def find_injection(text: str) -> list[str]:
    """Attempts to give the reviewer instructions, rather than describe a need."""
    return _matches(text, _INJECTION)


def find_cash_requests(text: str) -> list[str]:
    return _matches(text, _CASH)


def find_scam_signals(text: str) -> list[str]:
    return _matches(text, _SCAM)
