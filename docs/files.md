# What each file does

The experiment that answers the spec is `docs/protocol.md`. On a new machine, start at `docs/server.md`. Older per-query scripts (Q72 loop, SF=1 study-set harness) have been removed. Their lessons are in `docs/lab-notes.md`.

## Root

| File | What it is |
|---|---|
| `problem_statement.md` | The project as assigned: LLM candidates, measure cost and time, compare samples to the full database. |
| `README.md` | Short setup. Points at `docs/server.md` for a machine move. |
| `results.html` | One-page figure report of the SF=1 protocol run. |
| `protocol.html` | Step-by-step diagrams of the experiment, including sampler math. |
| `review.html` | Reviewer guide. |
| `review.tex` / `review.pdf` | LaTeX source and PDF of that guide. |
| `reviewer.html` | Shorter first-read briefing. |
| `papers/` | Local copies of related papers (`python3 papers/fetch.py`). PDFs are gitignored. List: `papers/README.md`. |

## Scripts

| File | What it does |
|---|---|
| `scripts/setup_env.sh` | DuckDB + Postgres check, include project conf, create database `col868`, install HypoPG. Set `COL868_PG_CONF` on a Linux server. |
| `scripts/load_tpcds.sh` | Generate TPC-DS with DuckDB and load schema `tpcds_sfN`. |
| `scripts/apply_pks.sh` | Apply `sql/tpcds_pks.sql` and `ANALYZE` once. Do not ANALYZE that schema again. |
| `scripts/pg.py` | Shared helpers. Database is `COL868_DB` or `col868`. |
| `scripts/make_sample.py` | Build a reduced schema. Samplers: `b0`, `sys`, `uitem`, `fk`, `strat`. Appends `results/samples.jsonl`. |
| `scripts/transplant_stats.py` | Copy full-database `pg_statistic` onto a sample (C4). Do not ANALYZE after. |
| `scripts/gen_candidates.py` | Per-query HypoPG shortlist by estimated cost. |
| `scripts/build_configs.py` | Merge advisors + empty + HypoPG top-5/top-8 into `results/configs_sf1.json`. |
| `scripts/eval_configs.py` | The measurement. One configuration at a time. Resumable. Experimental indexes must be named `ix_c%`. |
| `scripts/rank_metrics.py` | Kendall tau, top-1, regret, cost reduction vs the full-database ranking. |
| `scripts/distill_proxies.py` | Plan-hash and benefit-sign agreement from timed jsonl. |
| `scripts/explain_configs.py` | HypoPG `EXPLAIN` of every configuration. No builds. |
| `scripts/compare_explain.py` | Cost ranking and plan-shape agreement from those EXPLAIN files. |
| `scripts/progress_configs.py` | How far an `eval_configs.py` jsonl has got. |
| `scripts/run_dprime.sh` | `eval_configs.py` on the five native SF=1 5% schemas. |
| `scripts/run_sf10_study.sh` | Study-set pairs (no index vs that query's screen index) on one schema. |

## Advisors, workload, config

| File | What it is |
|---|---|
| `advisors/prompt.md` | Instructions given to each model. |
| `advisors/schema_tables.txt` | Table and column list the advisors were allowed to see. |
| `advisors/existing_indexes.txt` | PKs and indexes already on `tpcds_sf1`. |
| `workloads/tpcds/01.sql` to `99.sql` | TPC-DS in PostgreSQL dialect. |
| `config/postgresql-tpcds.conf` | Laptop: `shared_buffers=2GB`, autovacuum off, `effective_io_concurrency=0`. |
| `config/postgresql-server.conf` | Server template. Edit RAM numbers. `effective_io_concurrency=200`. |
| `sql/tpcds_pks.sql` | Primary keys plus a few FK-supporting indexes. |

## Docs

| File | What it is |
|---|---|
| `docs/server.md` | Context and setup for a new machine. Read this first on the server. |
| `docs/protocol.md` | The experiment as specified, plus the laptop choices. |
| `docs/results.md` | SF=1 5% numbers. |
| `docs/distillation-plan.md` | Distillation idea, SF=1 measurements, why larger D, related-work gap. |
| `docs/lab-notes.md` | Why the measurement rules exist (Q72 retraction, cache, cap). |
| `docs/sf10-screen-report.md` | Warm SF=10 per-query screen. Not a protocol result. |
| `docs/related-work.md` | Neighbours. Closest published system is SQL:Trek. |
| `docs/sampling-taxonomy.md` | Sampler catalogue. |
| `docs/literature.md` | Reading list. |
| `docs/wu-notes.md` | Notes on Wu et al. |
| `docs/presentation.md` | Slide order for talking about the SF=1 run. |
| `docs/files.md` | This page. |

## Protocol results (SF=1)

| File | What it is |
|---|---|
| `results/advisors/*.json` | Five configurations from each model. Winner is in `grok-4-7.json`. |
| `results/advisors_excluded/` | Gemini first run, excluded for reading result files. |
| `results/configs_sf1.json` | The 33 configurations measured. |
| `results/candidates_tpcds_sf1.json` | HypoPG shortlist on SF=1. |
| `results/samples.jsonl` | Sample-build times, used by `rank_metrics.py`. |
| `results/truth_sf1.jsonl` | Ground truth, 33 configs × 99 queries. |
| `results/truth_sf1_rep.jsonl` | Repeat, noise ceiling. |
| `results/dprime_tpcds_sf1_{b0,sys,uitem,fk,strat}_p5.jsonl` | Native 5% samples. |
| `results/dprime_tpcds_sf1_{b0,uitem}_p5_c4.jsonl` | Those two with full statistics copied on. |
| `results/rank_sf1_p5.md` | Comparison table. |
| `results/distill_proxies.md` | Plan-hash and sign agreement on the timed runs. |
| `results/distill_explain.md` | HypoPG cost vs time. |
| `results/explain_tpcds_sf1*.jsonl` | HypoPG EXPLAIN rows. |

## SF=10 screen (pilot, still the starting point on a bigger machine)

| File | What it is |
|---|---|
| `results/study_set_sf10.json` | 23 queries that moved by ≥1.3x on the warm rerun. |
| `results/configs_sf10_study.json` | none + one `ix_c<q>_0` index per study-set query. |
| `results/candidates_tpcds_sf10.json` | HypoPG shortlist at SF=10. |
| `results/candidates_tpcds_sf10_screen.json` / `_warm.json` | The one-index-per-query sets used in the screen. |
| `results/eval_tpcds_sf10_screen.jsonl` | Cold pass. |
| `results/eval_tpcds_sf10_screen_warm.jsonl` | Warm pass. This is the one to trust. |
| `results/eval_tpcds_sf10_timeouts.jsonl` | 30-minute rerun of queries that hit the 5-minute cap. |
