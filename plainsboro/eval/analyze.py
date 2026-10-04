"""Metrics, bootstrap intervals, matched-accuracy speedup and figures (design 12.3-12.4, 15).

    python -m plainsboro.eval.analyze
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon

from ..config import HYP_IDS, HYP_LABELS, RESULTS, experiment

BENCH = RESULTS / "benchmark"
FIG = RESULTS / "figures"
MAIN = ["B1-checklist", "B2-random", "B3-planner", "P-house-team"]
COLORS = {"P-house-team": "#2a78d6", "B1-checklist": "#eb6834", "B2-random": "#1baf7a", "B3-planner": "#eda100"}
PRETTY = {"B1-checklist": "B1 fixed checklist", "B2-random": "B2 random order", "B3-planner": "B3 EIG planner only",
          "P-house-team": "P House team", "A-no-foreman": "P without Foreman", "A-no-house": "P without House",
          "A-no-cameron": "P without Cameron", "A-no-parallel": "P without parallel dispatch",
          "A-adaptive": "P + Wilson adaptive tables"}


def load():
    rows = [json.loads(line) for line in open(BENCH / "records.jsonl", encoding="utf-8")]
    oracle = json.load(open(BENCH / "oracle.json", encoding="utf-8"))
    return rows, oracle


def tests_to_correct(r) -> int | None:
    traj = r["trajectory"]
    if not r["correct"]:
        return None
    k = len(traj) - 1
    while k > 0 and traj[k - 1]["leader"] == r["truth"]:
        k -= 1
    return traj[k]["tests"]


def brier(r) -> float:
    return float(sum((r["posterior"][h] - (1.0 if h == r["truth"] else 0.0)) ** 2 for h in HYP_IDS))


def ece(rows, n_bins=10) -> float:
    conf = np.array([r["top"] for r in rows])
    corr = np.array([r["correct"] for r in rows], float)
    edges = np.linspace(0, 1, n_bins + 1)
    e = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        m = (conf > a) & (conf <= b)
        if m.any():
            e += m.mean() * abs(conf[m].mean() - corr[m].mean())
    return float(e)


def ci(x, rng, n=1000, fn=np.mean):
    x = np.asarray(x, float)
    if len(x) == 0:
        return (np.nan, np.nan)
    bs = [fn(x[rng.integers(0, len(x), len(x))]) for _ in range(n)]
    return (float(np.percentile(bs, 5)), float(np.percentile(bs, 95)))


def summarize(rows, rng):
    acc = [r["correct"] for r in rows]
    cost = [r["cost"] for r in rows]
    t2c = [tests_to_correct(r) for r in rows]
    c2c = [r["cost"] for r in rows if r["correct"]]
    return {
        "n": len(rows), "accuracy": float(np.mean(acc)), "accuracy_ci90": ci(acc, rng),
        "mean_tests": float(np.mean([r["tests"] for r in rows])), "mean_cost": float(np.mean(cost)),
        "mean_cost_ci90": ci(cost, rng), "cost_to_correct": float(np.mean(c2c)) if c2c else None,
        "tests_to_correct": float(np.mean([t for t in t2c if t is not None])) if any(t is not None for t in t2c) else None,
        "brier": float(np.mean([brier(r) for r in rows])), "ece": ece(rows),
        "needs_human_rate": float(np.mean([r["needs_human"] for r in rows])),
        "escalations_per_target": float(np.mean([r["escalations"] for r in rows])),
        "wall_clock_ms": 1000 * float(np.mean([r["wall_clock_s"] for r in rows])),
        "parallel_batches": None,
    }


def curve(rows_by_thr, idx):
    """(cost, accuracy) points over the threshold sweep, for a subset of target indices."""
    pts = []
    for thr, rows in sorted(rows_by_thr.items()):
        sub = [rows[i] for i in idx]
        pts.append((float(np.mean([r["cost"] for r in sub])), float(np.mean([r["correct"] for r in sub]))))
    return sorted(pts)


def cost_to_reach(pts, target_acc):
    """Min mean cost at which a condition's best-so-far accuracy reaches target_acc (linear interp)."""
    best = -1.0
    prev = None
    for c, a in pts:
        a_run = max(best, a)
        if a_run >= target_acc - 1e-12:
            if prev is None or a_run == prev[1]:
                return c
            pc, pa = prev
            return pc + (target_acc - pa) / (a_run - pa) * (c - pc) if a_run > pa else c
        best = a_run
        prev = (c, a_run)
    return None


def speedup(by_cond_thr, base, prop, thr0, rng, n_boot):
    """Matched-accuracy speedup: cost(base) / cost(prop) at the highest accuracy BOTH can reach.

    Both costs are read off each condition's own accuracy-vs-cost curve (threshold sweep).
    Also reports the accuracy ceilings, since a higher ceiling is not captured by the ratio.
    """
    n = len(next(iter(by_cond_thr[prop].values())))

    def one(idx):
        cb, cp = curve(by_cond_thr[base], idx), curve(by_cond_thr[prop], idx)
        level = min(max(a for _, a in cb), max(a for _, a in cp))
        return cost_to_reach(cb, level) / cost_to_reach(cp, level), level, max(a for _, a in cb), max(a for _, a in cp)

    point, level, ceil_b, ceil_p = one(np.arange(n))
    bs = np.array([one(rng.integers(0, n, n)) for _ in range(n_boot)])
    return {"point": float(point), "matched_accuracy": float(level), "ci90": (float(np.percentile(bs[:, 0], 5)),
            float(np.percentile(bs[:, 0], 95))), "ceiling_baseline": float(ceil_b), "ceiling_house": float(ceil_p),
            "ceiling_gain_ci90": (float(np.percentile(bs[:, 3] - bs[:, 2], 5)),
                                  float(np.percentile(bs[:, 3] - bs[:, 2], 95)))}


def cost_table(by_cond_thr, levels=(0.75, 0.80, 0.85, 0.88, 0.90)):
    out = {}
    for c in MAIN:
        n = len(next(iter(by_cond_thr[c].values())))
        pts = curve(by_cond_thr[c], np.arange(n))
        out[c] = {str(lv): cost_to_reach(pts, lv) for lv in levels}
    return out


def acc_at_k(rows, k):
    out = []
    for r in rows:
        best = None
        for t in r["trajectory"]:
            if t["tests"] <= k:
                best = t
        out.append(best["leader"] == r["truth"])
    return float(np.mean(out))


def figures(by_cond_thr, nostop, oracle, summ, thr0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b29", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6})
    n = len(next(iter(by_cond_thr["P-house-team"].values())))
    idx = np.arange(n)

    # 1) accuracy vs cost frontier
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    offsets = {"P-house-team": (6, 6), "B3-planner": (6, 8), "B2-random": (6, -12), "B1-checklist": (6, -2)}
    for c in MAIN:
        pts = curve(by_cond_thr[c], idx)
        xs, ys = zip(*pts)
        ax.plot(xs, ys, "-o", color=COLORS[c], lw=2, ms=6, mec="white", mew=1.5, label=PRETTY[c])
        ax.annotate(PRETTY[c], (xs[-1], ys[-1]), xytext=offsets[c], textcoords="offset points", va="center",
                    fontsize=9, color="#2b2b29")
    ocost = [o["confident_cost"] for o in oracle if o["confident_cost"] is not None]
    oacc = len(ocost) / len(oracle)
    ax.plot([np.mean(ocost)], [oacc], marker="*", ms=14, color="#52514e", ls="none", label="Oracle (hindsight)")
    ax.annotate("Oracle (hindsight)", (np.mean(ocost), oacc), xytext=(6, -10), textcoords="offset points", fontsize=9)
    p = summ["conditions"]["P-house-team"]
    ax.axhline(p["accuracy"], color="#b5b4ad", lw=1, ls="--")
    ax.set_xlabel("Mean diagnostic cost per target (cost units)")
    ax.set_ylabel("Accuracy of final verdict")
    ax.set_title("Accuracy vs. vetting cost (stopping-threshold sweep, blind set)", loc="left", fontsize=11)
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.set_xlim(left=0, right=ax.get_xlim()[1] + 1.8)
    fig.tight_layout()
    fig.savefig(FIG / "accuracy_vs_cost.png", dpi=160)
    plt.close(fig)

    # 2) accuracy@k (no early stop)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ks = [1, 2, 3, 4, 5]
    w = 0.2
    for j, c in enumerate(MAIN):
        vals = [acc_at_k(nostop[c], k) for k in ks]
        ax.bar(np.array(ks) + (j - 1.5) * w, vals, width=w - 0.02, color=COLORS[c], label=PRETTY[c])
    ax.set_xlabel("Tests run (k)")
    ax.set_ylabel("Leader correct after k tests")
    ax.set_ylim(0, 1)
    ax.set_title("Accuracy after k tests (same budget, no early stopping)", loc="left", fontsize=11, pad=26)
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.tight_layout()
    fig.savefig(FIG / "accuracy_at_k.png", dpi=160)
    plt.close(fig)

    # 3) reliability diagram for P
    rows = by_cond_thr["P-house-team"][thr0]
    conf = np.array([r["top"] for r in rows])
    corr = np.array([r["correct"] for r in rows], float)
    edges = np.linspace(0.2, 1.0, 9)
    xs, ys, ns = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (conf > a) & (conf <= b)
        if m.sum() >= 3:
            xs.append(conf[m].mean()); ys.append(corr[m].mean()); ns.append(int(m.sum()))
    fig, ax = plt.subplots(figsize=(4.4, 4.2))
    ax.plot([0, 1], [0, 1], color="#b5b4ad", lw=1, ls="--")
    ax.plot(xs, ys, "-o", color=COLORS["P-house-team"], lw=2, ms=7, mec="white", mew=1.5)
    for x, y, k in zip(xs, ys, ns):
        ax.annotate(f"n={k}", (x, y), xytext=(4, -12), textcoords="offset points", fontsize=8, color="#52514e")
    ax.set_xlabel("Verdict confidence (top posterior)")
    ax.set_ylabel("Observed accuracy")
    ax.set_title("Calibration: P House team", loc="left", fontsize=11)
    ax.set_xlim(0.2, 1.02); ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(FIG / "calibration_P.png", dpi=160)
    plt.close(fig)


def main():
    cfg = experiment()
    rng = np.random.default_rng(cfg["seeds"]["bootstrap"])
    thr0 = cfg["stopping"]["posterior_threshold"]
    rows, oracle = load()
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["condition"]][r["threshold"]].append(r)
    nostop = {c: by[c].pop(1.01) for c in MAIN if 1.01 in by[c]}
    summ = {"threshold": thr0, "budget": cfg["budget"], "conditions": {}, "ablations": {}, "speedup": {},
            "paired_tests": {}, "accuracy_at_k": {}, "per_class_accuracy": {}}
    for c in by:
        s = summarize(by[c][thr0], rng)
        (summ["conditions"] if c in MAIN else summ["ablations"])[c] = s
    for c in nostop:
        summ["accuracy_at_k"][c] = {k: acc_at_k(nostop[c], k) for k in range(1, 6)}
    for c in MAIN:
        summ["per_class_accuracy"][c] = {h: float(np.mean([r["correct"] for r in by[c][thr0] if r["truth"] == h]))
                                         for h in HYP_IDS}
    nb = cfg["benchmark"]["n_bootstrap"]
    for base in ["B1-checklist", "B2-random", "B3-planner"]:
        summ["speedup"][base] = speedup(by, base, "P-house-team", thr0, rng, nb)
        a = np.array([r["cost"] for r in by[base][thr0]])
        b = np.array([r["cost"] for r in by["P-house-team"][thr0]])
        try:
            st = wilcoxon(a, b)
            summ["paired_tests"][base] = {"wilcoxon_cost_p": float(st.pvalue), "mean_cost_diff": float((a - b).mean())}
        except ValueError:
            pass
    summ["cost_to_reach_accuracy"] = cost_table(by)
    ocost = [o["confident_cost"] for o in oracle if o["confident_cost"] is not None]
    summ["oracle"] = {"frac_solvable_confidently": len(ocost) / len(oracle), "mean_cost_when_solvable": float(np.mean(ocost))}
    with open(RESULTS / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1)
    figures(by, nostop, oracle, summ, thr0)
    write_report(summ)
    return summ


def _fmt_ci(t):
    return f"[{t[0]:.2f}, {t[1]:.2f}]"


def write_report(s):
    L = ["# Benchmark results (auto-generated by `python -m plainsboro.eval.analyze`)", "",
         f"Blind synthetic set, n = {s['conditions']['P-house-team']['n']} targets. Stopping threshold "
         f"{s['threshold']}, budget {s['budget']['max_tests']} tests / {s['budget']['cost_units_max']} cost units. "
         "All conditions replay identical precomputed test outcomes (matched conditions). 90% bootstrap CIs.", "",
         "## Main comparison", "",
         "| Condition | Accuracy | Mean cost | Mean tests | Cost-to-correct | Tests-to-correct | Brier | ECE | needs_human |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c, m in list(s["conditions"].items()) + list(s["ablations"].items()):
        L.append(f"| {PRETTY.get(c, c)} | {m['accuracy']:.3f} {_fmt_ci(m['accuracy_ci90'])} | {m['mean_cost']:.2f} "
                 f"{_fmt_ci(m['mean_cost_ci90'])} | {m['mean_tests']:.2f} | {m['cost_to_correct']:.2f} | "
                 f"{m['tests_to_correct']:.2f} | {m['brier']:.3f} | {m['ece']:.3f} | {m['needs_human_rate']:.2f} |")
    L += ["", f"Oracle (hindsight-optimal subset): {s['oracle']['frac_solvable_confidently']:.2f} of targets "
              f"solvable to >= {s['threshold']} within budget, mean cost {s['oracle']['mean_cost_when_solvable']:.2f}.",
          "", "## Speedup at matched accuracy", "",
          "Each condition's accuracy-vs-cost curve comes from its stopping-threshold sweep. Speedup = cost the "
          "baseline needs / cost the House team needs, both at the highest accuracy the two can reach "
          "(usually the baseline's ceiling). Ceiling = best accuracy reachable within the 5-test / 10-unit budget.", "",
          "| Baseline | Matched accuracy | Speedup | 90% CI | Baseline ceiling | House ceiling | Ceiling gain 90% CI | Wilcoxon p (paired cost @0.9) |",
          "|---|---|---|---|---|---|---|---|"]
    for b, v in s["speedup"].items():
        p = s["paired_tests"].get(b, {}).get("wilcoxon_cost_p", float("nan"))
        L.append(f"| {PRETTY[b]} | {v['matched_accuracy']:.3f} | {v['point']:.2f}x | {_fmt_ci(v['ci90'])} | "
                 f"{v['ceiling_baseline']:.3f} | {v['ceiling_house']:.3f} | {_fmt_ci(v['ceiling_gain_ci90'])} | {p:.2g} |")
    L += ["", "### Mean cost to reach a given accuracy (None = not reachable within budget)", "",
          "| Condition | " + " | ".join(next(iter(s["cost_to_reach_accuracy"].values())).keys()) + " |",
          "|---" * (1 + len(next(iter(s["cost_to_reach_accuracy"].values())))) + "|"]
    for c, d in s["cost_to_reach_accuracy"].items():
        L.append(f"| {PRETTY[c]} | " + " | ".join("—" if v is None else f"{v:.2f}" for v in d.values()) + " |")
    L += ["", "## Accuracy after k tests (no early stopping)", "", "| Condition | k=1 | k=2 | k=3 | k=4 | k=5 |",
          "|---|---|---|---|---|---|"]
    for c, d in s["accuracy_at_k"].items():
        L.append(f"| {PRETTY[c]} | " + " | ".join(f"{d[k]:.3f}" for k in d) + " |")
    L += ["", "## Per-class accuracy at the operating threshold", "",
          "| Condition | " + " | ".join(HYP_LABELS[h] for h in HYP_IDS) + " |", "|---" * 6 + "|"]
    for c, d in s["per_class_accuracy"].items():
        L.append(f"| {PRETTY[c]} | " + " | ".join(f"{d[h]:.2f}" for h in HYP_IDS) + " |")
    L += ["", "Figures: `results/figures/accuracy_vs_cost.png`, `accuracy_at_k.png`, `calibration_P.png`."]
    with open(RESULTS / "REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    s = main()
    print(open(RESULTS / "REPORT.md", encoding="utf-8").read())
