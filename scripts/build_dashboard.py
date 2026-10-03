"""Run the demo campaigns and bake everything into one self-contained dashboard/index.html.

    python scripts/build_dashboard.py                 # seeds 7, 3, 11
    python scripts/build_dashboard.py --seeds 7 42
Open dashboard/index.html in any browser. No server needed.
"""
import argparse, json, os, sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labloop.export import export_trace  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[7, 3, 11])
    ap.add_argument("--budget", type=float, default=60.0)
    a = ap.parse_args()
    data_dir = ROOT / "dashboard" / "data"
    runs = []
    for s in a.seeds:
        t = export_trace(s, a.budget, data_dir / f"trace_seed{s}.json")
        print(f"seed {s}: {t['summary']}")
        runs.append(t)
    bench_path = data_dir / "benchmark.json"
    bench = json.loads(bench_path.read_text()) if bench_path.exists() else None
    if bench is None:
        print("no benchmark.json yet; run scripts/run_benchmark.py for the comparison section")
    payload = json.dumps({"runs": runs, "benchmark": bench}, default=str, separators=(",", ":"))
    html = (ROOT / "dashboard" / "template.html").read_text().replace("/*__DATA__*/null", payload.replace("</", "<\\/"))
    out = ROOT / "dashboard" / "index.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html) / 1e6:.2f} MB)")
