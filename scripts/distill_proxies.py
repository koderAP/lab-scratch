#!/usr/bin/env python3
"""Cheap distillation proxies from existing eval_configs.py jsonl files.

No database writes. Prints markdown. Optionally writes --md.

Proxies
  plan     fraction of (config, query) pairs whose stored plan_hash matches the full DB
  sign     fraction of pairs whose time-vs-none sign matches the full DB
  timeout  fraction of pairs whose timeout bit matches
  movable  Kendall tau using only queries whose full-DB time actually moves

Usage:
  python3 scripts/distill_proxies.py --md results/distill_proxies.md
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from rank_metrics import load, tau_b  # noqa: E402

SAMPLES = [
    ("full repeat", "results/truth_sf1_rep.jsonl"),
    ("Bernoulli 5%", "results/dprime_tpcds_sf1_b0_p5.jsonl"),
    ("Page 5%", "results/dprime_tpcds_sf1_sys_p5.jsonl"),
    ("Universe 5%", "results/dprime_tpcds_sf1_uitem_p5.jsonl"),
    ("FK 5%", "results/dprime_tpcds_sf1_fk_p5.jsonl"),
    ("Stratified 5%", "results/dprime_tpcds_sf1_strat_p5.jsonl"),
    ("Bernoulli + full stats", "results/dprime_tpcds_sf1_b0_p5_c4.jsonl"),
    ("Universe + full stats", "results/dprime_tpcds_sf1_uitem_p5_c4.jsonl"),
]
WINNER = "grok-4-7:small-dimension-filters"
RUNNER = "claude-opus-5:light_dimension_covering"
NONE = "none:none"
MOVE_MS = 200.0  # a query "moves" if max-min on the full DB exceeds this


def sign(x: float) -> int:
    if x > 1e-9:
        return 1
    if x < -1e-9:
        return -1
    return 0


def cfg_ids(T, S):
    return [c for c in T["cfg"] if c in S["cfg"]]


def tau_of(T, S, ids, qids=None):
    if qids is None:
        x = [T["cfg"][c]["workload_ms"] for c in ids]
        y = [S["cfg"][c]["workload_ms"] for c in ids]
    else:
        x, y = [], []
        for c in ids:
            x.append(sum(T["q"][c][q]["exec_ms"] for q in qids if q in T["q"][c] and q in S["q"].get(c, {})))
            y.append(sum(S["q"][c][q]["exec_ms"] for q in qids if q in T["q"][c] and q in S["q"].get(c, {})))
    return tau_b(x, y)


def pick(S, ids, qids=None):
    if qids is None:
        return min(ids, key=lambda c: S["cfg"][c]["workload_ms"])
    return min(ids, key=lambda c: sum(S["q"][c][q]["exec_ms"] for q in qids if q in S["q"].get(c, {})))


def pair_stats(T, S, ids):
    plan_n = plan_ok = 0
    sign_n = sign_ok = 0
    to_n = to_ok = 0
    qids = sorted({q for c in ids for q in T["q"].get(c, {})})
    for c in ids:
        if c == NONE:
            continue
        for q in qids:
            tq = T["q"].get(c, {}).get(q)
            sq = S["q"].get(c, {}).get(q)
            tn = T["q"].get(NONE, {}).get(q)
            sn = S["q"].get(NONE, {}).get(q)
            if not tq or not sq:
                continue
            to_n += 1
            if bool(tq.get("timed_out")) == bool(sq.get("timed_out")):
                to_ok += 1
            if tq.get("plan_hash") and sq.get("plan_hash"):
                plan_n += 1
                if tq["plan_hash"] == sq["plan_hash"]:
                    plan_ok += 1
            if tn and sn and not tq.get("timed_out") and not sq.get("timed_out"):
                sign_n += 1
                if sign(tq["exec_ms"] - tn["exec_ms"]) == sign(sq["exec_ms"] - sn["exec_ms"]):
                    sign_ok += 1
    return {
        "plan": plan_ok / plan_n if plan_n else None,
        "plan_n": plan_n,
        "sign": sign_ok / sign_n if sign_n else None,
        "sign_n": sign_n,
        "timeout": to_ok / to_n if to_n else None,
        "timeout_n": to_n,
    }


def query_range(T, ids):
    qids = sorted({q for c in ids for q in T["q"].get(c, {})})
    out = {}
    for q in qids:
        xs = [T["q"][c][q]["exec_ms"] for c in ids if q in T["q"].get(c, {})]
        tos = [bool(T["q"][c][q].get("timed_out")) for c in ids if q in T["q"].get(c, {})]
        out[q] = {
            "min": min(xs), "max": max(xs), "range": max(xs) - min(xs),
            "always_cap": all(tos), "never_cap": not any(tos),
        }
    return out


def flip_queries(T, S, a, b, ids):
    """Queries whose (a-b) sign disagrees between T and S, among those with |T(a)-T(b)| > MOVE_MS."""
    rows = []
    qids = sorted({q for c in ids for q in T["q"].get(c, {})})
    for q in qids:
        ta, tb = T["q"][a][q]["exec_ms"], T["q"][b][q]["exec_ms"]
        sa, sb = S["q"][a][q]["exec_ms"], S["q"][b][q]["exec_ms"]
        dt, ds = ta - tb, sa - sb
        if abs(dt) < MOVE_MS:
            continue
        if sign(dt) != sign(ds):
            rows.append((q, dt, ds, ta, tb, sa, sb))
    rows.sort(key=lambda r: -abs(r[1]))
    return rows


def fmt_pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", default="results/truth_sf1.jsonl")
    ap.add_argument("--md")
    a = ap.parse_args()

    T = load(a.truth)
    lines = []

    # --- which queries move ---
    ids_all = list(T["cfg"])
    qr = query_range(T, ids_all)
    always = sorted(q for q, r in qr.items() if r["always_cap"])
    movable = sorted(q for q, r in qr.items() if r["range"] >= MOVE_MS and not r["always_cap"])
    dead = sorted(q for q, r in qr.items() if r["range"] < MOVE_MS and not r["always_cap"])
    move_mass = sum(qr[q]["range"] for q in movable)
    lines.append("# Distillation proxies on the existing SF=1 run")
    lines.append("")
    lines.append(f"Full database: {len(ids_all)} configurations, 99 queries.")
    lines.append(f"Always at the 20 s cap under every configuration: {len(always)} queries ({', '.join('Q'+str(q) for q in always)}). That is 140 s of every total.")
    lines.append(f"Queries whose time moves by at least {MOVE_MS:.0f} ms across configurations: {len(movable)}. Combined range {move_mass/1000:.1f} s.")
    lines.append(f"Queries that never move: {len(dead)}.")
    lines.append("")

    # --- per-query contribution of the winner ---
    none_ms = T["cfg"][NONE]["workload_ms"]
    win_ms = T["cfg"][WINNER]["workload_ms"]
    contrib = []
    for q in range(1, 100):
        d = T["q"][NONE][q]["exec_ms"] - T["q"][WINNER][q]["exec_ms"]
        if abs(d) >= MOVE_MS:
            contrib.append((q, d))
    contrib.sort(key=lambda x: -x[1])
    lines.append(f"Winner {WINNER}: {win_ms/1000:.1f} s vs no-index {none_ms/1000:.1f} s (saved {(none_ms-win_ms)/1000:.1f} s).")
    lines.append("Queries that save at least 200 ms for the winner, largest first:")
    lines.append("")
    lines.append("| query | saved on full (s) |")
    lines.append("|---|---:|")
    for q, d in contrib:
        lines.append(f"| Q{q} | {d/1000:.2f} |")
    lines.append("")

    # --- proxy table ---
    lines.append("## Do cheap proxies track the ranking?")
    lines.append("")
    lines.append("Plan agreement uses the stored `plan_hash` from the timed runs (same index names, so hashes are comparable). Sign agreement is the sign of (config time minus no-index time) per query. Movable tau uses only the queries that move on the full database.")
    lines.append("")
    lines.append("| D' | tau (all 99) | tau (movable) | plan agree | sign agree | timeout agree | pick (all) | pick (movable) |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")

    table_rows = []
    for label, path in SAMPLES:
        p = ROOT / path
        if not p.exists():
            continue
        S = load(str(p))
        ids = cfg_ids(T, S)
        t_all = tau_of(T, S, ids)
        t_mov = tau_of(T, S, ids, movable)
        ps = pair_stats(T, S, ids)
        pick_all = pick(S, ids)
        pick_mov = pick(S, ids, movable)
        table_rows.append((label, t_all, t_mov, ps, pick_all, pick_mov))
        lines.append(
            f"| {label} | {t_all:.2f} | {t_mov:.2f} | {fmt_pct(ps['plan'])} "
            f"({ps['plan_n']}) | {fmt_pct(ps['sign'])} ({ps['sign_n']}) | "
            f"{fmt_pct(ps['timeout'])} | {pick_all} | {pick_mov} |"
        )
    lines.append("")
    lines.append("Full-repeat row is the noise ceiling: same database, next morning.")
    lines.append("")

    # --- grok vs opus, the only ranking that matters for top-1 ---
    lines.append("## Why every cheap sample misses top-1")
    lines.append("")
    lines.append(f"True best is `{WINNER}`. Every native sample except stratified picks `{RUNNER}` (1.4% slower on the full database). Queries where the full database prefers Grok by ≥200 ms but the sample disagrees:")
    lines.append("")
    for label, path in SAMPLES:
        p = ROOT / path
        if not p.exists():
            continue
        S = load(str(p))
        ids = cfg_ids(T, S)
        if WINNER not in ids or RUNNER not in ids:
            continue
        dt = T["cfg"][WINNER]["workload_ms"] - T["cfg"][RUNNER]["workload_ms"]
        ds = S["cfg"][WINNER]["workload_ms"] - S["cfg"][RUNNER]["workload_ms"]
        flips = flip_queries(T, S, WINNER, RUNNER, ids)
        lines.append(f"**{label}.** Full: Grok is {-dt/1000:.2f} s faster. Sample: Grok is {-ds/1000:.2f} s faster (negative means Grok loses). Flipped queries ({len(flips)}):")
        if not flips:
            lines.append("")
            lines.append("none.")
            lines.append("")
            continue
        lines.append("")
        lines.append("| query | full Grok−Opus (s) | sample Grok−Opus (s) |")
        lines.append("|---|---:|---:|")
        for q, dtf, dsf, *_ in flips[:12]:
            lines.append(f"| Q{q} | {dtf/1000:.2f} | {dsf/1000:.2f} |")
        lines.append("")

    # --- per-query tau distribution for Bernoulli, our headline sample ---
    lines.append("## Where Bernoulli agrees, query by query")
    lines.append("")
    b0 = load(str(ROOT / "results/dprime_tpcds_sf1_b0_p5.jsonl"))
    ids = cfg_ids(T, b0)
    qtau = []
    for q in range(1, 100):
        x = [T["q"][c][q]["exec_ms"] for c in ids]
        y = [b0["q"][c][q]["exec_ms"] for c in ids]
        if max(x) - min(x) < MOVE_MS:
            continue
        t = tau_b(x, y)
        qtau.append((q, t, max(x) - min(x)))
    qtau.sort(key=lambda r: r[1] if r[1] is not None else 99)
    lines.append(f"Kendall tau of the 33 configuration times, per query, for queries that move on the full database ({len(qtau)} queries). Lowest agreement first.")
    lines.append("")
    lines.append("| query | tau vs Bernoulli | full range (s) |")
    lines.append("|---|---:|---:|")
    for q, t, rng in qtau:
        lines.append(f"| Q{q} | {t:.2f} | {rng/1000:.2f} |")
    lines.append("")

    text = "\n".join(lines) + "\n"
    print(text)
    if a.md:
        Path(a.md).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
