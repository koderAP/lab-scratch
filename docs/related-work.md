# Related work and the novelty gap

Goal of this file: know every neighbour of "evaluate candidate indexes on a data sample, check the winner against the full DB", so the contribution is stated against real prior work and not against a strawman.

**Evidence level:** `R` = I read the full text (in `agent-tools/`), `S` = abstract / search snippet only. Anything marked `S` must be read before it is cited in a paper.
**Honest caveat:** this is a broad sweep (about 40 searches across index tuning, AQP, join sampling, cardinality estimation, test-data generation, tuning proxies). It is not a proof that nothing exists. Section 6 lists the residual-risk checks to run before claiming novelty.

---

## 1. Closest work: index evaluation by *executing* on something smaller or cloned

| Work | What it does | Sampling used | What it does **not** do | Ev. |
|---|---|---|---|---|
| **SQL:Trek** (Airbnb, PVLDB 2025; `vldb.org/pvldb/vol18/p5210-lightstone.pdf`) | External index designer. HypoPG-style what-if selects candidates, then **materializes them on a "simulation DB" and executes the workload** to prune false positives. | **Per-table uniform sample, 5 %, floor 20 K rows, cap 1 M rows** (same rate everywhere). Sweep 1/5/10/20/40 % on 32 DBs. | Compares **no sampling strategies**. Mostly OLTP/product workloads (+ 18 TPC-C-schema queries); no TPC-DS / multi-fact analytical joins. No join-consistency. Reports FP rate (3.2-3.8 %) and workload speedup, **not winner agreement, rank correlation or regret vs. full-DB ground truth per query**. Sample-size question left as future work item 7; "virtual statistics" (override sample stats with source stats) left as future work item 1. | R |
| **AIM** (Meta, ICDE 2023, Yadav/Valluri/Zait; arXiv 2605.31406) | Materializes candidates on a **full physical clone** before production. | None (full clone). | Cost of a full clone is exactly what we want to avoid. Gives us the "accurate but expensive" reference point. | R (snippets + text) |
| **Azure auto-indexing** (Das et al., SIGMOD 2019) | B-instances (full clone, forked workload) to validate; reverts ~11 % of indexes that regress. | None. | Validation is post-hoc on full data. | R |
| **Ding et al., "AI Meets AI"** (SIGMOD 2019) | ML classifier over two plans to predict which is cheaper, to stop cost-model regressions. | No data sampling; plan features. | Doesn't execute; needs training plans. | S |
| **Wu, Dutt, Xu, Narasayya, Chaudhuri** (QPR, PACMMOD/SIGMOD 2025-26) | Explains QPRs (mostly new expensive nested-loop joins under cardinality under-estimation) and a pattern detector. | None. | Our proposal's motivating paper. Shows why runtime, not cost, is the truth. | R |
| **Wu et al., ICDE 2013** (query time prediction) and **Wu/Naughton/Singh, SIGMOD 2016** (sampling-based re-optimization) | Use **samples to refine cardinalities** for a chosen plan, then calibrated cost model predicts time. Overhead: 5 % sample gives ~4 % overhead at 10 GB. | Sample used to *estimate cardinalities*, not to *run* the query. | Do not execute the workload on the sample; no index-choice agreement. Closest *method* cousin from the same group. | R |

**Read of the gap:** SQL:Trek proves the idea of "execute on a small simulated DB" is practical in industry. It does **not** answer the research question in `problem_statement.md`: *does the sample-selected winner equal the full-DB winner, and how does that depend on how the sample is built?*

## 2. Multi-fidelity / proxy evaluation in tuning (they cheapen evaluation differently)

| Work | Proxy for full evaluation | Relevance | Ev. |
|---|---|---|---|
| **MFIX** (ICDE 2024, Chang et al.) | Low fidelity = **what-if cost estimates**, high fidelity = real workload execution; Bayesian optimisation. | Same "cheap proxy then verify" logic; our sample is a *third fidelity level* between cost and full execution. Could be combined. | S |
| **MFTune** (PVLDB vol. 19, 2026; arXiv 2603.16450) | Spark SQL knob tuning; **states that generic proxies such as data-volume reduction show low Kendall-tau with full fidelity** and chooses query-subset fidelity instead. | **Direct counter-evidence to our hypothesis** (different problem: knobs on Spark, not indexes; but must be answered). | R (search) |
| **Hyperband / MFES-HB / BOHB** | Data subset or epochs as fidelity in AutoML. | Generic MFO theory: low fidelity must preserve ranking. | S |
| **DBA bandits** (ICDE 2021) | Learn benefit from **actual execution feedback** online, no optimizer. | Alternative to sampling: learn while running full data. Baseline family. | R (snippets) |
| **DISTILL** (VLDB 2022), **Budget-aware index tuning** (SIGMOD 2022), **AutoIndexer** (2025), **Beauty** (uncertainty) | Reduce *what-if calls* or prune candidate space. | Orthogonal: cheaper *candidate generation*, not cheaper *evaluation*. | R/S |

## 3. LLM index advisors (candidate source for the study)

- **LLMIdxAdvis / LLMIA** (arXiv 2503.07884, PostgreSQL + TPC-DS/JOB/TPC-H, HypoPG feedback, some actual executions), **MAAdvisor** (arXiv 2508.16044; zero-shot GPT-4o underperforms Extend by ~25 s on average; regressing indexes are the problem), **LLM4IA** (CIKM 2025 demo), **"Evaluating the Practical Effectiveness of LLM-Driven Index Tuning on Microsoft SQL Server"** (PVLDB 2026): LLMs sometimes beat DTA on execution time but have **high variance** and often worse optimizer cost. Ev.: S.
- **Implication:** LLM candidates are high-variance and can regress, which is the *motivation* for a cheap execution-based verifier. Nobody, to my search, verifies LLM candidates on a sample and compares to the full DB.

## 4. Sampling techniques (method sources; full taxonomy in `sampling-taxonomy.md`)

Join / multi-table: **Join Synopses** (Acharya et al. SIGMOD 1999, R), **Correlated sampling** (Vengerov et al. VLDB 2015, S), **Two-Level sampling** (Chen & Yi SIGMOD 2017, R), **Joins on Samples / SUBS** (Huang, Kandula et al., PVLDB 13, R), **Quickr** (Kandula et al. SIGMOD 2016; production experience PVLDB 12, R), **Wander Join** (Li et al. SIGMOD 2016, S), **Index-based join sampling** (Leis et al. CIDR 2017, S), **Bound Sketch** (Cai et al. SIGMOD 2019, S, sketch not sample).
Stratified / workload-aware: **STRAT** (Chaudhuri, Das, Narasayya TODS 2007), **BlinkDB / congressional** (Agarwal 2013, Acharya 2000), **Dynamic Sample Selection** (Babcock et al. 2003), **RL-STuner** (TKDE 2024) and **ASQP-RL / "Learning Approximation Sets"** (arXiv 2401.17059) for learned sample sets.
Statistics-side: **Random sampling for histograms** (Chaudhuri, Motwani, Narasayya SIGMOD 1998, R), **block-level sampling for statistics** (Chaudhuri, Das, Srivastava ICDE 2004, R), **bi-level Bernoulli** (Haas & König SIGMOD 2004, S).
These are all designed for *estimating answers or statistics*, not for *ranking physical designs by runtime*. The transfer is the open question.

## 5. Scaled-down or synthetic test databases (a competing route to "small but faithful")

**UpSizeR** (Tay et al. 2013), **Dscaler** (Zhang & Tay PVLDB 2016), **Touchstone** (Li et al. USENIX ATC 2018), **CODD** (Haritsa; transplants metadata/statistics to simulate a huge DB without data), **Singhal & Nambiar** (extrapolating SQL time to large volume, 2012/2016, and a 2017 tool), SQL Server `STATS_STREAM` / `DBCC OPTIMIZER_WHATIF`, industrial **referential subsetting** (Tonic, Neosync, Jailer) and PostgreSQL 18 statistics import. Ev.: S.
**Use for us:** (i) baselines/ablations ("synthetic downscale"), (ii) the **statistics-transplant** idea: keep sample data but give the optimizer full-DB statistics. SQL:Trek names this as future work; check that nobody publishes it first (see risk 2).

## 6. Optimizer behaviour context

**How Good Are Query Optimizers, Really?** (Leis et al. PVLDB 2015; VLDBJ 2018; PVLDB 2025 retrospective): cardinality errors dominate; more indexes make misestimation hurt more; table-sample-based single-table estimation works, join-crossing correlation does not. **Robustness metrics for plans** (Wolf et al., PVLDB 2018). **DSB** (Ding et al., PVLDB 2021): TPC-DS with skew/correlation and more plan diversity (7.9 vs 1.5 plans per template) → better stress test than plain TPC-DS. **Poess et al. VLDB 2007** on TPC-DS workload. Ev.: R/S.

---

## 7. Novelty statement (what we can defend)

> **The first systematic study of how the *design of the data sample* affects whether execution-based index evaluation ranks candidate indexes like the full database, on analytical multi-join workloads, measured by per-query winner agreement, rank correlation and regret against a real-index full-DB ground truth, with candidates that include LLM-generated indexes.**

Concrete deltas versus SQL:Trek (the main threat):
1. **Strategy comparison** (independent uniform vs. join-consistent vs. workload-aware vs. stats-aware), not one fixed 5 % recipe.
2. **Analytical, multi-fact TPC-DS (and DSB)** where independent sampling breaks joins. SQL:Trek's evidence is OLTP-shaped.
3. **Ground-truth-based agreement metrics** (winner, Kendall/Spearman, regret, sign accuracy) per query, not only workload-level speedup and FP rate.
4. **Size-vs-fidelity-vs-cost frontier**, including overhead accounting (SQL:Trek leaves minimal sample size open).
5. **Statistics treatment as a controlled factor** (sample-native stats vs. full-DB stats transplant).
6. **Candidate sources** (heuristic/HypoPG vs. LLM) and whether sample evaluation catches LLM regressions.

## 8. Threats to novelty and how to act on them

| # | Risk | Action |
|---|---|---|
| 1 | SQL:Trek authors publish a follow-up on sample-size / strategy. | Keep monitoring; our story must lead with strategy comparison + agreement metrics. |
| 2 | Someone publishes stats transplant for sample-based index evaluation. | Search "virtual statistics" / "statistics injection index tuning" again before writing; keep it one factor, not the headline. |
| 3 | MFTune-style finding (data reduction is a bad proxy) generalises to indexes. | Treat as a **hypothesis to test**, and report negative results honestly; join-consistent sampling is the specific fix we test. |
| 4 | Work in test-DB generation (Dscaler etc.) already shows performance-preserving downscaling. | Include a downscale baseline; cite. |
| 5 | Reviewers say "just use HypoPG". | Our Q72 data: cost is a poor predictor; QPR paper backs it. |

**Residual searches to run before submission:** Google Scholar / Semantic Scholar / DBLP for: "index tuning" AND "sample database"; "physical design" AND "sampling" AND "execution"; "what-if" AND "sampled data"; "downscaled database" AND "index"; "performance prediction across scale factors" ; "workload replay on subset"; citations of SQL:Trek, AIM, QPR paper (forward citation check); ICDE/VLDB/SIGMOD/CIDR 2025-2026 proceedings scan for "index" + "sample"; arXiv cs.DB last 12 months.
