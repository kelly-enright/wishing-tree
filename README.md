# Wishing Tree

A year-round giving tree for New Haven, CT. Families describe what they need in
their own words; an Intake agent turns that into wishes they approve; a Privacy
& Safety agent strips identifying details before anything goes public; a
Matchmaker agent ranks open wishes for a donor. Donations move through one
weekly drop-off at a hub and one weekly delivery run.

MGT 409 (AI Foundations for Managers) final project — Kelly Enright.

---

## Run it

You need **Python 3.11+ and nothing else**. The React frontend is already built
and committed; FastAPI serves it.

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python run.py
```

Then open **http://127.0.0.1:8000**.

On first run the app creates `data/wishing_tree.db` and fills it with synthetic
seed data, so the wish wall is populated immediately. Nothing else to install,
no Node, no database server.

If port 8000 is taken, the app says so and you can pick another:

```bash
./.venv/bin/python run.py --port 8001
```

### The API key

The app needs `PORTKEY_API_KEY`. It looks in two places, in this order:

1. `./.env` — this repo's own folder
2. `../.env` — the folder one level above the repo

The second is the one the teaching staff use. Copy `.env.example` to `.env` in
either place and fill in the key. If the key is in neither, the app stops before
starting and prints both paths it checked.

The model is **gpt-6-luna** through the Portkey gateway, named once in
`backend/config.py`. No other model is used anywhere in this project.

---

## The three ways in

The landing page has three entry points:

- **I need help** — family sign-up (zip, delivery address, phone)
- **I want to give** — donor sign-up (zip, address, phone, budget, categories, preference)
- **Coordinator** — passcode protected, because those screens show families' home
  addresses and phone numbers. The passcode is in `backend/config.py`; for now it is
  **`wishingtree-demo`**.

There are no passwords otherwise. Signing up creates the record and gives you an alias
like `Family A59`; this browser remembers the alias so you come back to the same account.

**Continue as…** on the landing page lists every existing family and donor by alias, so
you can switch accounts without typing anything. It is a demo shortcut and is labelled as
one. It shows aliases and zips only — never an address or a phone number.

---

## The Intake agent

Sign in as a family (or use **Continue as…**) and open *I need help*. You chat in
plain English; the Intake agent asks only the follow-ups that matter, drafts your
wishes in a neutral standard format, and you edit, delete or approve each one.
Approved wishes are saved as `pending_review` — nothing is public yet.

A panel beside the chat shows what the session has cost in tokens: input, cached
input, output, and dollars. Costs read "price not set" until the three prices in
`backend/config.py` are filled in; the token counts are real either way.

Every model call is logged to `output/audit_trail.json` (one JSON object per line)
and to the `agent_calls` table.

---

## Check it is working

```bash
curl http://127.0.0.1:8000/api/health
```

Reports the model, whether the key was found, the row counts in the database,
and the active region's hub and weekly windows.

```bash
./.venv/bin/python -m pytest tests -q
```

---

## Layout

```
backend/            FastAPI app
  config.py         every tunable setting: model, regions, limits,
                    retailer allowlist, token budgets, prices
  models.py         all Pydantic types
  db.py             SQLite schema and queries
  seed.py           synthetic seed data (nothing here is real)
  main.py           API + serves the built frontend
frontend/           React + Vite TypeScript source
  dist/             the BUILT site — committed on purpose
prompts/            agents' runtime system prompts
output/             harness.md, audit_trail.json and other evidence
data/               wishing_tree.db, created on first run
tests/              pytest suite
screenshots/        screenshots collected while building
run.py              the one command that starts everything
```

### Rebuilding the frontend

Only needed if you change anything under `frontend/src`:

```bash
cd frontend
npm install
npm run build
```

`npm run dev` also works for frontend development; it proxies `/api` to the
Python server on port 8000.

### Rebuilding the database

```bash
./.venv/bin/python -m backend.seed --reset
```

---

## About the data

Every family, donor, address, phone number and wish in this project is
**invented**. Phone numbers use the 555-01xx range reserved for fiction, street
names are made up, and product links point at allowlisted retailers with
made-up product paths. No part of the app ever fetches a product link. No real
person's details appear anywhere.
