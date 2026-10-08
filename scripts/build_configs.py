#!/usr/bin/env python3
"""Collect index configurations from the advisors and baselines into one file.

Inputs
  results/advisors/*.json            LLM advisors, 5 configurations each (see advisors/prompt.md)
  results/candidates_tpcds_sf1.json  HypoPG per-query candidates (the cost-only baseline)

Output
  results/configs_sf1.json   {"configs": [{"id", "source", "name", "rationale", "indexes": [{"table","columns","include","ddl"}]}]}

Validation: every table and column must exist in the schema, indexes that duplicate an existing
index (same table, same column list) are dropped, repeated indexes inside a configuration are
dropped, at most 8 indexes per configuration are kept. Anything dropped is printed.

Baselines added here
  none          the empty configuration (the starting point)
  hypopg-top5   the 5 indexes with the largest summed HypoPG cost gain over the workload
  hypopg-top10  same, 10 indexes

Usage: build_configs.py [--schema tpcds_sf1]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = "col868"
MAX_INDEXES = 8


def q(sql: str) -> list[list[str]]:
    p = subprocess.run(["psql", "-d", DB, "-Atq", "-F", "\t", "-c", sql], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def ddl(name: str, ix: dict) -> str:
    s = f"CREATE INDEX {name} ON {ix['table']} ({', '.join(ix['columns'])})"
    if ix.get("include"):
        s += f" INCLUDE ({', '.join(ix['include'])})"
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="tpcds_sf1")
    a = ap.parse_args()

    cols: dict[str, set[str]] = defaultdict(set)
    for t, c in q(f"SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='{a.schema}'"):
        cols[t].add(c)
    rows = {t: int(float(n)) for t, n in q(
        f"SELECT c.relname, c.reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        f"WHERE n.nspname='{a.schema}' AND c.relkind='r'")}
    existing = set()
    for t, cs in q(
            f"SELECT t.relname, string_agg(a.attname, ',' ORDER BY k.ord) FROM pg_index i "
            f"JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace AND n.nspname='{a.schema}' "
            f"JOIN LATERAL unnest(i.indkey::int2[]) WITH ORDINALITY k(attnum, ord) ON true "
            f"JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum GROUP BY t.relname, i.indexrelid"):
        existing.add((t, tuple(cs.split(","))))

    configs = []

    def add(source: str, name: str, rationale: str, indexes: list[dict]) -> None:
        clean, seen = [], set()
        for ix in indexes:
            t, cs = ix.get("table"), ix.get("columns") or []
            inc = ix.get("include") or []
            why = None
            if t not in cols:
                why = "unknown table"
            elif not cs or any(c not in cols[t] for c in cs + inc):
                why = "unknown column"
            elif rows.get(t, 0) < 1000:
                why = "table under 1000 rows"
            elif (t, tuple(cs)) in existing and not inc:
                why = "already exists"
            elif (t, tuple(cs), tuple(inc)) in seen:
                why = "repeated in this configuration"
            if why:
                print(f"  drop [{source}/{name}] {t}({','.join(cs)}): {why}")
                continue
            seen.add((t, tuple(cs), tuple(inc)))
            clean.append({"table": t, "columns": cs, "include": inc})
        if len(clean) > MAX_INDEXES:
            print(f"  trim [{source}/{name}] {len(clean)} -> {MAX_INDEXES}")
            clean = clean[:MAX_INDEXES]
        cid = f"{source}:{name}".replace(" ", "_")
        k = len(configs)
        for j, ix in enumerate(clean):
            ix["name"] = f"ix_c{k}_{j}"
            ix["ddl"] = ddl(ix["name"], ix)
        configs.append({"id": cid, "n": k, "source": source, "name": name, "rationale": rationale, "indexes": clean})

    add("none", "none", "no extra index (starting point)", [])

    # HypoPG baseline: rank indexes by summed cost gain over the whole workload
    cand = json.loads((ROOT / "results" / f"candidates_{a.schema}.json").read_text())
    gain: dict[tuple, float] = defaultdict(float)
    for items in cand.values():
        for it in items:
            if it.get("source") != "hypopg":
                continue
            gain[(it["table"], tuple(it["cols"]))] += max(it["cost_none"] - it["hypopg_cost"], 0.0)
    ranked = sorted(gain.items(), key=lambda kv: -kv[1])
    for k in (5, 8):
        add("hypopg", f"top{k}", f"the {k} indexes with the largest summed HypoPG cost gain over the workload",
            [{"table": t, "columns": list(cs), "include": []} for (t, cs), _ in ranked[:k]])

    for f in sorted((ROOT / "results" / "advisors").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception as e:  # noqa: BLE001
            print(f"SKIP {f.name}: {e}")
            continue
        src = f.stem
        print(f"{src}: {len(d.get('configs', []))} configurations")
        for c in d.get("configs", []):
            add(src, c.get("name", "cfg"), c.get("rationale", ""), c.get("indexes", []))

    out = ROOT / "results" / f"configs_{a.schema.replace('tpcds_', '')}.json"
    out.write_text(json.dumps({"schema": a.schema, "configs": configs}, indent=1))
    print(f"wrote {out} with {len(configs)} configurations, {sum(len(c['indexes']) for c in configs)} indexes")
    by = defaultdict(int)
    for c in configs:
        by[c["source"]] += 1
    print(dict(by))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
