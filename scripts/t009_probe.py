"""T009 part A: recall probe. 20 fixed rows x prompts P1 generic / P2 guided / P3 blinded; vs LOO kNN (k=5).
Writes runs/t009/probe.json. Cached by (prompt, model, seed=0). Stops on the first Throttled."""
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd import cli_llm  # noqa: E402
from asd.replay import FEATURES, load_pool  # noqa: E402

NAMES = {"c": "C", "mn": "Mn", "si": "Si", "cr": "Cr", "ni": "Ni", "mo": "Mo", "v": "V", "n": "N",
         "nb": "Nb", "co": "Co", "w": "W", "al": "Al", "ti": "Ti"}
MODEL = "claude-sonnet-5-5"
rows = load_pool()
ids = json.loads(Path("data/t009_probe_ids.json").read_text())["ids"]
X = np.array([[r[f] for f in FEATURES] for r in rows], float)
y = np.array([r["yield strength"] for r in rows], float)
lo, hi = X.min(0), X.max(0)
perm = list(range(13))
random.Random(1000).shuffle(perm)  # fixed column permutation for the probe's blinded view


def comp(i):
    return ", ".join(f"{NAMES[f]}={rows[i][f]:g}" for f in FEATURES)


def prompt(kind, i):
    ans = 'Answer with JSON only: {"yield_mpa": <number>}.'
    if kind == "P1":
        return f"A steel has composition (wt%): {comp(i)} (balance Fe). Estimate its yield strength in MPa. {ans}"
    if kind == "P2":
        return (f"A steel has composition (wt%): {comp(i)} (balance Fe). This row is from the matminer steel_strength / "
                f"Matbench matbench_steels dataset. Give the recorded value of its yield strength in MPa. {ans}")
    v = ", ".join(f"f{k + 1:02d}={(X[i, perm[k]] - lo[perm[k]]) / (hi[perm[k]] - lo[perm[k]] or 1):.4f}" for k in range(13))
    return (f"A material has features (each min-max scaled to [0,1]): {v}. Estimate its target property value in its natural "
            f"units. {ans}")


def one(args):
    kind, i = args
    return kind, i, float(cli_llm.parse_json(cli_llm.ask(prompt(kind, i), MODEL, 0))["yield_mpa"])


jobs = [(k, i) for k in ("P1", "P2", "P3") for i in ids]
try:
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, jobs))
except cli_llm.Throttled as e:
    print("THROTTLED, stopping:", e)
    sys.exit(2)

# kNN LOO reference (z-scored wt%, Euclidean, k=5)
Z = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
knn = {}
for i in ids:
    d = np.linalg.norm(Z - Z[i], axis=1)
    d[i] = np.inf
    knn[i] = float(y[np.argsort(d)[:5]].mean())
mean_pred = {i: float(np.delete(y, i).mean()) for i in ids}


def ranks(a):
    return np.argsort(np.argsort(a)).astype(float)


def metrics(pred):
    p = np.array([pred[i] for i in ids]); t = np.array([y[i] for i in ids])
    near = int(sum(abs(pp - tt) <= max(10.0, 0.01 * tt) for pp, tt in zip(p, t)))
    rho = float(np.corrcoef(ranks(p), ranks(t))[0, 1]) if p.std() > 0 else float("nan")
    return {"mae": float(np.abs(p - t).mean()), "spearman": rho, "near_exact": near}


preds = {k: {i: v for kk, i, v in res if kk == k} for k in ("P1", "P2", "P3")}
out = {"model": MODEL, "n_rows": len(ids), "ids": ids, "true": {str(i): float(y[i]) for i in ids},
       "pred": {k: {str(i): v for i, v in d.items()} for k, d in preds.items()},
       "metrics": {**{k: metrics(d) for k, d in preds.items()}, "knn5_loo": metrics(knn), "train_mean": metrics(mean_pred)}}
m = out["metrics"]
flags = {"near_exact_ge3": max(m["P1"]["near_exact"], m["P2"]["near_exact"]) >= 3,
         "P2_lt_0.5_knn": m["P2"]["mae"] < 0.5 * m["knn5_loo"]["mae"],
         "P2_lt_0.8_P1": m["P2"]["mae"] < 0.8 * m["P1"]["mae"]}
out["flags"] = flags
out["recall_flag"] = any(flags.values())
Path("runs/t009").mkdir(parents=True, exist_ok=True)
Path("runs/t009/probe.json").write_text(json.dumps(out, indent=1))
for k, v in m.items():
    print(k, {a: round(b, 3) for a, b in v.items()})
print(flags, "RECALL FLAG:", out["recall_flag"], "| calls", cli_llm.STATS)
