"""Large-sample prior-misspecification sweep (0, 50, 100 percent wrong) on worlds 3000-3059, 20 seeds each.

    python scripts/ll_big_misspec.py
    python scripts/ll_big_misspec.py --worlds 2 --seeds 2 --out /tmp/m.json   # smoke

Same manipulation as ll_misspec.py (reused via import, labloop/ is not edited): the surrogate's textbook prior is
(1-f)*truth + f*textbook, and "revision off" makes Surrogate.relax_prior a no-op. Bootstrap resamples WORLDS
(seeds pooled), arms paired by (world, seed). Simulated, team-designed worlds: a mechanism test only.
"""
import argparse, json, time
import numpy as np
from ll_big_benchmark import (ROOT, B, BUDGET, CEN, WORLD0, N_WORLDS, N_SEEDS, curve_ws, run_grid, wboot, tt, fin, f)
from ll_misspec import misspec

ARMS = [(fr, rev) for fr in (0.0, 0.5, 1.0) for rev in (True, False)]


def key(fr, rev):
    return f"wrong={int(fr*100)}%,revision={'on' if rev else 'off'}"


def _unit(args):
    world, seed, _names, budget = args
    out = []
    for fr, rev in ARMS:
        with misspec(fr, rev):
            out.append(curve_ws("LabLoop (full)", world, seed, budget))
    with misspec(None, True):
        out.append(curve_ws("LabLoop − literature prior", world, seed, budget))
    return out


NAMES = [key(*a) for a in ARMS] + ["no prior (use_prior=False)"]


def analyse(grid):
    arms, raw = {}, {}
    for n in NAMES:
        C = grid[n]; h = C[:, :, -1]; t1 = tt(C, 1); t1i = np.where(t1 >= CEN, np.inf, t1)
        arms[n] = {"hits60_mean": float(h.mean()), "hits60_ci": wboot(h), "hits60_median": float(np.median(h)),
                   "first_hit_mean_censored61": float(t1.mean()), "first_hit_mean_ci": wboot(t1),
                   "first_hit_median": fin(np.median(t1i)), "first_hit_reached": int((t1 < CEN).sum())}
        raw[n] = {"hits60": h.tolist(), "t_first": t1.tolist()}
    paired = {}
    for p in (0, 50, 100):
        on, off = raw[f"wrong={p}%,revision=on"], raw[f"wrong={p}%,revision=off"]
        dh = np.array(on["hits60"]) - np.array(off["hits60"]); dt = np.array(on["t_first"]) - np.array(off["t_first"])
        wh = dh.mean(1)
        paired[f"wrong={p}%"] = {
            "d_hits60_on_minus_off": float(dh.mean()), "ci": wboot(dh), "d_hits60_median": float(np.median(dh)),
            "d_first_hit_mean": float(dt.mean()), "d_first_ci": wboot(dt),
            "worlds_on_better": int((wh > 0).sum()), "worlds_equal": int((wh == 0).sum()), "worlds_on_worse": int((wh < 0).sum())}
    return arms, paired, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", type=int, default=N_WORLDS)
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    ap.add_argument("--procs", type=int, default=None)
    ap.add_argument("--out", default="runs/ll_big_misspec.json")
    a = ap.parse_args()
    t0 = time.time()
    worlds = [WORLD0 + i for i in range(a.worlds)]
    grid, totals = run_grid(worlds, a.seeds, NAMES, unit=_unit, procs=a.procs)
    run_s = time.time() - t0
    arms, paired, raw = analyse(grid)
    out = {"worlds": worlds, "seeds_per_world": a.seeds, "budget": BUDGET, "n_runs_per_arm": a.worlds * a.seeds,
           "arms": arms, "paired_revision_on_vs_off": paired, "raw_per_world_seed": raw, "runtime_seconds": round(run_s),
           "method": "prior_f = (1-f)*truth + f*textbook (script-level patch); relax_prior no-op for revision off; bootstrap over WORLDS",
           "caveat": "Team-designed simulator; synthetic worlds; mechanism test only. 'x% wrong' blend is our definition."}
    if a.out:
        (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.out).write_text(json.dumps(out))
    print(f"{a.worlds} worlds x {a.seeds} seeds, {run_s:.0f}s")
    for k, r in arms.items():
        print(f"{k:32s} hits60 {r['hits60_mean']:.2f} [{r['hits60_ci'][0]:.2f},{r['hits60_ci'][1]:.2f}] first(c61) {r['first_hit_mean_censored61']:.1f} [{r['first_hit_mean_ci'][0]:.1f},{r['first_hit_mean_ci'][1]:.1f}] reached {r['first_hit_reached']}")
    for k, p in paired.items():
        print(k, f"on-off d_hits {p['d_hits60_on_minus_off']:+.2f} [{p['ci'][0]:+.2f},{p['ci'][1]:+.2f}] d_first {p['d_first_hit_mean']:+.1f} [{p['d_first_ci'][0]:+.1f},{p['d_first_ci'][1]:+.1f}] better/eq/worse {p['worlds_on_better']}/{p['worlds_equal']}/{p['worlds_on_worse']}")


if __name__ == "__main__":
    main()
