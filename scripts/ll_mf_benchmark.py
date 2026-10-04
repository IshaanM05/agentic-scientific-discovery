"""Multi-fidelity vs single-fidelity LabLoop on unseen worlds at equal total budget.

Arms (all offline, same hidden worlds, same budget; screens cost 0.2 and count against it):
  mf         screen + synthesis, chosen per film by expected information gain per unit cost
  sf_eig     same surrogate and rule, synthesis only (clean single-fidelity ablation)
  sf_greedy  same surrogate, LabLoop-style exploit/explore designer, synthesis only
  labloop    reference: the full LabLoop campaign (arena, hypotheses, replication), synthesis only
A hit = a film synthesised successfully that truly meets spec (distinct films). Screens never count.
Paired bootstrap: worlds are resampled (seeds averaged inside a world), 10,000 draws, 95% percentile CI.

    python scripts/ll_mf_benchmark.py --out runs/ll_mf_benchmark.json
"""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labloop.multifidelity import first_hit, hits_by_budget, run_mf_campaign  # noqa: E402

BUDGET = 60.0
GRID = [15, 30, 45, 60]


def _labloop_ref(world: int, seed: int) -> dict:
    from labloop.campaign import Config, run_campaign
    from labloop.chemistry import set_world
    tr = run_campaign(Config(seed=seed, budget=BUDGET, target_discoveries=99, record_maps=False, world=world))
    spent, seen, ev = 0.0, set(), []
    for rd in tr["rounds"]:
        for e in rd["experiments"]:
            spent += e["result"]["cost"]
            if e["true_hit"] and e["result"]["ok"] and e["idx"] not in seen:
                seen.add(e["idx"])
                ev.append({"spent": round(spent, 2), "idx": e["idx"]})
    set_world(0)
    return {"hit_events": ev}


def _job(a):
    world, seed, arm = a
    r = _labloop_ref(world, seed) if arm == "labloop" else run_mf_campaign(world, seed, BUDGET, arm)
    return {"world": world, "seed": seed, "arm": arm, "hits": hits_by_budget(r, GRID),
            "first": first_hit(r, BUDGET), "n_hits": len(r["hit_events"]),
            "n_screen": r.get("n_screen", 0), "n_synth": r.get("n_synth")}


def _world_means(rows, arm, key):
    """array (n_worlds,) of per-world means over seeds, worlds sorted."""
    worlds = sorted({r["world"] for r in rows})
    return np.array([np.mean([r[key] for r in rows if r["arm"] == arm and r["world"] == w]) for w in worlds])


def _boot(diff, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), (n, len(diff)))
    m = diff[idx].mean(1)
    return float(diff.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", default="1000-1019")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--no-labloop", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default="runs/ll_mf_benchmark.json")
    a = ap.parse_args()
    lo, hi = map(int, a.worlds.split("-"))
    arms = ["mf", "sf_eig", "sf_greedy"] + ([] if a.no_labloop else ["labloop"])
    jobs = [(w, s, arm) for w in range(lo, hi + 1) for s in range(a.seeds) for arm in arms]
    with Pool(a.procs) as p:
        rows = p.map(_job, jobs, chunksize=4)
    for r in rows:
        for b, h in zip(GRID, r["hits"]):
            r[f"h{b}"] = h
    summary = {"arms": {}, "paired": {}}
    keys = [f"h{b}" for b in GRID] + ["first"]
    for arm in arms:
        sub = [r for r in rows if r["arm"] == arm]
        summary["arms"][arm] = {k: round(float(np.mean([r[k] for r in sub])), 3) for k in keys}
        summary["arms"][arm]["no_hit_runs"] = int(sum(r["n_hits"] == 0 for r in sub))
        summary["arms"][arm]["mean_screens"] = round(float(np.mean([r["n_screen"] for r in sub])), 1)
    for base in [x for x in arms if x != "mf"]:
        summary["paired"][f"mf - {base}"] = {}
        for k in keys:
            d = _world_means(rows, "mf", k) - _world_means(rows, base, k)
            m, l, h = _boot(d)
            summary["paired"][f"mf - {base}"][k] = {"diff": round(m, 3), "ci95": [round(l, 3), round(h, 3)],
                                                    "worlds_mf_better": int((d > 0).sum() if k != "first" else (d < 0).sum()),
                                                    "n_worlds": int(len(d))}
    out = {"budget": BUDGET, "grid": GRID, "worlds": [lo, hi], "seeds": a.seeds, "summary": summary,
           "note": "first = units spent at first hit, censored at the budget when none; lower is better",
           "rows": rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
