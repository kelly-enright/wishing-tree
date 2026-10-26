# Tokenomics — Wishing Tree

Measured against **gpt-6-luna** on 2026-10-26. Every number
here comes from a real run; nothing is estimated except where it says so.

Raw per-run records: `output/tokenomics_runs.json`.
Full call trail: `output/audit_trail.json` (benchmark sessions are prefixed
`measure-`).

## Prices

USD per million tokens, from the Lecture 11 slides (OpenAI Standard, short
context):

| Bucket | Price |
|---|---|
| input | $0.100 |
| cached input | $0.010 |
| cache write | $0.125 |
| output | $0.500 |

**Billing convention.** The API's input figure includes the cached and
cache-write parts, so uncached input = input − cached − cache write. Each
bucket is priced once. Output is **5× fresh input and 50× cached input**,
which turns out to decide most of what follows.

## How this was measured

- Ten intakes, a mix of four that name an exact item with a product link and
  six that describe a need. Each runs the opening message and, if the agent
  asks something, one follow-up — which is what a real intake looks like.
- Ten safety reviews over real open wishes.
- Ten matchmaker runs across five donors.
- Its own database (`data/measure.db`) and a raised daily cap for the burst,
  so benchmarking never spends the operational budget. The app's own cap is
  unchanged.

## Cost per run, by agent

| Agent | Runs | Calls/run | Input | Cached | Cache write | Output | Latency | $/call | $/run |
|---|---|---|---|---|---|---|---|---|---|
| Intake | 10 | 2.0 | 246 | 5,764 | 2,212 | 416 | 7.1 s | $0.000567 | $0.001134 |
| Privacy & Safety | 10 | 1.0 | 277 | 5,878 | 465 | 494 | 8.8 s | $0.000391 | $0.000391 |
| Matchmaker | 10 | 1.0 | 378 | 5,870 | 1,740 | 499 | 6.1 s | $0.000563 | $0.000563 |

Cached input is the largest bucket in every row, which is the explicit
prompt-cache breakpoint doing its job.

## Cost per journey

**A family journey** — one intake, then a safety review for each wish it
produced (0.8 wishes per intake, measured):

| Part | Cost |
|---|---|
| Intake (2.0 calls) | $0.001134 |
| Safety reviews (× 0.8) | $0.000313 |
| **Whole family journey** | **$0.001447** |

**A donor journey** — one matchmaker run. Browsing the wall, filtering and
granting are all plain database work and cost nothing.

| Part | Cost |
|---|---|
| **Whole donor journey** | **$0.000563** |

Roughly: **691 family journeys to the dollar**, and
**1,775 donor journeys to the dollar**.

## Monthly cost at scale

Stated assumptions, so they can be argued with:

- one family for every two donors (33% of users are families)
- a family posts wishes 1× a month
- a donor asks to be matched 2× a month
- the coordinator's screens, the wish wall, granting and delivery use no model
  calls at all

| Users | Families | Donors | Family cost | Donor cost | **Monthly total** |
|---|---|---|---|---|---|
| 100 | 33 | 67 | $0.05 | $0.08 | **$0.12** |
| 10,000 | 3,333 | 6,667 | $4.82 | $7.51 | **$12.33** |

At ten thousand users the model bill is **$12 a month** —
less than one volunteer coordinator's phone plan. The binding constraint on
this project is the coordinator's Saturday, not the token budget.

## Experiment C — does the matchmaker need more candidates?

The search tool hands the model at most `MATCHMAKER_CANDIDATE_LIMIT`
candidates. Run at 15 and with no limit, on the same five donors:

| Donor | Input @15 | Cost @15 | Input @all | Cost @all | Top five | Order |
|---|---|---|---|---|---|---|
| Granter D01 | 9,007 | $0.000693 | 8,975 | $0.000663 | same five | same order |
| Granter D02 | 7,015 | $0.000357 | 7,045 | $0.000381 | same five | same order |
| Granter D03 | 7,562 | $0.000488 | 7,570 | $0.000492 | same five | same order |
| Granter D04 | 9,301 | $0.000945 | 9,297 | $0.000914 | same five | same order |
| Granter D05 | 7,065 | $0.000314 | 7,048 | $0.000349 | same five | same order |

Average cost: **$0.000559** at 15, **$0.000560** with no limit
(+0%).

5 of 5 donors got the **same five wishes** either way.

**Keeping the limit at 15.** The wall is small
enough today that removing the limit changes little, but the cost grows with
the size of the wall while the answer does not: the matchmaker returns five
wishes however many it is shown, and the ones it picks are the most urgent,
which the database already sorts to the front. The limit is the setting that
stops a busy wall quietly becoming an expensive prompt.

## Experiment D — does capping output save money?

Output is the dearest bucket, so a cap per reply is the most direct lever.
Three arms, because the first tighter cap turned out not to be tight at all.

| | Default (1600) | 700 | 300 |
|---|---|---|---|
| Output tokens per call | 416 | 396 | 389 |
| Cost per intake | $0.001134 | $0.000710 | $0.000713 |
| Turns per intake | 2.0 | 2.0 | 2.0 |
| Wishes drafted | 0.8 | 0.5 | 0.7 |
| Wishes with a cost | 0.8 | 0.5 | 0.7 |
| **Intakes that failed outright** | **0 of 10** | **0 of 10** | **4 of 10** |

**A cap of 700 does nothing.** Mean output is about
416 tokens a call, so 700 never binds; the cost
difference between those two arms is run-to-run variance, not a saving. This is
worth saying plainly because it is the easy mistake: setting a cap, seeing a
lower bill in one sample, and concluding the cap caused it.

**A cap of 300 binds, and breaks things.** 4 of
10 intakes (40%) failed outright with *"Model token
limit (300) exceeded before any response was generated"* — the
structured reply could not be produced at all. The 6 that did
finish averaged $0.000713, a saving of $0.000421
(37%) per intake.

**Keeping 1600.** A saving of 37% of a tenth of a cent is worth
nothing against a 40% chance that a family who has just typed
out what their children need gets an error instead of a wish. And the saving is
overstated anyway: the failed runs are not free — the tokens were spent before
the limit was hit — they are just wasted.

The real lever on output is not the cap. It is the prompt: telling the intake
agent to ask only the follow-ups that change what a donor would buy is what
keeps replies short, and it does that without ever truncating one.

## What actually drives the bill

1. **Output tokens.** At $0.50/M they are 5× fresh input and
   50× cached. The single biggest lever is asking agents for less prose, not
   feeding them less context.
2. **Turn count.** A second intake turn roughly doubles that intake's cost.
   The follow-up rules in the intake prompt — ask only what changes what a
   donor would buy — are a cost control as much as a kindness.
3. **Cache hits.** The explicit breakpoint keeps the system prompt out of the
   fresh-input bucket on every call after the first.

Things that cost nothing and were deliberately kept that way: the wish wall,
filtering, granting, the whole delivery flow, the coordinator's run sheet, and
the intake greeting, which is a fixed string rather than a model call.
