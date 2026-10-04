"""Precompute test outcomes for a case set (so every condition replays identical evidence).

For detrending-sensitive tests we also store the result under an alternative
detrending window (window_factor=5); Foreman uses it as a sensitivity control.
"""
from __future__ import annotations

import os
import pickle
from concurrent.futures import ProcessPoolExecutor

from ..config import DATA
from ..vetting.registry import REGISTRY, run_test

ALT_WINDOW = 5.0


def target_outcomes(target) -> dict:
    out = {}
    for tid, td in REGISTRY.items():
        out[(tid, 3.0)] = run_test(tid, target, 3.0)
        if td.detrend_sensitive:
            out[(tid, ALT_WINDOW)] = run_test(tid, target, ALT_WINDOW)
    return out


def _work(target):
    return target.target_id, target_outcomes(target)


def load_outcomes(gk, rebuild: bool = False, workers: int | None = None) -> dict:
    path = DATA / f"{gk.name}_outcomes.pkl"
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            return pickle.load(f)
    targets = [gk.get_target(i) for i in gk.target_ids()]
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    res = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for tid, o in ex.map(_work, targets, chunksize=8):
            res[tid] = o
    with open(path, "wb") as f:
        pickle.dump(res, f)
    return res
