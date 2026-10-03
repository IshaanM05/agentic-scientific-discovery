"""Offline arena calibration. The oracle (all 312 rows) is read here only; never shown to any agent.
Realized outcome of a hypothesis = -(relative error of its predicted mean yield vs the true region mean;
0 inside a predicted range). Spearman(Elo, outcome) vs a random-ranking permutation baseline."""
import json
import pathlib
import random

from scipy.stats import rankdata

from asd.replay import load_pool


def spearman(x, y):
    a, b = rankdata(x), rankdata(y)
    a, b = a - a.mean(), b - b.mean()
    d = (a @ a * (b @ b)) ** 0.5
    return float(a @ b / d) if d else 0.0


def region_mean(pred, rows):
    ok = [r["yield strength"] for r in rows
          if all((r[c["feature"]] >= c["value"]) if c["op"] == ">=" else (r[c["feature"]] <= c["value"])
                 for c in pred["region"])]
    return (sum(ok) / len(ok) if ok else None), len(ok)


def rel_error(pred, truth):
    v = pred["value"]
    if isinstance(v, list):
        lo, hi = v
        return 0.0 if lo <= truth <= hi else min(abs(truth - lo), abs(truth - hi)) / ((lo + hi) / 2)
    return abs(truth - v) / v


def perm_test(elo, outcome, n=5000, seed=0):
    obs = spearman(elo, outcome)
    rng, o, ge = random.Random(seed), list(outcome), 0
    for _ in range(n):
        rng.shuffle(o)
        ge += spearman(elo, o) >= obs - 1e-12
    return obs, (ge + 1) / (n + 1)


def calibrate(hyps, elo, rows, min_n=3, n_perm=5000):
    items = []
    for h in hyps:
        m, k = region_mean(h["quantitative_prediction"], rows)
        if m is None or k < min_n:
            items.append({"id": h["id"], "testable": False, "n_rows": k})
            continue
        items.append({"id": h["id"], "testable": True, "n_rows": k, "true_mean": round(m, 1),
                      "rel_error": round(rel_error(h["quantitative_prediction"], m), 3), "elo": elo[h["id"]]})
    t = [i for i in items if i["testable"]]
    res = {"n_hypotheses": len(hyps), "n_testable": len(t), "items": items,
           "caveat": "n is tiny; calibrated against measured outcomes on a public benchmark, not expert review; "
                     "LLM may have memorised matbench_steels"}
    if len(t) >= 3:
        obs, p = perm_test([i["elo"] for i in t], [-i["rel_error"] for i in t], n_perm)
        res.update(spearman=round(obs, 3), perm_p_one_sided=round(p, 3), n_permutations=n_perm,
                   within_25pct=sum(i["rel_error"] <= 0.25 for i in t))
    return res


if __name__ == "__main__":
    d = pathlib.Path("runs/arena")
    hyps = [json.loads(x) for x in open(d / "hypotheses.jsonl")]
    elo = {r["id"]: r["elo"] for r in map(json.loads, open(d / "elo.jsonl")) if "id" in r}
    r = calibrate(hyps, elo, load_pool())
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path("results/arena_calibration.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({k: v for k, v in r.items() if k not in ("items", "caveat")}))
