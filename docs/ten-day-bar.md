# 10-day bar after Chetan’s assignment

Chetan asked for four things before the next meet. A strong 10-day sprint finishes those **and** one vertical slice of the actual research question, so the meeting is about results, not setup.

This is the bar. It is not the full project (no 100 GB, no LLM advisor bake-off).

## What Chetan actually assigned

1. Engine: SQL Server Enterprise Developer (we substituted PostgreSQL).
2. Client: SSMS (we substituted `psql` / any GUI).
3. Sampling methods: literature review.
4. macOS + run a basic TPC-DS workload and **record runtimes**.

Everything else in the proposal (samples at 1/5/10%, index agreement, LLM advisor) is the **project**, not the 10-day ask. Doing one tiny slice of it is what “out of the way” means.

## Must have done (minimum to be meeting-ready)

If any of these is missing, the first 20 minutes of the meet is still “are you set up?”

| # | Deliverable | Why Chetan asked | Done? |
| --- | --- | --- | --- |
| M1 | Engine up, you can create a DB and run SQL | Prove you can work at all | Yes (PG 14, `col868`) |
| M2 | Client you can show live (`psql` is enough) | SSMS analogue | Yes |
| M3 | 1-2 pages of **notes** on Wu et al. (not a link list): what-if cost ≠ time; QPR; why brute-force index materialize is expensive | The paper is the motivation | Yes, `docs/wu-notes.md` |
| M4 | Sampling taxonomy in your words: random, stratified, stats-aware, workload-aware, plus **join-consistent** (TPC-DS trap) | He asked for methods + literature | Yes, `docs/sampling-review.md` |
| M5 | TPC-DS loaded; **runtimes written down** for a real query set | He said record runtime | Yes, SF=1, 99 queries, 95/99 under 120s |
| M6 | One slide/paragraph: HypoPG / DTA is **cost**, ground truth is **CREATE INDEX + time** | Stops you looking confused if he asks “did you use the optimizer?” | Yes, `docs/meeting-notes.md` |

**Scale honesty:** He said “basic TPC-DS.” SF=1 with a full query log is a valid 10-day baseline **if you say** SF=10 is the iteration scale and 100 GB is later. Loading SF=10 in those 10 days is the expected stretch, not the floor.

## Out of the way (what one should have added)

These are what separate “I installed the tools” from “I started the project.” None of this is in Chetan’s email. All of it is cheap on SF=1.

| # | Deliverable | Time | Done? |
| --- | --- | --- | --- |
| O1 | PK/FK on the warehouse (or at least PKs on dims + fact date/item keys) | 0.5 day | Yes, PKs + date/customer indexes on `tpcds_sf1` |
| O2 | SF=10 loaded, 10-15 queries timed (not all 99) | 1 day + disk | Yes, 27 GB, 10 queries, Q23 = 188 s |
| O3 | Written 1-pager for Chetan: setup, numbers, next experiment, risks (16 GB RAM, timeouts Q4/11/14/35) | 2 hours | Yes, `docs/meeting-notes.md` |
| O4 | **One closed loop on one query:** 3 candidate indexes, materialize each, record cost vs time, pick a winner | 0.5-1 day | Done, then **retracted**: the `dd_year_week` win was a harness artefact (see `docs/meeting-notes.md`). Loop mechanics are valid, Q72 is index-insensitive. |
| O5 | **One 1% join-consistent sample** of that query’s fact table; same 3 indexes; did the winner match? | 0.5-1 day | Done, then **retracted**: the apparent mismatch was a harness artefact (see `docs/meeting-notes.md`, corrected Q72 section). Q72 turned out index-insensitive. |
| O6 | Wu + join synopses + STRAT read enough to defend sampler choice | 1 day | Yes, notes + review |
| O7 | Repeatable scripts (we have these) | n/a | Yes |

O4 + O5 is the only thing that proves you understood the proposal. Without it you only have an infrastructure demo.

## Ideal 10-day calendar (if starting from zero)

| Days | Work | Output you can show |
| --- | --- | --- |
| 1-2 | Engine, client, TPC-DS SF=1 load, 5 queries timed | Live demo |
| 3 | Wu notes + sampling 1-pager | Talk track |
| 4-5 | PKs; SF=10 **or** commit to SF=1 for the first loop and say why | Scale decision |
| 6-7 | 99-query no-index baseline (or 20-query subset on SF=10) | Runtime table |
| 8-9 | One query, 3 indexes, full vs 1% sample | Agreement yes/no |
| 10 | Chetan 1-pager + “here is what I will do next week” | Meeting |

Do **not** spend the 10 days on: LLM advisor, all four samplers, all 99 × many indexes, SQL Server VM, 100 GB.

## Where you actually are (~10 days in)

**Ahead of the email:** scripted PG env, HypoPG, Postgres-dialect 99 queries, SF=1 full baseline with logs.

**On the email:** engine, client, some literature pointers, TPC-DS runtimes.

**Behind a strong 10-day:** meeting notes on Wu, presentable sampling review, PKs, SF=10, any index experiment, any sample, a 1-pager.

## Streamlined next (do this, in order, then stop)

1. Write `docs/meeting-notes.md`: Wu in 8 bullets; four samplers + join trap; HypoPG ≠ runtime; SF=1 numbers; timeouts; ask Chetan to lock PG + SF=10.
2. Add PKs to `tpcds_sf1` and re-time 10 queries (show indexes change the baseline).
3. Pick **one** mid-cost query (not Q1, not a 120s timeout): e.g. Q10 / Q23 / Q72.
4. Three real indexes (HypoPG to propose, `CREATE INDEX` to measure). Table: cost rank vs time rank.
5. 1% join-consistent sample; same three indexes; one sentence: winner match or not.
6. Only then load SF=10.

That is a complete story for the next meet. Everything else waits.
