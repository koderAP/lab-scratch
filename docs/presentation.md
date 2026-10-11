# Presentation guide: sample-based index evaluation

Built from `problem_statement.md`, `docs/protocol.md`, `docs/results.md`, `docs/lab-notes.md` and `results/rank_sf1_p5.md`. Ordered as slides. Assumes the audience knows nothing about databases.

---

## Slide 1: The problem

**What is an index?** A database index is like a book's index. Without one, the database scans the whole table to find rows. With one, it jumps to them directly. The right indexes can make a query 100x faster. Too many indexes waste space and slow down writes.

**Index tuning** means choosing which indexes to build for a given set of queries (the "workload").

**How tuning is normally done:**
- The database's optimizer estimates a *cost* for each query under each candidate index. This is the "what-if" approach, for example HypoPG in PostgreSQL.
- It then picks the index with the lowest estimated cost.

**The catch** is that estimated cost is not real runtime. Wu et al. (SIGMOD 2025), the paper our proposal is based on, show that the index with the lowest estimated cost is often slower when you actually run it.

**The obvious fix is too expensive.** You could build every candidate index and run the workload for real. On a 100 GB database that takes days.

---

## Slide 2: The project idea

> **Can we run the real-execution test on a small sample of the database, and still pick the same best index set as we would on the full database?**

If yes, we get real runtimes (more trustworthy than cost estimates) at a fraction of the cost.

Two questions:
1. Does a sample pick the same winner as the full database?
2. Which way of sampling works best? (random, stratified, join-aware, statistics-aware, and so on)

---

## Slide 3: How the experiment works

Terms:
- **D** is the full database. **D'** is the reduced (sampled) database.
- **Configuration** is a *set* of indexes for the whole workload.
- **Workload** is the 99 TPC-DS queries. TPC-DS is the standard analytical benchmark (retail sales, many large joins).

Steps (diagrams in `protocol.html`):
1. **Generate candidate configurations.** Six LLMs (Claude Opus 5, Claude Fable 5.1, GPT 5.6 Sol, Gemini 3.8 Flash, Grok 4.7, Composer 2.5) each propose 5 configurations. They see only the schema and the query text, with no database access. Two baselines are added: no extra index, and HypoPG's greedy picks (top-5 and top-8). After de-duplication that gives **33 configurations**.
2. **Ground truth.** For each configuration, build its indexes (timed), run all 99 queries, sum the runtimes. Rank the 33 configurations. This is the "truth" ranking.
3. **Build samples D'.** 5% samples of the SF=1 database, with several methods (next slide).
4. **Repeat step 2 on each sample.** Same configurations, same queries, same measurement rules.
5. **Compare the sample's ranking with the truth ranking.**

**Metrics:**
- **Kendall tau**: rank correlation. 1 means identical order, 0 means unrelated.
- **Top-1 match**: did the sample pick the true best configuration?
- **Regret**: if it picked wrong, how much slower is its pick than the true best on the full DB? (1.014 means 1.4% slower.)
- **Top-3 hit**: is the true best in the sample's top 3?
- **Cost reduction**: (build time + runtime on D) divided by (the same on D'). This is the payoff.

**Two scores are used:** A is total workload runtime (primary). B is index build time plus runtime (secondary).

**Measurement rules:** `ANALYZE` once and frozen, autovacuum off, one discarded warm-up run, then the median of one or two timed runs, 20 s cap per query (a capped query counts as 20 s), one configuration at a time (create indexes, run 99 queries, drop them).

---

## Slide 4: The sampling methods

| Sampler | Idea | Why try it |
|---|---|---|
| **Bernoulli (B0)** | Keep each row independently with probability 5%, in every table | Simple baseline. This is the SQL:Trek paper's recipe. |
| **Page (sys)** | Keep random disk pages | Cheapest to build. Rows are clustered. |
| **Universe (uitem)** | Keep a row only if `hash(item_key)` falls under a threshold, in all tables that join on item. Dimension tables are kept in full | Joins stay consistent, so sampled rows still find their partners. |
| **FK closure** | Sample the big fact table, then pull in every dimension row it references | Same reason: joins don't break. |
| **Stratified** | Sample within groups (date, frequent items) so rare values survive | Protects skewed data. |
| **Stats transplant (C4)** | Take any sample but copy the *full* database's optimizer statistics onto it | Planner behaves as if the data were full size. A possible fix for plan differences. |

**Why independent sampling is risky:** if you sample `store_sales` and `item` independently at 5%, a join between them keeps only about 0.25% of the matches. Join-aware samplers were designed to avoid this.

Not done yet: the workload-aware sampler. The full catalogue is in `docs/sampling-taxonomy.md`.

---

## Slide 5: What we expected

- Sampling would work well enough to be useful, which is the proposal's hoped-for outcome.
- **Join-aware samplers (universe, FK closure) would beat plain random sampling**, because TPC-DS is join-heavy.
- **Copying full statistics (C4) would improve fidelity**, since the planner would choose the same plans as on the full DB.
- Bigger samples would be better. Only 5% has been run so far.

---

## Slide 6: What we found

### Ground truth on the full database (SF=1)
- No extra index: **190.7 s** for the workload.
- Best configuration (Grok's small dimension filters): **172.9 s**, so only about 9% better.
- **Seven queries hit the 20 s cap under every configuration.** That is 140 s that no index can change. The indexes only compete over about 50 s.
- So the differences between configurations are small, and a ranking of 33 near-ties is hard to reproduce even on the same database.

### Noise ceiling: the full database compared with itself
The full database was run twice. The two runs agree only at **tau = 0.45** (95% CI 0.18 to 0.67). The winner was the same both times, and so was second place. The whole machine was about 5.3 s slower on the second run (median), roughly a third of the 18 s best-to-worst gap.

**This matters for interpretation: tau around 0.45 is about the best any sample can realistically score.**

### Samples (5%, one seed, own statistics)

| Sample | tau | 95% CI | Top-1 | Regret | Cheaper than full |
|---|---:|---|---|---:|---:|
| Bernoulli | 0.51 | 0.26 to 0.72 | no | 1.4% | 43x (25x incl. build) |
| Page | 0.46 | 0.20 to 0.69 | no | 1.4% | 90x (33x) |
| Universe | 0.45 | 0.27 to 0.63 | no | 1.4% | 2.6x |
| FK closure | 0.42 | 0.17 to 0.62 | no | 1.4% | 3.5x |
| Stratified | 0.28 | -0.01 to 0.56 | yes | 0% | 3.4x |

- **Four of five samples pick the same configuration:** Claude Opus's light dimension covering. It is **only 1.4% slower** than the true best, and the true best is in every sample's top 3. In practice a near-miss, not a failure.
- The cheap samplers (Bernoulli, page) shrink every table, so they give 43x to 90x savings. The join-aware samplers keep dimension tables whole, so they only save about 3x.
- Stratified "wins" top-1 but has the lowest tau and its interval spans 0, so it is probably luck. With build time added to the score it also misses.
- Adding build time to the score raises tau a little (page goes to 0.64) and doesn't change the picks.

### Statistics transplant

| | tau | Top-3 | Regret |
|---|---:|---|---:|
| Bernoulli, own stats | 0.51 | yes | 1.4% |
| Bernoulli, full stats | 0.24 | no | 1.4% |
| Universe, own stats | 0.45 | yes | 1.4% |
| Universe, full stats | 0.30 | yes | 7.8% |

**Copying statistics made things worse**, the opposite of what we expected. Universe with full stats picks Composer's aggressive covering set, which is slower on the full DB. One possible reason (a hypothesis, not established): the statistics describe a full-size table while the physical indexes are small, so the planner gets inconsistent inputs. One seed, and the intervals overlap, so this is a direction, not a precise gap.

Side note: Q59 divides by zero on the universe sample under every configuration. The harness counts it as the 20 s cap, adding the same amount to every configuration, so the ranking is unaffected.

---

## Slide 7: Expected vs. actual

| Expectation | Result |
|---|---|
| Samples can find a near-best index set | **Partly yes.** The pick is within 1.4% of the best and the true best is in the top 3. It is not an exact match. |
| Join-aware samplers beat random | **No.** They are no better, and save far less (about 3x vs. 43x or more). |
| Full statistics help | **No.** Both samples got worse. |
| Samples rank like the full DB | **Roughly, to within noise.** The full DB only reaches tau 0.45 against itself. |

---

## Slide 8: Honest caveats

- **Deviation from the proposal.** The proposal says SQL Server at 100 GB. We used **PostgreSQL 14 at SF=1 (about 1 GB)** on a 16 GB laptop. Queries at SF=10 ran for hours.
- **20 s cap per query.** Capped queries understate the benefit of any index that fixes them.
- **One seed, one sampling rate (5%).** The proposal also asks for 1% and 10%. Not done yet.
- **Wide confidence intervals** with only 33 configurations. Treat the differences as directions.
- **The whole database fits in memory at SF=1**, unlike a real 100 GB deployment.
- **Methodology corrections along the way.**
  - An early Q72 result was **retracted** after problems with cache state, statistics and timeouts were found. Those became the measurement rules above.
  - An early per-query design (rank single indexes per query on an index-sensitive subset) was too noisy: single-query winners flipped between identical runs. The protocol was redone on 5 Oct to rank whole configurations by workload total.
  - One Gemini run was **excluded** because the model had read earlier result files. The clean rerun is used.

---

## Slide 9: Takeaways and next steps

**Takeaway:** a cheap 5% sample of a small database gets within about 1.4% of the best index configuration at 25x to 90x lower cost. Join-aware sampling and statistics copying did not help at this scale. The result is limited by noise and by how little the configurations differ, not only by the samples.

**Next:**
- More seeds, and 1% and 10% samples.
- A larger scale (SF=10 or more), where queries take seconds and the data doesn't fit in memory.
- The workload-aware sampler.
- Port to SQL Server, as the proposal specifies.

---

## Likely questions

- **Why not just trust the optimizer's cost?** Wu et al. showed it often picks slower indexes.
- **Why sum total runtime rather than per-query winners?** Per-query winners were too noisy (see caveats). A sum over 99 queries averages out per-query noise.
- **Is 1.4% regret good?** It is small, but the best-to-worst spread on the full DB is only 9%. Read regret relative to that spread.
- **Why did the stats transplant hurt?** Not established. The statistics-vs-index-size mismatch is a hypothesis.
- **Closest prior work?** SQL:Trek (PVLDB 2025), which uses 5% Bernoulli samples for index evaluation. See `docs/related-work.md`. Our additions: a comparison of sampling strategies, analytical multi-join workloads, ground-truth agreement metrics, and statistics as a controlled factor.

---

## Where to find things

| What | File |
|---|---|
| The assigned project | `problem_statement.md` |
| Experiment spec and design choices | `docs/protocol.md` |
| Numbers and tables | `docs/results.md`, `results/rank_sf1_p5.md` |
| Why the measurement rules exist | `docs/lab-notes.md` |
| Related work | `docs/related-work.md`, `docs/literature.md` |
| Sampler catalogue | `docs/sampling-taxonomy.md` |
| Figures for the talk | `results.html`, `protocol.html` |

---

## Appendix: the Wu et al. paper and why it motivates this project

**Paper:** Wu, Dutt, Xu, Narasayya, Chaudhuri (Microsoft Research). *Understanding and Detecting Query Performance Regression in Practical Index Tuning.* Proc. ACM Manag. Data 3(6), SIGMOD, December 2025. PDF: `papers/01-wu-qpr-sigmod2025.pdf`. Notes: `docs/wu-notes.md`.

### What it contributes

- Index tuners use the optimizer's *what-if API* (HypoPG on PostgreSQL) to estimate cost as if indexes existed. Those estimates can be wrong (cardinality errors), so a recommended index can make a query much slower once built. This is **query performance regression (QPR)**.
- It is a real operational problem: about **11% of indexes** created by Azure SQL Database auto-indexing had to be reverted because of QPR.
- They collected **1.2 million before/after plan pairs** across benchmarks and real workloads, in three tuning scenarios (one-shot, incremental, evolutionary).
- Most serious QPRs come from **a small set of plan-change patterns**. The most common is a new, expensive **nested-loop join** after the index is added, caused by cardinality underestimation. Others: a lost aggregation pushdown, a lost bitmap filter.
- They propose a **pattern-based QPR detector** on before/after plans. It beats ML-based detectors, which generalize poorly to new databases and workloads.

### How it motivates our work

1. Cost estimates do not reliably predict runtime, so we rank by **measured runtime**. HypoPG only proposes candidates; real indexes rank them.
2. Measuring every candidate on the full database is too expensive (index build plus execution at 100 GB). The paper's remedy is to detect regressions from plans without running anything.
3. Our remedy is different: make real measurement cheap by running it on a **sample**, and test whether the sample ranks configurations like the full database.
4. The paper's finding that regressions are plan-shape changes tells us the risk for sampling: samples can change plan shapes. Our pilot saw different plan skeletons on the sample in most query-index pairs (143 of 151 on Bernoulli).

### Likely questions

- *Does the paper use sampling?* No. We borrow its diagnosis and propose a different remedy.
- *Why not use their detector?* It predicts regression per query from plan pairs and gives no ranking of whole configurations. It is complementary and could filter bad candidates before measurement.
- *Is the 11% figure yours?* No, it is Azure's, cited in the paper.
- *Do your results contradict it?* No. We took its result as given and ranked by runtime.
- *Citation:* the proposal says SIGMOD 2025; the PDF is dated December 2025 (volume 3, issue 6).
