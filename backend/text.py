"""Wording helpers.

Small, but the app writes to families having a hard week, so "1 wish(es) went
back on the wall" is not good enough. Every count the app says out loud goes
through here.
"""

from __future__ import annotations


def plural(count: int, singular: str, many: str | None = None) -> str:
    """Just the noun: `plural(1, "wish", "wishes")` -> "wish"."""
    return singular if count == 1 else (many or f"{singular}s")


def counted(count: int, singular: str, many: str | None = None) -> str:
    """The number and the noun: `counted(2, "wish", "wishes")` -> "2 wishes"."""
    return f"{count} {plural(count, singular, many)}"


def verb(count: int, singular: str, many: str) -> str:
    """Agreement for the verb: `verb(1, "is", "are")` -> "is"."""
    return singular if count == 1 else many


# --------------------------------------------------------------------------
# Why a wish is not on the tree
# --------------------------------------------------------------------------
#
# The Privacy & Safety agent writes a sentence for the person who made the
# wish. It no longer reaches them: an agent's prose varies run to run, and a
# neighbor should not have to parse a model's explanation of their own wish.
#
# These are our sentences instead, one per reason, chosen from the flags the
# review raised. Each one says what to change, because a wish that is held
# with no way forward is worse than one refused outright.

HELD_REASONS = {
    "cash_request": (
        "This one asks for money to change hands directly, and Wishing Tree "
        "never does that — it's how both sides stay safe. If it's a bill, ask "
        "again as rent or utilities and we'll pay the provider directly. If "
        "it's something to buy, tell us the item and a neighbor can bring it."
    ),
    "scam": (
        "This one asks for bank or card details, and nothing on Wishing Tree "
        "ever needs those. A coordinator will look at it. If you meant "
        "something else, start a new chat and tell us the item instead."
    ),
    "prompt_injection": (
        "Something in the wording looked like an instruction to our system "
        "rather than a wish, so we've held it for a coordinator. Starting a "
        "new chat and describing the item plainly is usually the quickest fix."
    ),
    "policy_violation": (
        "This one falls outside what Wishing Tree can pass between neighbors. "
        "A coordinator will take a look and get back to you."
    ),
}

HELD_DEFAULT = (
    "This one isn't on the tree yet. A coordinator will take a look and get "
    "back to you."
)

OVER_CAP = (
    "This one comes to more than a single neighbor can grant at once "
    "({cap}). Splitting it into smaller wishes, or asking for part of it, "
    "usually gets it granted faster."
)


def held_reason(flag_kinds, over_cap_label: str | None = None) -> str:
    """Why a wish was held, in our words rather than the agent's.

    Takes the kinds the review raised, most serious first. A wish may trip
    more than one; we say the one that most needs acting on.
    """
    if over_cap_label:
        return OVER_CAP.format(cap=over_cap_label)
    for kind in ("cash_request", "scam", "prompt_injection", "policy_violation"):
        if kind in flag_kinds:
            return HELD_REASONS[kind]
    return HELD_DEFAULT
