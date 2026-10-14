# COL868, sample-based index evaluation

PostgreSQL iteration of the project in `problem_statement.md`.

**Moving to a new machine?** Read `docs/server.md` first. It is the full context: what the laptop already measured, what not to redo, how to set up Postgres, and the first experiment to run.

**Otherwise read `docs/protocol.md`.** It is the experiment as specified: candidate index configurations proposed by LLM advisors, every configuration measured on the full database by index build time and total runtime of all 99 queries, the same measurement on a reduced database D', and a comparison of the two rankings.

```bash
./scripts/setup_env.sh          # extensions, tuned conf, database col868
./scripts/load_tpcds.sh 1       # SF=1 (about 1 GB)
./scripts/apply_pks.sh tpcds_sf1

python3 scripts/eval_configs.py --schema tpcds_sf1 --configs results/configs_sf1.json --out results/truth_sf1.jsonl
python3 scripts/make_sample.py --src tpcds_sf1 --dst tpcds_sf1_b0_p5 --sampler b0 --pct 5
python3 scripts/eval_configs.py --schema tpcds_sf1_b0_p5 --configs results/configs_sf1.json --out results/dprime_tpcds_sf1_b0_p5.jsonl
python3 scripts/rank_metrics.py --truth results/truth_sf1.jsonl --sample results/dprime_tpcds_sf1_b0_p5.jsonl
python3 scripts/progress_configs.py results/truth_sf1.jsonl
```

What each file is for: `docs/files.md`. SF=1 numbers: `docs/results.md`. Distillation idea: `docs/distillation-plan.md`. Measurement rules: `docs/lab-notes.md`.
