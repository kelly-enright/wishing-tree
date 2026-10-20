"""The Intake agent: chats with a family and drafts their wishes.

What the family types reaches this agent. What they typed into the sign-up
form — their street address and phone number — does not, and cannot: the deps
this agent runs with carry an alias and an id, and nothing else about them.

Every call is timed, costed and written to the audit trail.
"""

from __future__ import annotations

import difflib
import json
import time
from datetime import date
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic_ai import Agent, CachePoint, RunContext
from pydantic_ai.messages import ModelMessage, ToolCallPart
from pydantic_ai.settings import ModelSettings

from backend import config, db, text
from backend.agents import audit, budget
from backend.agents.model import build_model
from backend.models import AgentCallLog, Category, IntakeReply, Occasion

AGENT_NAME = "intake"
PROMPT_PATH = config.PROMPTS_DIR / "intake_agent.md"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def prompt_version() -> str:
    return audit.prompt_version(system_prompt())


@dataclass
class IntakeDeps:
    """Everything the agent is allowed to know about who it is talking to.

    Deliberately an alias and an id. No address, no phone, no name.
    """

    family_alias: str
    family_id: int
    session_id: str
    blocked_lookups: list[int] = field(default_factory=list)


# --------------------------------------------------------------------------
# Price guide
# --------------------------------------------------------------------------

_STOPWORDS = {"a", "an", "the", "for", "of", "per", "and", "with", "one", "to"}

# Words families use for the same thing the guide names differently.
_SYNONYMS = {
    "boys": "children", "boy": "children", "girls": "children", "girl": "children",
    "kid": "children", "kids": "children", "child": "children", "son": "children",
    "daughter": "children", "toddler": "children", "baby": "children",
    "infant": "children", "newborn": "children", "youth": "children",
    "adults": "adult", "parent": "adult", "mom": "adult", "mother": "adult",
    "dad": "adult", "father": "adult", "coats": "coat", "shoes": "shoe",
    "sneaker": "shoe", "sneakers": "shoe", "boots": "shoe", "groceries": "grocery",
    "food": "grocery", "electricity": "electric", "rental": "rent",
}


def _words(text: str) -> set[str]:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower())
    out = set()
    for word in cleaned.split():
        if word in _STOPWORDS:
            continue
        out.add(_SYNONYMS.get(word, word))
    return out


def _match_score(probe: str, candidate: str) -> float:
    """How well a family's wording matches a price-guide entry.

    Mostly word overlap, because "boys winter coat" and "children's winter
    coat" are the same thing while looking quite different to a character-level
    comparison. A little string similarity breaks ties.
    """
    probe_words, candidate_words = _words(probe), _words(candidate)
    if not probe_words or not candidate_words:
        return 0.0
    shared = probe_words & candidate_words
    coverage = len(shared) / len(probe_words)
    precision = len(shared) / len(candidate_words)
    similarity = difflib.SequenceMatcher(None, probe.lower(), candidate.lower()).ratio()
    return 0.55 * coverage + 0.25 * precision + 0.20 * similarity


@lru_cache(maxsize=1)
def _price_guide() -> list[dict]:
    path = Path(config.PRICE_GUIDE_PATH)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("items", [])


# --------------------------------------------------------------------------
# The agent and its tools
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def intake_agent() -> Agent:
    """Built on first use, so importing this module needs no API key."""
    agent = Agent(
        build_model(),
        output_type=IntakeReply,
        deps_type=IntakeDeps,
        system_prompt=system_prompt(),
        model_settings=ModelSettings(max_tokens=config.MAX_OUTPUT_TOKENS_INTAKE),
        retries=2,
    )

    @agent.system_prompt
    def who_is_here(ctx: RunContext[IntakeDeps]) -> str:
        """Appended after the static prompt, so the cacheable prefix is unchanged.

        An alias and an id — the public label and a row number. Nothing that
        identifies the household.
        """
        return (
            f"Today's date is {date.today().isoformat()}. "
            f"You are talking with {ctx.deps.family_alias}, whose family_id is "
            f"{ctx.deps.family_id}. Pass that exact family_id to "
            f"check_open_wish_count."
        )

    @agent.tool
    def get_categories_and_occasions(ctx: RunContext[IntakeDeps]) -> dict:
        """The only category and occasion values a wish may use."""
        return {
            "categories": [c.value for c in Category],
            "occasions": [o.value for o in Occasion],
            "request_types": ["specific", "flexible"],
        }

    @agent.tool
    def check_open_wish_count(ctx: RunContext[IntakeDeps], family_id: int) -> dict:
        """How many wishes this family has open, and how many more they may add.

        The family_id argument is accepted because the agent is told to pass it,
        but it is not trusted: the count always comes from the family whose
        session this is. An agent that asks about a different family gets its
        own family's numbers and the attempt is recorded.
        """
        if family_id != ctx.deps.family_id:
            ctx.deps.blocked_lookups.append(family_id)

        with db.connect() as conn:
            used = db.open_wish_count(conn, ctx.deps.family_alias)
        cap = config.MAX_OPEN_WISHES_PER_FAMILY
        return {
            "family": ctx.deps.family_alias,
            "open_wishes": used,
            "maximum": cap,
            "remaining": max(0, cap - used),
        }

    @agent.tool
    def estimate_cost(ctx: RunContext[IntakeDeps], category: str, item: str) -> dict:
        """Typical local cost for an item, from data/price_guide.json.

        Returns the closest entry plus a couple of alternatives, so the agent
        can pick the one that actually fits. Returns `found: false` when
        nothing is close; the agent is told to leave the cost empty in that
        case rather than invent one.
        """
        entries = [e for e in _price_guide() if e["category"] == category]
        if not entries:
            return {"found": False, "reason": f"no price guide entries for {category!r}"}

        ranked = sorted(
            ((_match_score(item, e["item"]), e) for e in entries),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = ranked[0]

        if best_score < 0.45:
            lows = [e["range_usd"][0] for e in entries]
            highs = [e["range_usd"][1] for e in entries]
            return {
                "found": False,
                "category_range_usd": [min(lows), max(highs)],
                "reason": "no close match; use a range only if it clearly fits",
            }

        return {
            "found": True,
            "matched_item": best["item"],
            "typical_usd": best["typical_usd"],
            "range_usd": best["range_usd"],
            "other_options": [
                {"item": e["item"], "typical_usd": e["typical_usd"], "range_usd": e["range_usd"]}
                for _score, e in ranked[1:3]
            ],
        }

    return agent


# --------------------------------------------------------------------------
# Running one turn
# --------------------------------------------------------------------------

# PydanticAI uses an internal tool call to deliver structured output. It is
# not one of this agent's tools, so it is left out of the audit trail.
_INTERNAL_TOOLS = {"final_result"}


def _tool_names(messages: list[ModelMessage]) -> list[str]:
    names: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, ToolCallPart):
                continue
            if part.tool_name in _INTERNAL_TOOLS or part.tool_name in names:
                continue
            names.append(part.tool_name)
    return names


def summarize(message: str, reply: IntakeReply) -> tuple[str, str]:
    """Shape, never content, for the coordinator's activity page.

    The family's words are not summarized, counted into a snippet, or quoted.
    Only how long the message was and how many wishes came out of it. A name
    or a school in a family's message cannot reach the activity page by this
    route, because the words never travel.
    """
    return (
        f"family message, {len(message)} characters",
        f"{text.counted(len(reply.draft_wishes), 'wish', 'wishes')} drafted, "
        f"done={str(reply.done).lower()}",
    )


async def run_turn(
    deps: IntakeDeps,
    message: str,
    history: list[ModelMessage] | None = None,
) -> tuple[IntakeReply, list[ModelMessage], AgentCallLog]:
    """One family message in, one reply out, one audit record written."""
    budget.guard(deps.session_id)     # server-side; no browser can skip this

    agent = intake_agent()
    started = time.perf_counter()
    call = AgentCallLog(
        agent=AGENT_NAME,
        model=config.MODEL_NAME,
        operation="draft_wishes",
        session_id=deps.session_id,
        prompt_version=prompt_version(),
    )

    try:
        # A leading CachePoint marks "cache everything up to here", which is
        # the system prompt: long, stable, and first. The family's message comes
        # after the breakpoint, so it never invalidates the cached prefix.
        result = await agent.run(
            [CachePoint(), message], deps=deps, message_history=history or []
        )
    except Exception as exc:                      # noqa: BLE001 - recorded, then re-raised
        call.ok = False
        call.error = f"{type(exc).__name__}: {exc}"
        call.latency_ms = int((time.perf_counter() - started) * 1000)
        audit.record(call)
        raise

    usage = result.usage
    cached = usage.cache_read_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    # The API's input figure is the whole prompt, cached and cache-write parts
    # included. Split it so each bucket is priced once.
    uncached = config.split_input_tokens(usage.input_tokens or 0, cached, cache_write)

    call.input_tokens = uncached
    call.cached_input_tokens = cached
    call.cache_write_tokens = cache_write
    call.output_tokens = usage.output_tokens or 0
    call.latency_ms = int((time.perf_counter() - started) * 1000)
    call.tools_called = _tool_names(result.new_messages())
    call.input_summary, call.output_summary = summarize(message, result.output)
    call.estimated_cost_usd = config.estimate_cost_usd(
        uncached, cached, call.output_tokens, cache_write
    )
    audit.record(call)

    return result.output, list(result.all_messages()), call
