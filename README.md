# Wishing Tree

A year-round online giving tree for New Haven, Connecticut. A neighbor who
could use a hand describes it in their own words; an **Intake** agent turns
that into clear, approvable wishes; a **Privacy & Safety** agent removes names,
addresses, schools, employers and medical details before anything goes public;
a **Matchmaker** agent ranks the open wishes for a wish granter by what they
can actually help with. Everything moves through one weekly drop-off at Yale
School of Management and one weekly delivery run, so a neighbor and a wish
granter help each other without ever exchanging personal details.

MGT 409 (AI Foundations for Managers) final project — Kelly Enright.

---

## The three roles

| Role | Who they are | Where they go |
|---|---|---|
| **Neighbor** | asks for something they or their family could use | *Make a wish* → chat with the Intake agent, approve the wishes it drafts, then follow each one on *My wishes* |
| **Wish granter** | picks a wish and buys it | *The Wish Tree* → tap a leaf, commit to a wish, drop it off during the weekly window |
| **Admin** | the staff who make delivery happen | *Admin* → the weekly run sheet, and every agent call with its tokens and cost |

A neighbor never sees who granted their wish. A wish granter never sees a
neighbor's name, address or phone. Contact details exist on the admin run sheet
and nowhere else.

---

## Setup

You need **Python 3.11 or newer and nothing else**. The React frontend is
already built and committed, so there is no Node step and no database server.

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### Put the API key in place

The app needs `PORTKEY_API_KEY`. It looks in two places, in this order:

1. `./.env` — this repo's own folder
2. `../.env` — the folder one level above the repo

The second is the one the teaching staff use, so a key kept beside the repo is
found without copying it in. Either works:

```bash
cp .env.example .env     # then fill in the key
```

If the key is in neither place the app stops before starting and prints both
paths it checked. The model is **gpt-6-luna** through the Portkey gateway,
named once in `backend/config.py`.

### Seed the database and start the app

```bash
./.venv/bin/python -m backend.seed --reset
./.venv/bin/python run.py
```

Then open **http://127.0.0.1:8000**.

The seed step is optional on a fresh clone — the app creates and fills
`data/wishing_tree.db` on first start if it is missing — but running it
explicitly means you know what state you are in.

### The port

The app runs on **8000** by default. If that port is busy it says so and stops
rather than failing halfway; pick another one:

```bash
./.venv/bin/python run.py --port 8001
```

### Resetting the demo data

Any time you want a clean tree — before a demo, after testing:

```bash
./.venv/bin/python -m backend.seed --reset
```

That deletes `data/wishing_tree.db` and rebuilds it from `backend/seed.py`.
Reload the page afterwards. Every neighbor, wish granter, address, phone number
and wish in the seed is **invented** — see [About the data](#about-the-data).

---

## Trying it out

### Demo logins

Every seeded account uses the password **`neighbor-demo`**.

| Role | Email | Password |
|---|---|---|
| Neighbor | `neighbora07@example.com` | `neighbor-demo` |
| Wish granter | `granterd02@example.com` | `neighbor-demo` |

Any seeded alias works the same way: `neighbora04@`, `neighbora12@`,
`granterd01@`, `granterd03@` and so on, all `@example.com`.

**Continue as…** on the landing page is the faster route. It lists every
seeded neighbor and wish granter by alias and signs you in with one click, no
typing. It shows aliases and zip codes only — never an address or a phone
number — and it is labeled as a demo shortcut, because that is what it is.

**Admin** is in the footer of every page, and on the login page. The passcode
is **`wishingtree-demo`** (in `backend/config.py`, with a show/hide control on
the field).

### A five-minute walkthrough

1. **A neighbor makes a wish.** Continue as *Neighbor A07* → **Make a wish**.
   Type something in plain English — "my daughter needs a winter coat, she's 8"
   — and answer the follow-up. The Intake agent drafts the wish; edit or delete
   anything, then approve. It goes to the Privacy & Safety agent, which strips
   anything identifying, and only then appears on the tree. **My wishes** shows
   it at *Being checked*, then *On the tree*.

2. **A wish granter finds it.** Sign out, Continue as *Granter D02* → **The
   Wish Tree**. Every open wish is a leaf. Tap one and the wish opens in the
   panel beside the tree (or as a sheet over it on a phone). **Match me to
   wishes** asks the Matchmaker agent to rank the tree for your budget and the
   categories you like to help with, with one line saying why each fits.
   **I'll grant this wish** shows what to bring, the drop-off window and the
   Saturday it arrives, and locks the wish once you confirm you can make it.

3. **Admin makes it real.** Footer → **Admin** → passcode `wishingtree-demo` →
   **Run sheet**. One week at a time: drop-offs with the wish granter's
   contact details, deliveries grouped by household, and rent or utility
   payments in their own section. Mark the drop-off received, then mark the
   delivery delivered. The neighbor's *My wishes* tracker moves to **Delivered**
   and the leaf turns gold on the tree.

Rent and utility wishes never pass through the hub. Wishing Tree pays the
landlord or the provider directly — money never moves between two neighbors.

---

## Seeing the AI at work

Two places, for two audiences.

**Your own session.** On any neighbor or wish granter screen, open **Show AI
details**. It is collapsed by default and shows what *this session* has spent:
input tokens, cached input, output, and the dollar cost at the prices in
`backend/config.py`.

**Every call ever made.** Admin → **Agent activity** lists each model call in
order: which agent, which tools it ran, what the safety review removed and
flagged, tokens in and out, latency, and cost. Under it, **Intake
conversations** gives each intake's length and how many seconds it took. No
neighbor's contact details are recorded on that page.

The same trail is written to `output/audit_trail.json`, one JSON object per
line, and to the `agent_calls` table.

### Spending limits

Two caps in `backend/config.py`: **20,000 tokens per intake session** and
**500,000 per day** across the whole app. Both are checked on the server
immediately before every model call, so nothing sent from a browser can get
around them. When a cap is reached the chat stops with a plain explanation and
anything already drafted is kept.

---

## Running the tests

### The fast suite — no API key, no model calls, free

```bash
./.venv/bin/python -m pytest
```

Agents are stubbed. This is the suite to run after any change.

### The live safety tests — real attacks against gpt-6-luna

```bash
./.venv/bin/python -m pytest -m live tests/test_safety_live.py
```

Ten real attacks — prompt injection, cash requests, scam patterns, contact
details hidden in a wish — run against the real model and the real prompts.
Results are written to `output/safety_test_results.json` with the tokens and
cost each defense spent. Needs a working key and spends a few cents.

### The token measurement script

```bash
./.venv/bin/python -m backend.measure
```

Ten intakes, ten safety reviews, ten matchmaker runs, plus two experiments:
whether the Matchmaker needs more candidates, and whether capping output tokens
saves money. Writes `output/tokenomics_runs.json` (raw) and
`output/tokenomics.md` (the report). It runs against **its own database**
(`data/measure.db`) with a raised daily cap, so benchmarking never touches the
demo data or spends the operational budget.

### Check the app is alive

```bash
curl http://127.0.0.1:8000/api/health
```

Reports the model, whether the key was found, the row counts in the database,
and the hub and weekly windows.

---

## Layout

```
backend/            FastAPI app
  config.py         every tunable setting: model, region, limits,
                    retailer allowlist, token budgets, prices, passcode
  models.py         all Pydantic types
  db.py             SQLite schema and queries
  seed.py           synthetic seed data (nothing here is real)
  agents/           the three agents and their shared model plumbing
  measure.py        the token measurement script
  main.py           API, and serves the built frontend
frontend/           React + Vite + TypeScript source
  dist/             the BUILT site — committed on purpose, so running
                    this project needs nothing but Python
prompts/            the agents' runtime system prompts
output/             harness.md, audit_trail.json, tokenomics.md and the
                    safety results — the evidence for the report
data/               wishing_tree.db, created on first run
tests/              the pytest suite
screenshots/        screenshots taken while building
run.py              the one command that starts everything
```

### Rebuilding the frontend

Only needed if you change anything under `frontend/src`:

```bash
cd frontend
npm install
npm run build
```

`npm run dev` also works while developing; it proxies `/api` to the Python
server on port 8000.

---

## About the data

Every neighbor, wish granter, address, phone number and wish in this project is
**invented**. Phone numbers use the 555-01xx range reserved for fiction, street
names are made up, and product links point at allowlisted retailers with
made-up product paths. The app never fetches a product link — links are
compared as text. No real person's details appear anywhere in this repository.

`.env` is excluded by `.gitignore` and no key has ever been committed.
