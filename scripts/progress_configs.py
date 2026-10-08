#!/usr/bin/env python3
"""Progress of an eval_configs.py run.

Usage: progress_configs.py results/truth_sf1.jsonl [results/configs_sf1.json]
"""
import json
import sys
from datetime import datetime, timezone

path = sys.argv[1]
cfg_path = sys.argv[2] if len(sys.argv) > 2 else "results/configs_sf1.json"
total = len(json.load(open(cfg_path))["configs"])
done, qrows, first_ts, last_ts, last = [], 0, None, None, None
for l in open(path):
    r = json.loads(l)
    ts = datetime.fromisoformat(r["ts"])
    first_ts = first_ts or ts
    last_ts = ts
    if r["kind"] == "query":
        qrows += 1
    else:
        done.append(r)
        last = r
now = datetime.now(timezone.utc)
el = (last_ts - first_ts).total_seconds() if first_ts else 0
print(f"configurations finished {len(done)}/{total}, query rows {qrows}")
if last:
    print(f"last finished: {last['config']}  build {last['build_seconds']}s  workload {last['workload_ms'] / 1000:.1f}s  timeouts {last['timeouts']}")
if done:
    per = el / len(done)
    print(f"about {per / 60:.1f} min per configuration, about {(total - len(done)) * per / 3600:.1f} h left")
print(f"last write {(now - last_ts).total_seconds():.0f}s ago")
