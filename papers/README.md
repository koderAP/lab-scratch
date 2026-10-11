# Papers

Local PDFs for the work this project sits on. Fetch again with `python3 papers/fetch.py` (skips files that are already PDFs). They are gitignored.

Open copies only: author pages, PVLDB, arXiv, USENIX, JMLR, course copies. ACM / IEEE / some Microsoft Research URLs 403 or 404 from this machine.

## Downloaded

| File | Paper | Role |
|---|---|---|
| `01-wu-qpr-sigmod2025.pdf` | Wu et al. QPR. PACMMOD/SIGMOD 2025 | Proposal's cited paper. Cost is not runtime. |
| `02-wu-hybrid-cost-tkde2024.pdf` | Wu. Hybrid cost. TKDE 2024 | Index create/drop is the expensive part. |
| `03-wu-sampling-reopt-sigmod2016.pdf` | Wu, Naughton, Singh. SIGMOD 2016 | Sample used to fix cardinalities, not to run the workload. |
| `04-wu-time-prediction-icde2013.pdf` | Wu et al. ICDE 2013 | Time prediction from a calibrated cost model. |
| `05-sql-trek-pvldb2025.pdf` | Lightstone, Wang. SQL:Trek. PVLDB 2025 | Closest system: execute indexes on a 5% uniform sample. |
| `06-llminxadvis-arxiv2503.07884.pdf` | Zhou et al. LLMIdxAdvis | LLM advisor on PostgreSQL + HypoPG. |
| `07-maadvisor-arxiv2508.16044.pdf` | MAAdvisor | LLM candidates have high variance. |
| `08-join-synopses-sigmod1999.pdf` | Acharya et al. SIGMOD 1999 | Independent samples break FK joins. |
| `09-strat-tods2007.pdf` | Chaudhuri, Das, Narasayya. STRAT. TODS 2007 | Workload-aware stratified sampling. |
| `10-chaudhuri-aqp-sigmod2001.pdf` | Same authors. SIGMOD 2001 | Earlier STRAT. |
| `11-autoadmin-index-vldb1997.pdf` | Chaudhuri, Narasayya. VLDB 1997 | DTA ancestor. |
| `12-autoadmin-whatif-sigmod1998.pdf` | Chaudhuri, Narasayya. SIGMOD 1998 | Hypothetical indexes. |
| `13-leis-optimizers-pvldb2015.pdf` | Leis et al. How good are query optimizers? | Cardinality errors dominate. |
| `14-dsb-pvldb2021.pdf` | Ding et al. DSB | Skewed TPC-DS. |
| `15-joins-on-samples-pvldb2020.pdf` | Huang, Kandula et al. | Universe / SUBS hybrids. |
| `16-quickr-sigmod2016.pdf` | Kandula et al. Quickr | Hash-on-key sampling. |
| `18-asqp-rl-arxiv2401.17059.pdf` | Learning approximation sets | Learned samples. Not used here. |
| `22-azure-autoindex-sigmod2019.pdf` | Das et al. Azure auto-indexing | Validation on a full clone. |
| `24-touchstone-atc2018.pdf` | Li et al. Touchstone | Synthetic downscale. |
| `25-blinkdb-eurosys2013.pdf` | Agarwal et al. BlinkDB. EuroSys 2013 | Stratified AQP / query column sets. |
| `26-two-level-sampling-sigmod2017.pdf` | Chen, Yi | Block then row. |
| `27-poess-tpcds-vldb2002.pdf` | Poess, Smith. TPC-DS | Benchmark. |
| `28-hyperband-jmlr2018.pdf` | Li et al. Hyperband | Multi-fidelity ranking. |
| `30-mftune-arxiv2603.16450.pdf` | MFTune | Data-volume reduction is a bad proxy for Spark knobs. |

## Not downloaded (paywall or dead URL)

| Paper | Why it matters | Try |
|---|---|---|
| Schlosser et al. Extend. ICDE 2019 | PostgreSQL heuristic advisor | IEEE |
| Babcock, Chaudhuri, Das. Dynamic sample selection. SIGMOD 2003 | Workload-aware sample choice | ACM |
| Chaudhuri et al. Overcoming limitations of sampling. ICDE 2001 | Rare groups | IEEE |
| Chaudhuri, Motwani, Narasayya. Random sampling for histograms. SIGMOD 1998 | How ANALYZE-style stats are built | ACM |
| Zhang, Tay. Dscaler. PVLDB 2016 | Competing route to a small DB | PVLDB vol 9 HTML interstitial |
| Ding et al. AI Meets AI. SIGMOD 2019 | Plan-pair classifier instead of executing | Microsoft 403 |
| Valentin et al. DB2 Advisor. ICDE 2000 | Classical advisor | IEEE |
| AIM (Yadav et al.) | Full clone validation | |
| MFIX, DISTILL, budget-aware index tuning | Other cheap-evaluation methods | |
| LLM4IA CIKM 2025 | LLM advisor demo | |
| Wander Join, Leis CIDR 2017, Haas & König SIGMOD 2004 | Other samplers | |
