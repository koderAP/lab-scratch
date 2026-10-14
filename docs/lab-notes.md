# Lab notes

Running notes on why the experiment went the way it did. Dates are when the run happened.

The per-query jsonl files and the Q72 dumps named below were removed on 14 Oct 2026 when the tree was cleaned for the server move. The protocol jsonl files (`truth_sf1`, `dprime_*`) remain. The measurement rules this note explains are still the rules.

## 2026-10-02. What the 5% pilot is allowed to say

The five 5% samples on SF=1 (Bernoulli, page, universe, FK closure, stratified) agree with the full database on the winning index 27% to 40% of the time, with median regret about 1.2x. One seed. The database fits in memory. The indexes are HypoPG's shortlist, not an LLM advisor.

That is enough to stop treating universe sampling as the method we expect to win. It is not enough to claim that sampling fails on analytical workloads. The same numbers could be timer noise, or the planner reacting to sample statistics, or a real failure of every sample design. The next runs split those apart. The rule is written in `tasks/plan.md`: a repeated ground truth below 70% top-1 agreement means SF=1 cannot carry a sampler claim; a statistics transplant that lifts agreement by 0.15 or more means the failure was the statistics.

## Plans on the sample are different plans

Compared `plan_skeleton` in `results/eval_tpcds_sf1.jsonl` with `results/eval_tpcds_sf1_b0_p5.jsonl`. On the Bernoulli 5% sample, 143 of 151 measured query-index pairs have a different skeleton from the full SF=1 database. The same pattern holds for the other four samples (roughly 130 of 140 pairs).

Q2 with no extra index is a clear case. The full database parallelizes the aggregate (`Gather`) and finishes one branch with a merge join. The sample does not go parallel, and that branch is a pile of hash joins. Deleting the word `Gather` from both strings still leaves them different, so this is not only the parallel threshold.

19 of 30 Bernoulli queries miss the full-database winner, and on all 19 the plan of the index the sample picked is a different shape. Some queries agree on the winner with a different plan anyway, so a matching winner is not evidence the planner did the same thing.

This is why the next build is a statistics transplant onto the samples that already exist, rather than another way of picking rows. The planner on those samples is still using `ANALYZE` of the sample.

## FK closure is the size it was supposed to be

`pg_stat_user_tables.n_live_tup` on `tpcds_sf1_fk_p5` versus `tpcds_sf1`:

| table | sample | full | ratio |
|---|---:|---:|---:|
| store_sales | 143451 | 2880457 | 5.0% |
| store_returns | 14215 | 287867 | 4.9% |
| catalog_sales | 71651 | 1441501 | 5.0% |
| catalog_returns | 7195 | 144067 | 5.0% |
| web_sales | 35781 | 719384 | 5.0% |
| web_returns | 3599 | 71654 | 5.0% |
| inventory | 586196 | 11744593 | 5.0% |

Returns were built from the sampled sales keys, and they came out near 5% as well. Inventory too. Nothing is empty. The 50% false-alarm rate and the slightly negative rank correlation are what this sample produced. I am not rewriting the builder to chase that number.

## Statistics transplant, method

`scripts/transplant_stats.py` copies `pg_statistic` from the source schema onto the sample, matching columns by name, and sets `reltuples`, `relpages`, and `relallvisible` to the source values. The rows stay as they were. `ANALYZE` is not run afterwards.

The indexes are a loose end. An index built on the sample is physically small, while the table statistics say the table is the full size. Selectivity comes from the full database and the index cost comes from the small index. That is the version of "virtual statistics" being tested. If the plans move and the ranking does not, this mismatch is one place to look.

Applied to `tpcds_sf1_b0_p5` and `tpcds_sf1_uitem_p5` on 2 Oct, before re-timing. Check on `store_sales`: `ss_item_sk` and `ss_sold_date_sk` have the same `n_distinct`, most-common values, and histogram as `tpcds_sf1`.

Planning-only check, Q2, no extra index. Before the transplant the sample plan had no `Gather`. After it, the first half of the plan matches the full database, including the parallel aggregate and the same append order of `catalog_sales` and `web_sales`. The second half does not: the full database merge-joins the date dimension, the sample still hash-joins it. So the transplanted statistics move the plan toward the full database, and they do not reproduce it.

## The repeated ground truth does not agree with itself

Reran the 34-query study set on `tpcds_sf1` into `results/eval_tpcds_sf1_rep.jsonl` (same candidates, 20 s timeout, warm-up plus repeats). Scored against the first run with a 10% tie:

| | queries | top-1 | median regret | tau |
|---|---:|---:|---:|---:|
| second run of the full database | 30 | 0.47 | 1.15 | 0.32 |
| best 5% sample (page) | 30 | 0.40 | 1.22 | 0.23 |

Widening the tie to 20% only lifts the rerun to 0.57. It reaches 0.70 at a 30% tie. On the first run, the second-best index is within 10% of the best on 8 of 30 queries, and the median gap from best to second is 1.18x, so this is not a pile of exact ties. The median no-index time on this set is 323 ms. At that length a warm laptop moves the winner around.

Decision: SF=1 top-1 agreement is below the 0.70 bar I set in `tasks/plan.md`. I will not claim that any sampler failed, or worked, from these numbers. The 5% pilot sits next to a rerun of the full database and is not clearly worse. SF=10 is where the comparison has to be made, because those queries take seconds and the full database does not fit in memory.

The transplant timing on the two SF=1 samples still runs, as a check that the machinery moves plans and runtimes. It does not decide the paper.

## Transplant helps a little, and still sits on the noise

Timed the same study set after the transplant (`results/eval_tpcds_sf1_b0_p5_c4.jsonl`, `results/eval_tpcds_sf1_uitem_p5_c4.jsonl`).

| sample | top-1 | median regret | tau | false alarms |
|---|---:|---:|---:|---:|
| Bernoulli, own stats | 0.37 | 1.22 | 0.23 | 0.02 |
| Bernoulli, full stats | 0.50 | 1.10 | 0.30 | 0.05 |
| universe, own stats | 0.28 | 1.22 | 0.22 | 0.07 |
| universe, full stats | 0.41 | 1.16 | 0.24 | 0.05 |
| full database, run again | 0.47 | 1.15 | 0.32 | 0.16 |

The lift is about 0.13, short of the 0.15 I was going to treat as a result, and the better of the two transplanted samples (0.50) is the same neighbourhood as running the full database twice (0.47). Exact plan skeletons barely moved: 8 matching pairs before, 11 after, out of about 150. Q2's plan did change, so the statistics are being read. They are not making the sample pick the full-database plan often enough to see in this metric.

Bernoulli with full statistics has the best regret in the table (1.10), a bit under the rerun. I am not going to call that a win. On a 323 ms median query the ranking jitters by more than that.

What I take to SF=10, and why only these: Bernoulli with its own statistics (the SQL:Trek recipe), Bernoulli with the full statistics (the thing that moved SF=1, even if not enough to trust), and universe sampling (the join-consistent alternative, which lost here but this scale cannot show it). Page and stratified stay behind. Page matched Bernoulli. Stratified cost almost as much as the full run. FK closure stays behind until SF=10 says whether a join-consistent sample is worth having at all.

## SF=10 screening started

`gen_candidates.py` on `tpcds_sf10` finished in about half a minute. 72 of 99 queries have a HypoPG index at least 1% cheaper than no extra index. The screen times those 72 with no extra index and with that one cheapest index (`results/candidates_tpcds_sf10_screen.json`, 34 distinct indexes). The other 27 queries have nothing in the shortlist that the optimizer thinks will help, so they cannot show a 1.3x runtime change from this candidate source.

A query joins the SF=10 study set only if the no-index run is at least 1 second and some candidate moves the runtime by at least 1.3x. Cap around 25 if more than that qualify. Timeout is 300 seconds. This is the ground truth for the screen, not yet the full candidate list.

The screen finished the same day, about 7:49 pm. 72 no-index runs, 10 of them cut off at 300 s, and those 10 were not timed again with the index (the harness skips a timed-out baseline). 62 queries have both numbers. 25 of them move by at least 1.3x with a baseline of at least 1 s. List: `results/study_set_sf10_screen.json`.

The biggest "speedups" are not believable as index effects. Q21 went from 1249 s and 975k buffer reads with no index to 0.5 s and 0 reads with the index. Q18, Q27, Q44, and Q96 do the same thing: the no-index pass was the first touch of a cold 27 GB database, and the index pass found the pages already in memory. Q19 is the awkward one: still about 360k reads, but 2093 s down to 13 s, and the index was used. Q25 and Q28 stayed IO-heavy and got slower (10 s to 36 s, 35 s to 101 s), which is the kind of change that can survive a warm rerun.

I am retiming those 25 with no index and with the same index, now that the cache has been warmed, into `results/eval_tpcds_sf10_screen_warm.jsonl`. The study set is the queries that still move by 1.3x on that rerun.

The warm rerun finished about 8:56 pm. 21 of the 25 still qualify (`results/study_set_sf10.json`). Q19 does not: warmed up, no index is 14.4 s and the index is 13.7 s, so the 2093 s to 13 s drop was the cold cache. Q45 and Q54 also fall inside 1.3x. Q18's no-index time drops to 0.3 s, under the 1 s floor.

The ones that stay are real in a way the cold screen was not. Q21 is 15.4 s with no index and 0.5 s with the index, and the no-index plan still read about 975k buffer pages on this second pass. The index plan read none. That is the index avoiding the scan, not a second run finding the pages already in memory. Same pattern on Q27 (27 s to 0.2 s), Q44 (22 s to 0.5 s), Q96 (6.4 s to 0.1 s), Q90 (7.4 s to 0.2 s). The slowdowns that survived also still do their IO: Q28 42 s to 119 s, Q65 40 s to 71 s, Q70 83 s to 128 s, Q25 11 s to 42 s.

## 2026-10-05. The protocol was not being followed, so the experiment is being redone

The spec is: candidate index configurations (more than one index per configuration), each measured on the full database by index build time and total runtime of the workload, that ranking as ground truth, then the same on a reduced database, compared by Kendall tau, top-1 and evaluation cost reduction. Keep all 99 queries. Try more powerful models.

What had been done instead: one query at a time, a handful of single indexes per query from HypoPG, a subset of index-sensitive queries, no workload totals, no LLM. That is a pilot of a narrower question. Nothing from it is evidence on the protocol question, and it stays here only for what it taught about measurement.

What is being done now is written in `docs/protocol.md`, with the choices that were mine listed there (score definition, SF=1, a 20 s cap, repeat rule).

Candidates: six models were each given the schema, the existing indexes, and the 99 query texts, with no database access, and asked for 5 configurations of up to 8 indexes. Claude Opus 5, Claude Fable 5.1, GPT 5.6 Sol, Gemini 3.8 Flash, Grok 4.7, and Composer 2.5 as a weaker baseline. Plus the empty configuration and two HypoPG configurations (the 5 and the 8 indexes with the largest summed cost gain over the workload). 33 configurations, 198 indexes, all of which build.

First two full-database results: no extra index, 190.7 s for the whole workload, and the HypoPG 5-index configuration, 185.9 s. Seven queries hit the 20 s cap in both, which is 140 s of the total that no index changes. So differences between configurations will be small next to the total, and what matters is whether they are bigger than the run to run noise. A second pass over the full database is needed to know, and is planned after the first one.

### Advisor independence check (5 Oct)

The advisors had file access to the whole repository even though the prompt named only the schema, the existing indexes, and the query texts. Reading each advisor's transcript for the files it opened:

- Claude Opus 5, Claude Fable 5.1, GPT 5.6 Sol, Composer 2.5, Grok 4.7: opened only the three allowed inputs and their own output file.
- Gemini 3.8 Flash: also opened `results/study_set_sf1.json`, `results/candidates_tpcds_sf1.json`, the SF=10 screen logs, and the new harness scripts. The first two are measured results from the earlier pilot (which queries an index helped, HypoPG's picks), so its configurations were informed by exactly the kind of result this experiment tests.

Gemini's first output is kept at `results/advisors_excluded/gemini-3-8-flash.first-run.json` and is not used. It was rerun with an added instruction listing the only files it may open, and the transcript is checked again after that run. The full-database run had started with the first Gemini output in its list; it is restarted once the rerun is in, so every configuration in the ground truth comes from an advisor that saw only the allowed inputs.

Gemini's rerun opened only the allowed inputs (checked in its transcript). Its new configurations are in the set (33 configurations, 194 indexes in total, all of which build). The ground truth was restarted with that set. Three configurations were already complete (no index, HypoPG 5, HypoPG 8) and were kept, since none of them depends on Gemini.

One slip while restarting: killing the run mid-configuration left its experimental indexes in the database, and the configuration builder counted them as "existing" and silently dropped 26 indexes from the other advisors' configurations. Caught because the total changed from 198 to 172. Fixed by dropping leftovers before rebuilding. `build_configs.py` should refuse to run while `ix_c*` indexes exist; noted as a to do.
