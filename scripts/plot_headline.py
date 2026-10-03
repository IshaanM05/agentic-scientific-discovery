"""Headline plot -> docs/headline.png. Offline (reads cached runs/t009 JSON; recomputes baselines).
Panel 1: hits vs experiments used (mean line, IQR band across seeds). Panel 2: experiments to the k-th hit (median, IQR; censored at 61).
random: 500 seeds; OFAT, BO, blind llm_bo: seeds 0-19; named llm_bo: seeds 0-4 only (memorisation flag set)."""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd.baselines import run_arm  # noqa: E402

B = 60
T = np.arange(0, B + 1)


def curves(hs):
    return np.array([[sum(x <= t for x in h) for t in T] for h in hs])


def kth(hs, k):
    return np.array([h[k - 1] if len(h) >= k else B + 1 for h in hs])


def load(view, s):
    return json.loads(Path(f"runs/{view}/llm_bo_s{s}.json" if view.startswith("e1/") else f"runs/t009/{view}/llm_bo_s{s}.json").read_text())["hits_by_step"]


arms = {
    "random (n=500)": ([run_arm("random", s)["hits_by_step"] for s in range(500)], "#888888", "-"),
    "OFAT (n=20)": ([run_arm("ofat", s)["hits_by_step"] for s in range(20)], "#1b7837", "-"),
    "BO (n=20)": ([run_arm("bo", s)["hits_by_step"] for s in range(20)], "#2166ac", "-"),
    "blind llm_bo (n=20)": ([load("blind", s) for s in range(20)], "#b2182b", "-"),
    "counterfactual-named llm_bo (n=20, Ni<->Mn swapped)": ([load("e1/cfnamed", s) for s in range(20)], "#e08214", "-"),
    "named llm_bo (n=5, memorisation flag set)": ([load("named", s) for s in range(5)], "#b2182b", "--"),
}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
for name, (hs, c, ls) in arms.items():
    C = curves(hs)
    m = C.mean(0)
    a1.plot(T, m, color=c, ls=ls, label=name, lw=1.8)
    a1.fill_between(T, np.percentile(C, 25, 0), np.percentile(C, 75, 0), color=c, alpha=0.10 if ls == "-" else 0.05, lw=0)
a1.set(xlabel="experiments used", ylabel="hits found (yield >= 2000 MPa)", title="Hits within budget (mean, IQR band)")
a1.legend(fontsize=7.5, loc="upper left")
a1.grid(alpha=0.25)
names = list(arms)
w = 0.14
for i, name in enumerate(names):
    hs, c, ls = arms[name]
    med, lo, hi = [], [], []
    for k in (1, 3, 5):
        v = kth(hs, k)
        med.append(np.median(v)); lo.append(np.percentile(v, 25)); hi.append(np.percentile(v, 75))
    x = np.arange(3) + (i - 2.5) * w
    med, lo, hi = map(np.array, (med, lo, hi))
    a2.bar(x, med, w, color=c, alpha=0.9 if ls == "-" else 0.45, hatch="//" if ls == "--" else None,
           yerr=[med - lo, hi - med], capsize=2, error_kw={"lw": 0.8})
a2.set_xticks(range(3), ["k=1", "k=3", "k=5"])
a2.axhline(B + 1, color="k", lw=0.6, ls=":")
a2.text(2.4, B + 1.2, "censored (61)", fontsize=7, ha="right")
a2.set(ylabel="experiments to k-th hit (median, IQR)", title="Experiments to the k-th hit (lower is better)")
a2.grid(alpha=0.25, axis="y")
fig.suptitle("steel_strength, B=60. Named arm: n=5, memorisation flag set - NOT an acceleration claim", fontsize=10)
fig.tight_layout()
Path("docs").mkdir(exist_ok=True)
fig.savefig("docs/headline.png", dpi=140)
print("wrote docs/headline.png")
r = json.loads(Path("results/e1_counterfactual.json").read_text())["trust_mean_by_step"]
f2, ax = plt.subplots(figsize=(5.5, 3.6))
for n, c in (("blind", "#b2182b"), ("cfnamed", "#e08214")):
    ax.plot(range(len(r[n])), r[n], color=c, label={"blind": "blind", "cfnamed": "counterfactual-named"}[n])
ax.set(xlabel="step (revealed set grows)", ylabel="Spearman(prior, revealed y), mean of 20 seeds", title="Trust meter")
ax.legend()
ax.grid(alpha=0.25)
f2.tight_layout()
f2.savefig("docs/trust_meter.png", dpi=140)
print("wrote docs/trust_meter.png")
