# Notes for Chetan (COL868, 2026-09-29)

**Ask:** lock **PostgreSQL** and **TPC-DS SF=10** as the iteration stack. 100 GB / SQL Server after the loop is stable. Machine is a 16 GB Mac; SF=10 is the largest we can iterate on locally.

## Wu et al. (8 bullets)

Full write-up: `docs/wu-notes.md`. Short: index tuners rank with **what-if cost**; that cost misses real **QPR** (often expensive NLJ). Azure reverted ~11% of auto-indexes. Brute-force materialize is accurate and too expensive, that is why we sample. **HypoPG / DTA = cost. Ground truth = CREATE INDEX + time.**

## Sampling (what I will implement)

`docs/sampling-review.md`. Random / stratified / stats-aware / workload-aware (STRAT). **Must be join-consistent** on TPC-DS: sample the fact, keep dims (join synopses / Aqua). Independent 1% of two tables destroys the join.

## Setup

- Postgres 14.20, DuckDB dsdgen, HypoPG, `pg_stat_statements`, `shared_buffers=2GB`.
- Client: `psql`. Scripts in the repo.

## SF=1 no-index baseline (heap only, 2026-09-21)

99 queries, 120s cap: **95 ok**, timeouts **Q4, Q11, Q14, Q35**. Median **364 ms**. Q1 took 115 s.

## After PKs + date/customer FK indexes (2026-09-29)

Same 10 queries much faster (PKs change the baseline, we will always report “PK baseline” separately):

| Q | Heap-only exec | After PK exec |
| --- | ---: | ---: |
| 3 | 1197 ms | 46 ms |
| 10 | 5086 ms | 190 ms |
| 23 | 3884 ms | 2161 ms |
| 72 | 2391 ms | 459 ms (later ~146 ms warm) |

## Closed loop: Q72 (CORRECTED 2026-09-29; earlier version of this section was wrong)

**Retraction.** The first version of this section reported that Q72's full-DB winner was `dd_year_week` (3.2 s vs 10-18 s) and that no 1% sample reproduced it. That result was a **harness artefact**, not an index effect. Three confounders, all found on 2026-09-29:

1. **Autovacuum** was running a VACUUM on `tpcds_sf10.inventory` (133 M rows) for 30+ minutes, stealing IO/cache. Same plan, same stats: 10 s while it ran, 2.3 s when it did not.
2. **Uneven ANALYZE:** the loop ran `ANALYZE` after creating each index but not for `none`, and the fact tables had never been analyzed (autovacuum never reached them). `ANALYZE` also cancels a running autovacuum, so "indexed" candidates looked faster.
3. **Single cold runs.** No warm-up, no repeats. Cold vs warm for Q72 at SF=10 differs about 9x (21 s first pass vs 2.3 s warm).

**Corrected protocol** (in `scripts/run_index_loop.py`, `config/postgresql-tpcds.conf`): autovacuum off; `ANALYZE` once, then statistics frozen and fingerprinted (md5 of `pg_stats`); 1 warm-up + N timed runs, median; same statistics for `none` and every candidate.

**Corrected Q72 result** (median ms; min-max in `results/frozen_*_q72.jsonl`):

| DB | none | cs_sold_ship_item | inv_item_date_wh | dd_year_week | Reading |
| --- | ---: | ---: | ---: | ---: | --- |
| **SF=10 full (truth)** | **2281** | 2591 | 2367 | 2883 | No index helps; `none` is best. Q72 is **index-insensitive** |
| SF=1 (native 10 % scale-down) | 127.8 | 128.1 | 128.2 | 123.8 | flat (same conclusion) |
| Universe sample 5 % (`tpcds_sf10_u5`) | 116.9 | 116.0 | 116.3 | 111.0 | flat |
| Universe sample 1 % (`tpcds_sf10_u1`) | 41.5 | 41.9 | **305.7** | 41.4 | flat, except `inv_item_date_wh` shows a 7x regression (truth: +4 %): a false alarm |

What this means: **Q72 is a bad study query** (nothing to rank). The samples get the "nothing helps" conclusion right, but the 1 % sample invents a large regression for the `inventory` index. The optimizer *cost* still favours `dd_year_week` on every DB (4370 vs 7532 at 1 %), yet time is flat: cost and time disagree, as Wu et al. describe.
The valid takeaways from the whole detour are **methodological** and go straight into `docs/pipeline.md`: (a) statistics and cache state must be controlled, (b) query selection must screen out index-insensitive queries, (c) a false alarm on a sample (fan-out at 1 %) is a distinct failure mode worth measuring.

SF=10 single-pass baselines are cold and noisy (10 queries, clean env, `results/baseline_tpcds_sf10_clean/`): Q3 2.3 s, Q7 9.3 s, Q10 34 s, Q12 0.4 s, Q19 10.7 s, Q23 247 s, Q42 6.4 s, Q52 5.2 s, Q72 21.5 s, Q96 5.0 s. Use them only as "first-touch" times.

## Risks

- 16 GB RAM; SF=10 needs ~20 GB disk peak (CSV + heap).
- Q4/11/14/35 need a higher timeout or indexes before they finish.
- Sample inventory is still large if 1% sales touches many items, next: tighter join synopses / date-restricted inventory.

## Next week (if we lock PG + SF=10)

1. Phase B screening (`docs/pipeline.md`): find queries where an index really changes runtime.
2. Ground truth on the screened set; then B0 (SQL:Trek recipe) vs universe (C2) samples; agreement, regret, tau.
3. Read `docs/related-work.md` and `docs/sampling-taxonomy.md` (SQL:Trek is the closest prior work).
4. LLM advisor only as a **candidate source**, after the harness is boring.
