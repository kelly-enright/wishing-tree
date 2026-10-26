# Price guide — for checking

Every item in `data/price_guide.json`: **72 entries** across 8 categories. Last updated 2026-10-21.

These numbers are **invented reference figures**, not scraped prices — and
they reach families. When a family does not give a cost, the Intake agent
fills one in from this guide, and that is the number a donor sees and shops
to. A figure that is wrong by half is a donor turning up with the wrong
thing, so each row is worth a minute against a real store.

The **Checked** column is for you: write the real price you found, or a check mark.

## Clothing

| Item | Typical | Range | Checked |
|---|---|---|---|
| socks and underwear, multipack | $20 | $12–$35 | |
| winter hat, gloves and scarf set | $25 | $15–$40 | |
| children's rain boots | $28 | $18–$45 | |
| school uniform polo, pack of three | $30 | $20–$48 | |
| children's sneakers | $35 | $25–$55 | |
| children's sneakers, school | $35 | $22–$55 | |
| adult jeans | $35 | $22–$55 | |
| work shoes, non-slip | $40 | $28–$60 | |
| dress shirt and tie | $40 | $25–$65 | |
| infant clothing bundle | $40 | $25–$65 | |
| snow boots, child | $40 | $25–$65 | |
| children's winter coat | $45 | $30–$70 | |
| warm layers, per child | $45 | $30–$75 | |
| school uniform set | $50 | $30–$80 | |
| dress shoes, adult | $50 | $30–$85 | |
| interview blazer | $55 | $35–$90 | |
| adult winter coat | $70 | $45–$110 | |
| adult work boots, steel toe | $75 | $50–$120 | |

## Essentials (hygiene, diapers)

| Item | Typical | Range | Checked |
|---|---|---|---|
| wipes, one month | $20 | $12–$30 | |
| period products, one month | $20 | $12–$32 | |
| laundry and cleaning supplies | $30 | $20–$45 | |
| towels set | $30 | $18–$45 | |
| hygiene basics bundle | $35 | $20–$55 | |
| bedding set | $50 | $30–$85 | |
| diapers, one month | $55 | $40–$80 | |
| formula, one month | $120 | $90–$170 | |
| baby formula, one month | $150 | $100–$220 | |

## School supplies

| Item | Typical | Range | Checked |
|---|---|---|---|
| notebooks and folders | $20 | $12–$32 | |
| scientific calculator | $20 | $12–$32 | |
| backpack | $30 | $18–$50 | |
| elementary supply list | $35 | $25–$55 | |
| graphing calculator | $40 | $25–$65 | |
| middle school supply list | $45 | $30–$70 | |

## Household

| Item | Typical | Range | Checked |
|---|---|---|---|
| reacher grabber tool | $20 | $12–$32 | |
| grab bar, bathroom | $25 | $15–$40 | |
| box fan | $25 | $15–$40 | |
| small fire extinguisher | $30 | $20–$45 | |
| twin sheet set | $30 | $18–$50 | |
| bath towel set | $30 | $18–$50 | |
| table lamp | $30 | $18–$50 | |
| smoke detector, pack of two | $35 | $22–$55 | |
| laundry basket and drying rack | $35 | $20–$55 | |
| full or queen sheet set | $40 | $25–$65 | |
| floor lamp | $45 | $28–$75 | |
| dishes and cutlery for four | $45 | $28–$75 | |
| space heater | $45 | $30–$75 | |
| comforter or duvet | $55 | $35–$90 | |
| shower chair | $60 | $40–$95 | |
| pots and pans set | $60 | $35–$100 | |
| crib mattress | $70 | $45–$110 | |
| vacuum cleaner | $80 | $50–$130 | |
| microwave | $90 | $60–$140 | |
| kitchen table and chairs, small | $140 | $90–$220 | |

## Food

| Item | Typical | Range | Checked |
|---|---|---|---|
| birthday cake and dinner | $35 | $22–$55 | |
| groceries for one week, small household | $60 | $40–$90 | |
| prepared freezer meals, one week | $70 | $45–$110 | |
| groceries for one week, large household | $110 | $80–$160 | |
| groceries for one week, household of four | $120 | $80–$180 | |

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
| book set for a child | $25 | $15–$40 | |
| toy or game | $28 | $15–$45 | |
| children's holiday gift | $30 | $18–$50 | |
| birthday gift, child | $30 | $18–$50 | |

## Other

| Item | Typical | Range | Checked |
|---|---|---|---|
| monthly bus pass | $35 | $25–$50 | |
| smoke detector and extinguisher | $50 | $30–$80 | |
| mobility or bathing aid | $60 | $35–$110 | |
| soft hats, a lap blanket and slipper socks for hospital days | $75 | $50–$120 | |
| first apartment basics | $180 | $120–$300 | |

## Worth a closer look first

- **Widest range:** partial rent, one month at $300–$900. A wide range makes a vague wish, since the top of the range is what a donor is asked for.
- **Dearest:** partial rent, one month at $500 typical, against a $1,000 cap for rent & utilities. A figure that drifts above its cap quietly stops wishes posting, because they are held for a coordinator instead.
- **Cheapest:** socks and underwear, multipack at $20.

## How a wrong number shows up

- **Too low** — a donor grants the wish, finds it costs more, and either pays the difference or the family gets a cheaper substitute than they needed.
- **Too high** — the wish looks expensive next to others on the wall, and donors with smaller budgets filter it out. Rent and utility wishes are capped at $1,000 and items at $300; a figure above the cap is held rather than posted.

Change a price by editing `data/price_guide.json` and re-running this script. Nothing is cached — the agent reads the file at run time.

_Generated 2026-10-26 by `backend/price_guide_review.py`._