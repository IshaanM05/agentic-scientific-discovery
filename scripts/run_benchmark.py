"""Run the controlled comparison and write dashboard/data/benchmark.json.

    python scripts/run_benchmark.py --seeds 20 --budget 60
"""
import argparse, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LABLOOP_OFFLINE", "1")  # baselines must be deterministic and free

from labloop.benchmark import run_benchmark  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--out", default="dashboard/data/benchmark.json")
    a = ap.parse_args()
    t0 = time.time()
    res = run_benchmark(seeds=a.seeds, budget=a.budget)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res))
    print(f"wrote {a.out} in {time.time() - t0:.0f}s")
    for name, s in res["strategies"].items():
        print(f"{name:28s} hits@budget {s['final_mean']:.2f}  first-hit {s['first_hit_median']}  3-hits {s['three_hits_median']}  P(3) {s['success_3']:.0%}")
