"""Ground-truth calibration of the Judge and the hypothesis arena on the benchmark runs.

    python scripts/ll_calibrate.py

Re-runs LabLoop (full) on worlds 1000-1019 with the exact benchmark config (seed s, world 1000+s,
budget 60), so the runs are the same as in ll_benchmark.py. Hidden truth is used here only to SCORE.
(a) Judge: per measured film, 'confirmed' verdict vs true hit (precision, recall, accuracy, reliability).
(b) Arena: Spearman(final Elo, true share of the hypothesis region that meets spec) vs random orderings.
Counts and intervals only. Writes runs/ll_calibrate.json. Simulated, team-designed worlds.
"""
import json
import numpy as np
from scipy.stats import spearmanr
from ll_common import ROOT, boot_ci, run_curve, set_world, space_arrays
from labloop.hypotheses import region_mask


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(float(c - h), 3), round(float(c + h), 3)]


def main():
    judge_rows, arena_runs = [], []
    for s in range(20):
        _, tr = run_curve("LabLoop (full)", s)  # also sets world 1000+s
        truth = space_arrays()[-1]
        measured = {e["idx"] for rd in tr["rounds"] for e in rd["experiments"]}
        last = next(rd for rd in reversed(tr["rounds"]) if "discoveries" in rd)
        verdict = {d["idx"]: d for d in last["discoveries"]}
        for i in measured:
            d = verdict.get(i)
            judge_rows.append({"run": s, "idx": i, "true_hit": bool(truth[i]),
                               "confirmed": bool(d and d["status"] == "confirmed"),
                               "confidence": d["confidence"] if d and d["status"] == "confirmed" else None,
                               "n": d["n"] if d else None})
        hyps = last["hypotheses"]
        elo, share = [], []
        for h in hyps:
            m = region_mask({k: tuple(v) for k, v in h["region"].items()})
            if m.sum() == 0:
                continue
            elo.append(h["elo"]); share.append(float(truth[m].mean()))
        arena_runs.append({"run": s, "elo": elo, "share": share, "true_hits_total": int(truth.sum())})

    # (a) judge
    tp = sum(r["confirmed"] and r["true_hit"] for r in judge_rows)
    fp = sum(r["confirmed"] and not r["true_hit"] for r in judge_rows)
    fn = sum((not r["confirmed"]) and r["true_hit"] for r in judge_rows)
    tn = sum((not r["confirmed"]) and not r["true_hit"] for r in judge_rows)
    n = len(judge_rows)
    rel = {}
    for conf in sorted({r["confidence"] for r in judge_rows if r["confidence"]}):
        sub = [r for r in judge_rows if r["confidence"] == conf]
        k = sum(r["true_hit"] for r in sub)
        rel[conf] = {"n_confirmed": len(sub), "true_hits": k, "precision": round(k / len(sub), 3), "wilson95": wilson(k, len(sub))}
    judge = {"measured_films": n, "true_hits_among_measured": tp + fn, "confirmed": tp + fp,
             "TP": tp, "FP": fp, "FN": fn, "TN": tn,
             "precision": tp / (tp + fp) if tp + fp else None, "precision_wilson95": wilson(tp, tp + fp),
             "recall": tp / (tp + fn) if tp + fn else None, "recall_wilson95": wilson(tp, tp + fn),
             "accuracy": (tp + tn) / n, "accuracy_wilson95": wilson(tp + tn, n),
             "reliability_by_confidence": rel,
             "note": "A film enters the judge's pool only after a measured hit; FN includes true hits whose measurements failed or never met spec, or that were never replicated."}

    # (b) arena
    E = np.concatenate([r["elo"] for r in arena_runs]); S = np.concatenate([r["share"] for r in arena_runs])
    rho, p = spearmanr(E, S)
    rng = np.random.default_rng(0)
    null = []
    for _ in range(2000):  # random ordering of the same hypotheses, shuffled within each run
        null.append(spearmanr(np.concatenate([rng.permutation(r["elo"]) for r in arena_runs]), S)[0])
    null = np.array(null)
    per = []
    for r in arena_runs:
        if len(r["elo"]) >= 3 and len(set(r["share"])) > 1 and len(set(r["elo"])) > 1:
            per.append(spearmanr(r["elo"], r["share"])[0])
    arena = {"n_hypotheses": int(len(E)), "n_runs": len(arena_runs),
             "pooled_spearman": float(rho), "pooled_p_value": float(p),
             "random_order_spearman_mean": float(null.mean()), "random_order_spearman_95": [float(np.percentile(null, 2.5)), float(np.percentile(null, 97.5))],
             "permutation_p_two_sided": float((np.abs(null) >= abs(rho)).mean()),
             "per_run_spearman_mean": float(np.mean(per)) if per else None, "per_run_n": len(per),
             "per_run_spearman_bootstrap95": boot_ci(per) if per else None,
             "share_zero_fraction": float((S == 0).mean()),
             "note": "Pooled hypotheses share regions across runs, so the pooled p-value overstates independence; the per-run mean with bootstrap CI is the more honest interval. Elo ranks usefulness/relevance, not region quality, so Spearman vs true hit share is a proxy."}
    out = {"worlds": [1000 + s for s in range(20)], "judge": judge, "arena": arena,
           "caveat": "Team-designed simulator; synthetic worlds; single configuration."}
    (ROOT / "runs/ll_calibrate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"judge": {k: v for k, v in judge.items() if k != "note"}, "arena": {k: v for k, v in arena.items() if k != "note"}}, indent=1))


if __name__ == "__main__":
    main()
