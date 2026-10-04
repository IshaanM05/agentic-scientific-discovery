"""Shared helpers for the ll_* scripts: offline setup, per-seed benchmark runs, bootstrap.

Offline and deterministic. Hidden truth is read only to SCORE runs, never passed to agents.
"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LABLOOP_OFFLINE"] = "1"

import numpy as np  # noqa: E402

from labloop import benchmark as B  # noqa: E402
from labloop.campaign import Config, run_campaign  # noqa: E402
from labloop.chemistry import set_world, space_arrays  # noqa: E402

BUDGET = 60.0
WORLDS = [1000 + s for s in range(20)]
MAIN = ["Random", "Grad-student OFAT", "Pure BO (no literature)", "LabLoop (full)"]
ABL = ["LabLoop − arena", "LabLoop − negative memory", "LabLoop − literature prior"]


def world_of(seed: int) -> int:
    return 1000 + seed


def run_curve(name: str, seed: int, budget: float = BUDGET):
    """Return (curve of distinct true hits per integer budget unit, trace or None)."""
    set_world(world_of(seed))
    if name == "Random":
        return B.run_random(seed, budget), None
    if name == "Grad-student OFAT":
        return B.run_ofat(seed, budget), None
    cfg = Config(seed=seed, budget=budget, target_discoveries=99, record_maps=False, label=name,
                 world=world_of(seed), **B.STRATEGIES[name])
    trace = run_campaign(cfg)
    costs, flags, seen = [], [], set()
    for rd in trace["rounds"]:
        for e in rd["experiments"]:
            costs.append(e["result"]["cost"])
            flags.append(bool(e["true_hit"]) and e["idx"] not in seen)
            seen.add(e["idx"])
    return B._curve_from(costs, flags, budget), trace


def time_to(curve, k, censor):
    """First integer budget unit with >= k hits; censor value if never reached."""
    return next((b for b, v in enumerate(curve) if v >= k), censor)


def boot_ci(x, stat=np.mean, n=10000, seed=0, alpha=0.05):
    """Percentile bootstrap CI of stat(x) over resampled pairs (index-aligned arrays)."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (n, len(x)))
    vals = np.array([stat(x[i]) for i in idx])
    return float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2)))
