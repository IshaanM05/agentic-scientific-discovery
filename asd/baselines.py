"""Non-LLM baselines on the steel_strength replay oracle (T003). Offline, deterministic given the seed.

Matched conditions for every arm: same pool (ReplayOracle(seed) permutation), same budget (60), same
initial design (the first N_INIT ids of the seed's shuffled pool), same seeds. Arms differ only
in how they choose experiments after the initial design. Nothing here reads unrevealed yields.
"""
import math
import random

import numpy as np

from .replay import FEATURES, BudgetExceeded, ReplayOracle, experiments_to_k_hits

N_INIT = 5
BUDGET = 60


def _init(o):
    for cid in o.ids()[:N_INIT]:
        o.run(cid)


def _X(o):
    ids = o.ids()
    X = np.array([[o.features(c)[f] for f in FEATURES] for c in ids], float)
    sd = X.std(0)
    sd[sd == 0] = 1.0
    return ids, (X - X.mean(0)) / sd


def _revealed_vals(o):
    return {c: r["value"] for c, r in o._revealed.items()}


def random_arm(o, seed):
    _init(o)
    rest = o.ids()[N_INIT:]
    random.Random(f"rand{seed}").shuffle(rest)
    for c in rest:
        if o.spent >= o.budget:
            break
        o.run(c)


def ofat_arm(o, seed):
    """One-factor-at-a-time: from the best point so far, vary one feature (cycling) while holding the
    others as close as possible; step to the nearest unrevealed candidate that changes only that feature."""
    _init(o)
    ids, X = _X(o)
    idx = {c: i for i, c in enumerate(ids)}
    j = 0
    while o.spent < o.budget:
        vals = _revealed_vals(o)
        base = max(vals, key=vals.get)
        bi = idx[base]
        cand = [c for c in ids if c not in vals]
        best_c, best_s = None, math.inf
        for _ in range(len(FEATURES)):
            for c in cand:
                d = X[idx[c]] - X[bi]
                other = float(np.linalg.norm(np.delete(d, j)))
                move = abs(d[j])
                if move < 1e-9:
                    continue
                s = other / move  # small = mostly a single-factor change
                if s < best_s:
                    best_c, best_s = c, s
            if best_c:
                break
            j = (j + 1) % len(FEATURES)
        if best_c is None:
            best_c = cand[0]
        o.run(best_c)
        j = (j + 1) % len(FEATURES)


def _gp_ei(Xtr, ytr, Xte, ls=2.5, noise=1e-2):
    def k(A, B):
        d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
        return np.exp(-d2 / (2 * ls ** 2))
    mu_y, sd_y = ytr.mean(), ytr.std() or 1.0
    y = (ytr - mu_y) / sd_y
    K = k(Xtr, Xtr) + noise * np.eye(len(Xtr))
    Ks = k(Xte, Xtr)
    Kinv_y = np.linalg.solve(K, y)
    mu = Ks @ Kinv_y
    v = np.linalg.solve(K, Ks.T)
    var = np.clip(1.0 - (Ks * v.T).sum(1), 1e-9, None)
    s = np.sqrt(var)
    best = y.max()
    z = (mu - best) / s
    pdf = np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    cdf = 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))
    return s * (z * cdf + pdf)


def bo_arm(o, seed):
    """Pure BO: RBF GP on standardized composition features, expected improvement over candidates."""
    _init(o)
    ids, X = _X(o)
    idx = {c: i for i, c in enumerate(ids)}
    while o.spent < o.budget:
        vals = _revealed_vals(o)
        tr = [idx[c] for c in vals]
        te = [idx[c] for c in ids if c not in vals]
        ei = _gp_ei(X[tr], np.array([vals[c] for c in vals]), X[te])
        o.run(ids[te[int(np.argmax(ei))]])


ARMS = {"random": random_arm, "ofat": ofat_arm, "bo": bo_arm}


def run_arm(arm, seed, budget=BUDGET, ledger_path=None, fn=None):
    o = ReplayOracle(seed, budget, ledger_path=ledger_path)
    try:
        (fn or ARMS[arm])(o, seed)
    except BudgetExceeded:
        pass
    h = o.hits_by_step
    return {"arm": arm, "seed": seed, "budget": budget, "n_init": N_INIT, "spent": o.spent,
            "hits_by_step": h, "n_hits": len(h),
            "to_k": {str(k): experiments_to_k_hits(h, k, budget) for k in (1, 3, 5)}}
