#!/usr/bin/env python3
"""EXPLAIN (no ANALYZE) every configuration under HypoPG. No index builds, no timing.

For each configuration: create its indexes as hypothetical, EXPLAIN every query,
drop the hypothetical indexes. Writes one query row and one config row, resumable.

Plan shape ignores HypoPG's generated index names so shapes can be compared
across schemas. Cost is the optimizer's Total Cost.

Usage:
  python3 scripts/explain_configs.py --schema tpcds_sf1 --out results/explain_tpcds_sf1.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pg import DB, load_sql, parse_qids, skeleton  # noqa: E402


def shape(plan: dict) -> str:
    """Node types and relation names only. HypoPG index names are not stable across sessions."""
    def rec(n: dict) -> str:
        s = n["Node Type"]
        if "Relation Name" in n:
            s += ":" + n["Relation Name"]
        return s + "(" + ",".join(rec(c) for c in n.get("Plans", [])) + ")"
    return rec(plan)


def psql(sql: str, schema: str, timeout_ms: int = 15000) -> subprocess.CompletedProcess:
    pre = (
        f"SET search_path TO {schema}, public;\n"
        f"SET statement_timeout = '{timeout_ms}';\n"
        f"SET hypopg.enabled = on;\n"
    )
    return subprocess.run(["psql", "-d", DB, "-Atq"], input=pre + sql, capture_output=True, text=True)


def parse_explains(stdout: str, qids: list[int]) -> dict[int, dict]:
    chunks = re.split(r"^QID:(\d+)$", stdout, flags=re.M)
    out = {}
    # split gives [pre, id1, body1, id2, body2, ...]
    for i in range(1, len(chunks), 2):
        qid = int(chunks[i])
        body = chunks[i + 1]
        m = re.search(r"\[\s*\{.*\}\s*\]", body, re.S)
        if not m:
            err = body.strip()[:240]
            out[qid] = {"error": err or "no json"}
            continue
        d = json.loads(m.group(0))
        d = d[0] if isinstance(d, list) else d
        plan = d["Plan"]
        out[qid] = {
            "cost": plan["Total Cost"],
            "planning_ms": d.get("Planning Time"),
            "shape": shape(plan),
            "shape_hash": hashlib.md5(shape(plan).encode()).hexdigest()[:10],
            "skel_hash": hashlib.md5(skeleton(plan).encode()).hexdigest()[:10],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--configs", default=str(ROOT / "results" / "configs_sf1.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--queries", default="1-99")
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout-ms", type=int, default=15000)
    ap.add_argument("--set", default="", help="extra SET commands, one session, e.g. work_mem='400kB'")
    a = ap.parse_args()

    cfgs = json.loads(Path(a.configs).read_text())["configs"]
    if a.only:
        keep = set(a.only.split(","))
        cfgs = [c for c in cfgs if c["id"] in keep]
    qids = parse_qids(a.queries)
    sqls = {q: load_sql(q).rstrip().rstrip(";") for q in qids}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    done_cfg = set()
    if out.exists():
        for l in out.read_text().splitlines():
            r = json.loads(l)
            if r.get("kind") == "config":
                done_cfg.add(r["config"])

    extra = (a.set + ";\n") if a.set else ""

    def write(rec: dict) -> None:
        rec.update({"ts": datetime.now(timezone.utc).isoformat(), "schema": a.schema})
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    for i, c in enumerate(cfgs):
        cid = c["id"]
        if cid in done_cfg:
            continue
        creates = ["SELECT hypopg_reset();"]
        for ix in c["indexes"]:
            ddl = ix["ddl"].replace("'", "''")
            creates.append(f"SELECT hypopg_create_index('{ddl}');")
        body = extra + "\n".join(creates) + "\n"
        for q in qids:
            body += f"SELECT 'QID:{q}';\nEXPLAIN (FORMAT JSON)\n{sqls[q]};\n"
        body += "SELECT hypopg_reset();\n"
        p = psql(body, a.schema, a.timeout_ms)
        parsed = parse_explains(p.stdout, qids)
        if p.returncode != 0 and not parsed:
            print(f"  {cid}: psql failed {p.stderr[-200:]}", flush=True)
            write({"kind": "config", "config": cid, "error": True, "stderr": p.stderr[-300:]})
            continue
        n_ok = 0
        cost_sum = 0.0
        for q in qids:
            rec = parsed.get(q) or {"error": "missing"}
            row = {"kind": "query", "config": cid, "query_id": q, **rec}
            write(row)
            if "cost" in rec:
                n_ok += 1
                cost_sum += rec["cost"]
        write({
            "kind": "config", "config": cid, "n_ok": n_ok, "n_queries": len(qids),
            "n_indexes": len(c["indexes"]), "cost_sum": round(cost_sum, 2),
        })
        print(f"[{i+1}/{len(cfgs)}] {a.schema} {cid}: {n_ok}/{len(qids)} plans, cost_sum {cost_sum:.0f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
