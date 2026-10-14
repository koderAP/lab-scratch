# Moving this project to a bigger server

Read this file first on the new machine. The Cursor chat that produced it will not be there.

Repo: `https://github.com/koderAP/lab-scratch.git` (branch `main`).
Course: COL868. Assigned write-up: `problem_statement.md` (SQL Server, 100 GB). What we actually run: PostgreSQL 14, TPC-DS, measured execution time, samples vs a full-database ranking.

## 1. What the project is asking

Optimizer cost is a bad ranking of indexes (Wu et al., SIGMOD 2025). Timing every candidate on the full database is too expensive. The protocol (`docs/protocol.md`) asks: **does a reduced database D' rank whole index configurations the same way the full database D does**, by measured time of all 99 TPC-DS queries?

A configuration is a set of indexes, not one index per query. Score A is the sum of the 99 query times. Score B is index-build time plus A. Metrics: Kendall tau-b, top-1, regret, evaluation-cost reduction.

A later idea, **database distillation**, is: do not hope a random sample keeps the things the ranking depends on. Build a small D* on purpose so that I/O, plans, and benefit signs match D. Write-up: `docs/distillation-plan.md`.

## 2. What the laptop already finished (do not redo)

Machine: macOS arm64, 16 GB RAM, PostgreSQL 14.20, database `col868`, `shared_buffers=2GB`, autovacuum off.

**Protocol, SF=1, 33 configurations, 99 queries, 20 s cap, 5% samples.** Numbers in `docs/results.md` and `results/rank_sf1_p5.md`. The jsonl files are in git.

| | |
|---|---|
| No extra index | 190.7 s |
| Best | Grok small dimension filters, 172.9 s |
| Spread best to worst | 17.7 s |
| Always-capped queries | Q1 Q4 Q11 Q74 Q81 Q95 (120 s of every total) |
| Queries that actually move | 25. Most of the 17.7 s win is Q6 (10 s) and Q14 (3.3 s). |
| Full DB vs itself next morning | tau 0.45, same winner, totals shifted by 5.3 s |
| Bernoulli 5% | tau 0.51, regret 1.014, 43x cheaper, picks second place |
| Page 5% | tau 0.46, 90x cheaper |
| Universe / FK / stratified | tau 0.28 to 0.45, only ~3x cheaper (they keep dimensions whole) |
| Copying full statistics onto the sample | made both rankings worse |

Advisors: isolated agents, schema and query text only, no data. Gemini's first run read result files and was thrown out (`results/advisors_excluded/`). 33 configs in `results/configs_sf1.json`.

**HypoPG EXPLAIN on those same schemas** (`scripts/explain_configs.py`): samples recover the full-DB *cost* ranking at tau 0.81 to 0.91. Full-DB cost ranking vs *time* ranking is tau 0.43 and picks a 188 s loser. Plan-shape agreement is 8 to 12%. So matching plans or costs is the wrong distillation target on this SF=1 set.

**SF=10 screen** (old per-query harness, one HypoPG index per query, warm): 23 queries move by at least 1.3x. Effects are large (Q27 176x, Q21 32x, Q23 12x) and about half are regressions. Report: `docs/sf10-screen-report.md`. Study set: `results/study_set_sf10.json`. That screen is not the protocol (not whole configurations, not 99 queries).

**Do not ANALYZE a schema after its stats are frozen.** On the laptop `tpcds_sf1` fingerprint was `91bd9a3118e7556f`. A fresh load on the server will have a new fingerprint. That is expected. Freeze it after PKs and do not ANALYZE again.

## 3. What we concluded, and why you are on a bigger machine

SF=1 cannot carry a sampler or distillation claim. The ranking is 2.4 s wide (Grok vs Opus), overnight drift is 5.3 s, and 31 of 33 configs are near-ties. A method that "wins" there can be fitting jitter.

Larger data is the right test because the *target* has signal: tens of seconds to minutes, page-read drops of 400k to 3M, and real regressions. A 5% sample of that larger database does **not** automatically inherit the signal:

| Copy | Size | Fits in 16 GB laptop? |
|---|---|---|
| SF=1 full | 3.6 GB | yes (cache-resident, Q22 is cache noise) |
| SF=10 full | 35 GB, inventory 12 GB | no |
| SF=10 universe 5% | 1.5 GB | yes, same regime as SF=1 |

On a server with a lot of RAM, **SF=10 will fit in memory too**. Then you are back to the SF=1 problem. Pick the scale so the heap is larger than RAM (SF=100 on a 64 GB box, larger still on 128 GB), or you are not testing I/O-regime index selection.

Distillation at that scale means: keep the I/O (or scale `shared_buffers` / `effective_cache_size` / scan thresholds with the sample rate), keep both speedups and regressions, keep predicate rows. Details in `docs/distillation-plan.md` sections 6 and 7.

Stay on **PostgreSQL 14** if you can. PG 15/16 change the planner. Do not mix those timings with the laptop SF=1 numbers as if they were the same engine. The original proposal is SQL Server at 100 GB. We did not switch stacks. Do not switch on the server unless that is a deliberate new decision.

## 4. What git has, and what it does not

In git: scripts, configs, advisor json, protocol jsonl (truth, dprime, explain), SF=10 screen jsonl, docs, the 99 query files.

Not in git, and not portable as files: **Postgres heaps**. Load them on the server with `scripts/load_tpcds.sh`. CSV under `data/` is gitignored. After a successful load you can delete the CSV directory.

The laptop also had leftover schemas (`tpcds_sf1_b0_p5` still holding transplanted column stats, `tpcds_sf10_u5`, and so on). Do not try to dump/restore those. Load clean.

Retracted Q72 loops, early baselines, and the old per-query SF=1 jsonl were deleted from the tree. The lessons are in `docs/lab-notes.md`. The protocol files remain.

## 5. Hard rules (from the Q72 retraction)

1. `autovacuum = off`. Confirm with `SHOW autovacuum`.
2. `ANALYZE` once after load and primary keys, then never again on that schema.
3. One discarded warm-up per query. Then two timed runs if the warm-up was ≤2 s, else one. Median.
4. One configuration at a time: `CREATE INDEX` all of them, run the queries, `DROP`. `eval_configs.py` only auto-drops names matching `ix_c%`. New experimental indexes must use that prefix.
5. A timeout counts as the cap, on D and on D' alike. It does not cancel a query stuck inside a disk read. At SF=10 that burned hours. Use a cap you can live with, and prefer `statement_timeout`.
6. Leftover `ix_c%` indexes from a killed run will leak into the next config. `eval_configs.py` drops them at start. If you kill it hard, drop them by hand.

## 6. Setup on the server

Need: PostgreSQL 14, DuckDB (with the `tpcds` extension), HypoPG, Python 3, `psql` on PATH, disk about 3× the heap (CSV export + heap + indexes).

```bash
git clone https://github.com/koderAP/lab-scratch.git
cd lab-scratch

# record the machine
free -h
df -h .
psql --version
```

Edit `config/postgresql-server.conf` so `shared_buffers` is ~25% of RAM and `effective_cache_size` ~75%. Then:

```bash
export COL868_PG_CONF="$PWD/config/postgresql-server.conf"
# if autodetection misses the cluster:
# export PG_CONF=/etc/postgresql/14/main/postgresql.conf
./scripts/setup_env.sh
```

On systemd you will have to `sudo systemctl restart postgresql` (unit name varies) yourself, then rerun the script so the extensions install.

Check:

```
SHOW shared_buffers;
SHOW autovacuum;                 -- must be off
SHOW effective_io_concurrency;   -- should be >0 on Linux
SELECT extname FROM pg_extension; -- hypopg, pg_stat_statements, tsm_system_rows
```

HypoPG package names vary (`postgresql-14-hypopg` on Debian, or build from source). Without it, `gen_candidates.py` and `explain_configs.py` die; `eval_configs.py` still runs because it builds real indexes.

Pick SF so heap > RAM. Rough heaps we have seen: SF=1 ~3.6 GB, SF=10 ~35 GB. SF=100 is on the order of 100 GB plus indexes.

```bash
./scripts/load_tpcds.sh 10          # or 100
./scripts/apply_pks.sh tpcds_sf10   # ANALYZE happens here. Do not ANALYZE again.
# optional, reclaim CSV:
# rm -rf data/tpcds_sf10
```

Fingerprint after PKs (store this in the run log):

```sql
SELECT md5(string_agg(tablename||attname||coalesce(most_common_vals::text,'')
  ||coalesce(histogram_bounds::text,'')||n_distinct::text, ','
  ORDER BY tablename, attname))
FROM pg_stats WHERE schemaname = 'tpcds_sf10';
```

## 7. First experiment on the server (do this before 33×99)

The 23-query SF=10 study set, no extra index vs that query's screen index. Configs are `results/configs_sf10_study.json` (index names are `ix_c<q>_0` so the harness will drop them).

```bash
# full database, 30 minute cap
./scripts/run_sf10_study.sh tpcds_sf10 results/truth_sf10_study.jsonl 1800000

# 5% samples of the same full schema
python3 scripts/make_sample.py --src tpcds_sf10 --dst tpcds_sf10_b0_p5 --sampler b0 --pct 5
python3 scripts/make_sample.py --src tpcds_sf10 --dst tpcds_sf10_uitem_p5 --sampler uitem --pct 5
./scripts/run_sf10_study.sh tpcds_sf10_b0_p5 results/dprime_sf10_b0_p5_study.jsonl 1800000
./scripts/run_sf10_study.sh tpcds_sf10_uitem_p5 results/dprime_sf10_uitem_p5_study.jsonl 1800000
```

What "better at large scale" looks like, per query:

- Sign of (index time minus no-index time) matches the full database, including regressions (Q25, Q29, ...).
- Speedups still show a large drop in `shared_read`. If both sides read 0, the copy has gone cache-resident and you picked too small an SF or too much RAM.
- Then rerun the 5% sample with session knobs scaled by 0.05 (`shared_buffers` cannot change per session; `work_mem`, `effective_cache_size`, `min_parallel_table_scan_size`, `min_parallel_index_scan_size` can). If sign and read-drop jump, distillation is mostly environment scaling.

Do not trust a cold first pass. The laptop cold SF=10 screen turned Q21 from 21 minutes into a cache artifact of 0.5 s.

## 8. After that: the actual protocol at large SF

Same 33 configurations (`results/configs_sf1.json`). Same measurement. Raise the cap (20 s is wrong here; Q6 did not finish in 5 minutes at SF=10). Two full rankings for the noise ceiling, then Bernoulli 5% and universe 5%, then one more seed.

```bash
python3 scripts/eval_configs.py --schema tpcds_sf10 --configs results/configs_sf1.json \
  --out results/truth_sf10.jsonl --queries 1-99 --cap-ms 1800000
python3 scripts/progress_configs.py results/truth_sf10.jsonl
```

The run is resumable. `caffeinate` is a Mac command; on Linux use `tmux` or `systemd-run` so SSH drop does not kill it.

If 99 × 33 at this cap will not finish in the time you have, keep the 23-query study set as the workload and still rank the 33 configs on those 23 queries. Say so in the notes. Do not silently drop queries.

## 9. Commands cheat sheet

```bash
# environment
export COL868_DB=col868            # default
export COL868_PG_CONF=$PWD/config/postgresql-server.conf

# load
./scripts/load_tpcds.sh 10
./scripts/apply_pks.sh tpcds_sf10

# sample
python3 scripts/make_sample.py --src tpcds_sf10 --dst tpcds_sf10_b0_p5 --sampler b0 --pct 5 --seed 42
# samplers: b0 (Bernoulli), sys (page), uitem (universe on item), fk, strat

# statistics transplant (do not ANALYZE after)
python3 scripts/transplant_stats.py --src tpcds_sf10 --dst tpcds_sf10_b0_p5

# measure
python3 scripts/eval_configs.py --schema SCHEMA --configs results/configs_sf1.json \
  --out results/OUT.jsonl --queries 1-99 --cap-ms 1800000

# rank
python3 scripts/rank_metrics.py --truth results/truth_sf10.jsonl \
  --sample results/dprime_....jsonl --md results/rank_sf10.md

# cheap proxies (no builds, no timing)
python3 scripts/explain_configs.py --schema SCHEMA --out results/explain_SCHEMA.jsonl
python3 scripts/compare_explain.py --truth-explain results/explain_tpcds_sf10.jsonl \
  --sample-explain results/explain_tpcds_sf10_b0_p5.jsonl --md results/distill_explain_sf10.md
python3 scripts/distill_proxies.py --truth results/truth_sf10.jsonl --md results/distill_proxies_sf10.md
```

Drop leaked experimental indexes:

```sql
SELECT schemaname, indexname FROM pg_indexes WHERE indexname LIKE 'ix\_c%';
-- then DROP INDEX schema.ix_c... ;
```

## 10. Where to read more

| File | Why |
|---|---|
| `docs/protocol.md` | The experiment as specified, and the laptop choices. |
| `docs/results.md` | SF=1 numbers. |
| `docs/distillation-plan.md` | Why SF=1 overfits, what larger D must preserve, related-work gap. |
| `docs/lab-notes.md` | Why autovacuum, warm-up, and frozen stats exist (Q72 retraction). |
| `docs/sf10-screen-report.md` | Warm SF=10 per-query screen. |
| `docs/files.md` | What each remaining file is. |
| `advisors/prompt.md` | What the LLMs were allowed to see. |
| `review.pdf` | Short reviewer note of the SF=1 run. |

If a new chat starts on the server, point it at this file and `docs/distillation-plan.md`.
