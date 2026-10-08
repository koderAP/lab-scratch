# Literature and related systems

Papers and tools to read before the next meeting. Grouped by the role they play in *this* project, not by year.

## Core motivation (index tuning vs actual runtime)

These justify measuring **execution time**, not only optimizer cost.

1. **Wentao Wu, Anshuman Dutt, Gaoxiang Xu, Vivek Narasayya, Surajit Chaudhuri.** *Understanding and Detecting Query Performance Regression in Practical Index Tuning.* PACMMOD 3(6), SIGMOD issue, Dec 2025. DOI [10.1145/3769839](https://doi.org/10.1145/3769839). PDF: https://pages.cs.wisc.edu/~wentaowu/papers/sigmod26-qpr-detection.pdf  
   Index tuners use the optimizer what-if API. Cost estimates miss real regressions (often expensive nested-loop joins). Pattern-based QPR detector vs ML detectors. **This is the proposal’s cited paper.**

2. **Wentao Wu.** *Hybrid Cost Modeling for Reducing Query Performance Regression in Index Tuning.* IEEE TKDE 37(1), 2024. PDF: https://pages.cs.wisc.edu/~wentaowu/papers/tkde24-hybrid-cost-modeling.pdf  
   ML only on leaf operators (scan/seek), combine with optimizer costs for the rest. TPC-DS in the evaluation. Training data is expensive because indexes must be created/dropped, the same bottleneck our sampling idea attacks.

## Classical index advisors (what we are approximating)

3. **Chaudhuri & Narasayya.** *An Efficient Cost-Driven Index Selection Tool for Microsoft SQL Server.* VLDB 1997. Foundation of DTA.

4. **Chaudhuri & Narasayya.** *AutoAdmin “What-If” Index Analysis Utility.* SIGMOD 1998.

5. **Valentin et al.** *DB2 Advisor.* ICDE 2000.

6. **Schlosser, Kossmann, Boissier.** *Efficient Scalable Multi-attribute Index Selection (Extend).* ICDE 2019. Strong Postgres-era heuristic baseline.

## PostgreSQL what-if and advisors (SQL Server DTA equivalents)

7. **HypoPG**, hypothetical indexes visible to `EXPLAIN` in the current session. https://github.com/HypoPG/hypopg  
   Does **not** give true runtime. Required for cheap candidate ranking.

8. **Dexter** (ankane), workload → HypoPG candidate indexes. https://github.com/ankane/dexter

9. **pg_stat_statements**, workload capture (Query Store analogue).

## LLM index advisors (proposal methodology step 1)

10. **Zhou et al.** *LLMIdxAdvis: Resource-Efficient Index Advisor Utilizing Large Language Model.* arXiv:2503.07884. Experiments on PostgreSQL + HypoPG, TPC-DS/TPC-H. In-context learning, not full fine-tune.

11. **LLM4IA.** *Index Advising Via Large Language Models.* CIKM 2025 demo. DOI [10.1145/3746252.3761475](https://doi.org/10.1145/3746252.3761475). Iterative LLM selection vs Extend on TPC-H / TPC-DS.

12. **IdxL / Online Index Recommendation for Slow Queries.** ICDE 2024. Supervised index prediction when what-if is missing (MySQL). Useful contrast: we *do* have HypoPG.

For v0 of the harness, generate candidates with HypoPG/Dexter/hand-written indexes. Plug an LLM advisor in once runtime logging works.

## Sampling (proposal section 4)

### Random / SQL-standard

13. PostgreSQL `TABLESAMPLE`, `SYSTEM` (page-level, fast, clustered) vs `BERNOULLI` (row-level, slower, better IID). Extensions: `tsm_system_rows`, `tsm_system_time`.  
    Wiki: https://wiki.postgresql.org/wiki/TABLESAMPLE_Implementation

### Stratified / statistics-aware / workload-aware

14. **Chaudhuri, Das, Narasayya.** *Optimized Stratified Sampling for Approximate Query Processing.* TODS 2007 (STRAT). Workload-aware strata; robust to similar queries. Built on SQL Server.

15. **Chaudhuri, Das, Narasayya.** *A Robust, Optimization-Based Approach for Approximate Answering of Aggregate Queries.* SIGMOD 2001.

16. **Chaudhuri, Das, Datar, Motwani, Narasayya.** *Overcoming Limitations of Sampling for Aggregation Queries.* ICDE 2001. Rare groups / high variance.

17. **Babcock, Chaudhuri, Das.** *Dynamic Sample Selection for Approximate Query Processing.* SIGMOD 2003.

### Join-consistent sampling (mandatory for TPC-DS snowflake)

18. **Acharya, Gibbons, Poosala, Ramaswamy.** *Join Synopses for Approximate Query Answering.* SIGMOD 1999. Independent base-table samples break FK joins; precompute samples of distinguished joins. TPC-D / warehouse schemas, same issue as TPC-DS.

19. **Acharya et al.** *The Aqua Approximate Query Answering System.* SIGMOD 1999 demo.

If we sample `store_sales` at 1% independently of `date_dim` / `item`, many TPC-DS queries become empty or change plan shape. Ground-truth index ranking will not transfer.

### Planner statistics

20. PostgreSQL `ANALYZE`, `pg_stats` (MCV, histograms, correlation, n_distinct). A sample that does not preserve these will make the optimizer pick different indexes than the full DB even when data is “similar.”

## Benchmark

21. **TPC-DS**, 24 tables, 99 queries, official SF 1 / 10 / 100 / …  
    Generator on Mac: DuckDB `tpcds` extension (`CALL dsdgen(sf := 10)`), then `EXPORT DATABASE` + Postgres `COPY`.  
    DuckDB docs: https://duckdb.org/docs/current/core_extensions/tpcds  
    Loader pattern: https://github.com/duckdb/pg_duckdb/blob/main/scripts/load-tpcds.sh  
    Alternative: https://github.com/avamingli/pg_tpcds (in-Postgres dsdgen)

## Reading order for the next meeting (short)

1. Wu et al. PACMMOD 2025 (QPR), 26 pages; focus on what-if vs actual time.
2. Wu TKDE 2024 hybrid cost, why index create/drop is the expensive part.
3. Join synopses (SIGMOD 1999), why naive sampling fails on TPC-DS.
4. STRAT (TODS 2007), workload-aware strata.
5. HypoPG usage docs, what we can and cannot claim from `EXPLAIN`.
6. Skim LLMIdxAdvis + LLM4IA, candidate generation, not the first engineering task.
