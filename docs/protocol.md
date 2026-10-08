# Protocol (authoritative)

This is the experiment as specified for the project. Everything else in `docs/` describes earlier work that used a narrower design (per-query ranking of single indexes, an index-sensitive subset, HypoPG as the only candidate source). That work stays as a pilot and as a source of harness lessons. It does not answer the question below.

## Steps

1. **Generate candidate index configurations.** A configuration is a set of one or more indexes for the whole workload. Candidates come from several LLM advisors, including more powerful models, plus a no-index configuration and a HypoPG-greedy configuration as baselines.
2. **Evaluate every configuration on the full database.** For each configuration record the index build time and the total query runtime over the workload.
3. **Ground-truth ranking.** Rank the configurations on the full database from those measurements.
4. **Build a reduced database D'.** Several samplers, several settings.
5. **Evaluate the same workload on D'.** Same configurations, same 99 queries, same measurement rules.
6. **Compare the ranking on D' with the full-database ranking.** Kendall rank correlation, top-1 candidate, and evaluation cost reduction (index build time plus the sum of query runtimes, full database over D').

All 99 TPC-DS queries are kept. There is no filtering to index-sensitive queries.

## Decisions that were mine (not in the spec)

| Question | Choice | Reason |
|---|---|---|
| What is the ranking score? | **Primary: total workload runtime** (sum of the 99 query times). **Secondary: build time plus workload runtime.** Both rankings are scored. | The proposal's target is the execution-time-optimal configuration. Build time is a one-off cost and also a ranking input in the spec, so it is reported as a second ranking, not dropped. |
| Scale | **SF=1 for the full protocol.** SF=10 only as a capped check later. | 99 queries x about 30 configurations x several samples does not finish at SF=10 on a 16 GB laptop (single queries ran for hours there). |
| Per-query cap | 20 s. A capped query counts as 20 s in the sum, for the full database and for the sample alike. | Keeps every run finite. The cap is censoring: a configuration that fixes a capped query is still seen as better, but its gain is understated. |
| Repeats | One discarded warm-up. Then two timed runs if the first run took 2 s or less, one timed run otherwise. Median. | A sum over 99 queries averages out per-query noise. The earlier SF=1 rerun showed single-query winners are noisy. |
| Statistics | `ANALYZE` once per database, frozen. Autovacuum off. | Protocol lessons from the Q72 retraction. |
| Index builds | One configuration at a time. All its indexes are created, the 99 queries run, then they are dropped. Build time is the sum of the `CREATE INDEX` times. | Isolates configurations from each other. |
| Reduced database | 5% samples of SF=1 first: Bernoulli (the SQL:Trek recipe), Bernoulli with the full-database statistics, page, universe on item, FK closure, stratified. | Reuses the builders already written. Other rates and seeds only after this table exists. |
| Who the advisors are | Six models, run as isolated agents with the schema and the 99 query texts and no database access. Each proposes 5 configurations. | Spec asks for LLM candidates and for more powerful models than a baseline. |

## What counts as done

- `results/configs_sf1.json` holds the configurations with their source model.
- `results/truth_sf1.jsonl` has one row per (configuration, query) plus one row per configuration with build time.
- The same file shape exists for each reduced database.
- `scripts/rank_metrics.py` prints, per reduced database: Kendall tau, top-1 agreement (and regret), cost reduction, for both rankings.
- `docs/results.md` reports those tables and says what they do and do not show.
