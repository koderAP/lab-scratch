#!/usr/bin/env python3
"""Give a sample schema the full database's planner statistics.

SQL:Trek lists this as future work ("virtual statistics"): the sample keeps its
rows, but pg_statistic and the planner's idea of table size come from the source
schema. We do this so a later timing run can separate "the sample has the wrong
rows" from "ANALYZE on the sample told the planner a different story".

What is copied, per table (matched by relname):
  * pg_statistic rows, joined by column name so attnums need not match
  * pg_class.reltuples, relpages, relallvisible

What is not copied: index statistics. CREATE INDEX on the sample builds a small
index, and that index's size stays real. The table looks big to the planner and
the index looks small. That mismatch is part of the method; the lab note records it.

After this script, do not ANALYZE the destination. Autovacuum is already off.
Usage: transplant_stats.py --src tpcds_sf1 --dst tpcds_sf1_b0_p5
"""
from __future__ import annotations

import argparse
import subprocess

DB = "col868"

COPY_STATS = """
DELETE FROM pg_statistic s
USING pg_class c, pg_namespace n
WHERE s.starelid = c.oid AND c.relnamespace = n.oid AND n.nspname = '{dst}'
  AND c.relkind = 'r';

INSERT INTO pg_statistic (
    starelid, staattnum, stainherit, stanullfrac, stawidth, stadistinct,
    stakind1, stakind2, stakind3, stakind4, stakind5,
    staop1, staop2, staop3, staop4, staop5,
    stacoll1, stacoll2, stacoll3, stacoll4, stacoll5,
    stanumbers1, stanumbers2, stanumbers3, stanumbers4, stanumbers5,
    stavalues1, stavalues2, stavalues3, stavalues4, stavalues5)
SELECT dc.oid, da.attnum, s.stainherit, s.stanullfrac, s.stawidth, s.stadistinct,
    s.stakind1, s.stakind2, s.stakind3, s.stakind4, s.stakind5,
    s.staop1, s.staop2, s.staop3, s.staop4, s.staop5,
    s.stacoll1, s.stacoll2, s.stacoll3, s.stacoll4, s.stacoll5,
    s.stanumbers1, s.stanumbers2, s.stanumbers3, s.stanumbers4, s.stanumbers5,
    s.stavalues1, s.stavalues2, s.stavalues3, s.stavalues4, s.stavalues5
FROM pg_statistic s
JOIN pg_class sc ON s.starelid = sc.oid
JOIN pg_namespace sn ON sc.relnamespace = sn.oid AND sn.nspname = '{src}'
JOIN pg_attribute sa ON sa.attrelid = sc.oid AND sa.attnum = s.staattnum
JOIN pg_namespace dn ON dn.nspname = '{dst}'
JOIN pg_class dc ON dc.relnamespace = dn.oid AND dc.relname = sc.relname AND dc.relkind = 'r'
JOIN pg_attribute da ON da.attrelid = dc.oid AND da.attname = sa.attname AND da.attnum > 0
WHERE NOT s.stainherit;

UPDATE pg_class dc
SET reltuples = sc.reltuples, relpages = sc.relpages, relallvisible = sc.relallvisible
FROM pg_namespace dn, pg_namespace sn, pg_class sc
WHERE dc.relnamespace = dn.oid AND dn.nspname = '{dst}' AND dc.relkind = 'r'
  AND sc.relnamespace = sn.oid AND sn.nspname = '{src}' AND sc.relname = dc.relname;
"""

CHECK = """
SELECT d.tablename,
       round(s.n_distinct::numeric, 1) AS src_nd,
       round(d.n_distinct::numeric, 1) AS dst_nd,
       s.most_common_vals::text = d.most_common_vals::text AS mcv_same
FROM pg_stats s
JOIN pg_stats d ON d.tablename = s.tablename AND d.attname = s.attname
WHERE s.schemaname = '{src}' AND d.schemaname = '{dst}'
  AND s.tablename = 'store_sales' AND s.attname IN ('ss_item_sk', 'ss_sold_date_sk')
ORDER BY 1, s.attname;
"""


def psql(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(["psql", "-d", DB, "-v", "ON_ERROR_STOP=1"], input=sql, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    p = psql(COPY_STATS.format(src=a.src, dst=a.dst))
    if p.returncode != 0:
        print(p.stderr)
        return 1
    print(p.stdout)
    c = psql(CHECK.format(src=a.src, dst=a.dst))
    print(c.stdout)
    if c.returncode != 0:
        print(c.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
