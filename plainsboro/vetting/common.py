"""Shared light-curve operations: detrending, folding, local depth estimates."""
from __future__ import annotations

import numpy as np
import pandas as pd


def phase_fold(t: np.ndarray, period: float, epoch: float) -> np.ndarray:
    """Phase in days, in [-P/2, P/2), with transit center at 0."""
    return ((t - epoch + 0.5 * period) % period) - 0.5 * period


def epoch_index(t: np.ndarray, period: float, epoch: float) -> np.ndarray:
    return np.round((t - epoch) / period).astype(int)


def detrend(lc, period: float, epoch: float, dur_d: float, window_factor: float = 3.0) -> np.ndarray:
    """Running-median detrend with in-transit points masked (wotan-style 'median' method).

    Returns the detrended flux (flux / trend). `window_factor` sets the window in
    units of transit duration; Foreman reruns tests with a different factor to
    check detrending sensitivity.
    """
    t, f = lc.time, lc.flux
    dt = np.median(np.diff(t))
    win_days = max(window_factor * dur_d, 0.4)
    win = max(int(round(win_days / dt)) | 1, 5)
    masked = f.copy()
    masked[np.abs(phase_fold(t, period, epoch)) < 0.6 * dur_d] = np.nan
    masked[lc.quality] = np.nan
    s = pd.Series(masked)
    trend = s.rolling(win, center=True, min_periods=max(3, win // 5)).median()
    trend = trend.interpolate(limit_direction="both").to_numpy(copy=True)
    trend[~np.isfinite(trend)] = np.nanmedian(f)
    return f / trend


def robust_std(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def local_depth(flux: np.ndarray, phase: np.ndarray, center: float, dur_d: float, sel=None):
    """Depth (ppm-free fraction) at `center` phase vs local out-of-transit baseline.

    Returns (depth, err, n_in). Positive depth = dimming.
    """
    if sel is None:
        sel = np.ones_like(phase, dtype=bool)
    d = phase - center
    inn = sel & (np.abs(d) < 0.35 * dur_d)
    out = sel & (np.abs(d) > 0.75 * dur_d) & (np.abs(d) < 2.5 * dur_d + 0.1)
    n_in, n_out = int(inn.sum()), int(out.sum())
    if n_in < 2 or n_out < 5:
        return float("nan"), float("nan"), n_in
    base = np.median(flux[out])
    scatter = robust_std(flux[out])
    depth = base - np.mean(flux[inn])
    err = scatter * np.sqrt(1 / n_in + 1 / n_out)
    return float(depth), float(err), n_in
