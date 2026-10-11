# What each file does

The experiment that answers the spec is `docs/protocol.md`. Everything under `scripts/` that is still here is part of that experiment, or builds the database it runs on. Older scripts (per-query timing, the Q72 loop, the smoke test) have been removed. Their output is still under `results/` and is marked as such below.

## Root

| File | What it is |
|---|---|
| `problem_statement.md` | The project as assigned: LLM candidates, measure cost and time, compare samples to the full database. |
| `README.md` | How to set the machine up and run the protocol once. |
| `results.html` | One-page figure report of the SF=1 protocol run. Self-contained, so it can be attached to an email and opened in a browser. |
| `protocol.html` | Step-by-step diagrams of the experiment, including the math for each sampler. Self-contained HTML. |
| `review.html` | Reviewer guide for a first-time reader: problem, design decisions, results, threats, review questions. Self-contained HTML. |
| `reviewer.html` | First-read briefing for someone reviewing the work: question, design choices, measured results, and what is still missing. |
| `papers/` | Local copies of the related papers (`python3 papers/fetch.py`). PDFs are gitignored. List: `papers/README.md`. |

## Scripts

| File | What it does |
|---|---|
| `scripts/setup_env.sh` | Checks DuckDB and PostgreSQL 14, includes `config/postgresql-tpcds.conf`, creates database `col868`, installs HypoPG. |
| `scripts/load_tpcds.sh` | Generates TPC-DS at a scale factor with DuckDB and loads it into schema `tpcds_sfN`. |
| `scripts/apply_pks.sh` | Applies `sql/tpcds_pks.sql` on one schema and runs `ANALYZE` once. |
| `scripts/pg.py` | Shared helpers: read a query file, call `psql`, parse an `EXPLAIN ANALYZE` plan. Not run on its own. |
| `scripts/make_sample.py` | Builds a reduced schema. Samplers: `b0` Bernoulli, `sys` page, `uitem` universe on the item key, `fk` foreign-key closure, `strat` stratified. Appends a row to `results/samples.jsonl`. |
| `scripts/transplant_stats.py` | Copies the full database's `pg_statistic` onto a sample and sets `reltuples` / `relpages`. This is the C4 factor. |
| `scripts/gen_candidates.py` | HypoPG pass: per query, ranks hypothetical indexes by optimizer cost. Output is an input to `build_configs.py`, not a ranking of its own. |
| `scripts/build_configs.py` | Merges the six advisor files, the empty configuration, and the HypoPG top-5 and top-8 sets into `results/configs_sf1.json`. Drops unknown columns, tiny tables, indexes that already exist, and duplicates. |
| `scripts/eval_configs.py` | The measurement. One configuration at a time: create its indexes (timed), run the queries, drop them. Writes query rows and one summary row per configuration. Resumable. |
| `scripts/rank_metrics.py` | Compares a reduced-database jsonl to the full-database jsonl. Prints Kendall tau-b, bootstrap interval, top-1, regret, top-3, and cost reduction, for runtime and for build-plus-runtime. |
| `scripts/progress_configs.py` | How many configurations an `eval_configs.py` jsonl has finished, and a rough time left. |
| `scripts/run_dprime.sh` | Runs `eval_configs.py` on the five native 5% schemas in order. |

## Advisors and workload

| File | What it is |
|---|---|
| `advisors/prompt.md` | Instructions given to each model. Schema, existing indexes, and the 99 query texts only. |
| `advisors/schema_tables.txt` | Table and column list the advisors were allowed to see. |
| `advisors/existing_indexes.txt` | Primary keys and indexes already on `tpcds_sf1`. |
| `workloads/tpcds/01.sql` to `99.sql` | TPC-DS queries in PostgreSQL dialect. One file per query. |
| `workloads/tpcds/SOURCE.txt` | Where that dialect came from. |

## Config and SQL

| File | What it is |
|---|---|
| `config/postgresql-tpcds.conf` | `shared_buffers=2GB`, `effective_io_concurrency=0`, `autovacuum=off`. Included from the Homebrew PostgreSQL 14 config. |
| `sql/tpcds_pks.sql` | Primary keys applied to a loaded TPC-DS schema. |

## Docs

| File | What it is |
|---|---|
| `docs/protocol.md` | The experiment as specified, plus the choices that were mine (score, scale, cap, advisors, which samples). Read this first. |
| `docs/results.md` | The SF=1 5% numbers: native samples, transplanted statistics, and the second full-database run. |
| `docs/files.md` | This page. |
| `docs/lab-notes.md` | Running notes on why the measurement rules exist (the Q72 retraction, cache, the cap that does not cancel a stuck read). It still mentions `tasks/plan.md`, which was the old per-query plan and has been removed. |
| `docs/related-work.md` | Neighbours of the idea. Closest published system is SQL:Trek. |
| `docs/sampling-taxonomy.md` | Sampler catalogue (B0 through C5, and what was left out) and why. |
| `docs/literature.md` | Reading list, grouped by the role each paper plays here. |
| `docs/wu-notes.md` | Notes on Wu et al., the paper the proposal cites for measuring time rather than optimizer cost. |
| `docs/sf10-screen-report.md` | Warm SF=10 screen from the old per-query pilot. Not a protocol result. |
| `docs/ten-day-bar.md` | Checklist from the early meetings. It points at `docs/sampling-review.md`, which was a shorter version of `docs/sampling-taxonomy.md` and has been removed. |
| `docs/meeting-notes.md` | Notes from those meetings, including the Q72 retraction. It names scripts and `docs/pipeline.md` that have been removed. The measurement rules it describes are the ones in `docs/protocol.md`. |

## Results that the protocol uses

| File | What it is |
|---|---|
| `results/advisors/claude-opus-5.json` | Five configurations from Claude Opus 5. |
| `results/advisors/claude-fable-5-1.json` | Five from Claude Fable 5.1. |
| `results/advisors/gpt-5-6-sol.json` | Five from GPT 5.6 Sol. |
| `results/advisors/gemini-3-8-flash.json` | Five from Gemini 3.8 Flash. This is the clean rerun. |
| `results/advisors/grok-4-7.json` | Five from Grok 4.7. The full-database winner is in this file. |
| `results/advisors/composer-2-5.json` | Five from Composer 2.5, the weaker baseline. |
| `results/advisors_excluded/gemini-3-8-flash.first-run.json` | Gemini's first try. Excluded because it read earlier result files. |
| `results/configs_sf1.json` | The 33 configurations actually measured. Built by `build_configs.py`. |
| `results/candidates_tpcds_sf1.json` | HypoPG shortlist on SF=1. `build_configs.py` takes the top 5 and top 8 from this file. |
| `results/samples.jsonl` | One row per sample build, including how long the build took. `rank_metrics.py` reads it for the "including sample build" column. |
| `results/truth_sf1.jsonl` | Ground truth. 33 configurations on `tpcds_sf1`, all 99 queries. Log: `results/truth_sf1.log`. |
| `results/truth_sf1_rep.jsonl` | The same measurement again, for the noise ceiling. Log: `results/truth_sf1_rep.log`. |
| `results/dprime_tpcds_sf1_b0_p5.jsonl` | Bernoulli 5%, own statistics. |
| `results/dprime_tpcds_sf1_sys_p5.jsonl` | Page 5%, own statistics. |
| `results/dprime_tpcds_sf1_uitem_p5.jsonl` | Universe on item, 5%, own statistics. |
| `results/dprime_tpcds_sf1_fk_p5.jsonl` | Foreign-key closure, 5%, own statistics. |
| `results/dprime_tpcds_sf1_strat_p5.jsonl` | Stratified 5%, own statistics. |
| `results/dprime_sf1.log` | Log of those five native runs. |
| `results/dprime_tpcds_sf1_b0_p5_c4.jsonl` | Bernoulli 5% with full-database statistics copied on. |
| `results/dprime_tpcds_sf1_uitem_p5_c4.jsonl` | Universe 5% with full-database statistics copied on. |
| `results/dprime_sf1_c4.log` | Log of those two transplanted runs. |
| `results/rank_sf1_p5.md` | The comparison table from `rank_metrics.py` for the seven reduced databases. |

## Results from the earlier pilot

These were written by scripts that are no longer in the tree. They are not inputs to the protocol, except `candidates_tpcds_sf1.json` above.

| Files | What they are |
|---|---|
| `results/eval_tpcds_sf1.jsonl`, `results/eval_tpcds_sf1_rep.jsonl`, `results/eval_tpcds_sf1_rep.log` | Per-query timings on the full SF=1 database, and a repeat. |
| `results/eval_tpcds_sf1_{b0,sys,uitem,fk,strat}_p5.jsonl` | The same per-query timings on the five 5% samples. |
| `results/eval_tpcds_sf1_b0_p5_c4.jsonl`, `results/eval_tpcds_sf1_uitem_p5_c4.jsonl`, `results/eval_b0_c4.log`, `results/eval_uitem_c4.log` | Those two samples again after a statistics transplant, still per query. |
| `results/study_set_sf1.json`, `results/metrics_sf1_p5.md` | The index-sensitive subset and the old per-query score table. |
| `results/sample_study_sf1_p5.log`, `results/sample_study_sf1_p5_fk.log` | Logs of that sample study. |
| `results/candidates_tpcds_sf10.json`, `results/candidates_tpcds_sf10.log`, `results/candidates_tpcds_sf10_screen.json`, `results/candidates_tpcds_sf10_warm.json` | HypoPG shortlists at SF=10. |
| `results/eval_tpcds_sf10_screen.jsonl`, `results/eval_tpcds_sf10_screen_warm.jsonl`, `results/eval_tpcds_sf10_timeouts.jsonl` | SF=10 screen timings: cold, warm, and the timeout rerun. |
| `results/screen_sf10.log`, `results/screen_sf10_warm.log`, `results/screen_sf10_timeouts.log` | Logs of those three passes. |
| `results/study_set_sf10.json`, `results/study_set_sf10_screen.json` | Queries kept by the warm SF=10 rule. Written up in `docs/sf10-screen-report.md`. |
| `results/baseline_tpcds_sf1_*`, `results/baseline_tpcds_sf10_*` | No-index baselines from the first days, before the protocol. |
| `results/index_loop_*q72*`, `results/fixed_*q72*`, `results/frozen_*q72*` | The Q72-only loop. `fixed_*` and `frozen_*` are the reruns after the measurement rules were corrected. The first numbers were retracted. |
| `results/runtimes.jsonl` | An early unstructured timing dump. |
