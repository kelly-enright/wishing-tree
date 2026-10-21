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


# --------------------------------------------------------------------------
# What was taken out of a wish before it went up
# --------------------------------------------------------------------------
#
# "Taken out before anyone saw it" is a promise, so it has to be true. Two
# things went wrong with it in practice, and both are fixed here rather than
# only in the agent's prompt, because a prompt is a request and this is the
# guarantee.
#
# 1. Rewording was reported as a removal. Shortening a wish, or rewriting it
#    into the house voice, is not a privacy removal; saying it was teaches a
#    neighbor to distrust a message that should mean something.
# 2. The agent used its own vocabulary. "A use-purpose detail" is not a thing
#    anyone says, and it is not a thing anyone can check.
#
# So this is a closed vocabulary. Whatever the review returns is matched
# against it; anything that does not name one of these is not a personal
# detail and never reaches the neighbor.

PERSONAL_REMOVALS: tuple[tuple[tuple[str, ...], str], ...] = (
    # Most specific first: "a child's name" has to win over "a name".
    (("child's name", "childs name", "child name", "children's name",
      "kid's name"), "a child's name"),
    (("school",), "a school name"),
    (("employer", "workplace", "place of work", "company name"),
     "an employer's name"),
    (("landlord",), "a landlord's name"),
    (("doctor", "medical", "diagnosis", "condition", "treatment",
      "hospital", "clinic", "illness"), "a medical detail"),
    # Email and phone come before the address rule: "an email address" has
    # the word "address" in it, and the longest match is not the right one.
    (("email", "e-mail"), "an email address"),
    (("phone", "mobile number", "cell number", "telephone"), "a phone number"),
    (("social media", "instagram", "facebook", "handle", "username"),
     "a social media handle"),
    (("street address", "home address", "address", "apartment number",
      "unit number", "apartment", "street"), "an address"),
    # The catch-all for a name, last, so a more specific kind claims it first.
    (("name",), "a name"),
)

_NOT_A_REMOVAL = {"", "none", "nothing", "n/a", "na", "no", "-"}


def personal_removals(removed) -> list[str]:
    """The kinds of personal detail taken out, in words a neighbor uses.

    Only genuinely identifying things survive this: a name, a child's name, a
    school, an address, a phone number, an email, an employer, a medical
    detail. Everything else the review happened to mention — a tightened
    sentence, a dropped adjective, its own jargon — is dropped, because it was
    never a privacy removal in the first place.

    Order within the list follows the order the review gave, and duplicates
    collapse: two names taken out is still "a name" said once.
    """
    out: list[str] = []
    for item in removed or []:
        said = str(item).strip().lower()
        if said in _NOT_A_REMOVAL or said.startswith(("no ", "none ", "nothing ")):
            continue
        for keywords, plain in PERSONAL_REMOVALS:
            if any(word in said for word in keywords):
                if plain not in out:
                    out.append(plain)
                break
    return out
