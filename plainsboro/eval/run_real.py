"""Transfer test on real Kepler KOIs (likelihood tables calibrated on synthetic data only).

    python -m plainsboro.data.kepler --per-class 12     # once: downloads ~48 light curves
    python -m plainsboro.eval.run_real

Reported separately from the synthetic benchmark (design 12.4): small n, coarse labels,
and a synthetic-to-real calibration gap, so treat it as a sanity check, not the headline.
"""
from __future__ import annotations

import json

import numpy as np

from ..config import HYP_LABELS, RESULTS, experiment
from ..data.gatekeeper import load_set
from ..planner.likelihood import load_tables
from ..planner.outcomes import load_outcomes
from .analyze import ci
from .run_benchmark import CONDITIONS, run_condition


def loo_tables(syn, oc, labels, train_ids, K: float):
    """Synthetic tables as a prior (K pseudo-counts per class) + real outcome counts of train_ids.

    'H4|H5' labels contribute half a count to each of H4 and H5. Class prior = real training base rates.
    """
    from ..config import HYP_IDS
    from ..planner.likelihood import LikelihoodTables
    from ..vetting.registry import REGISTRY
    counts = {}
    for tid in REGISTRY:
        tab = syn.table(tid)
        counts[tid] = {h: list(K * tab[k]) for k, h in enumerate(HYP_IDS)}
    prior = {h: 0.0 for h in HYP_IDS}
    for j in train_ids:
        hs = labels[j].split("|")
        for h in hs:
            prior[h] += 1 / len(hs)
            for tid in REGISTRY:
                b = oc[j][(tid, 3.0)]["outcome_bin"]
                if b is not None:
                    counts[tid][h][b] += 1 / len(hs)
    return LikelihoodTables(counts, prior, alpha=0.5, temper=syn.temper,
                            meta={"loo": True, "K": K, "n_train": len(train_ids)})


def main():
    cfg = experiment()
    rng = np.random.default_rng(cfg["seeds"]["bootstrap"])
    gk = load_set("real")
    oc = load_outcomes(gk, workers=4)
    tabs = load_tables()
    ids = gk.target_ids()
    out = {}
    rows_all = []
    for name, kw in CONDITIONS.items():
        rows = run_condition(name, kw, gk, oc, tabs, ids, threshold=cfg["stopping"]["posterior_threshold"])
        rows_all += rows
        acc = [r["correct"] for r in rows]
        out[name] = {"n": len(rows), "accuracy": float(np.mean(acc)), "accuracy_ci90": ci(acc, rng),
                     "mean_cost": float(np.mean([r["cost"] for r in rows])),
                     "needs_human_rate": float(np.mean([r["needs_human"] for r in rows])),
                     "per_class": {t: float(np.mean([r["correct"] for r in rows if r["truth"] == t]))
                                   for t in sorted({r["truth"] for r in rows})},
                     "confident_wrong": int(sum((not r["correct"]) and r["top"] >= 0.9 for r in rows))}
    # ---- Wilson's recalibration, leave-one-out: each target is scored with tables that mix the
    # synthetic tables (as a Dirichlet prior of strength K per class) with the OTHER real KOIs' outcomes.
    labels = {i: gk._label(i, "evaluator") for i in ids}
    K = 8.0
    for name in ("B3-planner", "P-house-team"):
        rows = []
        for i in ids:
            t2 = loo_tables(tabs, oc, labels, [j for j in ids if j != i], K)
            rows += run_condition(f"{name}+real-LOO", CONDITIONS[name], gk, oc, t2, [i],
                                  threshold=cfg["stopping"]["posterior_threshold"], n_draws=20)
        rows_all += rows
        acc = [r["correct"] for r in rows]
        out[f"{name}+real-LOO"] = {
            "n": len(rows), "accuracy": float(np.mean(acc)), "accuracy_ci90": ci(acc, rng),
            "mean_cost": float(np.mean([r["cost"] for r in rows])),
            "needs_human_rate": float(np.mean([r["needs_human"] for r in rows])),
            "per_class": {t: float(np.mean([r["correct"] for r in rows if r["truth"] == t]))
                          for t in sorted({r["truth"] for r in rows})},
            "confident_wrong": int(sum((not r["correct"]) and r["top"] >= 0.9 for r in rows))}
    with open(RESULTS / "benchmark" / "real_records.jsonl", "w", encoding="utf-8") as f:
        for r in rows_all:
            f.write(json.dumps(r) + "\n")
    with open(RESULTS / "real_summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    classes = sorted(next(iter(out.values()))["per_class"])
    L = ["## Transfer test: real Kepler KOIs", "",
         f"n = {len(ids)} anonymized KOIs (one quarter each), dispositions from the NASA Exoplanet Archive cumulative "
         "table used as hidden labels. Likelihood tables are the synthetic-calibrated ones (no real-data tuning). "
         "'H4|H5' = archive 'not transit-like' false positives; either verdict counts as correct.", "",
         "| Condition | Accuracy [90% CI] | Mean cost | needs_human | confident & wrong | " +
         " | ".join(classes) + " |", "|---" * (5 + len(classes)) + "|"]
    for name, m in out.items():
        L.append(f"| {name} | {m['accuracy']:.2f} [{m['accuracy_ci90'][0]:.2f}, {m['accuracy_ci90'][1]:.2f}] | "
                 f"{m['mean_cost']:.2f} | {m['needs_human_rate']:.2f} | {m['confident_wrong']} | " +
                 " | ".join(f"{m['per_class'][c]:.2f}" for c in classes) + " |")
    L += ["", "Class key: " + "; ".join(f"{h} = {HYP_LABELS[h]}" for h in ("H1", "H2", "H3")) +
          "; H4|H5 = not transit-like.", "",
          "`+real-LOO` rows: Wilson's recalibration. Each target is scored with tables built from the synthetic "
          "tables (8 pseudo-counts per class) plus the outcomes of the *other* 47 real KOIs (leave-one-out, so "
          "no target ever sees its own label). The class prior becomes the real set's stratified base rate.", ""]
    (RESULTS / "REAL_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
