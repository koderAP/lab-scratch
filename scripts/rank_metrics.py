#!/usr/bin/env python3
"""Compare the configuration ranking on a reduced database D' with the full-database ranking.

Both files come from eval_configs.py. A configuration is ranked on its own measured numbers:
  score A (primary)   total workload runtime, sum over the queries (ms)
  score B (secondary) index build time plus total workload runtime (ms)
Lower is better. The ground truth is the ranking on the full database.

Reported per D' and per score
  tau        Kendall tau-b between the two score vectors over the configurations (ties handled),
             with a 95% bootstrap interval over configurations
  top-1      the configuration D' ranks first is also first on the full database (exact)
  regret     full-database score of D' pick divided by the best full-database score (1.0 is perfect)
  top-3 hit  the full-database best is among D' three best
  cost       sum over configurations of (build + workload) on the full database divided by the same
             on D'. This is the evaluation cost reduction. The column "incl. sample" adds the time
             spent building D' (from results/samples.jsonl, when known).

Usage: rank_metrics.py --truth results/truth_sf1.jsonl --sample results/dprime_b0_p5.jsonl [--sample ...]
         [--md out.md] [--exclude none]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    cfg, qrows = {}, {}
    for l in open(path):
        r = json.loads(l)
        if r["kind"] == "config":
            cfg[r["config"]] = r
        else:
            qrows.setdefault(r["config"], {})[r["query_id"]] = r
    return {"cfg": cfg, "q": qrows}


def tau_b(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    conc = disc = tx = ty = 0
    for i, j in itertools.combinations(range(n), 2):
        dx, dy = x[i] - x[j], y[i] - y[j]
        if dx == 0 and dy == 0:
            continue
        if dx == 0:
            tx += 1
        elif dy == 0:
            ty += 1
        elif (dx > 0) == (dy > 0):
            conc += 1
        else:
            disc += 1
    den = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return (conc - disc) / den if den else None


def boot_ci(x: list[float], y: list[float], reps: int = 1000, seed: int = 7) -> tuple[float, float] | None:
    rnd = random.Random(seed)
    n = len(x)
    ts = []
    for _ in range(reps):
        idx = [rnd.randrange(n) for _ in range(n)]
        t = tau_b([x[i] for i in idx], [y[i] for i in idx])
        if t is not None:
            ts.append(t)
    if len(ts) < reps // 2:
        return None
    ts.sort()
    return ts[int(0.025 * len(ts))], ts[int(0.975 * len(ts)) - 1]


def sample_build_seconds(name: str) -> float | None:
    p = ROOT / "results" / "samples.jsonl"
    if not p.exists():
        return None
    name = name.removesuffix("_c4")
    best = None
    for l in p.read_text().splitlines():
        r = json.loads(l)
        if r.get("dst") == name:
            best = r.get("total_seconds_with_pk_vacuum")
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", required=True)
    ap.add_argument("--sample", action="append", required=True)
    ap.add_argument("--md")
    ap.add_argument("--exclude", default="", help="comma separated config ids to leave out (for example none)")
    a = ap.parse_args()
    ex = set(filter(None, a.exclude.split(",")))

    T = load(a.truth)
    lines = []
    for sp in a.sample:
        S = load(sp)
        ids = [c for c in T["cfg"] if c in S["cfg"] and c not in ex]
        if len(ids) < 5:
            print(f"{sp}: only {len(ids)} configurations in common, skipping")
            continue
        label = Path(sp).stem.replace("dprime_", "")
        tb = {c: T["cfg"][c]["build_seconds"] * 1000 for c in ids}
        sb = {c: S["cfg"][c]["build_seconds"] * 1000 for c in ids}
        tw = {c: T["cfg"][c]["workload_ms"] for c in ids}
        sw = {c: S["cfg"][c]["workload_ms"] for c in ids}
        full_cost = sum(tb[c] + tw[c] for c in ids) / 1000
        dp_cost = sum(sb[c] + sw[c] for c in ids) / 1000
        extra = sample_build_seconds(label)
        for name, ts, ss in (("A runtime", tw, sw), ("B build+runtime", {c: tb[c] + tw[c] for c in ids}, {c: sb[c] + sw[c] for c in ids})):
            x, y = [ts[c] for c in ids], [ss[c] for c in ids]
            t = tau_b(x, y)
            ci = boot_ci(x, y)
            tbest = min(ids, key=lambda c: ts[c])
            spick = min(ids, key=lambda c: ss[c])
            top3 = sorted(ids, key=lambda c: ss[c])[:3]
            lines.append({
                "dprime": label, "score": name, "n": len(ids),
                "tau": None if t is None else round(t, 3),
                "ci": None if ci is None else f"[{ci[0]:.2f}, {ci[1]:.2f}]",
                "top1": spick == tbest, "regret": round(ts[spick] / ts[tbest], 3),
                "top3": tbest in top3, "cost_x": round(full_cost / dp_cost, 1) if dp_cost else None,
                "cost_x_incl": round(full_cost / (dp_cost + extra), 1) if (dp_cost and extra) else None,
                "pick": spick, "truth_best": tbest,
            })

    hdr = "| D' | score | configs | tau | 95% CI | top-1 | regret | top-3 hit | cost reduction | incl. sample build | D' pick | full-database best |"
    sep = "|---|---|---:|---:|---|---|---:|---|---:|---:|---|---|"
    md = [hdr, sep]
    for r in lines:
        md.append(f"| {r['dprime']} | {r['score']} | {r['n']} | {r['tau']} | {r['ci']} | {'yes' if r['top1'] else 'no'} | {r['regret']} | "
                  f"{'yes' if r['top3'] else 'no'} | {r['cost_x']}x | {r['cost_x_incl'] if r['cost_x_incl'] else '-'}x | {r['pick']} | {r['truth_best']} |")
    text = "\n".join(md)
    print(text)
    if a.md:
        Path(a.md).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
