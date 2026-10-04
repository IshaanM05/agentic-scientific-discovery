"""Real Kepler targets (NASA Exoplanet Archive KOI cumulative table + MAST light curves).

    python -m plainsboro.data.kepler --per-class 12

Ground truth (held only by the Data Gatekeeper; never shown to agents):
  CONFIRMED                                     -> H1
  FALSE POSITIVE, stellar-eclipse flag only     -> H2
  FALSE POSITIVE, centroid-offset flag          -> H3
  FALSE POSITIVE, not-transit-like flag only    -> "H4|H5" (variability OR artifact; either verdict scores correct)
Targets are anonymized as K-#### and the archive's false-positive flag columns are
treated as labels and stripped. One Kepler quarter (~90 d, long cadence) per target,
comparable to the synthetic 80-day baseline.
"""
from __future__ import annotations

import argparse
import io
import pickle

import numpy as np
import pandas as pd
import requests

from ..config import DATA
from .synth import LightCurve, Target, Truth

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
COLS = ("kepid,kepoi_name,koi_disposition,koi_fpflag_nt,koi_fpflag_ss,koi_fpflag_co,koi_fpflag_ec,"
        "koi_period,koi_time0bk,koi_duration,koi_depth,koi_model_snr,koi_srad,koi_slogg,koi_steff")
# Kepler quality bits treated as "flagged cadences": attitude tweak, safe mode, coarse point,
# Earth point, desaturation (momentum dump), manual exclude
FLAG_BITS = 1 | 2 | 4 | 8 | 32 | 128


def fetch_koi_table() -> pd.DataFrame:
    q = f"select {COLS} from cumulative where koi_period < 20 and koi_period > 0.5 and koi_model_snr > 10"
    r = requests.get(TAP, params={"query": q, "format": "csv"}, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.to_csv(DATA / "koi_cumulative_subset.csv", index=False)
    return df


def _label(row) -> str | None:
    if row.koi_disposition == "CONFIRMED":
        return "H1"
    if row.koi_disposition != "FALSE POSITIVE":
        return None
    nt, ss, co, ec = row.koi_fpflag_nt, row.koi_fpflag_ss, row.koi_fpflag_co, row.koi_fpflag_ec
    if ec:
        return None                      # ephemeris match: contamination from another source, ambiguous
    if co:
        return "H3"
    if ss and not nt:
        return "H2"
    if nt and not ss:
        return "H4|H5"
    return None


def download_target(row, idx: int, quarter_pref=(3, 4, 5, 6, 2)):
    import lightkurve as lk
    sr = lk.search_lightcurve(f"KIC {int(row.kepid)}", mission="Kepler", author="Kepler", cadence="long")
    if len(sr) == 0:
        return None
    qs = [int(str(m).split()[-1]) if str(m).split()[-1].isdigit() else -1 for m in sr.mission]
    pick = next((qs.index(q) for q in quarter_pref if q in qs), 0)
    lc = sr[pick].download(download_dir=str(DATA / "mast"), quality_bitmask="none")
    t = np.asarray(lc.time.value, float)
    f = np.asarray(lc.pdcsap_flux.value, float)
    fe = np.asarray(lc.pdcsap_flux_err.value, float)
    qual = np.asarray(lc.quality.value, int)
    cx = np.asarray(lc.centroid_col.value, float)
    cy = np.asarray(lc.centroid_row.value, float)
    good = np.isfinite(t) & np.isfinite(f) & np.isfinite(cx) & np.isfinite(cy)
    flagged = (qual & FLAG_BITS) != 0
    # keep flagged cadences in the series (systematics test needs them) but drop NaNs
    t, f, fe, flagged, cx, cy = t[good], f[good], fe[good], flagged[good], cx[good], cy[good]
    med = np.nanmedian(f)
    f, fe = f / med, fe / med
    lcobj = LightCurve(time=t, flux=f, flux_err=fe, quality=flagged,
                       cen_x=(cx - np.median(cx)) * 1000.0, cen_y=(cy - np.median(cy)) * 1000.0)
    rad = float(row.koi_srad) if np.isfinite(row.koi_srad) else 1.0
    logg = float(row.koi_slogg) if np.isfinite(row.koi_slogg) else 4.4
    rho = 10 ** (logg - 4.438) / rad
    tid = f"K-{idx:04d}"
    target = Target(target_id=tid, lc=lcobj,
                    signal=dict(period_d=float(row.koi_period), epoch=float(row.koi_time0bk),
                                duration_h=float(row.koi_duration), depth_ppm=float(row.koi_depth),
                                snr=float(row.koi_model_snr)),
                    stellar=dict(teff_k=float(row.koi_steff) if np.isfinite(row.koi_steff) else 5700.0,
                                 radius_rsun=rad, mass_msun=round(rho * rad**3, 3), rho_cat=round(rho, 4),
                                 rho_err_dex=0.12, logg=logg),
                    source="kepler", meta={"mission": "Kepler", "quarter": int(lc.meta.get("QUARTER", -1)),
                                           "n_points": int(len(t)), "cadence_min": 29.4})
    return target


def build_real_set(per_class: int = 12, seed: int = 3):
    df = fetch_koi_table()
    df["label"] = df.apply(_label, axis=1)
    df = df.dropna(subset=["label"])
    rng = np.random.default_rng(seed)
    picks = []
    for lab in ["H1", "H2", "H3", "H4|H5"]:
        sub = df[df.label == lab]
        n = min(per_class, len(sub))
        picks.append(sub.iloc[rng.choice(len(sub), n, replace=False)])
    sel = pd.concat(picks).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    targets, truths = [], []
    for i, row in sel.iterrows():
        try:
            t = download_target(row, i)
        except Exception as exc:
            print("skip", row.kepoi_name, type(exc).__name__, exc)
            continue
        if t is None:
            continue
        targets.append(t)
        # the KOI name lives only inside the gatekeeper's truth record
        truths.append(Truth(target_id=t.target_id, label=row.label,
                            details={"kepoi_name": row.kepoi_name, "kepid": int(row.kepid),
                                     "disposition": row.koi_disposition}))
        print(f"{t.target_id} ok ({len(targets)})", flush=True)
    with open(DATA / "real_set.pkl", "wb") as f:
        pickle.dump((targets, truths), f)
    return targets, truths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=12)
    build_real_set(ap.parse_args().per_class)
