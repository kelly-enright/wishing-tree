"""Write output/price_guide_review.md — every price, laid out to be checked.

    ./.venv/bin/python -m backend.price_guide_review

The guide is invented reference data. These numbers reach families: the Intake
agent uses them to fill in a cost when the family does not give one, and that
cost is what a donor sees and shops to. A number that is wrong by half is a
donor turning up with the wrong thing, so the guide should be spot-checked
against real store prices by a person.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from backend import config

OUTPUT_PATH = config.OUTPUT_DIR / "price_guide_review.md"

CATEGORY_TITLES = {
    "clothing": "Clothing",
    "essentials": "Essentials (hygiene, diapers)",
    "school_supplies": "School supplies",
    "food": "Food",
    "rent_utilities": "Rent & utilities",
    "gifts": "Gifts",
    "other": "Other",
}


def build() -> str:
    guide = json.loads(config.PRICE_GUIDE_PATH.read_text(encoding="utf-8"))
    items = guide["items"]

    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_category[item["category"]].append(item)

    lines = [
        "# Price guide — for checking",
        "",
        f"Every item in `data/price_guide.json`: **{len(items)} entries** across "
        f"{len(by_category)} categories. Last updated {guide.get('updated', 'unknown')}.",
        "",
        "These numbers are **invented reference figures**, not scraped prices — and",
        "they reach families. When a family does not give a cost, the Intake agent",
        "fills one in from this guide, and that is the number a donor sees and shops",
        "to. A figure that is wrong by half is a donor turning up with the wrong",
        "thing, so each row is worth a minute against a real store.",
        "",
        "The **Checked** column is for you: write the real price you found, or a tick.",
        "",
    ]

    for category in CATEGORY_TITLES:
        rows = by_category.get(category, [])
        if not rows:
            continue
        rows.sort(key=lambda r: r["typical_usd"])
        lines += [
            f"## {CATEGORY_TITLES[category]}",
            "",
            "| Item | Typical | Range | Checked |",
            "|---|---|---|---|",
        ]
        for item in rows:
            low, high = item["range_usd"]
            lines.append(
                f"| {item['item']} | ${item['typical_usd']:,} | "
                f"${low:,}–${high:,} | |"
            )
        lines.append("")

    cheapest = min(items, key=lambda i: i["typical_usd"])
    dearest = max(items, key=lambda i: i["typical_usd"])
    widest = max(items, key=lambda i: i["range_usd"][1] - i["range_usd"][0])

    # A guide figure above its own category cap is a wish that will be held
    # rather than posted — worth knowing before a family hits it.
    over_cap = [
        i for i in items
        if i["range_usd"][1] > config.wish_value_cap(i["category"])
    ]
    if over_cap:
        lines += [
            "## Over the cap — fix these first",
            "",
            "A wish costing more than its category cap is **held for a coordinator "
            "rather than posted**. These guide entries have a range top above their "
            "own cap, so a family who lands on the top of the range will quietly "
            "find their wish doesn't go up:",
            "",
            "| Item | Range top | Cap for its category |",
            "|---|---|---|",
        ]
        for item in over_cap:
            cap = config.wish_value_cap(item["category"])
            lines.append(
                f"| {item['item']} | ${item['range_usd'][1]:,} | ${cap:,.0f} |"
            )
        lines += [
            "",
            "Either lower the range top, or raise that category's cap in "
            "`backend/config.py`. Both are one line.",
            "",
        ]

    lines += [
        "## Worth a closer look first",
        "",
        f"- **Widest range:** {widest['item']} at "
        f"${widest['range_usd'][0]:,}–${widest['range_usd'][1]:,}. A wide range makes "
        "a vague wish, since the top of the range is what a donor is asked for.",
        f"- **Dearest:** {dearest['item']} at ${dearest['typical_usd']:,} typical, "
        f"against a ${config.wish_value_cap(dearest['category']):,.0f} cap for "
        f"{CATEGORY_TITLES[dearest['category']].lower()}. A figure that drifts above "
        "its cap quietly stops wishes posting, because they are held for a "
        "coordinator instead.",
        f"- **Cheapest:** {cheapest['item']} at ${cheapest['typical_usd']:,}.",
        "",
        "## How a wrong number shows up",
        "",
        "- **Too low** — a donor grants the wish, finds it costs more, and either "
        "pays the difference or the family gets a cheaper substitute than they needed.",
        "- **Too high** — the wish looks expensive next to others on the wall, and "
        "donors with smaller budgets filter it out. Rent and utility wishes are "
        f"capped at ${config.MAX_RENT_UTILITIES_WISH_USD:,.0f} and items at "
        f"${config.MAX_ITEM_WISH_USD:,.0f}; a figure above the cap is held rather "
        "than posted.",
        "",
        "Change a price by editing `data/price_guide.json` and re-running this script. "
        "Nothing is cached — the agent reads the file at run time.",
        "",
        f"_Generated {date.today().isoformat()} by `backend/price_guide_review.py`._",
    ]
    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
