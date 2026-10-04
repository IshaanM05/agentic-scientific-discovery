"""Vetting test registry (design 9.1).

Each test reads a light curve plus TCE ephemeris and returns continuous metrics
and a discrete outcome bin. The bins are what the calibrated likelihood tables
P(bin | H) are built on. Costs are relative compute/attention units.
"""
from __future__ import annotations

import hashlib
import inspect
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import lombscargle

from .common import detrend, epoch_index, local_depth, phase_fold, robust_std


@dataclass(frozen=True)
class TestDef:
    test_id: str
    name: str
    description: str
    cost: float
    separates: tuple
    bin_labels: tuple
    fn: Callable
    detrend_sensitive: bool = True
    method_refs: tuple = ()


def _ephem(target):
    s = target.signal
    return s["period_d"], s["epoch"], max(s["duration_h"] / 24.0, 0.03)


def _bin(value, edges):
    if not np.isfinite(value):
        return None
    return int(np.searchsorted(edges, value, side="right"))


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------

def t_odd_even(target, window_factor=3.0):
    P, t0, dur = _ephem(target)
    lc = target.lc
    f = detrend(lc, P, t0, dur, window_factor)
    ph = phase_fold(lc.time, P, t0)
    n = epoch_index(lc.time, P, t0)
    odd, even = (n % 2 == 1), (n % 2 == 0)
    d_o, e_o, n_o = local_depth(f, ph, 0.0, dur, odd)
    d_e, e_e, n_e = local_depth(f, ph, 0.0, dur, even)
    sig = abs(d_o - d_e) / np.hypot(e_o, e_e) if np.isfinite(d_o + d_e) else np.nan
    n_tr_odd = len(np.unique(n[odd & (np.abs(ph) < 0.35 * dur)]))
    n_tr_even = len(np.unique(n[even & (np.abs(ph) < 0.35 * dur)]))
    return dict(odd_depth_ppm=d_o * 1e6, even_depth_ppm=d_e * 1e6, diff_sigma=sig,
                n_odd_transits=n_tr_odd, n_even_transits=n_tr_even), {"odd": e_o * 1e6, "even": e_e * 1e6}, \
        _bin(sig, [1.5, 3.0])


def t_secondary(target, window_factor=3.0):
    P, t0, dur = _ephem(target)
    lc = target.lc
    f = detrend(lc, P, t0, dur, window_factor)
    ph = phase_fold(lc.time, P, t0 + 0.5 * P)
    d, e, n_in = local_depth(f, ph, 0.0, dur)
    sig = d / e if np.isfinite(d) else np.nan
    return dict(secondary_depth_ppm=d * 1e6, secondary_sigma=sig, n_in=n_in), {"depth": e * 1e6}, \
        _bin(sig, [2.0, 4.0])


def _trapezoid(ph, depth, T, tau):
    a = np.abs(ph)
    y = np.zeros_like(ph)
    flat = a <= T / 2 - tau
    ramp = (a > T / 2 - tau) & (a < T / 2)
    y[flat] = depth
    y[ramp] = depth * (T / 2 - a[ramp]) / max(tau, 1e-6)
    return -y


_FIT_CACHE: dict = {}


def _fit_trapezoid(target, window_factor=3.0):
    key = (target.target_id, id(target.lc), window_factor)
    if key not in _FIT_CACHE:
        if len(_FIT_CACHE) > 256:
            _FIT_CACHE.clear()
        _FIT_CACHE[key] = _fit_trapezoid_uncached(target, window_factor)
    return _FIT_CACHE[key]


def _fit_trapezoid_uncached(target, window_factor=3.0):
    P, t0, dur = _ephem(target)
    lc = target.lc
    f = detrend(lc, P, t0, dur, window_factor) - 1.0
    ph = phase_fold(lc.time, P, t0)
    sel = (np.abs(ph) < 2.0 * dur) & ~lc.quality
    x, y = ph[sel], f[sel]
    if len(x) < 15:
        return None
    d0 = max(-np.median(y[np.abs(x) < 0.25 * dur]) if (np.abs(x) < 0.25 * dur).any() else 1e-4, 1e-5)

    def resid(p):
        depth, T, frac = p
        return _trapezoid(x, depth, T, frac * T) - y

    best = None
    for frac0 in (0.1, 0.3, 0.48):
        try:
            r = least_squares(resid, [d0, dur, frac0], bounds=([0, 0.4 * dur, 0.02], [5 * d0 + 1e-3, 1.8 * dur, 0.5]))
        except ValueError:
            continue
        if best is None or r.cost < best.cost:
            best = r
    if best is None:
        return None
    depth, T, frac = best.x
    scatter = robust_std(y[np.abs(x) > 0.8 * T]) if (np.abs(x) > 0.8 * T).sum() > 5 else robust_std(y)
    n_in = int((np.abs(x) < T / 2).sum())
    snr = depth / scatter * np.sqrt(max(n_in, 1)) if scatter > 0 else np.nan
    return dict(depth=depth, T=T, frac=frac, snr=snr, n_in=n_in, period=P)


def t_shape(target, window_factor=3.0):
    fit = _fit_trapezoid(target, window_factor)
    if fit is None:
        return dict(ingress_frac=np.nan), {}, None
    return dict(ingress_frac=fit["frac"], fit_depth_ppm=fit["depth"] * 1e6, fit_duration_h=fit["T"] * 24,
                fit_snr=fit["snr"]), {}, _bin(fit["frac"], [0.17, 0.32])


def t_density(target, window_factor=3.0):
    """Transit-derived stellar density vs catalog (Seager & Mallen-Ornelas 2003)."""
    fit = _fit_trapezoid(target, window_factor)
    if fit is None:
        return dict(log_rho_ratio=np.nan), {}, None
    P, T, frac, depth = fit["period"], fit["T"], fit["frac"], max(fit["depth"], 1e-6)
    k = np.sqrt(depth)
    # finite cadence (and limb darkening) smear ingress; subtract the integration time
    cad = float(np.median(np.diff(target.lc.time)))
    tau = max(frac * T - 0.7 * cad, 0.01 * T)
    tF = max(T - 2 * tau, 0.0)
    r = (tF / T) ** 2
    b2 = np.clip(((1 - k) ** 2 - r * (1 + k) ** 2) / max(1 - r, 1e-3), 0, min((1 + k) ** 2 * 0.98, 0.81))
    s = np.sin(np.pi * T / P)
    a_r = np.sqrt(max(((1 + k) ** 2 - b2 * (1 - s * s)) / max(s * s, 1e-9), 1.0))
    rho_tr = (a_r / 4.206) ** 3 / P**2
    ratio = np.log10(rho_tr / target.stellar["rho_cat"])
    return dict(rho_transit=rho_tr, rho_catalog=target.stellar["rho_cat"], log_rho_ratio=ratio,
                a_over_r=a_r, impact_b=float(np.sqrt(b2))), {"rho_cat_dex": target.stellar["rho_err_dex"]}, \
        _bin(ratio, [-0.6, -0.25, 0.25, 0.6])


def t_centroid(target, window_factor=3.0):
    P, t0, dur = _ephem(target)
    lc = target.lc
    ph = phase_fold(lc.time, P, t0)
    inn = np.abs(ph) < 0.35 * dur
    out = (np.abs(ph) > 0.75 * dur) & (np.abs(ph) < 3 * dur + 0.1)
    if inn.sum() < 3 or out.sum() < 10:
        return dict(offset_sigma=np.nan), {}, None
    sig2 = 0.0
    offs = []
    for c in (lc.cen_x, lc.cen_y):
        d = np.mean(c[inn]) - np.median(c[out])
        e = robust_std(c[out]) * np.sqrt(1 / inn.sum() + 1 / out.sum())
        offs.append(d)
        sig2 += (d / e) ** 2
    sig = float(np.sqrt(sig2))
    return dict(offset_mpix=float(np.hypot(*offs)), offset_sigma=sig, dx_mpix=offs[0], dy_mpix=offs[1]), {}, \
        _bin(sig, [2.5, 5.0])


def t_periodogram(target, window_factor=3.0):
    """Rotation/variability search on out-of-transit flux; checks harmonic match with signal period."""
    P, t0, dur = _ephem(target)
    lc = target.lc
    t, f = lc.time, lc.flux - 1.0
    keep = (np.abs(phase_fold(t, P, t0)) > 0.75 * dur) & ~lc.quality
    if keep.sum() < 100:            # dips cover most of the orbit: use all good cadences
        keep = ~lc.quality
    t, f = t[keep], f[keep]
    # bin to 2 h for speed
    bins = np.floor((t - t[0]) / (2 / 24)).astype(int)
    cnt = np.bincount(bins)
    ok = cnt > 0
    tb = (np.bincount(bins, t) [ok] / cnt[ok])
    fb = (np.bincount(bins, f)[ok] / cnt[ok])
    fb = fb - fb.mean()
    periods = np.exp(np.linspace(np.log(0.5), np.log(30.0), 900))
    pw = lombscargle(tb, fb, 2 * np.pi / periods, normalize=True)
    i = int(np.argmax(pw))
    p_rot, power = float(periods[i]), float(pw[i])
    amp = robust_std(fb) * np.sqrt(2)
    noise = lc.flux_err[0] / np.sqrt(4)   # per 2 h bin
    ratio = P / p_rot
    harmonic = min(abs(ratio - h) / h for h in (0.5, 1.0, 2.0))
    strong = power > 0.25 and amp > 3 * noise
    if not strong:
        b = 0
    elif harmonic < 0.04:
        b = 2
    else:
        b = 1
    return dict(rotation_period_d=p_rot, ls_power=power, amplitude_ppm=amp * 1e6,
                harmonic_mismatch=harmonic, strong=bool(strong)), {}, b


def t_systematics(target, window_factor=3.0):
    """Fraction of transit epochs whose window contains a quality-flagged cadence."""
    P, t0, dur = _ephem(target)
    lc = target.lc
    n = epoch_index(lc.time, P, t0)
    ph = phase_fold(lc.time, P, t0)
    near = np.abs(ph) < 0.5 * dur + 0.03
    epochs = np.unique(n[near])
    if len(epochs) == 0:
        return dict(flagged_fraction=np.nan), {}, None
    flagged = np.unique(n[near & lc.quality])
    frac = len(flagged) / len(epochs)
    return dict(flagged_fraction=frac, n_epochs=int(len(epochs)), n_flagged=int(len(flagged))), {}, \
        _bin(frac, [0.15, 0.5])


def t_consistency(target, window_factor=3.0):
    """Depth constancy across four time segments ("quarters"): reduced chi-square."""
    P, t0, dur = _ephem(target)
    lc = target.lc
    f = detrend(lc, P, t0, dur, window_factor)
    ph = phase_fold(lc.time, P, t0)
    edges = np.linspace(lc.time[0], lc.time[-1] + 1e-6, 5)
    depths, errs = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (lc.time >= a) & (lc.time < b)
        d, e, n_in = local_depth(f, ph, 0.0, dur, sel)
        if np.isfinite(d) and e > 0:
            depths.append(d)
            errs.append(e)
    if len(depths) < 2:
        return dict(chi2_red=np.nan), {}, None
    d, e = np.array(depths), np.array(errs)
    w = 1 / e**2
    mean = np.sum(w * d) / np.sum(w)
    chi2 = float(np.sum(((d - mean) / e) ** 2) / (len(d) - 1))
    return dict(chi2_red=chi2, segment_depths_ppm=[float(x * 1e6) for x in d], n_segments=len(d)), {}, \
        _bin(chi2, [2.5, 6.0])


REGISTRY: dict[str, TestDef] = {
    "T-odd-even": TestDef("T-odd-even", "Odd/even depth", "Compare depths of odd vs even transits",
                          1.0, ("H1", "H2", "H3"), ("<1.5 sigma", "1.5-3 sigma", ">3 sigma"), t_odd_even,
                          method_refs=("coughlin2016", "thompson2018")),
    "T-secondary": TestDef("T-secondary", "Secondary eclipse", "Search for an eclipse at phase 0.5",
                           1.0, ("H1", "H2", "H3"), ("<2 sigma", "2-4 sigma", ">4 sigma"), t_secondary,
                           method_refs=("coughlin2016",)),
    "T-shape": TestDef("T-shape", "Transit shape", "Trapezoid fit: ingress fraction (U vs V shape)",
                       2.0, ("H1", "H2", "H4"), ("U-shaped", "intermediate", "V-shaped"), t_shape,
                       method_refs=("seager2003",)),
    "T-density": TestDef("T-density", "Stellar density", "Transit-derived vs catalog stellar density",
                         2.0, ("H1", "H2", "H3"),
                         ("much lower", "lower", "consistent", "higher", "much higher"), t_density,
                         method_refs=("seager2003",)),
    "T-centroid": TestDef("T-centroid", "Centroid shift", "In- vs out-of-transit flux-weighted centroid",
                          4.0, ("H3", "H5"), ("<2.5 sigma", "2.5-5 sigma", ">5 sigma"), t_centroid,
                          detrend_sensitive=False, method_refs=("bryson2013",)),
    "T-periodogram": TestDef("T-periodogram", "Rotation periodogram", "Lomb-Scargle; does modulation match P?",
                             1.0, ("H4", "H2"), ("no strong modulation", "unrelated modulation", "matches signal period"),
                             t_periodogram, detrend_sensitive=False, method_refs=("mcquillan2014",)),
    "T-systematics": TestDef("T-systematics", "Systematics", "Transit epochs coinciding with flagged cadences",
                             1.0, ("H5",), ("<15% flagged", "15-50% flagged", ">50% flagged"), t_systematics,
                             detrend_sensitive=False, method_refs=("thompson2018",)),
    "T-consistency": TestDef("T-consistency", "Depth consistency", "Depth constancy across quarters",
                             2.0, ("H4", "H5"), ("consistent", "mildly variable", "inconsistent"), t_consistency,
                             method_refs=("thompson2018",)),
}
TEST_IDS = list(REGISTRY)


def code_hash(test_id: str) -> str:
    src = inspect.getsource(REGISTRY[test_id].fn)
    return hashlib.sha1(src.encode()).hexdigest()[:10]


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 5)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def run_test(test_id: str, target, window_factor: float = 3.0) -> dict:
    """Execute a registered test. Raises KeyError for tests outside the allowlist."""
    td = REGISTRY[test_id]
    t0 = time.perf_counter()
    try:
        metrics, unc, b = td.fn(target, window_factor=window_factor)
    except Exception as exc:  # a failed test is evidence-free, not a crash
        metrics, unc, b = {"error": f"{type(exc).__name__}: {exc}"}, {}, None
    rt = time.perf_counter() - t0
    return dict(test_id=test_id, metrics={k: _clean(v) for k, v in metrics.items()},
                uncertainties={k: _clean(v) for k, v in unc.items()}, outcome_bin=b,
                outcome_label=(td.bin_labels[b] if b is not None else "failed"),
                runtime_s=round(rt, 4), code_hash=code_hash(test_id), params={"window_factor": window_factor})
