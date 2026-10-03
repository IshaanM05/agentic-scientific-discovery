"""T009 part B + T005: named vs blind LLM-prior arms (llm_bo, llm_greedy), seeds 0-4, B=60, vs T003 baselines.
Writes runs/t009/{named,blind}/<arm>_s<seed>.json and runs/t009/summary.json. Stops on Throttled."""
import json
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd import cli_llm, llm_prior  # noqa: E402
from asd.baselines import ARMS, run_arm  # noqa: E402

SEEDS = range(5)
out = Path("runs/t009")


def hits_at(h, k):
    return sum(x <= k for x in h)


def job(a):
    view, arm, s = a
    d = out / view
    d.mkdir(parents=True, exist_ok=True)
    led = d / f"{arm}_s{s}.ledger.jsonl"
    led.unlink(missing_ok=True)
    r = llm_prior.run(arm, s, view, ledger_path=led)
    (d / f"{arm}_s{s}.json").write_text(json.dumps(r))
    return r


# prime priors (the expensive part) in parallel, one per (seed, view)
jobs = [(v, "llm_bo", s) for v in ("named", "blind") for s in SEEDS]
try:
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(job, jobs))
    res += [job((v, "llm_greedy", s)) for v in ("named", "blind") for s in SEEDS]  # cached priors, offline
except cli_llm.Throttled as e:
    print("THROTTLED, stopping:", e)
    sys.exit(2)

base = {}
for arm in ARMS:
    base[arm] = {s: run_arm(arm, s) for s in SEEDS}
by = {}
for r in res:
    by.setdefault((r["view"], r["arm"]), {})[r["seed"]] = r

# random: mean over 500 seeds (hits@60 and hits@k) as the reference line
rnd = [run_arm("random", s) for s in range(500)]
summ = {"random500": {k: st.mean(hits_at(r["hits_by_step"], k) for r in rnd) for k in (20, 40, 60)},
        "random500_to_k": {k: st.mean(r["to_k"][k] for r in rnd) for k in "135"}}
rows = {}
for arm in ARMS:
    rows[("base", arm)] = base[arm]
for key, d in by.items():
    rows[key] = d


def per_seed(d, k):
    return [hits_at(d[s]["hits_by_step"], k) for s in SEEDS]


print("hits@60 per seed (0-4), mean | hits@20 mean | mean experiments to 1/3/5 hits | first pick hit")
for key, d in rows.items():
    h60 = per_seed(d, 60)
    to = {k: st.mean(d[s]["to_k"][k] if "to_k" in d[s] else 0 for s in SEEDS) for k in "135"}
    if key[0] != "base":
        from asd.replay import experiments_to_k_hits
        to = {k: st.mean(experiments_to_k_hits(d[s]["hits_by_step"], int(k)) for s in SEEDS) for k in "135"}
    fp = sum(d[s].get("first_pick_hit", False) for s in SEEDS) if key[0] != "base" else "-"
    summ["/".join(key)] = {"hits60": h60, "hits60_mean": st.mean(h60), "hits20_mean": st.mean(per_seed(d, 20)),
                           "hits40_mean": st.mean(per_seed(d, 40)), "to_k_mean": to, "first_pick_hit": fp}
    print(f"{'/'.join(key):18s} {h60} mean {st.mean(h60):.2f} | h20 {st.mean(per_seed(d, 20)):.2f} | "
          f"{to['1']:.1f}/{to['3']:.1f}/{to['5']:.1f} | fp {fp}")
print("random (500 seeds) hits@20/40/60", summ["random500"], "to_k", summ["random500_to_k"])
# decision rule inputs
best = max(ARMS, key=lambda a: st.mean(per_seed(base[a], 60)))
summ["best_baseline"] = best
for v in ("named", "blind"):
    d = by[(v, "llm_bo")]
    g = st.mean(per_seed(d, 60)) - st.mean(per_seed(base[best], 60))
    wins = sum(hits_at(d[s]["hits_by_step"], 60) > hits_at(base[best][s]["hits_by_step"], 60) for s in SEEDS)
    ties = sum(hits_at(d[s]["hits_by_step"], 60) == hits_at(base[best][s]["hits_by_step"], 60) for s in SEEDS)
    summ[f"G_{v}"] = g
    summ[f"wins_{v}_vs_best"] = [wins, ties]
    print(f"G_{v} (llm_bo - {best}, hits@60) = {g:.2f}; paired wins {wins}/5 (ties {ties})")
summ["trust_final"] = {f"{v}/{a}": [by[(v, a)][s]["trust_final"] for s in SEEDS] for (v, a) in by}
summ["prior_missing"] = {f"{v}/{a}": [by[(v, a)][s]["prior_missing"] for s in SEEDS] for (v, a) in by}
(out / "summary.json").write_text(json.dumps(summ, indent=1))
print("trust", summ["trust_final"], "| missing", summ["prior_missing"], "| LLM", cli_llm.STATS)
