# Results so far (protocol, SF=1, 5 Oct to 6 Oct)

Ground truth: 33 configurations on `tpcds_sf1`, all 99 queries, 20 s cap per query. Score A is the sum of the 99 query times. Score B adds the index build time. Full table: `results/rank_sf1_p5.md`.

## Full database

No extra index: 190.7 s for the whole workload. Best configuration: Grok's small set of dimension filters, 172.9 s. Worst of the 33: 190.7 s, the empty configuration. Spread from best to worst is 17.7 s.

Seven queries hit the 20 s cap under every configuration, including no index. That is 140 s of every total that no index can change. The indexes are fighting over the other 50 s, and the best of them wins about 18 s of it.

## Reduced databases, 5%, one seed, their own statistics

| Sample | tau (runtime) | 95% interval | top-1 | regret | cheaper than full |
|---|---:|---|---|---:|---:|
| Bernoulli | 0.51 | 0.26 to 0.72 | no | 1.014 | 43x (25x with the sample build) |
| Page | 0.46 | 0.20 to 0.69 | no | 1.014 | 90x (33x) |
| Universe | 0.45 | 0.27 to 0.63 | no | 1.014 | 2.6x |
| FK closure | 0.42 | 0.17 to 0.62 | no | 1.014 | 3.5x |
| Stratified | 0.28 | -0.01 to 0.56 | yes | 1.000 | 3.4x |

Every sample except stratified picks Claude Opus's light dimension covering instead of the true best, and that pick is 1.4% slower than the best on the full database. The true best is inside every sample's top 3. Adding build time to the score raises tau a bit (page goes to 0.64) and does not change the pick, except stratified, which then also misses.

The intervals are wide. Thirty-three configurations is not many, and a tau of 0.5 with an interval from 0.26 to 0.72 is a weak ranking, not a settled one. The repeat below is the check on how much of that is noise.

Universe, FK closure and stratified keep the dimension tables in full, which is why they are only about 3x cheaper. Bernoulli and page shrink every table, and that is where the cost reduction actually is.

## Same samples, full-database statistics copied on

The statistics fingerprint on these two matches the full database. Q59 divides by zero on the universe sample under every configuration (33 times). The harness counts each of those as the 20 s cap, so it adds the same amount to every configuration and does not change that sample's ranking.

| Sample | tau (runtime) | 95% interval | top-1 | regret | top-3 | cheaper |
|---|---:|---|---|---:|---|---:|
| Bernoulli, own stats | 0.51 | 0.26 to 0.72 | no | 1.014 | yes | 43x |
| Bernoulli, full stats | 0.24 | 0.01 to 0.50 | no | 1.014 | no | 30x |
| Universe, own stats | 0.45 | 0.27 to 0.63 | no | 1.014 | yes | 2.6x |
| Universe, full stats | 0.30 | 0.03 to 0.52 | no | 1.078 | yes | 2.4x |

Copying the full statistics made both rankings worse. Bernoulli's tau falls from 0.51 to 0.24 and the true best leaves its top 3. Universe's regret goes from 1.4% to 7.8%: it picks Composer's aggressive covering set, which is slower on the full database than the light dimension covering the other samples pick. This is one seed. The intervals still overlap, so it is a direction, not a precise gap.

## Repeat of the full database

Same 33 configurations, same schema, same statistics fingerprint, run again the next morning. Log: `results/truth_sf1_rep.log`.

| | tau (runtime) | 95% interval | top-1 | regret |
|---|---:|---|---|---:|
| Second full run vs the first | 0.45 | 0.18 to 0.67 | yes | 1.000 |

The winner is the same both times: Grok's small dimension filters. Second place is the same too, Claude Opus's light dimension covering. Below that the order moves. Adding build time lifts tau to 0.59 and the winner still matches.

Every configuration was slower on the second run, by a median of 5.3 s (the winner went from 172.9 s to 177.3 s). That is a shift of the whole machine, not a reshuffle around a fixed mean, and it is a third of the 18 s gap between best and worst on the first run. A sample whose tau sits near 0.45 is matching this ceiling, not falling short of a stable ranking. Bernoulli at 0.51 and page at 0.46 are inside that interval. The samples that miss top-1 are missing a choice the full database itself repeats.

## Not done yet

Other sampling rates and seeds.
