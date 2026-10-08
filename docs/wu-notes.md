# Wu et al. (PACMMOD 2025), notes for the meet

**Paper:** Wentao Wu, Anshuman Dutt, Gaoxiang Xu, Vivek Narasayya, Surajit Chaudhuri. *Understanding and Detecting Query Performance Regression in Practical Index Tuning.* Proc. ACM Manag. Data 3(6), Dec 2025. DOI 10.1145/3769839. PDF: https://pages.cs.wisc.edu/~wentaowu/papers/sigmod26-qpr-detection.pdf

## Eight bullets

1. **How index tuners work.** They do not build every candidate index. They call a **what-if API**: the optimizer estimates plan cost *as if* those indexes existed (with fake stats). DTA / AutoAdmin on SQL Server; **HypoPG** on Postgres.

2. **The failure mode.** That estimated cost is often wrong (cardinality errors, bad cost model). Azure auto-indexing had to **revert ~11%** of created indexes because the query got slower, query performance regression (**QPR**).

3. **What-if ≠ runtime.** A configuration with lower optimizer cost can have **higher wall-clock time**. Ranking indexes by `EXPLAIN` cost can pick the wrong winner. That is why our ground truth is `CREATE INDEX` + `EXPLAIN ANALYZE`, not HypoPG alone.

4. **Why brute-force is expensive.** The accurate alternative is: materialize each candidate, run the workload, drop the index. Index build + execution on a large DB is what makes “just measure everything” infeasible at 100 GB. **Sampling is our bet that we can do that measurement on a small copy.**

5. **QPR is often a plan-shape change.** Their study: most serious regressions are a **small set of patterns**, especially a new **expensive nested-loop join** after the new index (optimizer thinks NLJ + index seek is cheap; it is not).

6. **ML detectors do not travel well.** Supervised models trained on one DB/workload fail on the next. They propose a **pattern-based** detector on before/after plans instead of a black-box regressor.

7. **Related: hybrid cost (Wu TKDE 2024).** Same bottleneck: little training telemetry because create/drop is costly. They ML-model only **leaf** operators (scan/seek) and keep optimizer costs for the rest. Different fix than sampling; same diagnosis.

8. **What we take for COL868.** (a) Never report HypoPG cost as “the better index.” (b) Compare **execution-time ranks** on full vs sample. (c) Watch for NLJ plan changes when a sample is too small or join-inconsistent.

## One paragraph if he asks “optimizer or runtime?”

HypoPG (and SQL Server what-if) only changes what the **planner** believes. Wu et al. show those beliefs miss real regressions. Our protocol: HypoPG to **propose** candidates; **real indexes** to **rank** them; the full-DB time winner is ground truth; we ask whether a 1% sample picks the same winner.
