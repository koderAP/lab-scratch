#!/usr/bin/env python3
"""Generate candidate indexes per TPC-DS query using the baseline plan + HypoPG.

For each query:
  1. EXPLAIN (FORMAT JSON) on the schema; collect columns used in Filter / join conditions / sort+group keys.
  2. Enumerate single-column and 2-column candidate indexes on tables with >= MIN_ROWS rows.
  3. Rank by HypoPG estimated cost improvement (optimizer cost, NOT runtime).
  4. Keep the top K with improvement >= MIN_IMPROVE (source="hypopg") and one decoy
     (best candidate with improvement < MIN_IMPROVE, source="decoy") so that rankings
     contain indexes that look useless or harmful.

Output: results/candidates_<schema>.json  {query_id: [{name, ddl, hypopg_cost, cost_none, source, table, cols}]}
DDL is schema-agnostic (run with search_path set) so the same set is reused on samples.

Usage: gen_candidates.py --schema tpcds_sf1 [--queries 1-99] [--top 3]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pg import DB, load_sql  # noqa: E402
MIN_ROWS = 50_000
MIN_IMPROVE = 0.01
MAX_CANDS_PER_QUERY = 30
FILTER_KEYS = ("Filter", "Recheck Cond")
JOIN_KEYS = ("Hash Cond", "Merge Cond", "Join Filter", "Index Cond")
ORDER_KEYS = ("Sort Key", "Group Key")
TOKEN = re.compile(r"\b[a-z]{1,3}_[a-z0-9_]+\b")


def psql(sql: str, schema: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["psql", "-d", DB, "-Atq"], input=f"SET search_path TO {schema}, public;\nSET statement_timeout='{timeout * 1000}';\n{sql}",
                          capture_output=True, text=True)


def catalog(schema: str):
    col2tab = {}
    for l in psql("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema=current_schema()", schema).stdout.splitlines():
        t, c = l.split("|")
        col2tab[c] = t
    rows = {}
    for l in psql("SELECT relname, reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE nspname=current_schema() AND relkind='r'", schema).stdout.splitlines():
        t, r = l.split("|")
        rows[t] = int(r)
    lead = set()  # existing single-column-leading indexes (table, first column)
    for l in psql("SELECT tablename, indexdef FROM pg_indexes WHERE schemaname=current_schema()", schema).stdout.splitlines():
        t, d = l.split("|", 1)
        m = re.search(r"\(([^)]*)\)", d)
        if m:
            lead.add((t, m.group(1).split(",")[0].strip()))
    return col2tab, rows, lead


def parse_json(out: str):
    m = re.search(r"\[\s*\{.*\}\s*\]", out, re.S)
    if not m:
        return None
    d = json.loads(m.group(0))
    return d[0] if isinstance(d, list) else d


def collect(plan: dict, col2tab: dict, acc: dict):
    for k in FILTER_KEYS:
        if k in plan:
            for c in TOKEN.findall(plan[k]):
                if c in col2tab:
                    acc["F"].add(c)
    for k in JOIN_KEYS:
        if k in plan:
            for c in TOKEN.findall(plan[k]):
                if c in col2tab:
                    acc["J"].add(c)
    for k in ORDER_KEYS:
        if k in plan:
            v = plan[k]
            for c in TOKEN.findall(" ".join(v) if isinstance(v, list) else v):
                if c in col2tab:
                    acc["O"].add(c)
    for ch in plan.get("Plans", []):
        collect(ch, col2tab, acc)


def enumerate_candidates(acc, col2tab, rows, lead):
    by_table = {}
    for cat in ("F", "J", "O"):
        for c in acc[cat]:
            t = col2tab[c]
            if rows.get(t, 0) >= MIN_ROWS:
                by_table.setdefault(t, {"F": set(), "J": set(), "O": set()})[cat].add(c)
    cands = []
    for t, d in by_table.items():
        allc = sorted(d["F"] | d["J"] | d["O"])
        for c in allc:
            if (t, c) not in lead:
                cands.append((t, (c,)))
        pairs = set()
        for f in d["F"]:
            for j in d["J"]:
                if f != j:
                    pairs.add((f, j))
                    pairs.add((j, f))
        for f1, f2 in itertools.permutations(sorted(d["F"]), 2):
            pairs.add((f1, f2))
        for f in d["F"]:
            for o in d["O"]:
                if f != o:
                    pairs.add((f, o))
        for a, b in sorted(pairs):
            if col2tab[a] == t and col2tab[b] == t and (t, (a, b)) not in cands:
                cands.append((t, (a, b)))
    return cands[: MAX_CANDS_PER_QUERY * 3]


def name_of(t: str, cols) -> str:
    return "ix_" + t + "_" + "_".join(cols) if len("ix_" + t + "_" + "_".join(cols)) < 60 else "ix_" + hashlib.md5((t + str(cols)).encode()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--queries", default="1-99")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    qids = []
    for part in a.queries.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            qids += list(range(int(lo), int(hi) + 1))
        else:
            qids.append(int(part))
    col2tab, rows, lead = catalog(a.schema)
    out_path = Path(a.out) if a.out else ROOT / "results" / f"candidates_{a.schema}.json"
    res = json.loads(out_path.read_text()) if out_path.exists() else {}
    for q in qids:
        if str(q) in res:
            continue
        sql = load_sql(q).rstrip().rstrip(";")
        p = psql(f"EXPLAIN (FORMAT JSON)\n{sql};", a.schema)
        base = parse_json(p.stdout) if p.returncode == 0 else None
        if not base:
            print(f"Q{q}: explain failed", flush=True)
            res[str(q)] = []
            continue
        cost0 = base["Plan"]["Total Cost"]
        acc = {"F": set(), "J": set(), "O": set()}
        collect(base["Plan"], col2tab, acc)
        scored = []
        for t, cols in enumerate_candidates(acc, col2tab, rows, lead):
            ddl = f"CREATE INDEX {name_of(t, cols)} ON {t} ({', '.join(cols)})"
            hp = psql(f"SELECT hypopg_reset(); SELECT hypopg_create_index('{ddl}');\nEXPLAIN (FORMAT JSON)\n{sql};", a.schema)
            j = parse_json(hp.stdout) if hp.returncode == 0 else None
            if j:
                scored.append((cost0 - j["Plan"]["Total Cost"], j["Plan"]["Total Cost"], t, cols, ddl))
        scored.sort(key=lambda x: -x[0])
        good = [s for s in scored if s[0] / cost0 >= MIN_IMPROVE][: a.top]
        bad = [s for s in scored if s[0] / cost0 < MIN_IMPROVE][:1]
        items = []
        for src, group in (("hypopg", good), ("decoy", bad)):
            for gain, cost, t, cols, ddl in group:
                items.append({"name": name_of(t, cols), "ddl": ddl, "table": t, "cols": list(cols),
                              "hypopg_cost": cost, "cost_none": cost0, "source": src})
        res[str(q)] = items
        print(f"Q{q}: cost0={cost0:.0f} enumerated={len(scored)} kept={[(i['name'], round(1 - i['hypopg_cost'] / cost0, 3)) for i in items]}", flush=True)
        out_path.write_text(json.dumps(res, indent=1))
    psql("SELECT hypopg_reset();", a.schema)
    out_path.write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
