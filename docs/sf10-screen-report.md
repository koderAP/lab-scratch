# SF=10 screen, 2 Oct 2026

What this is: a first pass over TPC-DS at scale factor 10 on the local Postgres 14, to find queries where one extra index actually changes the runtime. It is not the sampling result. No sample has been built at this scale yet.

The indexes are HypoPG's cheapest suggestion, one per query. The LLM advisor from the proposal is not in this run.

## What was measured

72 queries had a HypoPG index at least 1% cheaper than no extra index. Each was timed with no extra index, then with that index. A warm-up run is thrown away. The reported time is the median of the repeats. Statistics were analyzed once and then left alone. Autovacuum is off.

The first pass hit a cold cache. The database is about 27 GB and `shared_buffers` is 2 GB, so the first execution of a query reads a lot of pages and the next one often does not. That made some speedups look enormous. Q21 went from 21 minutes and about a million buffer reads to half a second and zero reads. Most of that was the cache, not the index.

Ten queries did not finish the no-index run within 5 minutes: Q1, Q6, Q14, Q16, Q23, Q30, Q74, Q76, Q81, Q95. The harness does not try the index when the baseline times out, so those ten have no index number. They are being rerun with a 30 minute cap (`results/eval_tpcds_sf10_timeouts.jsonl`).

The other 25 queries that looked index-sensitive on the cold pass were timed again after the cache had been warmed. Both the no-index run and the index run in that second pass are warm. That is the pass the study set comes from.

## What survived the warm rerun

A query is in the study set when the warm no-index time is at least 1 second and the index changes it by at least 1.3x, faster or slower. 21 queries do. Four of the cold-pass candidates do not. Q19 is the clearest: warm, it is 14.4 s with no index and 13.7 s with the index, and both plans read about 360,000 pages. The 35 minute cold timing was the first touch of the table. Q45 and Q54 land inside 1.3x. Q18's warm no-index time is 0.3 s, under the 1 second floor.

`results/study_set_sf10.json` is the list: 10, 13, 17, 21, 25, 26, 27, 28, 29, 36, 41, 44, 58, 63, 65, 70, 88, 90, 94, 96, 99.

Times below are the warm pair. "Reads" is the median of `shared_read` blocks. A drop to zero means the index plan did not touch those pages. On this pass the no-index plan often still read them, so the gap is not "the second run found the data already in memory."

| Query | No index | With index | Change | Reads, no index | Reads, with index |
|---|---:|---:|---|---:|---:|
| 41 | 13.9 s | 0.03 s | 441x faster | 0 | 0 |
| 27 | 27.2 s | 0.2 s | 176x faster | 449k | 0 |
| 96 | 6.4 s | 0.1 s | 72x faster | 441k | 0 |
| 26 | 5.2 s | 0.1 s | 54x faster | 0 | 1 |
| 44 | 22.3 s | 0.5 s | 43x faster | 1.7M | 0 |
| 90 | 7.4 s | 0.2 s | 34x faster | 513k | 0 |
| 21 | 15.4 s | 0.5 s | 32x faster | 975k | 0 |
| 99 | 8.3 s | 1.4 s | 5.8x faster | 511k | 0 |
| 25 | 10.9 s | 41.7 s | 3.8x slower | 329k | 351k |
| 88 | 45.9 s | 12.9 s | 3.6x faster | 3.3M | 696k |
| 29 | 7.9 s | 28.1 s | 3.5x slower | 256k | 233k |
| 58 | 1.4 s | 0.4 s | 3.5x faster | 0 | 0 |
| 28 | 41.8 s | 119 s | 2.8x slower | 2.7M | 3.6M |
| 17 | 16.2 s | 39.8 s | 2.5x slower | 470k | 543k |
| 10 | 26.1 s | 11.2 s | 2.3x faster | 250k | 0 |
| 36 | 20.6 s | 40.2 s | 2.0x slower | 422k | 421k |
| 65 | 40.1 s | 71.3 s | 1.8x slower | 840k | 834k |
| 94 | 5.1 s | 3.1 s | 1.6x faster | 255k | 0 |
| 70 | 83.3 s | 128 s | 1.5x slower | 2.1M | 2.1M |
| 13 | 28.7 s | 40.7 s | 1.4x slower | 453k | 451k |
| 63 | 20.9 s | 27.9 s | 1.3x slower | 740k | 738k |

The index was used in every one of these plans. About half the set gets faster and about half gets slower. A sample that only notices speedups will miss the regressions, and the regressions are ones where the buffer reads stay large, so they are less likely to be a cache artifact.

Q41 is the odd row. Both sides read nothing, and the index is about 400x faster. Both timings are warm and in memory. It stays in the set, but it is a CPU-plan effect, not an IO one, and it is the number I trust least until it is repeated.

## What this does not say

SF=1 cannot support a sampler claim. A second timing of the same study set there agreed with the first on the winner 47% of the time, median regret 1.15x. The 5% samples landed in that same neighbourhood. Copying the full database's statistics onto the Bernoulli and universe samples moved agreement by about 0.13, which is inside that noise. Detail is in `docs/lab-notes.md`.

This screen used one HypoPG index per query, not the full shortlist, and not an LLM. The study set is "where that one index matters," which is the right filter before spending SF=10 sample builds. It is not yet a ranking task with several indexes per query.

## Timeout rerun (finished 4 Oct)

Ten queries that died at 5 minutes were run again with a 30 minute cap. The cap does not cancel a query that is inside a long disk read, so several of these ran for hours and the recorded "timeout" is just what the harness writes when the cancel finally lands.

Six never got an index timing: Q1, Q6, Q14, Q16, Q81, Q95. They stay out of the study set.

Four finished both sides:

| Query | No index | With index | Reads, no index | Reads, with index |
|---|---:|---:|---:|---:|
| 23 | 68 min | 5.5 min | 3.0M | 3.8M |
| 76 | 6.7 h | 6.7 min | 35M | 21M |
| 30 | 14 min | 13.5 min | 0 | 0 |
| 74 | 5.2 min | 4.8 min | 1.1M | 1.1M |

Q23 is a real 12x. Both plans read millions of pages, and the index was used. It is in the study set. Q30 and Q74 used the index and barely changed, so they are not. Q76 is in the set on the 1.3x rule, but the 6.7 hour no-index time is the stuck disk read, not a clean timing. The index side (6.7 min, 21M reads, index used) is the believable half.

The study set is now 23 queries, in `results/study_set_sf10.json`.

## Next

The comparison at this scale is three samples, not the whole sampler grid: Bernoulli with its own statistics, Bernoulli with the full database's statistics, and universe sampling. Page and stratified stay out. They tied Bernoulli at SF=1, and stratified cost almost as much as the full run, on data that was too noisy to trust.
