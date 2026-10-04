"""Foreman, analysis and skeptic agent (design 5.4).

Owns: is this result trustworthy, and how much should it move beliefs?
"Everybody lies": the data are sanity-checked before any reasoning, every result
gets a quality grade, and surprising results trigger a counter-experiment.
"""
from __future__ import annotations

import numpy as np

from ..config import HYP_IDS, HYP_LABELS
from ..schemas import CounterExperimentRequest, ResultAssessment, TestResult
from ..vetting.common import epoch_index, phase_fold
from ..vetting.registry import REGISTRY


class Foreman:
    name = "foreman"

    def __init__(self, cfg: dict, enabled: bool = True):
        self.cfg = cfg["foreman"]
        self.enabled = enabled

    # ---- data-trust check -------------------------------------------------------
    def data_trust(self, target) -> dict:
        lc, s = target.lc, target.signal
        f = lc.flux
        issues = []
        finite = np.isfinite(f)
        if finite.mean() < 0.98:
            issues.append(f"{100 * (1 - finite.mean()):.1f}% non-finite flux values")
        med = np.nanmedian(f)
        if abs(med - 1) > 0.05:
            issues.append(f"flux not normalized (median {med:.3f}); possible unit/scale error")
        dup = len(lc.time) - len(np.unique(np.round(lc.time, 6)))
        if dup:
            issues.append(f"{dup} duplicate cadences")
        P, t0, dur = s["period_d"], s["epoch"], s["duration_h"] / 24
        ph = phase_fold(lc.time, P, t0)
        oot = np.abs(ph) > 0.75 * dur          # the dips themselves are not outliers
        fo = f[oot] if oot.sum() > 50 else f
        mad = 1.4826 * np.nanmedian(np.abs(fo - np.nanmedian(fo)))
        outl = np.mean(np.abs(fo - np.nanmedian(fo)) > 8 * mad)
        if outl > 0.01:
            issues.append(f"{100 * outl:.1f}% >8-sigma out-of-transit flux outliers")
        n_tr = len(np.unique(epoch_index(lc.time, P, t0)[np.abs(ph) < 0.35 * dur]))
        if n_tr < 3:
            issues.append(f"only {n_tr} transits covered by data; odd/even and consistency tests will be weak")
        gaps = np.diff(lc.time)
        big = int((gaps > 0.5).sum())
        return dict(n_points=int(len(f)), n_transits=int(n_tr), n_gaps=big, scatter_ppm=float(mad * 1e6),
                    issues=issues, trusted=len([i for i in issues if "unit" in i or "non-finite" in i]) == 0)

    # ---- per-result assessment ------------------------------------------------------
    def grade(self, res: TestResult, target) -> tuple[str, str]:
        m, tid, snr = res.metrics, res.test_id, target.signal.get("snr", 0)
        if res.outcome_bin < 0:
            return "unreliable", "test failed to produce a metric (insufficient in-transit data or fit failure)"
        if tid == "T-odd-even":
            if min(m.get("n_odd_transits", 0), m.get("n_even_transits", 0)) < 2:
                return "unreliable", "fewer than 2 odd or even transits; comparison is meaningless"
            if snr < 10:
                return "marginal", f"signal SNR {snr:.0f} < 10; odd/even difference is noise-dominated"
        if tid == "T-secondary" and (m.get("n_in") or 0) < 5:
            return "unreliable", "phase 0.5 barely sampled"
        if tid in ("T-shape", "T-density") and snr < 12:
            return "marginal", f"SNR {snr:.0f} < 12; ingress/egress poorly constrained"
        if tid == "T-consistency" and (m.get("n_segments") or 0) < 3:
            return "marginal", "fewer than 3 segments with transits"
        if tid == "T-systematics" and (m.get("n_epochs") or 0) < 3:
            return "marginal", "fewer than 3 transit epochs"
        return "ok", "controls pass"

    def assess(self, res: TestResult, target, tables, post: np.ndarray) -> ResultAssessment:
        lik = tables.likelihood(res.test_id, res.outcome_bin) if res.outcome_bin >= 0 else np.ones(len(HYP_IDS))
        if not self.enabled:
            return ResultAssessment(test_id=res.test_id, run_id=res.run_id, quality="ok", weight=1.0,
                                    likelihoods=dict(zip(HYP_IDS, map(float, lik))), critique="(no skeptic)")
        quality, why = self.grade(res, target)
        leader = int(np.argmax(post))
        lik_norm = lik / lik.sum()
        surprise = bool(quality != "unreliable" and lik[leader] < self.cfg["surprise_threshold"]
                        and lik[leader] < lik.max())
        follow = None
        critique = f"{REGISTRY[res.test_id].name}: {res.outcome_label}. Quality {quality}: {why}."
        if surprise:
            favored = HYP_IDS[int(np.argmax(lik))]
            critique += (f" SURPRISE: P(result | {HYP_LABELS[HYP_IDS[leader]]}) = {lik[leader]:.2f}; "
                         f"this favours {HYP_LABELS[favored]}.")
            if REGISTRY[res.test_id].detrend_sensitive and res.params.get("window_factor", 3.0) == 3.0:
                follow = CounterExperimentRequest(
                    reason="Surprising result; rerun with a wider detrending window to rule out a detrending artifact.",
                    suggested_test_id=res.test_id, params={"window_factor": 5.0}, targets_hypothesis=favored)
            else:
                critique += " Needs corroboration from an independent test before stopping."
        w = self.cfg["weights"][quality]
        return ResultAssessment(test_id=res.test_id, run_id=res.run_id, quality=quality, weight=w,
                                likelihoods=dict(zip(HYP_IDS, map(lambda x: round(float(x), 4), lik_norm))),
                                critique=critique, surprise=surprise, follow_up_request=follow)

    def compare_rerun(self, original: TestResult, rerun: TestResult) -> tuple[bool, str]:
        same = original.outcome_bin == rerun.outcome_bin
        if same:
            return True, (f"Detrending control passed: {original.test_id} gives '{rerun.outcome_label}' with "
                          "window x5 as well. Result stands.")
        return False, (f"Detrending control FAILED: '{original.outcome_label}' (x3) vs '{rerun.outcome_label}' (x5). "
                       "Downgrading to marginal.")

    def pre_test_critique(self, test_id: str, target, trust: dict) -> str:
        notes = {
            "T-odd-even": "odd/even needs >= 2 transits of each parity; watch for detrending distortion.",
            "T-secondary": "an eccentric orbit could put the secondary away from phase 0.5; a null is not proof.",
            "T-shape": "V-shapes also arise from grazing planets; don't over-read a single shape metric.",
            "T-density": "catalog stellar density has ~0.1 dex error; small offsets are not significant.",
            "T-centroid": "centroid shifts can be pointing jitter, not only blends; compare with systematics.",
            "T-periodogram": "a rotation peak near P may be ellipsoidal variation of an EB, not spots.",
            "T-systematics": "coincidence with flagged cadences is expected by chance for long durations.",
            "T-consistency": "depth variation can come from spot crossings on a real planet host.",
        }
        extra = f" Data-trust: {trust['n_transits']} transits covered." if trust else ""
        return notes.get(test_id, "") + extra
