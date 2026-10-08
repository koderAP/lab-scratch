# COL868, sample-based index evaluation

PostgreSQL iteration of the project in `problem_statement.md`.

**Read `docs/protocol.md` first.** It is the experiment as specified: candidate index configurations (several indexes per configuration) proposed by LLM advisors, every configuration measured on the full database by index build time and total runtime of all 99 queries, the same measurement on a reduced database D', and a comparison of the two rankings by Kendall tau, top-1 and evaluation cost reduction.

An earlier per-query pilot (single HypoPG indexes, an index-sensitive subset, an SF=10 screen) shaped the measurement rules and is not the answer to the protocol. Those scripts are gone. The notes and the result files are still there. See `docs/lab-notes.md`.

```bash
./scripts/setup_env.sh          # extensions, tuned conf, database col868
./scripts/load_tpcds.sh 1       # SF=1 (about 1 GB)

# protocol pipeline (SF=1)
# 1. advisors write results/advisors/*.json  (prompt: advisors/prompt.md)
python3 scripts/build_configs.py                                   # -> results/configs_sf1.json
python3 scripts/eval_configs.py --schema tpcds_sf1 --configs results/configs_sf1.json --out results/truth_sf1.jsonl
python3 scripts/make_sample.py --src tpcds_sf1 --dst tpcds_sf1_b0_p5 --sampler b0 --pct 5
python3 scripts/eval_configs.py --schema tpcds_sf1_b0_p5 --configs results/configs_sf1.json --out results/dprime_tpcds_sf1_b0_p5.jsonl
python3 scripts/rank_metrics.py --truth results/truth_sf1.jsonl --sample results/dprime_tpcds_sf1_b0_p5.jsonl
python3 scripts/progress_configs.py results/truth_sf1.jsonl     # while a run is going
```

What each file is for: `docs/files.md`. Other writing: `docs/results.md` (numbers), `docs/lab-notes.md` (why the measurement rules look like this), `docs/related-work.md` (closest work is SQL:Trek), `docs/sampling-taxonomy.md` (sampler list), `docs/wu-notes.md` (motivating paper).
