# Exhaustive sampling taxonomy (what we must consider)

Purpose: every way of building a "small database" from a big one that is plausible for **execution-based index evaluation**, so no reviewer can say "you missed X".

Notation: **PG** = how to build it on PostgreSQL 14. **Tier**: `B` baseline we must beat, `C` core (implemented and evaluated), `S` stretch (implement if time), `X` out of scope (cite and explain why).

## Axes (a sampler is one choice on each axis)

| Axis | Options |
|---|---|
| **A. Unit** | row · page/block · key group (all rows of a join-key value) · row cluster (e.g., one order = header + lines) · time window / partition |
| **B. Inclusion probability** | uniform · stratified (equal / proportional / Neyman) · weighted (by size, by measure) · hash-threshold (deterministic) · reservoir (fixed size) · top-k/recent |
| **C. Multi-table coherence** | independent per table · FK-closure (sample root fact, pull referenced dims/children) · join synopsis · universe (same hash on the join key in all tables) · correlated · two-level · dimensions-in-full |
| **D. Workload awareness** | none · predicate witness (keep rows the queries touch) · query column sets (QCS/BlinkDB) · STRAT-style workload strata · index-candidate aware (keep rows the candidate index would seek) |
| **E. Size control** | fixed % · % with row floor/cap (SQL:Trek) · fixed bytes · adaptive until stable (pilot) |
| **F. Statistics treatment** | native `ANALYZE` on sample · full-DB statistics transplanted into sample · full-DB statistics scaled to sample cardinality · extended statistics preserved |
| **G. Data source** | true subset of real rows · synthetic scale-down (learned from data) |

## Catalogue

| ID | Sampler | Axes | Origin | PG implementation | Tier |
|---|---|---|---|---|---|
| **B0** | **Independent uniform Bernoulli per table, p = 5 %, floor 20 K / cap 1 M rows** | A row, B uniform, C independent, E floor/cap, F native | **SQL:Trek** (PVLDB 2025) | `TABLESAMPLE BERNOULLI` + `LIMIT`/floor logic | **B (headline baseline)** |
| B1 | Independent page sampling | A page, B uniform | SQL std | `TABLESAMPLE SYSTEM` | B (cheap, clustered bias) |
| B2 | Independent reservoir / fixed-row sample | B reservoir | Vitter | `tsm_system_rows` | B |
| B3 | **No data: what-if cost only** (HypoPG) | none | AutoAdmin/DTA | HypoPG | B (incumbent) |
| B4 | Full clone | none | AIM, Azure B-instance | full DB | ground truth, not a sampler |
| **C1** | **FK-closure / join synopsis**: sample the driving fact table, keep all referenced dimension rows, pull matching child-fact rows | A row-cluster, C FK-closure | Acharya et al. SIGMOD 1999 (Join Synopses, Aqua) | `JOIN` on sampled keys; `make_sample.py --sampler fk` | C |
| **C2** | **Universe (hash-on-join-key) sampling**: keep row iff `hash(key) mod M < t` in *every* table that joins on that key; dims full | A key group, B hash, C universe | Kandula et al. Quickr 2016; Huang et al. "Joins on Samples" PVLDB 2020; correlated sampling (Vengerov 2015) | `hashint8extended(key,seed)` filter, `make_sample.py --sampler uitem` | **C (primary)** |
| **C3** | **Stratified** on skew/selectivity columns (date, high-frequency item, MCV values) with row floor per stratum | B stratified | Chaudhuri et al. STRAT TODS 2007; congressional (Acharya 2000) | `row_number() OVER (PARTITION BY stratum ORDER BY random())` | C |
| **C4** | **Statistics-aware**: build any of the above, then **inject full-DB `pg_statistic`** (or scaled `reltuples`, `n_distinct`, MCV/histogram) so the planner sees production statistics | F transplant | CODD (Haritsa), SQL Server `STATS_STREAM`, PG18 stats import, SQL:Trek future-work #1 | PG14: write `pg_statistic`/`pg_class.reltuples` as superuser; `pg_stats` ANALYZE off for those columns | C (as a factor, crossed with C1-C3, B0) |
| **C5** | **Workload-aware / predicate-witness**: ensure sample contains rows satisfying each workload predicate at min count; keep rows the candidate indexes would seek | D witness/candidate-aware | STRAT, BlinkDB QCS, Babcock 2003 | run per-query predicate `SELECT ... LIMIT k` + union with uniform base | C |
| S1 | Two-level sampling (block then row, join-aware) | A page+row, C join | Chen & Yi SIGMOD 2017 | custom SQL | S |
| S2 | SUBS: stratified + universe + Bernoulli hybrid | B,C | Huang et al. PVLDB 2020 | combine C2 + C3 | S |
| S3 | Neyman / variance-optimal allocation | B stratified-opt | Chaudhuri et al. | compute stratum variance of runtime proxy | S |
| S4 | Time-window subset (most recent N months / partitions) | A window | Industrial practice | `WHERE d_year=...` on fact + dims | S |
| S5 | Bi-level Bernoulli (page rate p, row rate r) | A page+row | Haas & König SIGMOD 2004 | custom | S |
| S6 | Adaptive size: grow sample until winner ranking stabilises | E adaptive | Chaudhuri et al. 1998 (adaptive page sampling) | loop | S (natural for the "how big" study) |
| S7 | Index-based join sampling / Wander Join walks to construct join-result samples | C | Leis et al. CIDR 2017; Li et al. SIGMOD 2016 | needs indexes on full DB; use for stats, not for the eval DB | S/X |
| S8 | Learned / RL sample selection | D learned | RL-STuner 2024; ASQP-RL 2024 | out of PG | S/X |
| S9 | Synthetic downscale (learn dataset then generate s× smaller) | G synthetic | UpSizeR 2013; Dscaler 2016; Touchstone 2018 | external generator | S (as comparison) |
| X1 | Sketches / bound sketch / learned cardinality (no rows) | none | Cai et al. 2019; DeepDB | n/a | X: they estimate cardinality, cannot execute an index |
| X2 | Query-subset "fidelity" (run fewer queries on full data) | orthogonal | MFTune 2026 | n/a | X but **report as alternative proxy** |

## What runs in the evaluation (the experimental grid)

Factors: **sampler** ∈ {B0, B1, C1, **C2**, C3, C5} × **rate** ∈ {0.1 %, 1 %, 5 %, 10 %} × **stats** ∈ {native, full-DB transplant (C4)} × **seed** ∈ {3 seeds at 1 %; 1 seed elsewhere}.
That is 6 × 4 × 2 = 48 sample databases per scale, before seeds. Too many to run in full: run **C2/B0 fully crossed** first, then add the rest one factor at a time (screening design). The run that was actually done is in `docs/protocol.md`.

## Why this list is complete enough

Every sampling design in the literature reviewed in `related-work.md` decomposes into the axes above (unit, probability, multi-table coherence, workload awareness, size control, statistics, real-vs-synthetic). Anything genuinely new must sit on a new axis. The two axes that are least studied for index evaluation, and where we expect novelty, are **C (coherence) under analytical multi-fact joins** and **F (statistics treatment)**.

## PG-specific gotchas

- `TABLESAMPLE SYSTEM` clustering: TPC-DS loaded via `COPY` in generator order, so pages are correlated with `*_sold_date_sk`; page samples will over/under-represent date ranges. Good baseline to show that bias.
- Universe sampling shrinks the *item universe*: a 1 % hash keeps ~1 % of items **and** ~1 % of rows per item's facts, preserving per-item fan-out but not cross-item statistics of a query that filters on other dimensions (e.g., date). Keep dims full.
- Any sample changes `ANALYZE` results (`n_distinct`, histogram bounds, correlation), which changes plans, which is exactly why axis F exists.
- Plan shape can change between sample and full even with identical stats because of cost-model constants and `work_mem` versus size (SQL:Trek saw one such regression). Log the plan hash for both sides and count plan-mismatch as a separate metric.
