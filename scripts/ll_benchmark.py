"""Rerun the LabLoop benchmark on unseen worlds, with paired bootstrap CIs, and verify the README table.

    python scripts/ll_benchmark.py            # worlds 1000-1019, 20 seeds, budget 60  (about 2 min)
    python scripts/ll_benchmark.py --seeds 2  # smoke

Outputs runs/ll_benchmark.json and docs/ll_headline.png. Offline, deterministic, no model calls.
The simulator is team-designed and the worlds are synthetic: a benchmark, not evidence about real devices.
Unit of resampling = the 20 (world, seed) pairs; all arms share the same pairs, so differences are paired.
Time-to-hit medians treat "not reached" as +inf (None in JSON = undefined, i.e. half or more not reached),
exactly as labloop.benchmark does; paired time differences code not-reached as budget+1 (61). Counts reached are reported.
"""
import argparse, json, time
import numpy as np
from ll_common import ROOT, B, BUDGET, MAIN, ABL, boot_ci, run_curve, time_to

# Claimed in docs/LABLOOP_README.md: name -> (first-hit median, third-hit median, hits by 60, share found).
CLAIMED = {
    "Random": (None, None, 0.1, 0.01), "Grad-student OFAT": (6, None, 2.9, 0.20),
    "LLM-style (no BO)": (6.5, 34, 2.9, 0.22), "Pure BO (no literature)": (30.5, 37, 8.2, 0.56),
    "LabLoop (full)": (6.5, 24, 9.9, 0.67), "LabLoop − arena": (11.5, 24, 9.2, 0.58),
    "LabLoop − negative memory": (6.5, 21, 9.6, 0.65), "LabLoop − literature prior": (16.5, 28.5, 10.4, 0.68),
}


def fin(v):
    """JSON-safe: infinite (not reached) -> None."""
    return None if not np.isfinite(v) else float(v)


def f(v, spec=".1f"):
    return ">60" if v is None else format(v, spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="runs/ll_benchmark.json")
    ap.add_argument("--plot", default="docs/ll_headline.png")
    a = ap.parse_args()
    t0, cen = time.time(), BUDGET + 1
    names = list(B.STRATEGIES)
    curves = {n: [run_curve(n, s)[0] for s in range(a.seeds)] for n in names}
    from labloop.chemistry import set_world, space_arrays
    totals = []
    for s in range(a.seeds):
        set_world(1000 + s); totals.append(int(space_arrays()[-1].sum()))
    totals = np.array(totals)
    res, raw = {}, {}
    for n in names:
        C = np.array(curves[n], float)
        h60 = C[:, -1]
        t1 = np.array([time_to(c, 1, cen) for c in C]); t3 = np.array([time_to(c, 3, cen) for c in C])
        # medians treat "not reached" as +inf (as labloop.benchmark does): undefined (None) if half or more are censored
        t1i = np.where(t1 >= cen, np.inf, t1); t3i = np.where(t3 >= cen, np.inf, t3)
        share = h60 / totals
        res[n] = {
            "hits60_mean": float(h60.mean()), "hits60_mean_ci": boot_ci(h60),
            "hits60_median": float(np.median(h60)),
            "first_hit_median": fin(np.median(t1i)), "first_hit_median_ci": [fin(v) for v in boot_ci(t1i, np.median)],
            "first_hit_reached": int((t1 < cen).sum()),
            "third_hit_median": fin(np.median(t3i)), "third_hit_median_ci": [fin(v) for v in boot_ci(t3i, np.median)],
            "third_hit_reached": int((t3 < cen).sum()), "share_found_mean": float(share.mean()),
        }
        raw[n] = {"hits60": h60.tolist(), "t_first": t1.tolist(), "t_third": t3.tolist()}
    # paired differences vs LabLoop (full): positive hits diff / negative time diff favour LabLoop
    L = raw["LabLoop (full)"]
    paired = {}
    for n in names:
        if n == "LabLoop (full)":
            continue
        d_h = np.array(L["hits60"]) - np.array(raw[n]["hits60"])
        d_t1 = np.array(L["t_first"]) - np.array(raw[n]["t_first"])
        d_t3 = np.array(L["t_third"]) - np.array(raw[n]["t_third"])
        paired[n] = {"d_hits60_mean": float(d_h.mean()), "d_hits60_ci": boot_ci(d_h),
                     "d_first_hit_median": float(np.median(d_t1)), "d_first_hit_ci": boot_ci(d_t1, np.median),
                     "d_third_hit_median": float(np.median(d_t3)), "d_third_hit_ci": boot_ci(d_t3, np.median),
                     "worlds_labloop_more_hits": int((d_h > 0).sum()), "worlds_equal": int((d_h == 0).sum()),
                     "worlds_labloop_fewer_hits": int((d_h < 0).sum())}
    # README verification (README rounding: hits to 0.1, share to whole percent)
    check = []
    for n, (f1, f3, hits, share) in CLAIMED.items():
        r = res[n]
        got = (r["first_hit_median"], r["third_hit_median"],
               round(r["hits60_mean"], 1), round(r["share_found_mean"], 2))
        want = (f1, f3, hits, share)
        ok = got[0] == want[0] and got[1] == want[1] and abs(got[2] - hits) < .051 and abs(got[3] - share) < .0051
        check.append({"strategy": n, "claimed": want, "rerun": got, "match": bool(ok)})
    full = a.seeds == 20
    out = {"worlds": [1000 + s for s in range(a.seeds)], "seeds": a.seeds, "budget": BUDGET,
           "censor_value": cen, "hits_per_world": totals.tolist(), "strategies": res, "raw_per_seed": raw,
           "paired_vs_labloop_full": paired, "readme_check": check if full else [],
           "readme_all_match": all(c["match"] for c in check) if full else None,
           "caveat": "Team-designed simulator; synthetic worlds; benchmark only. n=20 world-seed pairs."}
    (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / a.out).write_text(json.dumps(out))
    plot(curves, res, ROOT / a.plot)
    print(f"wrote {a.out}, {a.plot} in {time.time()-t0:.0f}s")
    for n in names:
        r = res[n]
        print(f"{n:28s} hits60 {r['hits60_mean']:.2f} [{r['hits60_mean_ci'][0]:.2f},{r['hits60_mean_ci'][1]:.2f}] "
              f"first {f(r['first_hit_median'])} [{f(r['first_hit_median_ci'][0])},{f(r['first_hit_median_ci'][1])}] "
              f"({r['first_hit_reached']}/{a.seeds}) third {f(r['third_hit_median'])} ({r['third_hit_reached']}/{a.seeds})")
    for n, p in paired.items():
        print(f"LabLoop - {n:26s} d_hits {p['d_hits60_mean']:+.2f} [{p['d_hits60_ci'][0]:+.2f},{p['d_hits60_ci'][1]:+.2f}] "
              f"d_first {p['d_first_hit_median']:+.1f} [{p['d_first_hit_ci'][0]:+.1f},{p['d_first_hit_ci'][1]:+.1f}]")
    for c in check:
        print("OK  " if c["match"] else "DIFF", c["strategy"], c["claimed"], "->", c["rerun"])


def plot(curves, res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"Random": "#999999", "Grad-student OFAT": "#d9822b", "Pure BO (no literature)": "#2b6cb0",
            "LabLoop (full)": "#1a8f5a"}
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
    for n in MAIN:
        C = np.array(curves[n], float); x = np.arange(C.shape[1])
        m = C.mean(0)
        lo, hi = np.percentile(C, 25, 0), np.percentile(C, 75, 0)
        ax[0].plot(x, m, color=cols[n], lw=2, label=n); ax[0].fill_between(x, lo, hi, color=cols[n], alpha=.12)
    ax[0].set_xlabel("budget spent (units)"); ax[0].set_ylabel("distinct true hits (mean, IQR band)")
    ax[0].set_title("20 unseen simulated worlds, 60-unit budget"); ax[0].legend(frameon=False, fontsize=8)
    ys = np.arange(len(MAIN))[::-1]
    for y, n in zip(ys, MAIN):
        r = res[n]
        med = 61 if r["first_hit_median"] is None else r["first_hit_median"]
        lo, hi = [61 if v is None else v for v in r["first_hit_median_ci"]]
        ax[1].errorbar(med, y, xerr=[[med - lo], [hi - med]],
                       fmt="o", color=cols[n], capsize=3)
        ax[1].text(62, y, f"{r['first_hit_reached']}/{len(curves[n])} reached", va="center", fontsize=8)
    ax[1].set_yticks(ys); ax[1].set_yticklabels(MAIN, fontsize=8); ax[1].set_xlim(0, 80)
    ax[1].axvline(61, color="#bbb", ls=":"); ax[1].set_xlabel("median units to first hit (95% CI; 61 = none)")
    fig.suptitle("LabLoop benchmark rerun: simulated, team-designed worlds (not real devices)", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
