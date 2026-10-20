# Wishing Tree — Harness

A running record of how this project is built. It grows with every problem.
Written for the report: the agent-design, safety and tokenomics sections are
assembled from here.

---

## 1. Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 19 + Vite + TypeScript | Types catch wrong shapes at build time, and Vite's build is a plain static folder that any server can host. |
| Backend | Python FastAPI | Same process serves the API and the built site, so there is one port and one command. |
| Agents | PydanticAI | Agents return the Pydantic models in `backend/models.py` directly, so a model's answer is validated before it reaches the database. Added in a later problem. |
| Storage | SQLite (`data/wishing_tree.db`) | A single file, created on first run, with no database server to install. Keeps the project inside the course's 10-minute setup rule. |
| Gateway | Portkey | The course key routes to the one allowed model. |

**How it runs.** `python run.py` checks the key, creates and seeds the database,
then serves both the API and `frontend/dist` on one port. The built frontend is
committed, so the teaching staff need Python and nothing else. The reloader is
off, so one edit cannot leave a trail of orphaned servers.

## 2. Model

One model, everywhere: **`gpt-6-luna`**, through the Portkey gateway at
`https://api.portkey.ai/v1`. It is named once, in `backend/config.py`, so no
second model can appear anywhere in the code or in a run.

Prices for the tokenomics section are **placeholders** in `config.py` until
measured runs exist. While they are placeholders, `PRICES_ARE_PLACEHOLDERS` is
`True` and every cost the app reports is `0.00`, so a placeholder number cannot
quietly reach the report. A test asserts this.

## 3. The .env lookup

Required by the course run rules, implemented in `config.require_api_key()`:

1. `<repo>/.env`
2. `<repo>/../.env` ← where the teaching staff keep their key

Nearest wins (`override=False`, loaded in order), and a key already exported in
the shell beats both files. If `PORTKEY_API_KEY` is in neither, the app stops
before serving anything and prints both paths it checked, with what to do next.
Four tests in `tests/test_config.py` cover this, including the staff case of a
key only in the parent folder.

## 4. Data model

All structured types are Pydantic models in `backend/models.py`. Nothing in the
project defines a shape anywhere else.

| Model | What it holds | Notes |
|---|---|---|
| `Region` | name, zip codes, hub name and address, weekly drop-off and delivery windows, active flag | Pure configuration. Adding a city is an edit to `REGIONS` in `config.py`. |
| `Window` | weekday, start, end | Validates that the end is after the start; `label()` renders "Thursday 4:00 PM-7:00 PM" for the UI. |
| `Family` | alias, zip, region, contact address, contact phone | Address and phone are **coordinator-only**. `public_view()` returns alias, zip and region only. |
| `Request` | family alias, category, type, description, cost or range, deadline, occasion, zip, status, plus type-specific fields | A "request" in the code is a "wish" in the interface. |
| `Donor` | alias, zip, contact details, budget, preferred categories, preference | Also has `public_view()`. |
| `Pledge` | request, donor, drop-off date, delivery date, family confirmation, status | One per claimed wish. |
| `AgentCallLog` | agent, model, operation, input / cached input / output tokens, latency, ok, error, cost | One row per model call; the evidence for tokenomics. |

### Vocabulary

- **Categories:** rent/utilities, essentials, clothing, school supplies, gifts, food, other
- **Occasions:** holiday, birthday, back-to-school, job interview, emergency, everyday
- **Request type:** `specific` (exact item, product link, brand/size/colour, open-to-substitute) or `flexible` (described need, essentials only, optional budget range)
- **Request status:** `draft` → `pending_review` → `open` → `granted` → `dropped_off` → `delivered`, or `missed`
- **Pledge status:** `pledged` → `dropped_off` → `delivered`, or `missed` / `cancelled`

### Rules the types enforce on their own

- A specific wish must carry a product link; a flexible wish must not.
- Every wish needs an estimated cost or a budget range; a backwards range is rejected.
- Zip codes must be five digits.
- A new wish starts as `draft`: nothing is public until the family approves it.

## 5. Region configuration

One active region, in `config.REGIONS`:

| | |
|---|---|
| Name | New Haven, CT |
| Zips | 06510–06520, 06524, 06525 |
| Hub | Yale School of Management, 165 Whitney Ave, New Haven, CT 06511 |
| Drop-off | Thursday 4:00–7:00 PM |
| Delivery | Saturday 10:00 AM–1:00 PM |

A second city needs one more `Region` entry and no code change anywhere.

## 6. Seed data

`backend/seed.py`, run automatically when the database is empty: **15 families,
40 wishes, 8 donors, 8 pledges**.

- All 7 categories and all 6 occasions appear.
- 19 specific / 21 flexible.
- Statuses spread across the whole life of a wish, so later screens have real rows: 27 open, 4 granted, 3 delivered, 2 pending review, 2 missed, 1 dropped off, 1 draft.
- Deadlines are offsets from today, so the data never goes stale.
- Situations are the ones from the project brief: a single parent working two jobs, a child in chemo, an eviction notice, an interview outfit, an apartment fire, a teen ageing out of foster care.

**Everything is invented.** Street names are made up, phone numbers use the
555-01xx fiction range, and all 19 product links point at allowlisted retailers
with made-up product paths. Tests assert all three.

## 7. Safety measures so far

Agents arrive in later problems; these are the ones already standing.

| Measure | Where | What it stops |
|---|---|---|
| Retailer allowlist | `config.is_allowed_retailer()` | A wish linking anywhere but 20 known retailers. https only, no embedded credentials, and the host must match or be a subdomain of an allowlisted domain — a lookalike like `target.com.evil.example` fails. |
| Links are never fetched | by design | No agent and no server code opens a product URL, so a hostile link has nothing to run against. |
| Contact details are separable | `public_view()` on `Family` and `Donor` | Addresses and phone numbers reaching the wish wall, a donor, or a model. |
| Nothing is public by default | `RequestStatus.DRAFT` default | A drafted wish going public before the family approves it. |
| Placeholder prices cannot pass as real | `PRICES_ARE_PLACEHOLDERS` + test | A made-up cost reaching the report. |
| Token budgets declared | `config.py` | Groundwork for the overspending guard: per-session, per-review, per-match-run and daily caps. |

## 8. Tests

`./.venv/bin/python -m pytest tests -q` — **37 passing**.

- `test_config.py` — the .env lookup in all four cases, region config, allowlist accept/reject, placeholder prices
- `test_models.py` — every validator, and that `public_view()` drops contact details
- `test_seed.py` — counts, category and occasion coverage, specific/flexible balance, all links allowlisted, fiction-range phone numbers, re-seeding does not duplicate

## 9. Specs

_Filled in as the agents are built._

### Agents
_Not built yet._

### Tools
_Not built yet._
