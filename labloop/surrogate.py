"""Bayesian-optimisation surrogate: two GPs (bandgap, stability) over composition features.

The literature prior is used as the GP mean, so the GP only has to learn where
nature departs from the textbook. Acquisition is the probability that a film meets
the full spec (bandgap window AND stability), plus an optional exploration bonus.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.stats import norm
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

from .chemistry import LOG_T80_MIN, TARGET, space_arrays



class Surrogate:
    def __init__(self, use_prior: bool = True, use_failures: bool = True):
        self.use_prior = use_prior
        self.use_failures = use_failures
        X, eg_prior, lt_prior, *_ = space_arrays()
        self.X = X
        self.eg_prior = eg_prior if use_prior else np.full(len(X), 1.9)
        self.lt_prior = lt_prior if use_prior else np.full(len(X), 2.0)
        self.mu_eg = self.eg_prior.copy()
        self.mu_lt = self.lt_prior.copy()
        self.sd_eg = np.full(len(X), 0.08 if use_prior else 0.4)
        self.sd_lt = np.full(len(X), 0.4 if use_prior else 0.9)
        self.p_ok = np.ones(len(X))
        self.relaxed_lt = self.relaxed_eg = False

    def _fit_one(self, idx, y, prior, noise, length):
        if len(idx) < 2:
            return prior.copy(), (self.sd_eg if noise < 0.01 else self.sd_lt).copy()
        resid = y - prior[idx]
        kernel = ConstantKernel(0.1, (1e-3, 4.0)) * Matern(length, (0.15, 4.0), nu=2.5) + WhiteKernel(noise, (1e-4, 0.3))
        gp = GaussianProcessRegressor(kernel, normalize_y=False, n_restarts_optimizer=1, random_state=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            gp.fit(self.X[idx], resid)
        m, s = gp.predict(self.X, return_std=True)
        return prior + m, np.maximum(s, 1e-3)

    def relax_prior(self, prop: str, observations: list[dict], keep: float = 0.35):
        """Belief revision: shrink a discredited prior toward the observed mean and widen it."""
        vals = [o[prop] for o in observations if o["ok"]]
        if not vals:
            return
        if prop == "lt":
            self.lt_prior = keep * self.lt_prior + (1 - keep) * float(np.mean(vals))
            self.relaxed_lt = True
        else:
            self.eg_prior = keep * self.eg_prior + (1 - keep) * float(np.mean(vals))
            self.relaxed_eg = True
        if prop == "lt":
            self.sd_lt = np.maximum(self.sd_lt, 0.6)
        else:
            self.sd_eg = np.maximum(self.sd_eg, 0.15)

    def fit(self, observations: list[dict]):
        ok = [o for o in observations if o["ok"]]
        if ok:
            idx = np.array([o["idx"] for o in ok])
            self.mu_eg, self.sd_eg = self._fit_one(idx, np.array([o["eg"] for o in ok]), self.eg_prior, 0.001, 0.6)
        if ok:
            idx = np.array([o["idx"] for o in ok])
            self.mu_lt, self.sd_lt = self._fit_one(idx, np.array([o["lt"] for o in ok]), self.lt_prior, 0.02, 0.7)
        # negative-result memory: a separate model of "will this film even form?"
        fails = [o for o in observations if not o["ok"]]
        if self.use_failures and fails:
            idx = np.array([o["idx"] for o in observations])
            y = np.array([1.0 if o["ok"] else 0.0 for o in observations])
            m, _ = self._fit_one(idx, y, np.full(len(self.X), 0.9), 0.05, 0.35)
            self.p_ok = np.clip(m, 0.03, 1.0)

    def p_hit(self, inflate: float = 1.0) -> np.ndarray:
        """P(film meets spec). ``inflate`` > 1 gives an optimistic, exploration-friendly variant."""
        sd_eg, sd_lt = self.sd_eg * inflate, self.sd_lt * inflate
        p_eg = norm.cdf((TARGET["eg_max"] - self.mu_eg) / sd_eg) - norm.cdf((TARGET["eg_min"] - self.mu_eg) / sd_eg)
        p_lt = 1 - norm.cdf((LOG_T80_MIN - self.mu_lt) / sd_lt)
        return p_eg * p_lt * self.p_ok

    def uncertainty(self) -> np.ndarray:
        return self.sd_eg / 0.35 + self.sd_lt / 0.8
