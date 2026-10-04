"""Synthetic injection set: Kepler-like light curves with known ground truth.

Each target is a 30-min-cadence light curve with white + red noise, data gaps,
weak background stellar variability, reaction-wheel momentum dumps (quality-
flagged cadences) and flux-weighted centroids. One of five mechanisms
(H1..H5) is injected, and a "threshold-crossing event" (TCE) ephemeris is
reported for it the way a detection pipeline would (including pipeline
mistakes, e.g. EBs reported at half their true period).

The generator returns (Target, truth). Truth goes to the Data Gatekeeper only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

A_R_SUN_1D = 4.206          # a/R* for a solar-density star at P = 1 day
RHO_SUN_CGS = 1.41


@dataclass
class LightCurve:
    time: np.ndarray          # days
    flux: np.ndarray          # normalized (median 1)
    flux_err: np.ndarray
    quality: np.ndarray       # bool, True = flagged cadence (momentum dump etc.)
    cen_x: np.ndarray         # flux-weighted centroid offsets, millipixels
    cen_y: np.ndarray

    def __len__(self) -> int:
        return len(self.time)


@dataclass
class Target:
    target_id: str
    lc: LightCurve
    signal: dict               # period_d, epoch, duration_h, depth_ppm, snr
    stellar: dict              # teff_k, radius_rsun, mass_msun, rho_cat (solar), rho_err_dex, logg
    source: str = "synthetic"
    meta: dict = field(default_factory=dict)   # non-label metadata safe for agents


@dataclass
class Truth:
    target_id: str
    label: str                 # H1..H5
    details: dict


# ----------------------------------------------------------------------------
# Transit / eclipse geometry
# ----------------------------------------------------------------------------

def _overlap_area(z: np.ndarray, k: float) -> np.ndarray:
    """Area of overlap between unit disk and disk of radius k at separation z."""
    z = np.asarray(z, dtype=float)
    a = np.zeros_like(z)
    full = z <= 1 - k
    a[full] = np.pi * k * k
    if k > 1:
        a[z <= k - 1] = np.pi
    part = (z > abs(1 - k)) & (z < 1 + k)
    zp = z[part]
    c1 = np.clip((zp**2 + k * k - 1) / (2 * zp * k), -1, 1)
    c2 = np.clip((zp**2 + 1 - k * k) / (2 * zp), -1, 1)
    sq = np.sqrt(np.clip((-zp + k + 1) * (zp + k - 1) * (zp - k + 1) * (zp + k + 1), 0, None))
    a[part] = k * k * np.arccos(c1) + np.arccos(c2) - 0.5 * sq
    return a


def eclipse_deficit(t, period, t0, k, a_r, b, u1=0.4, u2=0.25) -> np.ndarray:
    """Fractional flux deficit for a dark disk of radius ratio k crossing a limb-darkened star."""
    phase = 2 * np.pi * (t - t0) / period
    x = a_r * np.sin(phase)
    y = b * np.cos(phase)
    z = np.sqrt(x * x + y * y)
    front = np.cos(phase) > 0
    area = _overlap_area(z, k)
    r = np.clip(z, 0, 1)
    mu = np.sqrt(1 - r * r)
    intensity = 1 - u1 * (1 - mu) - u2 * (1 - mu) ** 2
    norm = 1 - u1 / 3 - u2 / 6
    return np.where(front, area / np.pi * intensity / norm, 0.0)


def a_over_r(period_d: float, rho_solar: float) -> float:
    return A_R_SUN_1D * rho_solar ** (1 / 3) * period_d ** (2 / 3)


def total_duration_d(period, a_r, k, b) -> float:
    arg = np.sqrt(max((1 + k) ** 2 - b * b, 1e-6)) / (a_r * np.sin(np.arccos(min(b / a_r, 0.999))))
    return period / np.pi * np.arcsin(min(arg, 1.0))


# ----------------------------------------------------------------------------
# Base star + instrument
# ----------------------------------------------------------------------------

def _base(rng: np.random.Generator, baseline_days: float, cadence_min: float):
    dt = cadence_min / 1440.0
    t = np.arange(0, baseline_days, dt) + 131.0
    keep = np.ones_like(t, dtype=bool)
    for _ in range(rng.integers(1, 3)):                         # data gaps
        g0 = rng.uniform(t[0] + 5, t[-1] - 8)
        keep &= ~((t > g0) & (t < g0 + rng.uniform(0.8, 3.0)))
    t = t[keep]
    n = len(t)

    sigma = float(rng.uniform(60, 500)) * 1e-6                  # per-point white noise
    white = rng.normal(0, sigma, n)
    phi = 0.97                                                  # AR(1) red noise
    red_amp = float(rng.uniform(0.1, 0.5)) * sigma
    eps = rng.normal(0, red_amp * np.sqrt(1 - phi**2), n)
    red = np.zeros(n)
    for i in range(1, n):
        red[i] = phi * red[i - 1] + eps[i]

    prot = float(rng.uniform(5, 35))                            # weak background rotation
    amp = float(rng.uniform(0, 600)) * 1e-6
    var = amp * np.sin(2 * np.pi * t / prot + rng.uniform(0, 2 * np.pi))

    dump_interval = float(rng.uniform(2.9, 3.6))                # momentum dumps
    dump_t0 = t[0] + rng.uniform(0.2, dump_interval)
    dumps = np.arange(dump_t0, t[-1], dump_interval)
    idx = np.clip(np.searchsorted(t, dumps), 0, n - 1)
    quality = np.zeros(n, dtype=bool)
    quality[idx] = True

    cen_sig = float(rng.uniform(0.8, 2.5))                      # millipixels
    cen_x = rng.normal(0, cen_sig, n)
    cen_y = rng.normal(0, cen_sig, n)
    # small pointing excursion after every dump (instrumental, all targets)
    for d in dumps:
        m = (t >= d) & (t < d + 0.15)
        cen_x[m] += rng.normal(0.6, 0.3) * cen_sig
        cen_y[m] += rng.normal(0.3, 0.3) * cen_sig

    return dict(t=t, sigma=sigma, noise=white + red, var=var, quality=quality,
                cen_x=cen_x, cen_y=cen_y, dumps=dumps, dump_interval=dump_interval,
                cen_sig=cen_sig, prot_bg=prot)


def _star(rng):
    radius = float(rng.uniform(0.7, 1.6))
    mass = float(np.clip(radius ** 1.15 * rng.normal(1, 0.06), 0.5, 1.6))
    rho = mass / radius**3
    rho_err_dex = float(rng.uniform(0.06, 0.15))
    rho_cat = rho * 10 ** rng.normal(0, rho_err_dex)
    teff = float(5778 * mass ** 0.55 * rng.normal(1, 0.03))
    logg = float(4.438 + np.log10(mass / radius**2))
    return dict(teff_k=round(teff), radius_rsun=round(radius, 3), mass_msun=round(mass, 3),
                rho_cat=round(rho_cat, 4), rho_err_dex=round(rho_err_dex, 3), logg=round(logg, 3)), rho


def _pick_period(rng, base_days, lo=0.8, hi=18.0):
    hi = min(hi, base_days / 3.2)
    return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))


# ----------------------------------------------------------------------------
# Mechanisms
# ----------------------------------------------------------------------------

def _inject(label: str, rng, b0: dict, rho_true: float, base_days: float):
    t = b0["t"]
    signal_flux = np.zeros_like(t)
    cen_dx = np.zeros_like(t)
    details: dict = {"mechanism": label}

    if label == "H1":                                           # transiting planet
        period = _pick_period(rng, base_days)
        depth = float(np.exp(rng.uniform(np.log(250e-6), np.log(15000e-6))))
        k = np.sqrt(depth)
        b = float(rng.uniform(0, 0.85))
        a_r = a_over_r(period, rho_true)
        t0 = t[0] + rng.uniform(0, period)
        signal_flux = -eclipse_deficit(t, period, t0, k, a_r, b)
        rep_period, rep_t0 = period, t0
        dur = total_duration_d(period, a_r, k, b)
        details.update(period=period, k=k, b=b, a_r=a_r)

    elif label == "H2":                                         # EB on target
        true_p = _pick_period(rng, base_days, 1.0, 14.0)
        k = float(rng.uniform(0.15, 0.55))
        a_r = a_over_r(true_p, rho_true * rng.uniform(0.6, 1.2))
        grazing = rng.random() < 0.55
        b = float(rng.uniform(0.85, 1.0 + 0.6 * k)) if grazing else float(rng.uniform(0, 0.7))
        t0 = t[0] + rng.uniform(0, true_p)
        prim = eclipse_deficit(t, true_p, t0, k, a_r, b)
        half_mode = rng.random() < 0.5
        if half_mode:                                           # twin-ish stars: pipeline reports P/2
            s = float(rng.uniform(0.45, 0.92))
        else:
            s = float(np.exp(rng.uniform(np.log(0.01), np.log(0.4))))
        sec = s * eclipse_deficit(t, true_p, t0 + true_p / 2, k, a_r, b)
        signal_flux = -(prim + sec)
        if rng.random() < 0.35:                                 # ellipsoidal variation
            signal_flux += -rng.uniform(1e-4, 1e-3) * np.cos(4 * np.pi * (t - t0) / true_p)
        rep_period = true_p / 2 if half_mode else true_p
        rep_t0 = t0
        dur = total_duration_d(true_p, a_r, k, b)
        details.update(true_period=true_p, k=k, b=b, s=s, half_period_reported=half_mode, grazing=grazing)

    elif label == "H3":                                         # blended background EB
        true_p = _pick_period(rng, base_days, 0.8, 14.0)
        k = float(rng.uniform(0.25, 0.8))
        rho_bg = rho_true * 10 ** rng.uniform(-1.2, 0.6)        # background star unrelated to target
        a_r = a_over_r(true_p, rho_bg)
        b = float(rng.uniform(0, 0.9))
        t0 = t[0] + rng.uniform(0, true_p)
        dilution = float(np.exp(rng.uniform(np.log(0.004), np.log(0.06))))
        half_mode = rng.random() < 0.3
        s = float(rng.uniform(0.5, 0.95)) if half_mode else float(rng.uniform(0.0, 0.4))
        raw = eclipse_deficit(t, true_p, t0, k, a_r, b) + s * eclipse_deficit(t, true_p, t0 + true_p / 2, k, a_r, b)
        signal_flux = -dilution * raw
        sep_px = float(np.exp(rng.uniform(np.log(0.15), np.log(3.0))))
        ang = rng.uniform(0, 2 * np.pi)
        # centroid moves away from the background star during its eclipse (millipixels)
        cen_dx = -signal_flux * sep_px * 1000.0
        b0["cen_y"] = b0["cen_y"] + cen_dx * np.sin(ang)
        cen_dx = cen_dx * np.cos(ang)
        rep_period = true_p / 2 if half_mode else true_p
        rep_t0 = t0
        dur = total_duration_d(true_p, a_r, k, b)
        details.update(true_period=true_p, dilution=dilution, sep_px=sep_px, half_period_reported=half_mode)

    elif label == "H4":                                         # spot modulation with sharp minima
        prot = float(rng.uniform(1.0, min(14.0, base_days / 4)))
        amp = float(np.exp(rng.uniform(np.log(4e-4), np.log(8e-3))))
        width = prot * rng.uniform(0.03, 0.08)                  # dip width (days, gaussian sigma)
        t0 = t[0] + rng.uniform(0, prot)
        n_cyc = int(np.ceil((t[-1] - t0) / prot)) + 2
        cyc_amp = amp * np.clip(1 + rng.normal(0, rng.uniform(0.25, 0.6), n_cyc), 0.05, None)
        drift = np.cumsum(rng.normal(0, 0.01 * prot, n_cyc))   # phase wander from spot evolution
        cyc = np.round((t - t0) / prot).astype(int)
        cyc_c = np.clip(cyc, 0, n_cyc - 1)
        dphase = (t - t0) - cyc * prot - drift[cyc_c]
        signal_flux = -cyc_amp[cyc_c] * np.exp(-0.5 * (dphase / width) ** 2)
        signal_flux += -0.5 * amp * np.sin(2 * np.pi * (t - t0) / prot + 0.6)
        if rng.random() < 0.4:                                  # second spot group
            wrapped = ((t - t0 - 0.45 * prot + 0.5 * prot) % prot) - 0.5 * prot
            signal_flux += -0.4 * amp * np.exp(-0.5 * (wrapped / width) ** 2)
        rep_period, rep_t0 = prot, t0
        dur = 2.6 * width
        details.update(prot=prot, amp=amp)

    elif label == "H5":                                         # momentum-dump artifacts
        dumps = b0["dumps"]
        dip_dur = float(rng.uniform(0.08, 0.25))
        amp = float(np.exp(rng.uniform(np.log(2e-4), np.log(4e-3))))
        p_hit = float(rng.uniform(0.6, 1.0))
        for d in dumps:
            if rng.random() < p_hit:
                m = (t >= d) & (t < d + dip_dur)
                a = amp * rng.uniform(0.4, 1.6)
                signal_flux[m] -= a
                cen_dx[m] += a * rng.uniform(300, 1500)        # pointing excursion
        rep_period = b0["dump_interval"] * (1 + rng.normal(0, 2e-4))
        rep_t0 = dumps[0] + dip_dur / 2
        dur = dip_dur
        details.update(dip_amp=amp, p_hit=p_hit, dump_interval=b0["dump_interval"])
    else:
        raise ValueError(label)

    return signal_flux, cen_dx, rep_period, rep_t0, dur, details


def make_target(target_id: str, label: str, seed: int, baseline_days=80.0, cadence_min=30.0):
    rng = np.random.default_rng(seed)
    b0 = _base(rng, baseline_days, cadence_min)
    stellar, rho_true = _star(rng)
    sig, cen_dx, period, t0, dur, details = _inject(label, rng, b0, rho_true, baseline_days)
    t = b0["t"]
    flux = 1.0 + b0["noise"] + b0["var"] + sig
    flux = flux / np.median(flux)
    lc = LightCurve(time=t, flux=flux, flux_err=np.full_like(t, b0["sigma"]),
                    quality=b0["quality"], cen_x=b0["cen_x"] + cen_dx, cen_y=b0["cen_y"])

    # Pipeline-style TCE report (with measurement noise)
    rep_period = period * (1 + rng.normal(0, 3e-5))
    phase = ((t - t0 + 0.5 * rep_period) % rep_period) - 0.5 * rep_period
    in_tr = np.abs(phase) < 0.35 * dur
    depth = float(max(-np.mean(sig[in_tr]) if in_tr.any() else 0.0, 1e-5))
    n_in = int(in_tr.sum())
    snr = float(depth / b0["sigma"] * np.sqrt(max(n_in, 1)))
    signal = dict(period_d=round(rep_period, 6), epoch=round(float(t0 + rng.normal(0, 0.002)), 5),
                  duration_h=round(float(dur * 24 * rng.normal(1, 0.06)), 3),
                  depth_ppm=round(depth * 1e6 * rng.normal(1, 0.05), 1), snr=round(snr, 1))
    target = Target(target_id=target_id, lc=lc, signal=signal, stellar=stellar,
                    meta={"cadence_min": cadence_min, "baseline_days": baseline_days,
                          "n_points": len(t), "mission": "synthetic-kepler-like"})
    details.update(seed=seed, rho_true=rho_true)
    return target, Truth(target_id=target_id, label=label, details=details)


def make_set(n: int, seed: int, class_mix: dict, prefix: str = "T", **kw):
    """Deterministic stratified set: labels drawn per class_mix, ids anonymized and shuffled."""
    rng = np.random.default_rng(seed)
    labels = list(class_mix)
    probs = np.array([class_mix[k] for k in labels], dtype=float)
    probs /= probs.sum()
    counts = np.floor(probs * n).astype(int)
    counts[np.argmax(probs)] += n - counts.sum()
    seq = [lab for lab, c in zip(labels, counts) for _ in range(c)]
    rng.shuffle(seq)
    seeds = rng.integers(0, 2**31 - 1, size=n)
    out = []
    for i, (lab, s) in enumerate(zip(seq, seeds)):
        out.append(make_target(f"{prefix}-{i:04d}", lab, int(s), **kw))
    return out
