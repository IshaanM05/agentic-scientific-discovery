"""Bayesian posterior over the differential (design 9.2) and expected information gain (9.3)."""
from __future__ import annotations

import numpy as np

from ..config import HYP_IDS


def entropy_bits(p: np.ndarray) -> float:
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def normalize_log(logp: np.ndarray) -> np.ndarray:
    logp = logp - np.logaddexp.reduce(logp)
    return np.exp(logp)


def update(post: np.ndarray, lik: np.ndarray, weight: float = 1.0, temper: float = 1.0) -> np.ndarray:
    """P(H | r) ∝ P(H) · L(r | H)^(weight·temper). weight < 1 flattens a low-quality result toward uniform."""
    logp = np.log(np.clip(post, 1e-300, None)) + weight * temper * np.log(np.clip(lik, 1e-300, None))
    return normalize_log(logp)


def expected_info_gain(post: np.ndarray, table: np.ndarray, temper: float = 1.0) -> float:
    """EIG(t) = H(post) - Σ_o P(o | post) H(post | o), table = [n_hyp, n_bins]."""
    h0 = entropy_bits(post)
    p_o = post @ table
    logq = np.log(np.clip(post, 1e-300, None))[:, None] + temper * np.log(np.clip(table, 1e-300, None))
    logq -= np.logaddexp.reduce(logq, axis=0, keepdims=True)
    q = np.exp(logq)                                   # posterior after each outcome, column-wise
    h_after = -(q * np.where(q > 0, logq, 0.0)).sum(axis=0) / np.log(2)
    return max(h0 - float(p_o @ h_after), 0.0)


def pairwise_info(post: np.ndarray, table: np.ndarray, i: int, j: int, temper: float = 1.0) -> float:
    """EIG restricted to the two-hypothesis sub-problem {leader i, contrarian j}.

    This is how strongly a test can settle House's specific challenge to the leader.
    Scaled by the mass on those two hypotheses so it cannot dominate when both are unlikely.
    """
    mass = post[i] + post[j]
    if mass <= 0:
        return 0.0
    sub = np.array([post[i], post[j]]) / mass
    return mass * expected_info_gain(sub, table[[i, j], :], temper)


def as_dict(p: np.ndarray) -> dict:
    return {h: round(float(x), 5) for h, x in zip(HYP_IDS, p)}
