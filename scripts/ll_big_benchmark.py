"""Large-sample rerun of the LabLoop benchmark, with bootstrap CIs that resample WORLDS.

    python scripts/ll_big_benchmark.py                  # worlds 3000-3059, 20 seeds each, budget 60
    python scripts/ll_big_benchmark.py --worlds 2 --seeds 2 --out /tmp/x.json --plot ''   # smoke

Outputs runs/ll_big_benchmark.json and docs/ll_big_headline.png. Offline, deterministic, no model calls.
Same arms and ablations as ll_benchmark.py. Every (world, seed) unit is a pure function of (world, seed),
so multiprocessing changes only the runtime, never the numbers (results are assembled by index).
Unit of resampling = the WORLD: seeds within a world share the same hidden physics and are not independent,
so each bootstrap draw resamples worlds with replacement and keeps all their seeds (pooled).
Arms are paired by (world, seed). Time to hit: not reached = inf for medians (None in JSON = undefined),
and budget+1 (61) for paired differences. Simulator is team-designed; worlds are synthetic.
"""
import argparse, json, time
from multiprocessing import Pool
import numpy as np
from ll_common import ROOT, B, BUDGET, MAIN, ABL, Config, run_campaign, set_world, space_arrays, time_to

WORLD0, N_WORLDS, N_SEEDS = 3000, 60, 20
CEN = BUDGET + 1


def curve_ws(name, world, seed, budget=BUDGET):
    """Distinct true hits per integer budget unit for one arm on one (world, seed)."""
    set_world(world)
    if name == "Random":
        return B.run_random(seed, budget)
    if name == "Grad-student OFAT":
        return B.run_ofat(seed, budget)
    cfg = Config(seed=seed, budget=budget, target_discoveries=99, record_maps=False, label=name,
                 world=world, **B.STRATEGIES[name])
    trace = run_campaign(cfg)
    costs, flags, seen = [], [], set()
    for rd in trace["rounds"]:
        for e in rd["experiments"]:
            costs.append(e["result"]["cost"])
            flags.append(bool(e["true_hit"]) and e["idx"] not in seen)
            seen.add(e["idx"])
    return B._curve_from(costs, flags, budget)


def _unit(args):
    world, seed, names, budget = args
    return [curve_ws(n, world, seed, budget) for n in names]


def run_grid(worlds, seeds, names, budget=BUDGET, unit=_unit, procs=None):
    """Return {name: array (W, S, budget+1)} plus true hit counts per world. Deterministic for any procs."""
    jobs = [(w, s, names, budget) for w in worlds for s in range(seeds)]
    if procs == 1:
        out = [unit(j) for j in jobs]
    else:
        with Pool(procs) as p:
            out = p.map(unit, jobs, chunksize=1)  # map keeps job order
    W, S = len(worlds), seeds
    grid = {n: np.array([o[i] for o in out], float).reshape(W, S, -1) for i, n in enumerate(names)}
    totals = []
    for w in worlds:
        set_world(w); totals.append(int(space_arrays()[-1].sum()))
    return grid, np.array(totals)


def wboot(x, stat=np.mean, n=10000, seed=0, alpha=0.05):
    """Percentile CI of stat over WORLD-level resampling. x has shape (W, S); each draw picks W worlds with
    replacement and pools all their seeds. Percentiles take actual draws (no interpolation) so inf is safe."""
    x = np.asarray(x, float)
    W = x.shape[0]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, W, (n, W))
    pooled = x[idx].reshape(n, -1)
    vals = np.sort(stat(pooled, axis=1))
    lo = vals[int(np.floor(n * alpha / 2))]; hi = vals[int(np.ceil(n * (1 - alpha / 2))) - 1]
    return float(lo), float(hi)


def fin(v):
    return None if not np.isfinite(v) else float(v)


def f(v, spec=".1f"):
    return ">60" if v is None else format(v, spec)


def tt(C, k):
    return np.array([[time_to(c, k, CEN) for c in row] for row in C], float)


def summarise(grid, totals, names):
    res, raw = {}, {}
    for n in names:
        C = grid[n]; h = C[:, :, -1]
        t1, t3 = tt(C, 1), tt(C, 3)
        t1i = np.where(t1 >= CEN, np.inf, t1); t3i = np.where(t3 >= CEN, np.inf, t3)
        share = h / totals[:, None]
        res[n] = {
            "hits60_mean": float(h.mean()), "hits60_mean_ci": wboot(h),
            "hits60_median": float(np.median(h)), "hits60_median_ci": wboot(h, np.median),
            "share_found_mean": float(share.mean()), "share_found_ci": wboot(share),
            "first_hit_mean_censored61": float(t1.mean()), "first_hit_mean_ci": wboot(t1),
            "first_hit_median": fin(np.median(t1i)), "first_hit_median_ci": [fin(v) for v in wboot(t1i, np.median)],
            "first_hit_reached": int((t1 < CEN).sum()),
            "third_hit_mean_censored61": float(t3.mean()), "third_hit_mean_ci": wboot(t3),
            "third_hit_median": fin(np.median(t3i)), "third_hit_median_ci": [fin(v) for v in wboot(t3i, np.median)],
            "third_hit_reached": int((t3 < CEN).sum()),
        }
        raw[n] = {"hits60": h.tolist(), "t_first": t1.tolist(), "t_third": t3.tolist()}
    return res, raw


def paired(raw, ref, names):
    R = {k: np.array(v) for k, v in raw[ref].items()}
    out = {}
    for n in names:
        if n == ref:
            continue
        O = {k: np.array(v) for k, v in raw[n].items()}
        dh = R["hits60"] - O["hits60"]; d1 = R["t_first"] - O["t_first"]; d3 = R["t_third"] - O["t_third"]
        wh = dh.mean(1)  # per-world mean gain
        out[n] = {
            "d_hits60_mean": float(dh.mean()), "d_hits60_ci": wboot(dh), "d_hits60_median": float(np.median(dh)),
            "d_hits60_median_ci": wboot(dh, np.median),
            "d_first_hit_mean": float(d1.mean()), "d_first_hit_mean_ci": wboot(d1),
            "d_first_hit_median": float(np.median(d1)), "d_first_hit_median_ci": wboot(d1, np.median),
            "d_third_hit_mean": float(d3.mean()), "d_third_hit_mean_ci": wboot(d3),
            "d_third_hit_median": float(np.median(d3)), "d_third_hit_median_ci": wboot(d3, np.median),
            "worlds_ref_more_hits": int((wh > 0).sum()), "worlds_equal": int((wh == 0).sum()),
            "worlds_ref_fewer_hits": int((wh < 0).sum()),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", type=int, default=N_WORLDS)
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    ap.add_argument("--procs", type=int, default=None)
    ap.add_argument("--out", default="runs/ll_big_benchmark.json")
    ap.add_argument("--plot", default="docs/ll_big_headline.png")
    a = ap.parse_args()
    t0 = time.time()
    names = list(B.STRATEGIES)
    worlds = [WORLD0 + i for i in range(a.worlds)]
    grid, totals = run_grid(worlds, a.seeds, names, procs=a.procs)
    run_s = time.time() - t0
    res, raw = summarise(grid, totals, names)
    pr = paired(raw, "LabLoop (full)", names)
    out = {"worlds": worlds, "seeds_per_world": a.seeds, "budget": BUDGET, "censor_value": CEN,
           "n_runs_per_arm": a.worlds * a.seeds, "hits_per_world": totals.tolist(), "strategies": res,
           "paired_vs_labloop_full": pr, "raw_per_world_seed": raw, "runtime_seconds": round(run_s),
           "method": "bootstrap over WORLDS (10000 draws, all seeds of a drawn world pooled); arms paired by (world, seed)",
           "caveat": "Team-designed simulator; synthetic worlds; benchmark only."}
    if a.out:
        (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.out).write_text(json.dumps(out))
    if a.plot:
        plot(grid, res, pr, a.worlds, a.seeds, ROOT / a.plot)
    print(f"{a.worlds} worlds x {a.seeds} seeds, {run_s:.0f}s")
    for n in names:
        r = res[n]
        print(f"{n:28s} hits60 {r['hits60_mean']:.2f} [{r['hits60_mean_ci'][0]:.2f},{r['hits60_mean_ci'][1]:.2f}] "
              f"first med {f(r['first_hit_median'])} third med {f(r['third_hit_median'])}")
    for n, p in pr.items():
        print(f"LabLoop - {n:26s} d_hits {p['d_hits60_mean']:+.2f} [{p['d_hits60_ci'][0]:+.2f},{p['d_hits60_ci'][1]:+.2f}] "
              f"d_first_med {p['d_first_hit_median']:+.1f} [{p['d_first_hit_median_ci'][0]:+.1f},{p['d_first_hit_median_ci'][1]:+.1f}]")


def plot(grid, res, pr, nw, ns, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"Random": "#999999", "Grad-student OFAT": "#d9822b", "Pure BO (no literature)": "#2b6cb0",
            "LabLoop (full)": "#1a8f5a"}
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw={"width_ratios": [1.4, 1, 1]})
    for n in MAIN:
        C = grid[n].reshape(-1, grid[n].shape[-1]); x = np.arange(C.shape[1])
        ax[0].plot(x, C.mean(0), color=cols[n], lw=2, label=n)
        ax[0].fill_between(x, np.percentile(C, 25, 0), np.percentile(C, 75, 0), color=cols[n], alpha=.12)
    ax[0].set_xlabel("budget spent (units)"); ax[0].set_ylabel("distinct true hits (mean, IQR band)")
    ax[0].set_title(f"{nw} unseen worlds x {ns} seeds"); ax[0].legend(frameon=False, fontsize=8)
    ys = np.arange(len(MAIN))[::-1]
    for y, n in zip(ys, MAIN):
        r = res[n]; m = r["hits60_mean"]; lo, hi = r["hits60_mean_ci"]
        ax[1].errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="o", color=cols[n], capsize=3)
    ax[1].set_yticks(ys); ax[1].set_yticklabels(MAIN, fontsize=8); ax[1].set_xlabel("mean hits by 60 (95% CI over worlds)")
    others = [n for n in pr if n in ("Pure BO (no literature)", "LLM-style (no BO)", "Grad-student OFAT", "Random")]
    ys2 = np.arange(len(others))[::-1]
    for y, n in zip(ys2, others):
        p = pr[n]; m = p["d_hits60_mean"]; lo, hi = p["d_hits60_ci"]
        ax[2].errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="o", color="#1a8f5a", capsize=3)
    ax[2].axvline(0, color="#888", ls=":"); ax[2].set_yticks(ys2); ax[2].set_yticklabels(others, fontsize=8)
    ax[2].set_xlabel("LabLoop minus arm: hits by 60 (paired, 95% CI over worlds)")
    fig.suptitle("LabLoop large-sample benchmark: simulated, team-designed worlds (not real devices)", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
