"""Matched-condition benchmark (design 12).

All conditions see the same blind targets, the same precomputed test outcomes
(identical evidence), the same registry, costs, budget and stopping threshold.
Only the orchestration differs.

    python -m plainsboro.eval.run_benchmark [--n 240] [--quick]
"""
from __future__ import annotations

import argparse
import itertools
import json
import time

import numpy as np

from ..config import HYP_IDS, RESULTS, experiment
from ..data.gatekeeper import load_set
from ..lab import Lab
from ..planner.likelihood import load_tables
from ..planner.outcomes import load_outcomes
from ..planner.posterior import update
from ..record.ledger import Ledger
from ..vetting.registry import REGISTRY

CONDITIONS = {
    # name: Lab kwargs
    "B1-checklist": dict(strategy="fixed", use_foreman=False, use_house=False, use_cameron=False, parallel=False),
    "B2-random": dict(strategy="random", use_foreman=False, use_house=False, use_cameron=False, parallel=False),
    "B3-planner": dict(strategy="eig", use_foreman=False, use_house=False, use_cameron=False, parallel=False),
    "P-house-team": dict(strategy="eig"),
}
ABLATIONS = {
    "A-no-foreman": dict(strategy="eig", use_foreman=False),
    "A-no-house": dict(strategy="eig", use_house=False),
    "A-no-cameron": dict(strategy="eig", use_cameron=False),
    "A-no-parallel": dict(strategy="eig", parallel=False),
    "A-adaptive": dict(strategy="eig", adaptive=True),
}


def compact(rec: dict, truth: str) -> dict:
    v = rec["verdict"]
    ok = truth.split("|")          # real-data "H4|H5" (not transit-like) accepts either verdict
    traj = [{"tests": t.get("tests", 0), "cost": t.get("cost", 0.0),
             "leader": max(t["posterior"], key=t["posterior"].get),
             "top": max(t["posterior"].values()), "p_true": sum(t["posterior"][h] for h in ok)}
            for t in rec["trajectory"]]
    for t in traj:
        t["leader_correct"] = t["leader"] in ok
    return {"target_id": rec["target_id"], "condition": rec["condition"], "truth": truth, "label": v["label"],
            "correct": v["label"] in ok, "top": v["top_posterior"], "posterior": v["posterior"],
            "interval": v["interval"], "tests": rec["tests_used"], "cost": round(rec["cost_used"], 3),
            "needs_human": v["needs_human"], "escalations": rec["escalations"], "wall_clock_s": rec["wall_clock_s"],
            "trajectory": traj, "tests_run": [t["test_id"] + ("@rerun" if t.get("rerun") else "")
                                              for t in rec["whiteboard"]["tests_run"]]}


def run_condition(name, kwargs, gk, outcomes, tables, ids, threshold=None, n_draws=30, ledger_path=None,
                  budget_override=None):
    cfg = experiment()
    if budget_override:
        cfg = json.loads(json.dumps(cfg))
        cfg["budget"].update(budget_override)
    lab = Lab(tables, cfg, name=name, outcome_cache=outcomes, threshold=threshold, n_interval_draws=n_draws,
              gatekeeper=gk, ledger=Ledger(ledger_path), rng_seed=cfg["seeds"]["random_baseline"], **kwargs)
    out = []
    for i in ids:
        rec = lab.run(gk.get_target(i))
        truth = gk._label(i, "evaluator")
        out.append(compact(rec, truth))
    return out


def oracle(gk, outcomes, tables, ids, threshold, budget):
    """Hindsight-optimal: cheapest test subset (within budget) whose posterior is correct (and confident)."""
    tids = list(REGISTRY)
    subsets = []
    for r in range(1, budget["max_tests"] + 1):
        for comb in itertools.combinations(tids, r):
            c = sum(REGISTRY[t].cost for t in comb)
            if c <= budget["cost_units_max"] + 1e-9:
                subsets.append((c, comb))
    subsets.sort()
    res = []
    for i in ids:
        truth = gk._label(i, "evaluator")
        ti = HYP_IDS.index(truth)
        best_conf, best_any = None, None
        for c, comb in subsets:
            p = tables.prior()
            for t in comb:
                b = outcomes[i][(t, 3.0)]["outcome_bin"]
                if b is not None:
                    p = update(p, tables.likelihood(t, b), 1.0, tables.temper)
            if int(np.argmax(p)) == ti:
                if best_any is None:
                    best_any = (c, len(comb))
                if p[ti] >= threshold:
                    best_conf = (c, len(comb))
                    break
        res.append({"target_id": i, "truth": truth, "confident_cost": best_conf[0] if best_conf else None,
                    "any_correct_cost": best_any[0] if best_any else None,
                    "confident_tests": best_conf[1] if best_conf else None})
    return res


def main(n: int | None = None, quick: bool = False, ablations: bool = True):
    cfg = experiment()
    t0 = time.time()
    tables = load_tables()
    gk = load_set("blind")
    print(f"[bench] blind set: {len(gk.target_ids())} targets; computing/caching outcomes ...", flush=True)
    outcomes = load_outcomes(gk)
    ids = gk.target_ids()[: n or None]
    out_dir = RESULTS / "benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)
    thr0 = cfg["stopping"]["posterior_threshold"]
    sweep = [0.6, 0.9] if quick else cfg["benchmark"]["threshold_sweep"]
    if thr0 not in sweep:
        sweep = sorted(set(sweep) | {thr0})

    all_rows = []
    for name, kw in CONDITIONS.items():
        for thr in sweep:
            ledger_path = out_dir / "ledger_P.jsonl" if (name == "P-house-team" and thr == thr0) else None
            if ledger_path and ledger_path.exists():
                ledger_path.unlink()
            rows = run_condition(name, kw, gk, outcomes, tables, ids, threshold=thr, ledger_path=ledger_path)
            for r in rows:
                r["threshold"] = thr
            all_rows += rows
            acc = np.mean([r["correct"] for r in rows])
            cost = np.mean([r["cost"] for r in rows])
            print(f"[bench] {name:14s} thr={thr:.2f}: acc={acc:.3f} mean cost={cost:.2f} "
                  f"mean tests={np.mean([r['tests'] for r in rows]):.2f}", flush=True)
        # no-early-stop trajectories for accuracy@k
        rows = run_condition(name, kw, gk, outcomes, tables, ids, threshold=1.01, n_draws=5)
        for r in rows:
            r["threshold"] = 1.01
        all_rows += rows

    if ablations:
        for name, kw in ABLATIONS.items():
            rows = run_condition(name, kw, gk, outcomes, tables, ids, threshold=thr0)
            for r in rows:
                r["threshold"] = thr0
            all_rows += rows
            print(f"[bench] {name:14s} thr={thr0:.2f}: acc={np.mean([r['correct'] for r in rows]):.3f} "
                  f"mean cost={np.mean([r['cost'] for r in rows]):.2f}", flush=True)

    orc = oracle(gk, outcomes, tables, ids, thr0, cfg["budget"])
    with open(out_dir / "records.jsonl", "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r) + "\n")
    with open(out_dir / "oracle.json", "w", encoding="utf-8") as f:
        json.dump(orc, f)
    with open(out_dir / "label_access_audit.json", "w", encoding="utf-8") as f:
        callers = {}
        for e in gk.label_access_log:
            callers[e["caller"]] = callers.get(e["caller"], 0) + 1
        json.dump({"label_reads_by_caller": callers,
                   "note": "agents never read labels; only the evaluator, oracle and Wilson adaptive mode"}, f, indent=1)
    print(f"[bench] done in {time.time() - t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-ablations", action="store_true")
    a = ap.parse_args()
    main(a.n, a.quick, not a.no_ablations)
