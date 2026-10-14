#!/usr/bin/env python3
"""Compare HypoPG EXPLAIN jsonl files (from explain_configs.py) to each other and to timed rankings.

Usage:
  python3 scripts/compare_explain.py --truth-explain results/explain_tpcds_sf1.jsonl \\
      --sample-explain results/explain_tpcds_sf1_sys_p5.jsonl \\
      --truth-time results/truth_sf1.jsonl --md results/distill_explain.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rank_metrics import load as load_time, tau_b  # noqa: E402

NONE = "none:none"
WINNER = "grok-4-7:small-dimension-filters"
RUNNER = "claude-opus-5:light_dimension_covering"


def load_explain(path: str) -> dict:
    cfg, qrows = {}, {}
    for l in open(path):
        r = json.loads(l)
        if r["kind"] == "config":
            cfg[r["config"]] = r
        else:
            qrows.setdefault(r["config"], {})[r["query_id"]] = r
    return {"cfg": cfg, "q": qrows}


def sign(x: float) -> int:
    if x > 1e-9:
        return 1
    if x < -1e-9:
        return -1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth-explain", required=True)
    ap.add_argument("--sample-explain", action="append", required=True)
    ap.add_argument("--truth-time", default=str(ROOT / "results" / "truth_sf1.jsonl"))
    ap.add_argument("--md")
    a = ap.parse_args()

    TE = load_explain(a.truth_explain)
    TT = load_time(a.truth_time)
    lines = ["# HypoPG EXPLAIN on existing schemas", ""]

    ids_t = [c for c in TE["cfg"] if TE["cfg"][c].get("n_ok")]
    cost_t = {c: TE["cfg"][c]["cost_sum"] for c in ids_t if "cost_sum" in TE["cfg"][c]}
    time_t = {c: TT["cfg"][c]["workload_ms"] for c in ids_t if c in TT["cfg"]}
    common = [c for c in ids_t if c in cost_t and c in time_t]
    t_cost_vs_time = tau_b([cost_t[c] for c in common], [time_t[c] for c in common])
    pick_cost = min(common, key=lambda c: cost_t[c])
    pick_time = min(common, key=lambda c: time_t[c])
    lines.append(f"Full database: Kendall tau of HypoPG cost ranking vs measured time ranking: **{t_cost_vs_time:.2f}** over {len(common)} configs.")
    lines.append(f"Cost pick: `{pick_cost}`. Time pick: `{pick_time}`.")
    lines.append("")

    # Q22 costs on full
    def qcost(E, c, q):
        r = E["q"].get(c, {}).get(q, {})
        return r.get("cost")

    lines.append("## Q22 (the query that decides top-1)")
    lines.append("")
    lines.append("| schema | none cost | Grok cost | Opus cost | Grok/none | shape none | shape Grok | Grok shape = full Grok |")
    lines.append("|---|---:|---:|---:|---:|---|---|---|")

    rows = [("full", TE)]
    samples = []
    for sp in a.sample_explain:
        E = load_explain(sp)
        label = Path(sp).stem.replace("explain_", "")
        rows.append((label, E))
        samples.append((label, E, sp))

    full_g_shape = TE["q"][WINNER][22].get("shape_hash")
    full_n_shape = TE["q"][NONE][22].get("shape_hash")
    for label, E in rows:
        cn, cg, co = qcost(E, NONE, 22), qcost(E, WINNER, 22), qcost(E, RUNNER, 22)
        if cn is None or cg is None:
            continue
        sg = E["q"][WINNER][22].get("shape_hash")
        sn = E["q"][NONE][22].get("shape_hash")
        ratio = cg / cn if cn else None
        lines.append(
            f"| {label} | {cn:.0f} | {cg:.0f} | {co:.0f} | {ratio:.3f} | "
            f"{sn} | {sg} | {'yes' if sg == full_g_shape else 'no'} |"
        )
    lines.append("")

    lines.append("## Plan-shape agreement and cost ranking")
    lines.append("")
    lines.append("Shape ignores HypoPG index names. Cost tau is the sample's cost ranking vs the full database's cost ranking (both noise-free). Time tau is copied from the timed protocol.")
    lines.append("")
    lines.append("| D' | shape agree | cost-sign agree | cost tau vs full cost | cost tau vs full time | cost pick |")
    lines.append("|---|---:|---:|---:|---:|---|")

    qids = list(range(1, 100))
    for label, E, sp in samples:
        ids = [c for c in common if c in E["cfg"] and "cost_sum" in E["cfg"][c]]
        shape_n = shape_ok = 0
        sign_n = sign_ok = 0
        for c in ids:
            for q in qids:
                tq = TE["q"].get(c, {}).get(q, {})
                sq = E["q"].get(c, {}).get(q, {})
                if tq.get("shape_hash") and sq.get("shape_hash"):
                    shape_n += 1
                    if tq["shape_hash"] == sq["shape_hash"]:
                        shape_ok += 1
                tn = TE["q"].get(NONE, {}).get(q, {})
                sn = E["q"].get(NONE, {}).get(q, {})
                if tq.get("cost") is not None and sq.get("cost") is not None and tn.get("cost") is not None and sn.get("cost") is not None:
                    sign_n += 1
                    if sign(tq["cost"] - tn["cost"]) == sign(sq["cost"] - sn["cost"]):
                        sign_ok += 1
        cx = [cost_t[c] for c in ids]
        cy = [E["cfg"][c]["cost_sum"] for c in ids]
        tx = [time_t[c] for c in ids]
        t_cc = tau_b(cx, cy)
        t_ct = tau_b(tx, cy)
        pick = min(ids, key=lambda c: E["cfg"][c]["cost_sum"])
        lines.append(
            f"| {label} | {shape_ok}/{shape_n} ({100*shape_ok/shape_n:.0f}%) | "
            f"{sign_ok}/{sign_n} ({100*sign_ok/sign_n:.0f}%) | {t_cc:.2f} | {t_ct:.2f} | {pick} |"
        )
    lines.append("")
    lines.append(f"Full Grok Q22 shape_hash `{full_g_shape}` (Index Only Scan on date_dim). Full none `{full_n_shape}` (Seq Scan on date_dim).")
    lines.append("")

    text = "\n".join(lines) + "\n"
    print(text)
    if a.md:
        Path(a.md).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
