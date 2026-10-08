#!/usr/bin/env python3
"""Build a sample database (schema) from a full TPC-DS schema with a chosen sampler.

Samplers (ids match docs/sampling-taxonomy.md):
  b0      B0  independent uniform Bernoulli per table, SQL:Trek recipe:
              rate p, floor 20K rows/table, cap 1M rows/table (cap scaled by p/0.05)
  sys     B1  same sizing rule as b0 but independent page sampling (TABLESAMPLE SYSTEM)
  uitem   C2  universe sampling: keep a fact row iff hash(item_sk) falls in the kept
              fraction, identically in all 7 fact tables; dimensions in full
  fk      C1  FK-closure: sample the 3 sales facts at p, keep returns that match a
              sampled sale (item, order), inventory rows for sampled items at rate p
  strat   C3  stratified: sales facts sampled at p per sold-date stratum with at least
              5 rows per stratum; other facts as b0; dimensions in full

Statistics: after loading, VACUUM (ANALYZE) once (frozen afterwards).
Usage: make_sample.py --src tpcds_sf1 --dst tpcds_sf1_b0_p5 --sampler b0 --pct 5 [--seed 42]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = "col868"

FACT_ITEM = {
    "store_sales": "ss_item_sk", "store_returns": "sr_item_sk",
    "catalog_sales": "cs_item_sk", "catalog_returns": "cr_item_sk",
    "web_sales": "ws_item_sk", "web_returns": "wr_item_sk",
    "inventory": "inv_item_sk",
}
SALES_DATE = {"store_sales": "ss_sold_date_sk", "catalog_sales": "cs_sold_date_sk", "web_sales": "ws_sold_date_sk"}
RETURNS_OF = {  # returns table -> (sales table, [(returns col, sales col)])
    "store_returns": ("store_sales", [("sr_item_sk", "ss_item_sk"), ("sr_ticket_number", "ss_ticket_number")]),
    "catalog_returns": ("catalog_sales", [("cr_item_sk", "cs_item_sk"), ("cr_order_number", "cs_order_number")]),
    "web_returns": ("web_sales", [("wr_item_sk", "ws_item_sk"), ("wr_order_number", "ws_order_number")]),
}
FLOOR_ROWS = 20_000
CAP_ROWS_AT_5PCT = 1_000_000


def psql(sql: str, search_path: str | None = None) -> str:
    pre = f"SET search_path TO {search_path};\n" if search_path else ""
    p = subprocess.run(["psql", "-d", DB, "-v", "ON_ERROR_STOP=1", "-Atq"], input=pre + sql,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr)
    return p.stdout.strip()


def tables(schema: str) -> dict[str, int]:
    out = psql(f"SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE nspname='{schema}' AND relkind='r' ORDER BY 1")
    names = out.splitlines()
    return {t: int(psql(f"SELECT count(*) FROM {schema}.{t}")) for t in names}


def rate_for(n: int, pct: float) -> float:
    """SQL:Trek sizing: pct of rows, at least FLOOR_ROWS, at most CAP (scaled), at most n."""
    cap = CAP_ROWS_AT_5PCT * (pct / 5.0)
    target = min(max(n * pct / 100.0, FLOOR_ROWS), cap, n)
    return target / n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--sampler", required=True, choices=["b0", "sys", "uitem", "fk", "strat"])
    ap.add_argument("--pct", type=float, required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    src, dst, pct, seed = a.src, a.dst, a.pct, a.seed
    t0 = time.perf_counter()
    counts = tables(src)
    psql(f"DROP SCHEMA IF EXISTS {dst} CASCADE; CREATE SCHEMA {dst};")
    keep_buckets = int(round(pct * 100))  # of 10000

    def ctas(t: str, sel: str) -> None:
        psql(f"SELECT setseed({(seed % 1000) / 1000.0}); CREATE TABLE {dst}.{t} AS {sel};")

    def bern(t: str, rate: float) -> str:
        if rate >= 0.999999:
            return f"SELECT * FROM {src}.{t}"
        return f"SELECT * FROM {src}.{t} TABLESAMPLE BERNOULLI ({rate * 100:.6f}) REPEATABLE ({seed})"

    def system(t: str, rate: float) -> str:
        if rate >= 0.999999:
            return f"SELECT * FROM {src}.{t}"
        return f"SELECT * FROM {src}.{t} TABLESAMPLE SYSTEM ({rate * 100:.6f}) REPEATABLE ({seed})"

    def hashed(t: str, col: str) -> str:
        return (f"SELECT * FROM {src}.{t} WHERE ((hashint8extended(({col})::bigint, {seed}) & 2147483647) % 10000) < {keep_buckets}")

    # dependents (returns, inventory) must be built after the sales tables they reference
    order = sorted(counts, key=lambda x: (x in RETURNS_OF or x == "inventory"))
    for t in order:
        n = counts[t]
        if a.sampler == "b0":
            ctas(t, bern(t, rate_for(n, pct)))
        elif a.sampler == "sys":
            ctas(t, system(t, rate_for(n, pct)))
        elif a.sampler == "uitem":
            ctas(t, hashed(t, FACT_ITEM[t]) if t in FACT_ITEM else f"SELECT * FROM {src}.{t}")
        elif a.sampler == "fk":
            if t in SALES_DATE:
                ctas(t, bern(t, pct / 100.0))
            elif t in RETURNS_OF:
                sales, keys = RETURNS_OF[t]
                cond = " AND ".join(f"r.{rc} = s.{sc}" for rc, sc in keys)
                ctas(t, f"SELECT r.* FROM {src}.{t} r WHERE EXISTS (SELECT 1 FROM {dst}.{sales} s WHERE {cond})")
            elif t == "inventory":
                sel = (f"SELECT i.* FROM {src}.inventory i TABLESAMPLE BERNOULLI ({pct:.6f}) REPEATABLE ({seed}) "
                       f"WHERE i.inv_item_sk IN (SELECT DISTINCT ss_item_sk FROM {dst}.store_sales "
                       f"UNION SELECT DISTINCT cs_item_sk FROM {dst}.catalog_sales "
                       f"UNION SELECT DISTINCT ws_item_sk FROM {dst}.web_sales)")
                ctas(t, sel)
            else:
                ctas(t, f"SELECT * FROM {src}.{t}")
        elif a.sampler == "strat":
            if t in SALES_DATE:
                d = SALES_DATE[t]
                psql(f"SELECT setseed({(seed % 1000) / 1000.0}); CREATE TABLE {dst}.{t} AS "
                     f"SELECT q.* FROM (SELECT x.*, row_number() OVER (PARTITION BY {d} ORDER BY random()) AS __rn, random() AS __u FROM {src}.{t} x) q "
                     f"WHERE __rn <= 5 OR __u < {pct / 100.0}; ALTER TABLE {dst}.{t} DROP COLUMN __rn, DROP COLUMN __u;")
            elif t in FACT_ITEM:
                ctas(t, bern(t, rate_for(n, pct)))
            else:
                ctas(t, f"SELECT * FROM {src}.{t}")
    build_s = time.perf_counter() - t0
    subprocess.run([str(ROOT / "scripts" / "apply_pks.sh"), dst], check=True, capture_output=True)
    psql("VACUUM (ANALYZE);", search_path=dst)
    total_s = time.perf_counter() - t0
    size = int(psql(f"SELECT coalesce(sum(pg_total_relation_size(c.oid)),0) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE nspname='{dst}' AND relkind IN ('r','i')"))
    new_counts = tables(dst)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(), "src": src, "dst": dst, "sampler": a.sampler, "pct": pct, "seed": seed,
        "build_seconds": round(build_s, 2), "total_seconds_with_pk_vacuum": round(total_s, 2), "size_bytes": size,
        "rows_fact": {t: new_counts[t] for t in FACT_ITEM}, "rows_fact_full": {t: counts[t] for t in FACT_ITEM},
    }
    out = ROOT / "results" / "samples.jsonl"
    out.parent.mkdir(exist_ok=True)
    with out.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps({k: rec[k] for k in ("dst", "sampler", "pct", "build_seconds", "total_seconds_with_pk_vacuum", "size_bytes")}))
    print({t: f"{new_counts[t]}/{counts[t]}" for t in FACT_ITEM})
    return 0


if __name__ == "__main__":
    sys.exit(main())
