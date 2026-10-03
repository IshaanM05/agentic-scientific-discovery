"""E1: counterfactual-named llm_bo (Ni<->Mn labels swapped) seeds 0-19 vs OFAT/BO, with blind control (cached).
Writes runs/e1/cfnamed/*, runs/e1/blind/* (trust traces), results/e1_counterfactual.json. Stops on Throttled."""
import json
import random
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd import cli_llm, llm_prior  # noqa: E402
from asd.baselines import run_arm  # noqa: E402
from asd.replay import experiments_to_k_hits  # noqa: E402

out = Path("runs/e1")
S = range(20)


def h60(h):
    return sum(x <= 60 for x in h)


def job(a):
    view, s = a
    d = out / view
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"llm_bo_s{s}.json"
    if f.exists():
        return json.loads(f.read_text())
    led = d / f"llm_bo_s{s}.ledger.jsonl"
    led.unlink(missing_ok=True)
    r = llm_prior.run("llm_bo", s, view, ledger_path=led)
    f.write_text(json.dumps(r))
    return r


def paired(L, v):
    rng = random.Random(0)
    d = [x - y for x, y in zip(L, v)]
    bs = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(10000))
    return {"wins": sum(x > 0 for x in d), "ties": sum(x == 0 for x in d), "losses": sum(x < 0 for x in d),
            "mean_diff": st.mean(d), "boot95": [bs[250], bs[9749]]}


def main():
    try:
        with ThreadPoolExecutor(4) as ex:
            cf = list(ex.map(job, [("cfnamed", s) for s in S]))
        bl = [job(("blind", s)) for s in S]  # primed from cached blind priors (offline)
    except cli_llm.Throttled as e:
        print("THROTTLED, stopping:", e)
        sys.exit(2)
    base = {a: [run_arm(a, s)["hits_by_step"] for s in S] for a in ("ofat", "bo")}
    arms = {"cfnamed": [r["hits_by_step"] for r in cf], "blind": [r["hits_by_step"] for r in bl], **base}
    res = {"seeds": 20, "budget": 60, "swap": "Ni<->Mn", "arms": {}}
    for k, hs in arms.items():
        res["arms"][k] = {"hits60": [h60(h) for h in hs], "mean_hits60": st.mean(h60(h) for h in hs),
                          "to_k_mean": {kk: st.mean(experiments_to_k_hits(h, int(kk)) for h in hs) for kk in "135"}}
    better = max(("ofat", "bo"), key=lambda a: res["arms"][a]["mean_hits60"])
    res["better_baseline"] = better
    for name in ("cfnamed", "blind"):
        res[f"{name}_vs_ofat"] = paired(res["arms"][name]["hits60"], res["arms"]["ofat"]["hits60"])
        res[f"{name}_vs_bo"] = paired(res["arms"][name]["hits60"], res["arms"]["bo"]["hits60"])
        res[f"{name}_vs_better"] = paired(res["arms"][name]["hits60"], res["arms"][better]["hits60"])
    lo, hi = res["cfnamed_vs_better"]["boot95"]
    res["rule_met"] = bool(res["cfnamed_vs_better"]["mean_diff"] > 0 and lo > 0)
    T = {n: [r["trust_trace"] for r in rr] for n, rr in (("cfnamed", cf), ("blind", bl))}
    res["trust_mean_by_step"] = {n: [round(st.mean(t[i] for t in tr), 3) for i in range(len(tr[0]))] for n, tr in T.items()}
    res["trust_final_mean"] = {n: st.mean(r["trust_final"] for r in rr) for n, rr in (("cfnamed", cf), ("blind", bl))}
    res["trust_mean_all_steps"] = {n: st.mean(st.mean(t) for t in tr) for n, tr in T.items()}
    res["first_pick_hits"] = {"cfnamed": sum(r["first_pick_hit"] for r in cf), "blind": sum(r["first_pick_hit"] for r in bl)}
    res["prior_missing"] = {"cfnamed": sum(r["prior_missing"] for r in cf)}
    Path("results").mkdir(exist_ok=True)
    Path("results/e1_counterfactual.json").write_text(json.dumps(res, indent=1))
    print({k: (round(v["mean_hits60"], 2), v["to_k_mean"]) for k, v in res["arms"].items()})
    for k in ("cfnamed_vs_ofat", "cfnamed_vs_bo", "blind_vs_ofat", "blind_vs_bo", "cfnamed_vs_better"):
        print(k, res[k])
    print("rule_met", res["rule_met"], "trust", res["trust_final_mean"], res["trust_mean_all_steps"], res["first_pick_hits"], cli_llm.STATS)


main()
