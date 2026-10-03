"""A2: blind llm_bo on seeds 5-19 (same path/conditions as t009_t005_run.py seeds 0-4; cached). Stops on Throttled.
Then paired stats over seeds 0-19 vs OFAT and BO. Writes runs/t009/blind20_summary.json."""
import json
import random
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd import cli_llm, llm_prior  # noqa: E402
from asd.baselines import run_arm  # noqa: E402

out = Path("runs/t009/blind")


def h60(r):
    return sum(x <= 60 for x in r["hits_by_step"])


def job(s):
    f = out / f"llm_bo_s{s}.json"
    if f.exists():
        return json.loads(f.read_text())
    led = out / f"llm_bo_s{s}.ledger.jsonl"
    led.unlink(missing_ok=True)
    r = llm_prior.run("llm_bo", s, "blind", ledger_path=led)
    f.write_text(json.dumps(r))
    return r


def main():
    try:
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(job, range(20)))
    except cli_llm.Throttled as e:
        print("THROTTLED, stopping:", e)
        sys.exit(2)
    L = [h60(r) for r in res]
    arms = {a: [h60(run_arm(a, s)) for s in range(20)] for a in ("ofat", "bo")}
    summ = {"llm_blind": L, "mean": st.mean(L)}
    rng = random.Random(0)
    for a, v in arms.items():
        d = [x - y for x, y in zip(L, v)]
        w, t, lo = sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)
        bs = sorted(st.mean(rng.choices(d, k=20)) for _ in range(10000))
        n = w + lo
        p = min(1.0, 2 * sum(comb(n, i) for i in range(0, min(w, lo) + 1)) / 2 ** n) if n else 1.0
        summ[a] = {"hits60": v, "mean": st.mean(v), "wins": w, "ties": t, "losses": lo, "mean_diff": st.mean(d),
                   "boot95": [bs[250], bs[9749]], "sign_p": p}
        print(f"blind llm_bo {st.mean(L):.2f} vs {a} {st.mean(v):.2f}: W/T/L {w}/{t}/{lo}, diff {st.mean(d):+.2f}, "
              f"CI95 [{bs[250]:+.2f},{bs[9749]:+.2f}], sign p={p:.3f}")
    (out.parent / "blind20_summary.json").write_text(json.dumps(summ))
    print("per-seed", L, "| LLM", cli_llm.STATS)


main()
