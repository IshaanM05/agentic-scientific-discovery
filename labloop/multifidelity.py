"""Multi-fidelity testing for LabLoop: a cheap noisy 'screen' beside full synthesis.

Additive module: nothing in the existing LabLoop code is changed. The hidden world is the same
(``chemistry.set_world``); the wrapper lab only adds a second, cheaper test whose noise is large.

* ``MFLab``          screen (cost 0.2, noisy bandgap, coarse stability proxy) and synthesis
                     (cost 1 / 1.5). Every measurement is a pure function of
                     (world, seed, film, test kind, repeat number): deterministic, order independent.
                     Only noisy measurements leave the lab, never true bandgap / T80 / hit flags.
* ``MFSurrogate``    LabLoop's Surrogate with a heteroscedastic fit: every observation carries its
                     known noise variance, so screens enter the Gaussian process with inflated noise.
* ``plan_actions``   picks screen vs synthesis per film by expected information gain per unit cost.
* ``run_mf_campaign`` offline campaign loop used by the benchmark (arms: mf, sf_eig, sf_greedy).
"""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
from scipy.stats import norm
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

from .chemistry import LOG_T80_MIN, TARGET, composition_space, set_world, space_arrays
from .lab import PerovskiteReplayLab, make_protocol, safety_review
from .surrogate import Surrogate

SCREEN_COST = 0.2
SCREEN_EG_SD = 0.06     # eV, noisy optical bandgap estimate
SCREEN_LT_SD = 0.35     # log10 hours, coarse stability proxy ...
SCREEN_LT_STEP = 0.25   # ... reported in coarse bins
SYNTH_EG_SD = 0.015     # matches PerovskiteReplayLab defaults
SYNTH_LT_SD = 0.10
EPS = 1e-12


def synth_cost(idx: int) -> float:
    return 1.5 if composition_space()[idx].sn > 0 else 1.0


def _seed(world: int, seed: int, idx: int, kind: str, n: int) -> int:
    h = hashlib.sha256(f"mf|{world}|{seed}|{idx}|{kind}|{n}".encode()).digest()
    return int.from_bytes(h[:8], "little")


class MFLab:
    """Two-fidelity wrapper over the hidden-physics lab. Stateless apart from repeat counters."""

    def __init__(self, world: int, seed: int, counts: dict | None = None):
        self.world, self.seed = int(world), int(seed)
        self.counts = {"synth": {}, "screen": {}}
        for k in self.counts:
            self.counts[k] = {int(i): int(n) for i, n in ((counts or {}).get(k, {})).items()}
        set_world(self.world)
        self._eg_true, self._lt_true = space_arrays()[3:5]

    def export_counts(self) -> dict:
        return {k: {str(i): n for i, n in v.items()} for k, v in self.counts.items()}

    def _next(self, kind: str, idx: int) -> int:
        n = self.counts[kind].get(idx, 0)
        self.counts[kind][idx] = n + 1
        return n

    def screen(self, idx: int) -> dict:
        n = self._next("screen", idx)
        rng = np.random.default_rng(_seed(self.world, self.seed, idx, "screen", n))
        eg = float(self._eg_true[idx] + rng.normal(0, SCREEN_EG_SD))
        lt = float(self._lt_true[idx] + rng.normal(0, SCREEN_LT_SD))
        lt = round(lt / SCREEN_LT_STEP) * SCREEN_LT_STEP
        return {"idx": idx, "fid": "screen", "ok": True, "eg": round(eg, 3), "lt": round(lt, 3),
                "cost": SCREEN_COST, "repeat": n}

    def synthesize(self, idx: int) -> dict:
        n = self._next("synth", idx)
        c = composition_space()[idx]
        res = PerovskiteReplayLab(seed=_seed(self.world, self.seed, idx, "synth", n) % (2 ** 32)).run(
            make_protocol(c))
        return {"idx": idx, "fid": "synth", "ok": bool(res.ok),
                "eg": None if res.bandgap_ev is None else round(res.bandgap_ev, 3),
                "lt": None if res.log_t80 is None else round(res.log_t80, 3),
                "phase": res.phase, "cost": res.cost, "repeat": n}


# --------------------------------------------------------------------------- surrogate

class MFSurrogate(Surrogate):
    """Surrogate whose GPs take a per-observation noise variance (screens are noisier)."""

    def _fit_het(self, idx, y, prior, noise_var, length):
        resid = y - prior[idx]
        kernel = ConstantKernel(0.1, (1e-3, 4.0)) * Matern(length, (0.15, 4.0), nu=2.5)
        gp = GaussianProcessRegressor(kernel, alpha=noise_var + 1e-6, normalize_y=False,
                                      n_restarts_optimizer=0, random_state=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            gp.fit(self.X[idx], resid)
        m, s = gp.predict(self.X, return_std=True)
        return prior + m, np.maximum(s, 1e-3)

    def fit(self, observations: list[dict]):
        """observations: dicts with idx, fid ('synth'|'screen'), ok, eg, lt."""
        ok = [o for o in observations if o["ok"]]
        if ok:
            idx = np.array([o["idx"] for o in ok])
            sc = np.array([o["fid"] == "screen" for o in ok])
            self.mu_eg, self.sd_eg = self._fit_het(
                idx, np.array([o["eg"] for o in ok]), self.eg_prior,
                np.where(sc, SCREEN_EG_SD, SYNTH_EG_SD) ** 2, 0.6)
            self.mu_lt, self.sd_lt = self._fit_het(
                idx, np.array([o["lt"] for o in ok]), self.lt_prior,
                np.where(sc, SCREEN_LT_SD, SYNTH_LT_SD) ** 2, 0.7)
        synth = [o for o in observations if o["fid"] == "synth"]
        if self.use_failures and any(not o["ok"] for o in synth):
            idx = np.array([o["idx"] for o in synth])
            y = np.array([1.0 if o["ok"] else 0.0 for o in synth])
            m, _ = self._fit_one(idx, y, np.full(len(self.X), 0.9), 0.05, 0.35)
            self.p_ok = np.clip(m, 0.03, 1.0)


# --------------------------------------------------------------------------- information gain

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(7)
_GH_W = _GH_W / _GH_W.sum()


def _entropy(p):
    p = np.clip(p, EPS, 1 - EPS)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def _p_parts(mu_eg, sd_eg, mu_lt, sd_lt):
    p_eg = norm.cdf((TARGET["eg_max"] - mu_eg) / sd_eg) - norm.cdf((TARGET["eg_min"] - mu_eg) / sd_eg)
    p_lt = 1 - norm.cdf((LOG_T80_MIN - mu_lt) / sd_lt)
    return p_eg, p_lt


def expected_info_gain(sur: Surrogate, idx: np.ndarray, noise_eg: float, noise_lt: float,
                       reveals_ok: bool) -> np.ndarray:
    """Expected reduction (nats) of the entropy of the 'film meets spec' indicator after one test.

    Point-wise Gaussian update of the latent bandgap and log T80 (cross-film correlation ignored,
    so this is a conservative lower bound), integrated with 7-point Gauss-Hermite quadrature.
    ``reveals_ok`` is True for synthesis, which also resolves whether the film forms."""
    mu_e, sd_e = sur.mu_eg[idx], sur.sd_eg[idx]
    mu_l, sd_l = sur.mu_lt[idx], sur.sd_lt[idx]
    q = sur.p_ok[idx]
    p_eg, p_lt = _p_parts(mu_e, sd_e, mu_l, sd_l)
    h0 = _entropy(p_eg * p_lt * q)

    def post(mu, sd, noise):
        k = sd ** 2 / (sd ** 2 + noise ** 2)
        return mu[:, None] + (sd * np.sqrt(k))[:, None] * _GH_X[None, :], np.sqrt(sd ** 2 * (1 - k))
    me, se = post(mu_e, sd_e, noise_eg)
    ml, sl = post(mu_l, sd_l, noise_lt)
    pe = norm.cdf((TARGET["eg_max"] - me) / se[:, None]) - norm.cdf((TARGET["eg_min"] - me) / se[:, None])
    pl = 1 - norm.cdf((LOG_T80_MIN - ml) / sl[:, None])
    joint = pe[:, :, None] * pl[:, None, :]                  # (n, ge, gl)
    w = _GH_W[:, None] * _GH_W[None, :]
    if reveals_ok:
        h1 = q * (w[None] * _entropy(joint)).sum((1, 2))
    else:
        h1 = (w[None] * _entropy(joint * q[:, None, None])).sum((1, 2))
    return np.maximum(h0 - h1, 0.0)


def action_scores(sur: Surrogate, tested: np.ndarray, screened: np.ndarray, allow_screen: bool,
                  beta: float = 1.0) -> dict:
    """Score every film for each fidelity. score = (EIG + beta * P(hit) for synthesis) / cost.

    beta is the discovery bonus in nats per expected hit: only synthesis can deliver a hit, a screen
    only informs. beta = 0 is pure information gain per unit cost."""
    n = len(sur.X)
    all_idx = np.arange(n)
    costs = np.array([synth_cost(i) for i in range(n)])
    p = sur.p_hit()
    eig_syn = expected_info_gain(sur, all_idx, SYNTH_EG_SD, SYNTH_LT_SD, True)
    syn = (eig_syn + beta * p) / costs
    syn = np.where(tested, -np.inf, syn)
    scr = np.full(n, -np.inf)
    eig_scr = np.zeros(n)
    if allow_screen:
        eig_scr = expected_info_gain(sur, all_idx, SCREEN_EG_SD, SCREEN_LT_SD, False)
        scr = np.where(tested | screened, -np.inf, eig_scr / SCREEN_COST)
    return {"synth": syn, "screen": scr, "eig_synth": eig_syn, "eig_screen": eig_scr, "p_hit": p,
            "cost_synth": costs}


def plan_actions(sur: Surrogate, tested: np.ndarray, screened: np.ndarray, n: int = 5,
                 allow_screen: bool = True, beta: float = 1.0, min_dist: float = 0.12,
                 budget_left: float = np.inf) -> list[dict]:
    """Greedy batch: highest score-per-cost actions, one action per film, diverse within a batch."""
    sc = action_scores(sur, tested, screened, allow_screen, beta)
    X = sur.X
    best = np.maximum(sc["synth"], sc["screen"])
    min_cost = np.minimum(np.where(np.isfinite(sc["screen"]), SCREEN_COST, np.inf),
                          np.where(np.isfinite(sc["synth"]), sc["cost_synth"], np.inf))
    chosen: list[int] = []
    out: list[dict] = []
    left = budget_left
    for _ in range(n):
        s = best.copy()
        for j in chosen:
            s = np.where(np.linalg.norm(X - X[j], axis=1) < min_dist, -np.inf, s)
        s = np.where(min_cost > left + 1e-9, -np.inf, s)
        if not np.isfinite(s).any():
            break
        i = int(np.argmax(s))
        fid = "screen" if sc["screen"][i] >= sc["synth"][i] else "synth"
        cost = SCREEN_COST if fid == "screen" else float(sc["cost_synth"][i])
        out.append({"idx": i, "fid": fid, "cost": cost, "score_per_cost": float(s[i]),
                    "alt_fid": "synth" if fid == "screen" else "screen",
                    "alt_score_per_cost": float(sc["synth" if fid == "screen" else "screen"][i]),
                    "eig_screen": float(sc["eig_screen"][i]), "eig_synth": float(sc["eig_synth"][i]),
                    "p_hit": float(sc["p_hit"][i])})
        chosen.append(i)
        left -= cost
    return out



# --------------------------------------------------------------------------- offline campaign

def _greedy_batch(sur: Surrogate, tested: np.ndarray, rng: np.random.Generator, n: int = 5,
                  min_dist: float = 0.12) -> list[int]:
    """LabLoop-style designer: exploit P(hit) plus optimistic exploration (3 + 2 per batch)."""
    p, p_opt = sur.p_hit(), sur.p_hit(inflate=2.5)
    u = sur.uncertainty()
    un = u / (u.max() + 1e-9)
    jit = rng.uniform(0, 1e-3, len(p))
    chosen: list[int] = []
    for k in range(n):
        s = np.where(tested, -np.inf, (p + 0.02 * un if k < 3 else p_opt) + jit)
        for j in chosen:
            s = np.where(np.linalg.norm(sur.X - sur.X[j], axis=1) < min_dist, -np.inf, s)
        if not np.isfinite(s).any():
            break
        chosen.append(int(np.argmax(s)))
    return chosen


def run_mf_campaign(world: int, seed: int, budget: float = 60.0, arm: str = "mf",
                    beta: float = 1.0, batch: int = 5) -> dict:
    """arm: 'mf' (screen + synthesis by EIG/cost), 'sf_eig' (same rule, synthesis only),
    'sf_greedy' (LabLoop-style exploit/explore, synthesis only). A hit is a film that was
    SYNTHESISED successfully and truly meets spec (screens never count; failed films do not count)."""
    set_world(world)
    true_hits = space_arrays()[5]
    n = len(true_hits)
    lab = MFLab(world, seed)
    sur = MFSurrogate()
    rng = np.random.default_rng(seed)
    tested, screened = np.zeros(n, bool), np.zeros(n, bool)
    obs, events = [], []
    spent, found = 0.0, set()
    n_screen = n_synth = 0
    while spent < budget - 1e-9:
        left = budget - spent
        if arm == "sf_greedy":
            acts = [{"idx": i, "fid": "synth", "cost": synth_cost(i)} for i in _greedy_batch(sur, tested, rng, batch)]
        else:
            acts = plan_actions(sur, tested, screened, batch, allow_screen=(arm == "mf"), beta=beta,
                                budget_left=left)
        progressed = False
        for a in acts:
            i, cost = a["idx"], a["cost"]
            if spent + cost > budget + 1e-9:
                continue
            if a["fid"] == "screen":
                o = lab.screen(i)
                screened[i] = True
                n_screen += 1
            else:
                if not safety_review(make_protocol(composition_space()[i]))["approved"]:
                    tested[i] = True
                    continue
                o = lab.synthesize(i)
                tested[i] = True
                n_synth += 1
                if true_hits[i] and o["ok"]:
                    if i not in found:
                        events.append({"spent": round(spent + o["cost"], 2), "idx": i})
                    found.add(i)
            spent += o["cost"]
            obs.append(o)
            progressed = True
        if not progressed:
            break
        sur.fit(obs)
    return {"world": world, "seed": seed, "arm": arm, "spent": round(spent, 3), "n_synth": n_synth,
            "n_screen": n_screen, "hit_events": events, "true_hits_total": int(true_hits.sum())}


def hits_by_budget(res: dict, grid) -> list[int]:
    return [sum(e["spent"] <= b + 1e-9 for e in res["hit_events"]) for b in grid]


def first_hit(res: dict, budget: float) -> float:
    """Units spent at the first hit; censored at ``budget`` when there is none."""
    return float(res["hit_events"][0]["spent"]) if res["hit_events"] else float(budget)
