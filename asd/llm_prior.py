"""T005/T009: LLM-prior-guided acquisition (named vs blinded view), matched to the T003 baselines.

The LLM is asked once per (seed, view) to give a prior estimate of the target for every pool candidate (batches of
BATCH rows). Its context holds the same 5 initial-design observations (the first N_INIT ids, raw y) in both views. The prior is static
(it never sees later reveals), so the arm is cheap and fully cached; this deviates from the "LLM sees all reveals" variant.
Acquisition: GP residual model, mean m(x)=a+b*prior(x) fitted (ridge toward b0=0.5) on revealed points, RBF GP on the residuals,
expected improvement. 'trust' = Spearman(prior, y) over revealed points, logged per step. Arm llm_greedy = rank by prior only.
Nothing here reads unrevealed yields: priors come from features + initial-design y only.
"""
import random

import numpy as np

from . import cli_llm
from .baselines import N_INIT, _X, _init, _revealed_vals
from .replay import FEATURES, BudgetExceeded, ReplayOracle

NAMES = {"c": "C", "mn": "Mn", "si": "Si", "cr": "Cr", "ni": "Ni", "mo": "Mo", "v": "V", "n": "N",
         "nb": "Nb", "co": "Co", "w": "W", "al": "Al", "ti": "Ti"}
BATCH = 52
MODEL = "claude-sonnet-5-5"


def cf_names(a="ni", b="mn"):
    """E1 counterfactual: labels of columns a and b swapped (labels only; data untouched)."""
    n = dict(NAMES)
    n[a], n[b] = NAMES[b], NAMES[a]
    return n


def _view_rows(o, seed, view, ids):
    raw = np.array([[o.features(c)[f] for f in FEATURES] for c in ids], float)
    if view in ("named", "cfnamed"):
        nm = cf_names() if view == "cfnamed" else NAMES
        return [", ".join(f"{nm[f]}={raw[k, j]:g}" for j, f in enumerate(FEATURES)) for k in range(len(ids))]
    perm = list(range(13))
    random.Random(1000 + seed).shuffle(perm)
    lo, hi = raw.min(0), raw.max(0)
    sc = (raw - lo) / np.where(hi - lo == 0, 1, hi - lo)
    return [", ".join(f"f{k + 1:02d}={sc[r, perm[k]]:.4f}" for k in range(13)) for r in range(len(ids))]


def get_prior(seed, view, init_vals, stats=None):
    """Return {id: prior estimate}. init_vals = {id: y} for the initial design."""
    o = ReplayOracle(seed, 60)
    ids = o.ids()
    desc = dict(zip(ids, _view_rows(o, seed, view, ids)))
    if view in ("named", "cfnamed"):
        head = ("Steel candidates are described by composition in wt% (balance Fe). Estimate the yield strength in MPa of each "
                "candidate. We want candidates with yield >= 2000 MPa. Known measurements:\n")
        tail = 'Reply JSON only: {"<id>": <MPa>, ...} with one number for every id listed.'
    else:
        head = ("Candidates are described by 13 features, each min-max scaled to [0,1]. Estimate the target value y of each "
                "candidate. We want candidates with y >= 2000. Known measurements:\n")
        tail = 'Reply JSON only: {"<id>": <y>, ...} with one number for every id listed.'
    known = "".join(f"{c}: {desc[c]} -> {init_vals[c]:.1f}\n" for c in init_vals)
    rest = [c for c in ids if c not in init_vals]
    prior, missing = {}, 0
    mean0 = float(np.mean(list(init_vals.values())))
    for b in range(0, len(rest), BATCH):
        chunk = rest[b:b + BATCH]
        q = head + known + "\nCandidates to estimate:\n" + "".join(f"{c}: {desc[c]}\n" for c in chunk) + "\n" + tail
        d = cli_llm.parse_json(cli_llm.ask(q, MODEL, seed, cache_dir=f"runs/t009/cache"))
        for c in chunk:
            try:
                prior[c] = float(d[c])
            except Exception:
                prior[c] = mean0
                missing += 1
    prior.update(init_vals)
    if stats is not None:
        stats["missing"] = missing
    return prior


def _rank(a):
    return np.argsort(np.argsort(a)).astype(float)


def _spearman(a, b):
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(_rank(a), _rank(b))[0, 1])


def _k(A, B, ls=2.5):
    d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
    return np.exp(-d2 / (2 * ls ** 2))


def _ei_resid(Xtr, ytr, ptr, Xte, pte, noise=1e-2, b0=0.5, lam=1.0):
    import math
    mu_y, sd_y = ytr.mean(), ytr.std() or 1.0
    y = (ytr - mu_y) / sd_y
    p_mu, p_sd = ptr.mean(), ptr.std() or 1.0
    pt, pe = (ptr - p_mu) / p_sd, (pte - p_mu) / p_sd
    # ridge toward b0 on the standardized prior: b = argmin sum (y - a - b p)^2 + lam (b-b0)^2
    a = y.mean()
    b = (np.sum((y - a) * pt) + lam * b0) / (np.sum(pt ** 2) + lam)
    r = y - (a + b * pt)
    K = _k(Xtr, Xtr) + noise * np.eye(len(Xtr))
    Ks = _k(Xte, Xtr)
    mu = a + b * pe + Ks @ np.linalg.solve(K, r)
    v = np.linalg.solve(K, Ks.T)
    s = np.sqrt(np.clip(1.0 - (Ks * v.T).sum(1), 1e-9, None))
    best = y.max()
    z = (mu - best) / s
    pdf = np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    cdf = 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))
    return s * (z * cdf + pdf), float(b)


def run(arm, seed, view, budget=60, ledger_path=None):
    """arm in {llm_bo, llm_greedy}. Returns run record incl. trust trace."""
    o = ReplayOracle(seed, budget, ledger_path=ledger_path)
    _init(o)
    stats = {}
    prior = get_prior(seed, view, _revealed_vals(o), stats)
    ids, X = _X(o)
    idx = {c: i for i, c in enumerate(ids)}
    P = np.array([prior[c] for c in ids])
    trust = []
    try:
        while o.spent < budget:
            vals = _revealed_vals(o)
            tr = [idx[c] for c in vals]
            te = [idx[c] for c in ids if c not in vals]
            ytr = np.array([vals[c] for c in vals])
            trust.append(round(_spearman(P[tr], ytr), 3))
            if arm == "llm_greedy":
                o.run(ids[te[int(np.argmax(P[te]))]])
            else:
                ei, b = _ei_resid(X[tr], ytr, P[tr], X[te], P[te])
                o.run(ids[te[int(np.argmax(ei))]])
    except BudgetExceeded:
        pass
    h = o.hits_by_step
    first_pick = (N_INIT + 1) in h
    return {"arm": arm, "view": view, "seed": seed, "budget": budget, "n_init": N_INIT, "spent": o.spent,
            "n_hits": len(h), "hits_by_step": h, "hits_at": {str(k): sum(x <= k for x in h) for k in (20, 40, 60)},
            "first_hit": h[0] if h else budget + 1, "first_pick_hit": first_pick,
            "prior_missing": stats["missing"], "trust_final": trust[-1], "trust_trace_every10": trust[::10], "trust_trace": trust}
