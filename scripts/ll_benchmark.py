"""Rerun the LabLoop benchmark on unseen worlds and verify the README table.

    python scripts/ll_benchmark.py                 # worlds 1000-1019, 20 seeds, budget 60
    python scripts/ll_benchmark.py --seeds 2       # quick smoke

Writes runs/ll_benchmark.json (fresh numbers + comparison against the claimed table).
Offline and deterministic; no model calls. The simulator is team-designed, so this is
a benchmark, not evidence about real devices.
"""
import argparse, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LABLOOP_OFFLINE"] = "1"

from labloop.benchmark import run_benchmark  # noqa: E402

# Claimed in docs/LABLOOP_README.md (unseen-worlds table): name -> (first hit, third hit, hits by 60, share found).
CLAIMED = {
    "Random": (None, None, 0.1, 0.01),
    "Grad-student OFAT": (6, None, 2.9, 0.20),
    "LLM-style (no BO)": (6.5, 34, 2.9, 0.22),
    "Pure BO (no literature)": (30.5, 37, 8.2, 0.56),
    "LabLoop (full)": (6.5, 24, 9.9, 0.67),
    "LabLoop − arena": (11.5, 24, 9.2, 0.58),
    "LabLoop − negative memory": (6.5, 21, 9.6, 0.65),
    "LabLoop − literature prior": (16.5, 28.5, 10.4, 0.68),
}


def compare(strategies: dict) -> list[dict]:
    rows = []
    for name, (f1, f3, hits, share) in CLAIMED.items():
        s = strategies[name]
        got = (s["first_hit_median"], s["three_hits_median"], round(s["final_mean"], 1), round(s["found_frac"], 2))
        want = (f1, f3, hits, share)
        # README rounds hits to 0.1 and share to whole percent; allow that rounding only.
        ok = (got[0] == want[0] and got[1] == want[1]
              and abs(got[2] - want[2]) < 0.051 and abs(got[3] - want[3]) < 0.0051)
        rows.append({"strategy": name, "claimed": want, "rerun": got, "match": bool(ok)})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--out", default="runs/ll_benchmark.json")
    a = ap.parse_args()
    t0 = time.time()
    res = run_benchmark(seeds=a.seeds, budget=a.budget, unseen_worlds=True)
    full = a.seeds == 20 and a.budget == 60.0
    rows = compare(res["strategies"]) if full else []
    committed = ROOT / "runs" / "benchmark_unseen.json"
    same_as_committed = None
    if full and committed.exists():
        old = json.loads(committed.read_text())["strategies"]
        same_as_committed = all(old[k]["mean"] == v["mean"] for k, v in res["strategies"].items())
    out = {
        "worlds": [1000 + s for s in range(a.seeds)], "seeds": a.seeds, "budget": a.budget,
        "hits_per_world": res["hits_per_world"], "random_expected_budget": res["random_expected_budget"],
        "strategies": {k: {m: v[m] for m in ("final_mean", "first_hit_median", "three_hits_median",
                                              "success_3", "found_frac", "mean")}
                       for k, v in res["strategies"].items()},
        "readme_check": rows, "all_match": all(r["match"] for r in rows) if rows else None,
        "identical_to_committed_benchmark_unseen_json": same_as_committed,
        "caveat": "Team-designed simulator; synthetic worlds; benchmark only.",
    }
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out))
    print(f"wrote {a.out} in {time.time() - t0:.0f}s")
    for r in rows:
        print(f"{'OK ' if r['match'] else 'DIFF'} {r['strategy']:28s} claimed {r['claimed']} rerun {r['rerun']}")
    print("all_match:", out["all_match"], "| identical to committed json:", same_as_committed)
