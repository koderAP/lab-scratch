#!/usr/bin/env python3
"""Measure whole index configurations: build time and total workload runtime.

For each configuration (docs/protocol.md): create all its indexes (timed), run the whole
workload (all 99 queries by default), drop the indexes. One configuration at a time.

Per query: one discarded warm-up run, then 2 timed runs if the warm-up took 2 s or less,
otherwise 1 timed run. Median. A query that exceeds the cap is recorded at the cap and not
repeated. Statistics are not re-analyzed (fingerprint stored). Resumable: queries already
written for a configuration are skipped, and the summary row is rewritten from the rows.

Output rows (jsonl)
  {"kind":"query","config":id,"query_id":n,"exec_ms":..,"timed_out":bool,"plan_hash":..,"shared_read":..}
  {"kind":"config","config":id,"build_seconds":..,"workload_ms":..,"timeouts":n,"n_queries":n,"stats_fp":..}

Usage: eval_configs.py --schema tpcds_sf1 --configs results/configs_sf1.json --out results/truth_sf1.jsonl
         [--queries 1-99] [--cap-ms 20000] [--only id1,id2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pg import load_sql, parse_qids, psql, run_explain, skeleton  # noqa: E402


def measure(sql: str, schema: str, cap_ms: int) -> dict:
    first = run_explain(sql, schema, cap_ms)
    if "timeout" in first:
        return {"exec_ms": float(cap_ms), "timed_out": True}
    if "error" in first:
        return {"error": first["error"]}
    n = 2 if first["ms"] <= 2000 else 1
    runs, plan, reads = [], first["plan"], []
    for _ in range(n):
        r = run_explain(sql, schema, cap_ms)
        if "ms" not in r:
            return {"exec_ms": float(cap_ms), "timed_out": True}
        runs.append(r["ms"])
        plan = r["plan"]
        reads.append(plan.get("Shared Read Blocks", 0))
    return {"exec_ms": statistics.median(runs), "timed_out": False, "runs": [round(x, 2) for x in runs],
            "plan_hash": hashlib.md5(skeleton(plan).encode()).hexdigest()[:10],
            "shared_read": statistics.median(reads)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--configs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--queries", default="1-99")
    ap.add_argument("--cap-ms", type=int, default=20000)
    ap.add_argument("--only", default="", help="comma separated config ids")
    a = ap.parse_args()

    cfgs = json.loads(Path(a.configs).read_text())["configs"]
    if a.only:
        keep = set(a.only.split(","))
        cfgs = [c for c in cfgs if c["id"] in keep]
    qids = parse_qids(a.queries)
    sqls = {q: load_sql(q).rstrip().rstrip(";") for q in qids}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    done: dict[str, dict[int, dict]] = {}
    summary_done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            r = json.loads(l)
            if r["kind"] == "query":
                done.setdefault(r["config"], {})[r["query_id"]] = r
            elif r["kind"] == "config":
                summary_done.add(r["config"])

    fp = psql("SELECT md5(string_agg(tablename||attname||coalesce(most_common_vals::text,'')||coalesce(histogram_bounds::text,'')"
              "||n_distinct::text, ',' ORDER BY tablename, attname)) FROM pg_stats WHERE schemaname = current_schema();",
              a.schema).stdout.strip()
    print("schema", a.schema, "stats fingerprint", fp, flush=True)

    def drop_experimental() -> None:
        for l in psql("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND indexname LIKE 'ix\\_c%'",
                      a.schema).stdout.splitlines():
            psql(f"DROP INDEX IF EXISTS {l};", a.schema)

    def write(rec: dict) -> None:
        rec.update({"ts": datetime.now(timezone.utc).isoformat(), "schema": a.schema})
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    drop_experimental()
    t_all = time.time()
    for ci, c in enumerate(cfgs):
        cid = c["id"]
        if cid in summary_done and len(done.get(cid, {})) >= len(qids):
            continue
        t0 = time.time()
        build = 0.0
        ok = True
        for ix in c["indexes"]:
            tb = time.perf_counter()
            p = psql(ix["ddl"] + ";", a.schema)
            build += time.perf_counter() - tb
            if p.returncode != 0:
                print(f"  build failed {cid}: {ix['ddl']} {p.stderr[-160:]}", flush=True)
                ok = False
        if not ok:
            drop_experimental()
            continue
        rows = done.setdefault(cid, {})
        for q in qids:
            if q in rows:
                continue
            m = measure(sqls[q], a.schema, a.cap_ms)
            if "error" in m:
                print(f"  Q{q} error {m['error'][:100]}", flush=True)
                m = {"exec_ms": float(a.cap_ms), "timed_out": True, "error": True}
            rec = {"kind": "query", "config": cid, "query_id": q, **m}
            write(rec)
            rows[q] = rec
        wl = sum(rows[q]["exec_ms"] for q in qids)
        to = sum(1 for q in qids if rows[q]["timed_out"])
        write({"kind": "config", "config": cid, "build_seconds": round(build, 3), "workload_ms": round(wl, 1),
               "timeouts": to, "n_queries": len(qids), "n_indexes": len(c["indexes"]), "stats_fp": fp})
        drop_experimental()
        print(f"[{ci + 1}/{len(cfgs)}] {cid}: build {build:.1f}s workload {wl / 1000:.1f}s timeouts {to} "
              f"(this config {time.time() - t0:.0f}s, total {time.time() - t_all:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
