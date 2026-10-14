#!/usr/bin/env bash
# Time the SF=10 study-set queries: no extra index, then that query's screen index.
# Usage: scripts/run_sf10_study.sh <schema> <out.jsonl> [cap-ms]
# Default cap 30 minutes. Resumable (eval_configs.py skips rows already in out).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SCHEMA="${1:?schema e.g. tpcds_sf10}"
OUT="${2:?output jsonl}"
CAP="${3:-1800000}"
CFGS="$ROOT/results/configs_sf10_study.json"

python3 - <<PY
import json, subprocess, sys
cfgs = json.loads(open("$CFGS").read())
queries = cfgs["queries"]
print("schema $SCHEMA  queries", queries, "cap ${CAP}ms", flush=True)
for q in queries:
    cmd = [
        "python3", "scripts/eval_configs.py",
        "--schema", "$SCHEMA",
        "--configs", "$CFGS",
        "--out", "$OUT",
        "--only", f"none:none,screen:q{q}",
        "--queries", str(q),
        "--cap-ms", "${CAP}",
    ]
    print("==> Q%s" % q, flush=True)
    r = subprocess.call(cmd)
    if r != 0:
        sys.exit(r)
print("done", "$OUT")
PY
