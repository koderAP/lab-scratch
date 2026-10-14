# Distillation proxies on the existing SF=1 run

Full database: 33 configurations, 99 queries.
Always at the 20 s cap under every configuration: 6 queries (Q1, Q4, Q11, Q74, Q81, Q95). That is 140 s of every total.
Queries whose time moves by at least 200 ms across configurations: 25. Combined range 24.6 s.
Queries that never move: 68.

Winner grok-4-7:small-dimension-filters: 172.9 s vs no-index 190.7 s (saved 17.7 s).
Queries that save at least 200 ms for the winner, largest first:

| query | saved on full (s) |
|---|---:|
| Q6 | 10.01 |
| Q14 | 3.27 |
| Q39 | 0.97 |
| Q22 | 0.90 |
| Q23 | 0.52 |
| Q38 | 0.25 |
| Q41 | 0.22 |
| Q31 | 0.21 |
| Q35 | -0.29 |

## Do cheap proxies track the ranking?

Plan agreement uses the stored `plan_hash` from the timed runs (same index names, so hashes are comparable). Sign agreement is the sign of (config time minus no-index time) per query. Movable tau uses only the queries that move on the full database.

| D' | tau (all 99) | tau (movable) | plan agree | sign agree | timeout agree | pick (all) | pick (movable) |
|---|---:|---:|---:|---:|---:|---|---|
| full repeat | 0.45 | 0.48 | 100% (2946) | 62% (2946) | 100% | grok-4-7:small-dimension-filters | grok-4-7:small-dimension-filters |
| Bernoulli 5% | 0.51 | 0.53 | 8% (2946) | 55% (2946) | 93% | claude-opus-5:light_dimension_covering | claude-opus-5:light_dimension_covering |
| Page 5% | 0.46 | 0.47 | 9% (2946) | 54% (2946) | 93% | claude-opus-5:light_dimension_covering | claude-opus-5:light_dimension_covering |
| Universe 5% | 0.45 | 0.42 | 11% (2914) | 57% (2914) | 94% | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| FK 5% | 0.42 | 0.25 | 13% (2946) | 52% (2946) | 95% | claude-opus-5:light_dimension_covering | claude-opus-5:light_dimension_covering |
| Stratified 5% | 0.28 | 0.19 | 10% (2946) | 54% (2946) | 95% | grok-4-7:small-dimension-filters | grok-4-7:small-dimension-filters |
| Bernoulli + full stats | 0.24 | 0.23 | 8% (2946) | 44% (2946) | 93% | claude-opus-5:light_dimension_covering | claude-opus-5:light_dimension_covering |
| Universe + full stats | 0.30 | 0.29 | 13% (2914) | 61% (2914) | 94% | composer-2-5:aggressive-mixed-covering | grok-4-7:small-dimension-filters |

Full-repeat row is the noise ceiling: same database, next morning.

## Why every cheap sample misses top-1

True best is `grok-4-7:small-dimension-filters`. Every native sample except stratified picks `claude-opus-5:light_dimension_covering` (1.4% slower on the full database). Queries where the full database prefers Grok by ≥200 ms but the sample disagrees:

**full repeat.** Full: Grok is 2.43 s faster. Sample: Grok is 7.52 s faster (negative means Grok loses). Flipped queries (0):

none.

**Bernoulli 5%.** Full: Grok is 2.43 s faster. Sample: Grok is -0.01 s faster (negative means Grok loses). Flipped queries (1):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q57 | -0.24 | 0.02 |

**Page 5%.** Full: Grok is 2.43 s faster. Sample: Grok is -0.02 s faster (negative means Grok loses). Flipped queries (2):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q22 | -1.04 | 0.00 |
| Q57 | -0.24 | 0.00 |

**Universe 5%.** Full: Grok is 2.43 s faster. Sample: Grok is -0.07 s faster (negative means Grok loses). Flipped queries (2):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q22 | -1.04 | 0.00 |
| Q57 | -0.24 | 0.00 |

**FK 5%.** Full: Grok is 2.43 s faster. Sample: Grok is -0.07 s faster (negative means Grok loses). Flipped queries (1):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q22 | -1.04 | 0.00 |

**Stratified 5%.** Full: Grok is 2.43 s faster. Sample: Grok is 0.01 s faster (negative means Grok loses). Flipped queries (1):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q22 | -1.04 | 0.00 |

**Bernoulli + full stats.** Full: Grok is 2.43 s faster. Sample: Grok is -2.48 s faster (negative means Grok loses). Flipped queries (2):

| query | full Grok−Opus (s) | sample Grok−Opus (s) |
|---|---:|---:|
| Q22 | -1.04 | 0.06 |
| Q57 | -0.24 | 0.01 |

**Universe + full stats.** Full: Grok is 2.43 s faster. Sample: Grok is 4.80 s faster (negative means Grok loses). Flipped queries (0):

none.

## Where Bernoulli agrees, query by query

Kendall tau of the 33 configuration times, per query, for queries that move on the full database (25 queries). Lowest agreement first.

| query | tau vs Bernoulli | full range (s) |
|---|---:|---:|
| Q57 | -0.26 | 0.28 |
| Q69 | -0.12 | 0.32 |
| Q47 | -0.05 | 0.28 |
| Q7 | -0.04 | 0.22 |
| Q51 | -0.02 | 0.20 |
| Q39 | 0.02 | 0.97 |
| Q23 | 0.03 | 0.93 |
| Q52 | 0.05 | 0.21 |
| Q36 | 0.06 | 0.32 |
| Q22 | 0.06 | 1.04 |
| Q31 | 0.12 | 0.23 |
| Q30 | 0.12 | 0.22 |
| Q67 | 0.17 | 0.28 |
| Q38 | 0.19 | 0.50 |
| Q89 | 0.23 | 0.31 |
| Q41 | 0.25 | 0.24 |
| Q27 | 0.25 | 0.37 |
| Q35 | 0.28 | 0.48 |
| Q16 | 0.33 | 1.25 |
| Q6 | 0.35 | 10.01 |
| Q14 | 0.35 | 3.37 |
| Q9 | 0.38 | 1.03 |
| Q87 | 0.41 | 0.43 |
| Q88 | 0.44 | 0.75 |
| Q5 | 0.47 | 0.35 |

