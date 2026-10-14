# Database distillation for index evaluation

Draft, 12 October 2026. Numbers are from the existing SF=1 5% run plus a HypoPG EXPLAIN pass on the same schemas (no new timings, no `ANALYZE`).

## 1. Claim

A distilled database D* is a small, runnable copy of D that **ranks index configurations by measured time the way D does**. A sample is one candidate for D*. Distillation means building D* so that the things the ranking actually depends on survive, instead of hoping a random 5% keeps them.

## 2. What the ranking on this dataset actually is

33 configurations, 99 TPC-DS queries, 20 s cap.

| Piece | Size | What it means for D* |
|---|---|---|
| Always 20 s, every config | Q1, Q4, Q11, Q74, Q81, Q95 (120 s of every total) | Indexes never touch this. Ignore it. |
| Never moves (≥200 ms) | 68 queries | Noise. Matching these cannot help. |
| Moves | 25 queries, combined range 24.6 s | This is the whole ranking. |
| Winner vs no-index | 172.9 s vs 190.7 s (saves 17.7 s) | Almost all of that is Q6 (10.0 s) and Q14 (3.3 s). |
| Winner vs second | Grok small-dimension-filters vs Opus light covering, 2.4 s | This is the only top-1 question. On the next-morning repeat the same pair still wins, but the gap is 7.5 s and Q22's share of it falls from 1.04 s to 0.26 s. |

The full database only agrees with itself at tau 0.45. Any D* whose tau sits near 0.45 is hitting the ceiling of this testbed, not proving a method.

## 3. Experiments on the current data

### 3.1 Cheap proxies from the stored timings

Plan hash is stored per (config, query) from the timed runs. Benefit sign is sign(config time minus no-index time) per query.

| D' | tau (99 q) | tau (25 movable) | plan hash agree | sign agree (movable) | top-1 |
|---|---:|---:|---:|---:|---|
| Full, next morning | 0.45 | 0.48 | 100% | 66% | Grok (correct) |
| Bernoulli 5% | 0.51 | 0.53 | 8% | 60% | Opus |
| Page 5% | 0.46 | 0.47 | 9% | 54% | Opus |
| Universe 5% | 0.45 | 0.42 | 11% | 66% | Opus |
| FK 5% | 0.42 | 0.25 | 13% | 53% | Opus |
| Stratified 5% | 0.28 | 0.19 | 10% | 54% | Grok |
| Bernoulli + full stats | 0.24 | 0.23 | 8% | 42% | Opus |
| Universe + full stats | 0.30 | 0.29 | 13% | 62% | Composer |

**Plan agreement does not track tau.** Every sample is 8 to 13%. The repeat is 100%. Bernoulli (best tau) is the worst plan match. Copying full statistics made sign agreement worse, which matches the tau drop.

Restricting to the 25 queries that move does not raise tau. FK and stratified get worse. The disagreement is in the queries that matter, not in the 68 that do not.

### 3.2 HypoPG EXPLAIN on the live schemas

Hypothetical indexes, `EXPLAIN` only, 33 configs × 99 queries × 6 schemas. Plan shape drops HypoPG's generated index names. Cost is the optimizer's Total Cost.

| Comparison | Result |
|---|---|
| Full-DB **cost ranking vs time ranking** | tau **0.43**. Cost pick is GPT `customer_windows` (188.1 s). Time pick is Grok (172.9 s). |
| Sample **cost ranking vs full-DB cost ranking** | tau **0.81 to 0.91**. Page 0.91, Bernoulli 0.84. |
| Sample cost ranking vs full-DB time ranking | tau 0.45 to 0.50, i.e. the same as a second timing run. |
| Plan-shape agreement vs full | 8 to 12% (same as the stored hashes). |
| Cost-sign agreement (does the index lower cost?) | 83 to 86%. |

The samples already recover how the optimizer ranks the configurations. The optimizer does not rank them by time. Matching plans or costs harder cannot fix the time ranking on this set.

### 3.3 Q22, the query that decides top-1

Q22 is inventory × date_dim × item, filter `d_month_seq BETWEEN 1200 AND 1211`.

On the full database Grok and Opus get the **same plan**: hash join, seq scan of inventory, index-only scan of date_dim. Optimizer cost drops 2% for both (139924 to 137316). Measured times on run 1: none 2.35 s, Grok 1.45 s, Opus 2.49 s. On run 2: 2.22 / 1.72 / 1.98. The 1 s Grok-Opus gap is not a plan difference and is not stable.

On every 5% sample the plan changes (hash join of item becomes a nested loop) because inventory shrank, and the whole query is 50 to 100 ms. A 1 s effect cannot appear. Grok minus Opus is 0.00 s on every native sample.

A one-off `EXPLAIN ANALYZE` of Q22 showed the inventory seq scan (2.3 M rows × 5 loops) dominating, and its time moving with cache warmth across consecutive runs. That is execution and cache, not a missing row in the sample.

### 3.4 Q6, the 10 s effect both winners already have

Q6 is the date-dimension filter that Grok and Opus both cover.

| D' | no-index | Grok | saved | notes |
|---|---:|---:|---:|---|
| Full | 20.0 s (cap) | 10.0 s | 10.0 s | real effect |
| Bernoulli | 0.19 s | 0.05 s | 0.14 s | sign kept, ~70× smaller |
| Page | 0.003 s | 0.003 s | 0 | predicate rows gone |
| FK / universe / stratified (dims kept) | ~2.2 s | ~0.52 s | ~1.7 s | sign kept, ~6× smaller |

Page sampling drops the year/month Q6 needs, so every configuration looks the same. Bernoulli keeps the sign and loses the magnitude. Keeping dimensions whole (the join-aware samples) keeps more of the magnitude, which is why they are only 3× cheaper: they did not shrink date_dim.

## 4. Related work, and the gap

| Family | Small D*? | Runnable SQL? | What it preserves | Ranking of physical designs? |
|---|---|---|---|---|
| SQL:Trek | 5% sample | yes | enough to prune false-positive indexes | not checked against a full ranking |
| CODD, DTA shell | no data | plans only | optimizer behaviour | cost only |
| QAGen, Hydra, Mirage, SAM | usually same scale | yes | operator cardinalities | no |
| UpSizeR, Dscaler | yes | yes | key correlations | no |
| Gupta et al. 2011, PrivBench | any | yes | privacy plus fidelity | named, not measured |
| T2G "Relational Database Distillation" | yes | no (graph) | ML accuracy | no |

Nobody found so far builds a small database **to preserve a measured runtime ranking of index configurations**. The name is already used for an ML graph paper. Re-check Haritsa's group and the DTA test-server papers before claiming the gap in writing.

Dataset distillation's useful lesson is the cheap proxy (gradient matching instead of full training). The proxies we can actually run here are plan agreement and cost agreement. **On this dataset they are the wrong proxies** (section 3.2).

## 5. What this means at SF=1

1. **Do not distill for plan or cost match on this set.** Samples already match the full-DB cost ranking at tau 0.8 to 0.9. That ranking has tau 0.43 against time, the same as overnight noise.
2. **Sampling compresses the few real effects below the noise.** Q6's 10 s win becomes 0.14 s (Bernoulli) or 0 s (page). Q22's unstable 1 s win becomes 0 s because inventory shrank.
3. **Fitting a D* to the 33-config SF=1 ranking is overfitting.** The target is 2.4 s wide and a second full run moves totals by 5.3 s. A method that "wins" here can be fitting machine jitter.

## 6. Why larger data is the right test

The SF=10 screen already shows a different target. Warm, one HypoPG index per query, 23 queries move by at least 1.3x. Effects are tens of seconds to minutes, not 200 ms: Q27 27 s to 0.2 s (176x, 449k page reads to 0), Q21 15 s to 0.5 s (32x), Q23 68 min to 5.5 min (12x, both sides millions of pages). About half the set gets **slower** with the index (Q25 3.8x, Q29 3.5x), and those regressions still read hundreds of thousands of pages, so they are not a cache artifact. Q6 and Q14, which were a 10 s / 3 s fight under a 20 s cap at SF=1, did not finish in 5 minutes with no index.

That ranking has a signal-to-noise ratio this SF=1 33-config set does not. Distillation is worth doing against *that*, not against Grok vs Opus by 2.4 s.

A naive 5% sample of the larger database does **not** automatically inherit that signal. On this machine:

| Copy | On-disk size | Fits in `shared_buffers` (2 GB) / 16 GB RAM? |
|---|---|---|
| SF=1 full | 3.6 GB | yes, cache-resident. Why Q22 is cache noise. |
| SF=10 full | 35 GB (inventory 12 GB, `store_sales` 6.5 GB) | no. Index benefit is avoiding 400k to 3M page reads. |
| SF=10 universe 5% | 1.5 GB | **yes**. Same regime as SF=1. |
| SF=10 universe 1% | 0.5 GB | yes. |

So a 5% sample of SF=10 recreates the SF=1 failure: D does not fit in memory, D' does. The 176x Q27 win is "do not seq-scan the fact table." On a 1.5 GB sample that scan is already in cache, so the index looks useless or looks like a tiny CPU win. Scaling the data without scaling the memory knobs is how sampling overfits to in-memory behaviour even more at large scale.

That is the actual distillation job at large D:

- **Keep the I/O.** Either do not shrink the fact table the index is saving scans on, or scale `shared_buffers`, `effective_cache_size`, `work_mem`, and the parallel-scan thresholds with the sample rate so D' still spills and still misses cache the way D does.
- **Keep both signs.** A D' that only preserves speedups will miss Q25/Q29-style regressions, which are the dangerous mistakes for index selection.
- **Keep predicate rows.** Page sampling already zeroed Q6 at SF=1. At SF=10 the same miss costs minutes, not 10 s.

Plan agreement may start to matter here, because at SF=10 an index that changes the plan also changes hundreds of thousands of page reads. At SF=1 it often does not. The HypoPG finding that "cost ranking is recovered and time is not" is an SF=1 result. It should be re-measured at SF=10 before being treated as a method conclusion.

On a bigger machine, start at `docs/server.md`. Do not rerun the SF=1 33-config protocol. The first server experiment is the 23-query SF=10 study set, written there as section 7.

## 7. Next experiment

Not another SF=1 contrast ranking, and not 33 configs × 99 queries at SF=10 (that does not finish on this laptop).

Use the 23-query SF=10 study set, two configurations (no extra index, and the screen's one HypoPG index per query), on three copies that already exist: `tpcds_sf10`, `tpcds_sf10_u5` (5%, 1.5 GB), `tpcds_sf10_u1` (1%, 0.5 GB).

| Check | What "better at large scale" looks like |
|---|---|
| Sign on the 23 queries | D' gets speedup vs regression the same way D does, including the slower-with-index rows |
| Page reads | D' still shows a large `shared_read` drop on the speedups. If reads go to 0 on both sides, D' has gone cache-resident |
| Same copies, knobs × 0.05 | `shared_buffers` / `effective_cache_size` / scan thresholds scaled with the sample. If sign and read-drop agreement jump, the missing piece was the environment, not the rows |

Success is not tau on 33 near-tie configs. It is: a 1.5 GB D' that still sees Q27 as a large I/O win and Q25 as a regression. If the scaled-knob copy does that and the native-knob sample does not, distillation at large D is mostly **environment scaling**, which is cheap. If neither does, the rows themselves have to be chosen (predicate witnesses, keep the scanned fact pages), which is the slower path.

## Files for this note

- Stored-timing proxies: `scripts/distill_proxies.py`, `results/distill_proxies.md`
- HypoPG pass: `scripts/explain_configs.py`, `scripts/compare_explain.py`, `results/explain_tpcds_sf1*.jsonl`, `results/distill_explain.md`
