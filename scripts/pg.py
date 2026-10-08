"""Shared PostgreSQL helpers used by the protocol scripts.

Database is always `col868`. Query text lives in workloads/tpcds/NN.sql.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

DB = "col868"
ROOT = Path(__file__).resolve().parents[1]
QUERY_DIR = ROOT / "workloads" / "tpcds"


def load_sql(qid: int) -> str:
    text = (QUERY_DIR / f"{qid:02d}.sql").read_text()
    return re.sub(r";\s*$", "", text.strip(), flags=re.S)


def parse_qids(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out += list(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return out


def psql(sql: str, schema: str, timeout_ms: int | None = None) -> subprocess.CompletedProcess:
    pre = f"SET search_path TO {schema}, public;\n"
    if timeout_ms:
        pre += f"SET statement_timeout = '{timeout_ms}';\n"
    return subprocess.run(["psql", "-d", DB, "-Atq"], input=pre + sql, capture_output=True, text=True)


def skeleton(plan: dict) -> str:
    def rec(n: dict) -> str:
        s = n["Node Type"]
        if "Relation Name" in n:
            s += ":" + n["Relation Name"]
        if "Index Name" in n:
            s += "@" + n["Index Name"]
        return s + "(" + ",".join(rec(c) for c in n.get("Plans", [])) + ")"
    return rec(plan)


def run_explain(sql: str, schema: str, timeout_ms: int) -> dict:
    p = psql(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n{sql};", schema, timeout_ms)
    if p.returncode != 0 or not p.stdout.strip():
        err = p.stderr or ""
        if "statement timeout" in err or "canceling statement" in err:
            return {"timeout": True}
        return {"error": err[-300:]}
    m = re.search(r"\[\s*\{.*\}\s*\]", p.stdout, re.S)
    d = json.loads(m.group(0))
    d = d[0] if isinstance(d, list) else d
    return {"ms": d["Execution Time"], "plan": d["Plan"], "planning_ms": d.get("Planning Time")}
