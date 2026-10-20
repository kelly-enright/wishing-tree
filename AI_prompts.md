# AI Prompts — Final Project: Wishing Tree

Log of the prompts I typed into the vibe coder (Claude Code) while building Wishing Tree,
my final project for MGT 409 (AI Foundations for Managers).

One section per problem, in the order the work happened. Prompts are recorded **verbatim**,
including typos. Where a problem needed more than one prompt, a **Why a follow-up was needed**
note records, in one sentence, what the first prompt was lacking.

---

## Setup — Project Kickoff

### Prompt 1

> Final Project: "Wishing Tree" — a year-round giving tree powered by AI agents
>
> This is my final project for MGT 409 (AI Foundations for Managers). It is a solo project due Monday, October 26 at 6:00 PM. The full requirements are here: https://zlisto.github.io/mgt_409_fa26/project_requirements.html. Read them before we start, and keep them in mind at every step.
>
> The scenario: Each Christmas my church put up a "giving tree," where families in need listed a need and parishioners fulfilled it. I have also volunteered with Lasagna Love, which matches volunteers with nearby families going through hard times. But need doesn't only happen at Christmas. A single mom facing eviction, a family whose child is in chemo, or a parent who needs an interview outfit could use help any time of year. Donors can't easily find people in their area to help, and families face long forms and a lack of privacy. Wishing Tree launches in New Haven, CT, and is designed to expand to other cities later.
>
> The three roles:
> a.) Family: signs up, chats with the Intake agent, approves their drafted wishes, and confirms a delivery window.
> b.) Donor: signs up with zip, budget, categories they like to help with, and whether they prefer specific items, flexible ones, or either. They browse the wish wall or get matched, then grant a wish and choose a weekly drop-off.
> c.) Coordinator: works for Wishing Tree (initially just me). Sees a weekly run sheet of expected drop-offs and deliveries, with contact details and statuses.
>
> Wishes: a single need is a "request" in the code and a "wish" in the interface. Each wish is either:
> a.) Specific: an exact item with product link, brand, size, color, and an "open to a similar substitute" option.
> b.) Flexible: a described need with only the essentials (e.g. size) and an optional budget range.
> Categories: rent/utilities, essentials (hygiene, diapers), clothing, school supplies, gifts, food, other. Occasions: holiday, birthday, back-to-school, job interview, emergency, everyday.
>
> Logistics: Donors drop items at the region's hub, which for New Haven is Yale School of Management, during a weekly 3-hour drop-off window. The coordinator delivers to families during a weekly 3-hour delivery window. Rent and utility wishes are paid directly to the landlord or provider, never as cash to the family. Payments are simulated in the MVP. Regions, hubs and windows are stored as configuration so new cities can be added without code changes.
>
> The three AI agents:
> a.) Intake agent: chats with a family in English and drafts structured wishes. It asks only the follow-up questions that matter (sizes for clothing; a brand only if the family has one in mind). The family must approve every wish before it is submitted. The Intake agent never asks for or receives home addresses or phone numbers; those are collected in a plain form and never sent to the model.
> b.) Privacy & Safety agent: reviews every wish before it goes public. It removes personal details (names, children's names, schools, employers, medical specifics), keeps location to town or zip, enforces policy (no cash between people), checks product links against a retailer allowlist, and flags scams or prompt injection. Agents never visit product links.
> c.) Matchmaker agent: takes a donor's preferences and returns ranked wishes with a one-line reason for each, putting time-sensitive wishes first and saying which weekly drop-off they must make to arrive before the deadline. It must be fair: urgency and how long a wish has waited count; how emotionally a story is written does not.
>
> The stack: a React + Vite TypeScript frontend and a Python FastAPI backend whose agents are built with PydanticAI. Use SQLite for storage. Commit the built frontend and have FastAPI serve it, so the teaching staff only need Python to run the app. There are no passwords in the MVP: a landing page offers demo roles ("I need help," "I want to give," "Coordinator," and a seeded-family option for demos).
>
> The data: there is no real data. You will generate synthetic seed data. Never use real people's details.
>
> Model instructions: use PORTKEY_API_KEY with gpt-6-luna only. The app must look for the .env file first in the repo's own folder, then in the folder one level above it, because the teaching staff keep their .env one level up. Never commit a real .env.
>
> Conventions from my homeworks:
> a.) AI_prompts.md (underscore) is the prompt log; one section per problem.
> b.) prompts/ holds the agents' runtime system prompts (intake_agent.md, safety_agent.md, matchmaker_agent.md).
> c.) output/harness.md is a running file we append to every problem: models, agents, tools, safety measures and specs.
> d.) output/audit_trail.json logs every agent call with input, cached input and output token counts. This is the evidence for my tokenomics section.
> e.) screenshots/ collects screenshots as we go, including failures and safety defenses working.
> f.) A per-project .venv, plus requirements.txt, README.md and .env.example.
>
> We are building an MVP only. Do not add features beyond what each problem asks for, even if they seem helpful. Every problem must leave the app in a working, runnable state.
>
> The final deliverables are a GitHub repo, report.html (10–15 pages) and slides.html (reveal.js, 10 slides max), all self-contained with images embedded. The report needs real evidence from the running app, so build with that in mind.
>
> We will work one problem at a time. Do not go ahead at any point. Are you ready to begin?

**Outcome:** Read the full requirements page at the link above and noted the rules that shape
how the app gets built, not just how the report gets written: tokenomics needs real token
counts (estimates earn half credit), safety needs a screenshot or test of a defense actually
working (a description earns half), and the per-row evidence rule caps any report section
missing its evidence at half that row's points. Verified the local setup — `PORTKEY_API_KEY`
is present in the course `.env` one level above this folder (so the staff `.env` fallback path
is testable here), Python 3.14.7, Node v24.20.0 / npm 11.19.0, git 2.39.5, and `gh` 2.101.0
logged in as `kelly-enright`. Flagged two things before building: Tier 3 and the Impact row
both want evidence from a real person trying the app, which has to be gathered during the week
rather than at the end; and the model name is `gpt-6-luna` per this brief and the requirements
page (the course `AGENTS.md` says `gpt5-6-luna`; HW 5 established these resolve to the same
model through Portkey), to be read from `MODEL_NAME` in `.env` so the string lives in one place.

---

## Problem 1 — Vibe Coder Prompts

### Prompt 1

> Problem 1: "Vibe coder prompts"
>
> Create AI_prompts.md in the project root. It should have one section per problem. Each section contains:
> a.) the problem number and title
> b.) at least one prompt I typed, copied verbatim
> c.) if I needed a follow-up prompt, a one-sentence note on what the first prompt was lacking
>
> Whenever I give you an additional prompt for the same problem, ask me why I needed it, and record my answer. Add the kickoff message and this problem's prompt as the first entries. Let me know if I need to clarify anything before beginning.

**Outcome:** Created `AI_prompts.md` in the project root with the structure above, seeded with
the kickoff message and this prompt. The file gets a new section at the end of each problem as
work proceeds. When a problem takes more than one prompt, I will be asked for one sentence on
what the first prompt was lacking, and the answer recorded under
**Why a follow-up was needed**.

---

## Problem 2 — Scaffold, Data Model, and Seed Data

### Prompt 1

> Problem 2: "Scaffold, data model, and seed data"
>
> Before any agents, we need the skeleton every later problem builds on.
>
> a.) Folder structure: backend/ (FastAPI), frontend/ (React + Vite TypeScript), prompts/, output/, data/, tests/, screenshots/, plus README.md, requirements.txt and .env.example (PORTKEY_API_KEY with no value).
> b.) Config loader: look for .env first in the repo folder, then one level above. If PORTKEY_API_KEY is missing in both, stop with a clear error message. Test it by moving the .env up a folder.
> c.) backend/config.py holds every tunable setting in one place: model name, regions, limits, retailer allowlist, token budgets, and price per million tokens (input, cached input, output) for cost calculations. Leave the prices as clearly marked placeholders for me to fill in.
> d.) Put all structured types in backend/models.py as Pydantic models: Region, Family, Request, Donor, Pledge and AgentCallLog.
>    Region: name, zip codes covered, hub name and address, weekly drop-off window (day, start, end), weekly delivery window (day, start, end), active flag. Seed one active region: New Haven, with hub Yale School of Management, 165 Whitney Ave, drop-off Thursday 4–7 PM, delivery Saturday 10 AM–1 PM.
>    Family: alias (e.g. "Family A27"), zip, and contact details (address, phone) that are only ever shown to the coordinator.
>    Request: family alias, category, request_type (specific or flexible), item description, estimated cost or range, deadline, occasion, zip, status (draft, pending_review, open, granted, dropped_off, delivered, missed). Specific requests add product link, brand, size, color, open_to_substitute. Flexible requests add size/preferences (optional) and budget range.
>    Donor: alias, zip, contact details (coordinator only), budget, preferred categories, preference (specific, flexible, either).
>    Pledge: request, donor, drop-off date, delivery date, family confirmed delivery (yes/no), status.
> e.) SQLite at data/wishing_tree.db, created automatically on first run.
> f.) A seed script that creates about 15 synthetic families with 40 requests and 8 donors around New Haven. Cover every category and occasion, roughly half specific and half flexible, with realistic situations (single parent working two jobs, a child in cancer treatment, an upcoming eviction, a parent needing an interview outfit). Everything must be invented. Product links should point to retailers on the allowlist.
> g.) A landing page with the demo-role buttons. Each opens an empty placeholder page for now.
> h.) One command starts everything: FastAPI serves the built frontend. Commit the built frontend so the teaching staff only need Python.
> i.) Start output/harness.md with the stack, model, data model, region configuration and .env lookup.
>
> Do not build any agents yet. Ask any questions you have before starting.

**Outcome:** The skeleton is built and runs end to end with `python run.py`.

- **Folders and files** as listed, plus `run.py` (the one command), `.gitignore`, and `.claude/launch.json`.
- **Config loader** in `backend/config.py`: `./.env` first, then `../.env`, nearest wins. A missing key stops the app before it serves anything and prints both paths. Four tests cover it, including the staff case of a key only in the parent folder — which is how it actually resolves on this machine, since the course `.env` sits one level up.
- **`backend/config.py`** holds the model name, the region list, app limits, a 20-domain retailer allowlist with a strict checker, token budgets, and the three prices — left at `0.00` and clearly marked, with `PRICES_ARE_PLACEHOLDERS` and a test so a placeholder cannot read as a real cost in the report.
- **`backend/models.py`** has all six models plus `Window` and the enums. Validators enforce that a specific wish carries a product link and a flexible one does not, that every wish has a cost or a range, and that zips are five digits. `Family` and `Donor` expose `public_view()`, the only shape allowed to leave the coordinator's screen.
- **SQLite** at `data/wishing_tree.db`, created on first run and seeded if empty.
- **Seed data:** 15 families, 40 wishes, 8 donors, 8 pledges. All 7 categories, all 6 occasions, 19 specific / 21 flexible, statuses spread across the whole life of a wish. Everything invented — made-up street names, 555-01xx phone numbers, and all 19 product links on the allowlist.
- **Landing page** with the three role cards and the seeded-demo-family option, in the blue and green theme, each opening a styled placeholder. The footer reads the live region and windows from `/api/health`.
- **One command:** `python run.py` checks the key, creates and seeds the database, and serves the API plus the committed `frontend/dist` on one port. Reloader off. A busy port gets a clear message instead of a traceback.
- **37 tests pass.** Screenshots of the landing page and a placeholder are in `screenshots/`.

Three judgement calls I made rather than stopping to ask, all easy to change:
the 20 retailers on the allowlist (a config value); four pledged wishes seeded
so the coordinator's run sheet has rows; and `/api/health` as the only endpoint,
since the problem asked for no features yet.

### Prompt 2

> Before we move on, one addition to Problem 2. Update the landing page so it has three entry points: "I need help" (family sign-up), "I want to give" (donor sign-up), and "Coordinator." Signing up creates the family or donor record and remembers them in this browser so they can come back later. Also add a "Continue as…" option on the landing page that lists existing families and donors by alias, clearly labeled as a demo shortcut, so testers can switch into any account without typing. The Coordinator entry requires a simple passcode stored in config.py (use "wishingtree-demo" for now) because those screens will show home addresses and phone numbers. There are no other passwords in the MVP. Keep each page as a placeholder for now, and update harness.md.

**Why a follow-up was needed:** _(waiting on Kelly's one sentence — to be filled in)_

**Outcome:** The landing page now has the three real entry points, and the screens
behind them are still placeholders.

- **Sign-up endpoints.** `POST /api/families` and `POST /api/donors` create the record, assign the next alias (`Family A59`, `Donor D09`), and return the alias and zip only — never the address or phone that was just typed. Both refuse a zip outside a configured region with a message naming where Wishing Tree operates.
- **Remembered in the browser.** `{role, alias, zip}` goes into `localStorage`. The landing page shows a "This browser is signed in as Family A04" strip with Continue and Sign out; a full reload keeps it.
- **"Continue as…"** lists all 15 families and 8 donors by alias with their zip and a count ("3 wishes", "$75 budget"), labelled *Demo shortcut — not part of the real product*. `GET /api/accounts` returns alias-and-zip shapes only, and a test asserts no seeded address or phone appears in the response.
- **Coordinator passcode** in `config.COORDINATOR_PASSCODE` (`wishingtree-demo`), checked server-side by `POST /api/coordinator/unlock`. A test greps the whole built frontend to prove the passcode never ships to the browser. Unlock is kept in `sessionStorage`, so closing the tab re-locks it.
- **53 tests pass** (16 new). Screenshots of all four screens, plus the passcode refusing a wrong value, are in `screenshots/`.

One judgement call: the coordinator gate uses `sessionStorage` rather than
`localStorage`, so it does not persist the way a family or donor session does.
Those screens show home addresses, so re-entering the passcode in a new tab
seemed right. Easy to change.
