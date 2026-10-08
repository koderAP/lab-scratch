#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."
for S in tpcds_sf1_b0_p5 tpcds_sf1_sys_p5 tpcds_sf1_uitem_p5 tpcds_sf1_fk_p5 tpcds_sf1_strat_p5; do
  echo "=== $(date +%H:%M:%S) $S"
  python3 scripts/eval_configs.py --schema "$S" --configs results/configs_sf1.json --out "results/dprime_${S}.jsonl" --queries 1-99 --cap-ms 20000 || echo "FAILED $S"
done
echo "=== $(date +%H:%M:%S) ALL DONE"
