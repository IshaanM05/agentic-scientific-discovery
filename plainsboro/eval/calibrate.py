"""Build likelihood tables from the calibration set only (design 9.2, 12.6).

    python -m plainsboro.eval.calibrate [--rebuild]
"""
from __future__ import annotations

import argparse
import json
import time

from ..config import HYP_IDS, RESULTS
from ..data.gatekeeper import load_set
from ..planner.likelihood import build_tables, fit_temper, save_tables
from ..planner.outcomes import load_outcomes
from ..vetting.registry import REGISTRY


def calibrate(rebuild: bool = False, verbose: bool = True):
    t0 = time.time()
    gk = load_set("calibration", rebuild=rebuild)
    outcomes = load_outcomes(gk, rebuild=rebuild)
    ids = gk.target_ids()
    labels = {i: gk._label(i, "calibration") for i in ids}
    tau, scores = fit_temper(outcomes, labels, ids)
    tab = build_tables(outcomes, labels, ids)
    tab.temper = tau
    tab.meta.update(temper_cv_logloss={str(k): round(v, 4) for k, v in scores.items()},
                    split="calibration", n_cases=len(ids))
    save_tables(tab)
    if verbose:
        print(f"calibration: {len(ids)} cases in {time.time() - t0:.1f}s; temper={tau} (CV log-loss {scores[tau]:.3f})")
        for tid in REGISTRY:
            t = tab.table(tid)
            print(f"  {tid:14s} " + " | ".join(f"{h}:" + ",".join(f"{x:.2f}" for x in t[i]) for i, h in enumerate(HYP_IDS)))
    with open(RESULTS / "calibration_summary.json", "w", encoding="utf-8") as f:
        json.dump({"n": len(ids), "temper": tau, "cv_logloss": scores,
                   "class_counts": tab.prior_counts}, f, indent=1)
    return tab


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    calibrate(ap.parse_args().rebuild)
