# Price guide — for checking

Every item in `data/price_guide.json`: **37 entries** across 7 categories. Last updated 2026-10-20.

These numbers are **invented reference figures**, not scraped prices — and
they reach families. When a family does not give a cost, the Intake agent
fills one in from this guide, and that is the number a donor sees and shops
to. A figure that is wrong by half is a donor turning up with the wrong
thing, so each row is worth a minute against a real store.

The **Checked** column is for you: write the real price you found, or a tick.

## Clothing

| Item | Typical | Range | Checked |
|---|---|---|---|
| children's sneakers | $35 | $25–$55 | |
| work shoes, non-slip | $40 | $28–$60 | |
| dress shirt and tie | $40 | $25–$65 | |
| children's winter coat | $45 | $30–$70 | |
| warm layers, per child | $45 | $30–$75 | |
| school uniform set | $50 | $30–$80 | |
| interview blazer | $55 | $35–$90 | |
| adult winter coat | $70 | $45–$110 | |

## Essentials (hygiene, diapers)

| Item | Typical | Range | Checked |
|---|---|---|---|
| wipes, one month | $20 | $12–$30 | |
| laundry and cleaning supplies | $30 | $20–$45 | |
| towels set | $30 | $18–$45 | |
| hygiene basics bundle | $35 | $20–$55 | |
| bedding set | $50 | $30–$85 | |
| diapers, one month | $55 | $40–$80 | |
| formula, one month | $120 | $90–$170 | |

## School supplies

| Item | Typical | Range | Checked |
|---|---|---|---|
| notebooks and folders | $20 | $12–$32 | |
| backpack | $30 | $18–$50 | |
| elementary supply list | $35 | $25–$55 | |
| graphing calculator | $40 | $25–$65 | |
| middle school supply list | $45 | $30–$70 | |

## Food

| Item | Typical | Range | Checked |
|---|---|---|---|
| birthday cake and dinner | $35 | $22–$55 | |
| grocery gift card, one week, small household | $60 | $40–$90 | |
| prepared freezer meals, one week | $70 | $45–$110 | |
| grocery gift card, one week, large household | $110 | $80–$160 | |

## Rent & utilities

| Item | Typical | Range | Checked |
|---|---|---|---|
| water bill, one quarter | $110 | $70–$170 | |
| gas bill, one month | $130 | $70–$220 | |
| electric bill, one month | $150 | $90–$250 | |
| partial rent, one month | $500 | $300–$900 | |

## Gifts

| Item | Typical | Range | Checked |
|---|---|---|---|
| art or craft set | $25 | $15–$40 | |
| toy or game | $28 | $15–$45 | |
| children's holiday gift | $30 | $18–$50 | |
| birthday gift, child | $30 | $18–$50 | |

## Other

| Item | Typical | Range | Checked |
|---|---|---|---|
| monthly bus pass | $35 | $25–$50 | |
| smoke detector and extinguisher | $50 | $30–$80 | |
| mobility or bathing aid | $60 | $35–$110 | |
| gas card for medical travel | $75 | $50–$120 | |
| first apartment basics | $200 | $120–$350 | |

## Over the cap — fix these first

A wish costing more than its category cap is **held for a coordinator rather than posted**. These guide entries have a range top above their own cap, so a family who lands on the top of the range will quietly find their wish doesn't go up:

| Item | Range top | Cap for its category |
|---|---|---|
| first apartment basics | $350 | $300 |

Either lower the range top, or raise that category's cap in `backend/config.py`. Both are one line.

## Worth a closer look first

- **Widest range:** partial rent, one month at $300–$900. A wide range makes a vague wish, since the top of the range is what a donor is asked for.
- **Dearest:** partial rent, one month at $500 typical, against a $1,000 cap for rent & utilities. A figure that drifts above its cap quietly stops wishes posting, because they are held for a coordinator instead.
- **Cheapest:** wipes, one month at $20.

## How a wrong number shows up

- **Too low** — a donor grants the wish, finds it costs more, and either pays the difference or the family gets a cheaper substitute than they needed.
- **Too high** — the wish looks expensive next to others on the wall, and donors with smaller budgets filter it out. Rent and utility wishes are capped at $1,000 and items at $300; a figure above the cap is held rather than posted.

Change a price by editing `data/price_guide.json` and re-running this script. Nothing is cached — the agent reads the file at run time.

_Generated 2026-10-20 by `backend/price_guide_review.py`._