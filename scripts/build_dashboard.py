"""Run the demo campaign (and the benchmark if needed) and bake one self-contained HTML file.

    python scripts/build_dashboard.py                  # seed 1, reuse runs/benchmark.json if present
    python scripts/build_dashboard.py --seed 3 --fresh-bench --bench-seeds 20

Output: docs/index.html (works offline, and from GitHub Pages: Settings > Pages > /docs).
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dashboard"))

from labloop.benchmark import run_benchmark  # noqa: E402
from labloop.campaign import Config, run_campaign  # noqa: E402
from labloop.chemistry import A_MIXES, composition_space, space_arrays  # noqa: E402
from labloop.literature import CLAIMS  # noqa: E402
from labloop.surrogate import Surrogate  # noqa: E402
import ll_summary  # noqa: E402


def space_payload() -> dict:
    space = composition_space()
    a_index = {a: i for i, a in enumerate(A_MIXES)}
    *_, hits = space_arrays()
    prior = Surrogate().p_hit()
    return {
        "points": [[a_index[(c.cs, c.fa, c.ma)], round(c.sn * 10), round(c.br * 10), round(c.cl * 10)] for c in space],
        "formulas": [c.formula() for c in space],
        "true_hits": [int(i) for i in hits.nonzero()[0]],
        "prior_p": [int(round(100 * p)) for p in prior],
        "literature": CLAIMS,
    }


def compact(trace: dict) -> dict:
    for r in trace["rounds"]:
        if r.get("p_map"):
            r["p_map"] = [int(round(100 * p)) for p in r["p_map"]]
        for e in r.get("experiments", []):
            e.pop("comp", None)
    return trace


def embed(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), default=str).replace("</", "<\\/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--fresh-bench", action="store_true")
    ap.add_argument("--bench-seeds", type=int, default=20)
    a = ap.parse_args()

    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    trace = run_campaign(Config(seed=a.seed, budget=a.budget))
    (runs / f"trace_seed{a.seed}.json").write_text(json.dumps(trace, default=str, indent=1))
    print("campaign:", trace["summary"])

    bench = {}
    for key, fname, unseen in (("demo", "benchmark.json", False), ("unseen", "benchmark_unseen.json", True)):
        path = runs / fname
        if a.fresh_bench or not path.exists():
            print(f"running {key} benchmark over {a.bench_seeds} seeds (about a minute)...")
            path.write_text(json.dumps(run_benchmark(seeds=a.bench_seeds, budget=a.budget, unseen_worlds=unseen)))
        bench[key] = json.loads(path.read_text())

    html = (ROOT / "dashboard" / "template.html").read_text()
    html = html.replace("__TRACE__", embed(compact(trace))).replace("__BENCH__", embed(bench)).replace("__SPACE__", embed(space_payload())).replace("__LLRUNS__", embed(ll_summary.summarize_all()))
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)} ({len(html) / 1e3:.0f} kB)")
