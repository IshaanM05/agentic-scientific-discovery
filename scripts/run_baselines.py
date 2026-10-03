"""Run the offline baselines: python scripts/run_baselines.py [n_seeds=10] [out=runs/t003]
Writes <out>/<arm>_s<seed>.json (run record + ledger) and prints a table of experiments-to-k-hits
(censored at budget+1 = 61 when k hits are not reached)."""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd.baselines import ARMS, BUDGET, run_arm  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
out = Path(sys.argv[2] if len(sys.argv) > 2 else "runs/t003")
out.mkdir(parents=True, exist_ok=True)
rows = {}
for arm in ARMS:
    for seed in range(n):
        led = out / f"{arm}_s{seed}.ledger.jsonl"
        led.unlink(missing_ok=True)
        r = run_arm(arm, seed, ledger_path=led)
        (out / f"{arm}_s{seed}.json").write_text(json.dumps(r))
        rows.setdefault(arm, []).append(r)
print(f"steel_strength, budget {BUDGET}, n_init 5, seeds 0..{n-1}; mean (median) experiments to k hits, "
      f"censored at {BUDGET+1}; reached = seeds reaching k hits")
print("arm      k=1            k=3            k=5            mean hits/60")
for arm, rs in rows.items():
    cells = []
    for k in "135":
        v = [r["to_k"][k] for r in rs]
        reached = sum(x <= BUDGET for x in v)
        cells.append(f"{st.mean(v):5.1f} ({st.median(v):4.1f}) {reached}/{n}")
    print(f"{arm:8s} " + "  ".join(cells) + f"   {st.mean(r['n_hits'] for r in rs):.2f}")
