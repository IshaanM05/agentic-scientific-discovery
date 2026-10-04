"""Calibrated likelihood tables P(outcome bin | H) (design 9.2).

Built ONLY from the calibration set. Laplace-smoothed counts are kept so that
credible intervals can be obtained by Dirichlet resampling of the tables.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from ..config import HYP_IDS, RESULTS
from ..vetting.registry import REGISTRY


@dataclass
class LikelihoodTables:
    counts: dict                      # test_id -> {H: [counts per bin]}
    prior_counts: dict                # H -> count
    alpha: float = 1.0
    temper: float = 1.0               # power applied to likelihoods (correlated-test correction)
    meta: dict = field(default_factory=dict)

    def prior(self) -> np.ndarray:
        c = np.array([self.prior_counts[h] for h in HYP_IDS], dtype=float) + self.alpha
        return c / c.sum()

    def _counts_arr(self, test_id: str) -> np.ndarray:
        cache = self.__dict__.setdefault("_cache", {})
        if test_id not in cache:
            c = np.array([self.counts[test_id][h] for h in HYP_IDS], dtype=float) + self.alpha
            cache[test_id] = (c, c / c.sum(axis=1, keepdims=True))
        return cache[test_id][0]

    def table(self, test_id: str) -> np.ndarray:
        """Array [n_hyp, n_bins] of P(bin | H)."""
        self._counts_arr(test_id)
        return self._cache[test_id][1]

    def likelihood(self, test_id: str, outcome_bin: int) -> np.ndarray:
        return self.table(test_id)[:, outcome_bin]

    def sample_likelihoods(self, test_id: str, outcome_bin: int, n: int, rng: np.random.Generator) -> np.ndarray:
        """n Dirichlet draws of P(outcome_bin | H) for every H -> array [n, n_hyp]."""
        c = self._counts_arr(test_id)
        g = rng.gamma(np.broadcast_to(c, (n,) + c.shape))
        return (g / g.sum(axis=2, keepdims=True))[:, :, outcome_bin]

    def sample(self, rng: np.random.Generator) -> "LikelihoodTables":
        """One Dirichlet draw of all tables (for bootstrap credible intervals)."""
        new = {}
        for tid, per_h in self.counts.items():
            new[tid] = {h: list(rng.dirichlet(np.array(v, float) + self.alpha) * (sum(v) + self.alpha * len(v)))
                        for h, v in per_h.items()}
        return LikelihoodTables(new, self.prior_counts, alpha=0.0, temper=self.temper)

    def add_observation(self, test_id: str, hyp: str, outcome_bin: int, w: float = 1.0):
        """Online calibration (Wilson adaptive mode, delayed labels)."""
        self.counts[test_id][hyp][outcome_bin] += w
        self.__dict__.get("_cache", {}).pop(test_id, None)

    def to_json(self) -> dict:
        return dict(counts=self.counts, prior_counts=self.prior_counts, alpha=self.alpha,
                    temper=self.temper, meta=self.meta)

    @classmethod
    def from_json(cls, d: dict) -> "LikelihoodTables":
        return cls(d["counts"], d["prior_counts"], d.get("alpha", 1.0), d.get("temper", 1.0), d.get("meta", {}))

    def copy(self) -> "LikelihoodTables":
        return LikelihoodTables.from_json(json.loads(json.dumps(self.to_json())))


def build_tables(outcomes: dict, labels: dict, ids=None, alpha: float = 1.0) -> LikelihoodTables:
    ids = list(ids if ids is not None else outcomes)
    counts = {tid: {h: [0.0] * len(td.bin_labels) for h in HYP_IDS} for tid, td in REGISTRY.items()}
    prior = {h: 0 for h in HYP_IDS}
    for cid in ids:
        h = labels[cid]
        prior[h] += 1
        for tid in REGISTRY:
            b = outcomes[cid][(tid, 3.0)]["outcome_bin"]
            if b is not None:
                counts[tid][h][b] += 1
    return LikelihoodTables(counts, prior, alpha=alpha, meta={"n_cases": len(ids)})


def fit_temper(outcomes, labels, ids, grid=(0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)) -> tuple[float, dict]:
    """Choose the likelihood temper by 2-fold cross-validated log-loss on the calibration set.

    Tests are not conditionally independent; tempering (power < 1) counters the
    resulting over-confidence. Uses all-tests posteriors.
    """
    ids = list(ids)
    rng = np.random.default_rng(0)
    rng.shuffle(ids)
    folds = [ids[::2], ids[1::2]]
    scores = {}
    for tau in grid:
        nll = 0.0
        for k in range(2):
            tab = build_tables(outcomes, labels, folds[1 - k])
            tab.temper = tau
            for cid in folds[k]:
                logp = np.log(tab.prior())
                for tid in REGISTRY:
                    b = outcomes[cid][(tid, 3.0)]["outcome_bin"]
                    if b is not None:
                        logp += tau * np.log(tab.likelihood(tid, b))
                logp -= np.logaddexp.reduce(logp)
                nll -= logp[HYP_IDS.index(labels[cid])]
        scores[tau] = nll / len(ids)
    best = min(scores, key=scores.get)
    return best, scores


TABLES_PATH = RESULTS / "likelihood_tables.json"


def save_tables(tab: LikelihoodTables, path=TABLES_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tab.to_json(), f, indent=1)


def load_tables(path=TABLES_PATH) -> LikelihoodTables:
    with open(path, encoding="utf-8") as f:
        return LikelihoodTables.from_json(json.load(f))
