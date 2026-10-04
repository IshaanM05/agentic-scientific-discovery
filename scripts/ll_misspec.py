"""Prior-misspecification sweep: does belief revision matter when the textbook prior is wrong?

    python scripts/ll_misspec.py

No edits to labloop/*. A controlled monkeypatch inside this script wraps the `space_arrays` name used by
labloop.campaign and labloop.surrogate so the surrogate's textbook prior (bandgap and log-T80 means) is
    prior_f = (1 - f) * hidden_truth + f * textbook_prior,   f = fraction wrong in {0, 0.5, 1}
f=1 is the unmodified LabLoop prior (fully wrong in the sense of the world's hidden physics), f=0 is a
perfect prior. Hidden truth is used ONLY to build this experimental manipulation inside the simulator
side; the agent code sees an ordinary prior array. The hard-coded literature hypotheses are unchanged.
"Belief revision" = Surrogate.relax_prior (loosening the prior after a literature claim fails); the
no-revision arm patches it to a no-op. Reference arm: no prior at all (use_prior=False).
Worlds 1000-1019, budget 60, same Config as the benchmark. Writes runs/ll_misspec.json.
Simulated, team-designed worlds: a controlled test of the mechanism, not of real chemistry.
"""
import json
from contextlib import contextmanager
import numpy as np
from ll_common import ROOT, boot_ci, run_curve, time_to, BUDGET
from labloop import campaign, surrogate, chemistry

CEN = BUDGET + 1


@contextmanager
def misspec(f=None, revision=True):
    orig_sa, orig_relax = chemistry.space_arrays, surrogate.Surrogate.relax_prior
    if f is not None:
        def patched():
            X, egp, ltp, egt, ltt, h = orig_sa()
            return X, (1 - f) * egt + f * egp, (1 - f) * ltt + f * ltp, egt, ltt, h
        campaign.space_arrays = patched
        surrogate.space_arrays = patched
    if not revision:
        surrogate.Surrogate.relax_prior = lambda self, prop, observations, keep=0.35: None
    try:
        yield
    finally:
        campaign.space_arrays, surrogate.space_arrays = orig_sa, orig_sa
        surrogate.Surrogate.relax_prior = orig_relax


def run_arm(f, revision, name="LabLoop (full)"):
    with misspec(f, revision):
        return np.array([run_curve(name, s)[0] for s in range(20)], float)


def summ(C):
    h = C[:, -1]
    t1 = np.array([time_to(c, 1, CEN) for c in C]); t3 = np.array([time_to(c, 3, CEN) for c in C])
    ti = np.where(t1 >= CEN, np.inf, t1)
    fin = lambda v: None if not np.isfinite(v) else float(v)
    return {"hits60_mean": float(h.mean()), "hits60_ci": boot_ci(h), "first_hit_median": fin(np.median(ti)),
            "first_hit_mean_censored61": float(t1.mean()), "first_hit_mean_ci": boot_ci(t1),
            "first_hit_reached": int((t1 < CEN).sum()), "third_hit_reached": int((t3 < CEN).sum()),
            "raw_hits60": h.tolist(), "raw_t_first": t1.tolist()}


def main():
    arms = {}
    for f in (0.0, 0.5, 1.0):
        for rev in (True, False):
            arms[f"wrong={int(f*100)}%,revision={'on' if rev else 'off'}"] = (f, rev, run_arm(f, rev))
    with misspec(None, True):
        arms["no prior (use_prior=False)"] = (None, True, np.array([run_curve("LabLoop − literature prior", s)[0] for s in range(20)], float))
    res = {k: summ(v[2]) for k, v in arms.items()}
    paired = {}
    for f in (0, 50, 100):
        on, off = res[f"wrong={f}%,revision=on"], res[f"wrong={f}%,revision=off"]
        dh = np.array(on["raw_hits60"]) - np.array(off["raw_hits60"])
        dt = np.array(on["raw_t_first"]) - np.array(off["raw_t_first"])
        paired[f"wrong={f}%"] = {"d_hits60_on_minus_off": float(dh.mean()), "ci": boot_ci(dh),
                                 "d_first_hit_on_minus_off_mean": float(dt.mean()), "d_first_ci": boot_ci(dt),
                                 "worlds_on_better": int((dh > 0).sum()), "worlds_equal": int((dh == 0).sum()), "worlds_on_worse": int((dh < 0).sum())}
    out = {"worlds": list(range(1000, 1020)), "budget": BUDGET, "arms": {k: {m: v for m, v in r.items() if not m.startswith("raw")} for k, r in res.items()},
           "paired_revision_on_vs_off": paired, "raw": {k: {m: v for m, v in r.items() if m.startswith("raw")} for k, r in res.items()},
           "method": "prior_f = (1-f)*truth + f*textbook, monkeypatched inside the script; relax_prior no-op for revision off; labloop/* unedited",
           "caveat": "Team-designed simulator; synthetic worlds; mechanism test only. Blend definition of 'x% wrong' is ours."}
    (ROOT / "runs/ll_misspec.json").write_text(json.dumps(out, indent=1))
    for k, r in out["arms"].items():
        print(f"{k:34s} hits60 {r['hits60_mean']:.2f} [{r['hits60_ci'][0]:.2f},{r['hits60_ci'][1]:.2f}]  first-hit mean(c61) {r['first_hit_mean_censored61']:.1f} [{r['first_hit_mean_ci'][0]:.1f},{r['first_hit_mean_ci'][1]:.1f}] median {r['first_hit_median']} reached {r['first_hit_reached']}/20")
    for k, p in paired.items():
        print(k, f"revision on-off: d_hits {p['d_hits60_on_minus_off']:+.2f} [{p['ci'][0]:+.2f},{p['ci'][1]:+.2f}] d_first {p['d_first_hit_on_minus_off_mean']:+.1f} [{p['d_first_ci'][0]:+.1f},{p['d_first_ci'][1]:+.1f}] better/equal/worse {p['worlds_on_better']}/{p['worlds_equal']}/{p['worlds_on_worse']}")


if __name__ == "__main__":
    main()
