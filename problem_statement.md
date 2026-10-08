Project Proposal: Sample-Based Index Evaluation for SQL Server 

Motivation 

Index tuning is a fundamental technique for improving SQL Server performance. Appropriate indexes can significantly reduce query execution time and resource consumption by enabling more efficient execution plans. 

Most index tuning approaches rely on optimizer cost estimates to rank candidate indexes. However, recent work by Wu et al. (SIGMOD 2025) shows that lower estimated costs do not always translate into lower execution times. In practice, the index configuration chosen by the optimizer may be slower than alternative configurations when executed on the actual database. 

A straightforward solution is to materialize every candidate index, execute the workload, and select the index yielding the best runtime. While accurate, this brute-force approach is prohibitively expensive for large databases and workloads. 

This project investigates whether the best execution-time index can be identified using only a sample of the database rather than the full dataset. 

Objective 

Determine whether index-selection decisions made on sampled databases match those obtained from full-database execution-time measurements, and identify the most effective sampling strategy for this purpose. 

Methodology 

1. Benchmark Setup 

Deploy the TPC-DS benchmark at 100 GB scale factor on SQL Server and use the standard workload of 100 analytical queries. 

2. Full Database Evaluation 

For each query: 

Generate candidate index recommendations using an LLM-based advisor. 

Materialize each candidate index. 

Measure both optimizer-estimated cost and actual execution time. 

Identify the execution-time-optimal index on the full database. 

This serves as the ground truth. 

3. Sample-Based Evaluation 

Create database samples at 1%, 5%, and 10% scales. 

For each sample: 

Evaluate the same candidate indexes. 

Measure execution times. 

Determine the optimal index. 

Compare the selected index against the full-database optimum. 

4. Sampling Strategy Study 

Evaluate multiple sampling techniques, including random, stratified, statistics-aware, and workload-aware sampling. 

Measure: 

Agreement with full-database index choices 

Ranking correlation among index candidates 

Sampling overhead 

Expected Outcome 

The project will determine whether small database samples can reliably identify the execution-time-optimal index configuration for SQL Server workloads. If successful, it can substantially reduce the cost of evaluating large numbers of candidate indexes while preserving recommendation quality. 

Reference 

Wu et al. Understanding and Detecting Query Performance Regression in Practical Index Tuning: Experiments & Analysis. Proc. ACM Management of Data (SIGMOD 2025). 

 