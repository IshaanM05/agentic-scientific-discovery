"""One round: generate -> pick -> run -> analyze -> update belief -> decide."""
from . import schemas as S
from .belief import Belief
from .cache import Cache
from .llm import LLM
from .oracle import ToyOracle


def generate(llm, belief, rnd):
    tried = [e[1] for e in belief.experiments()]
    g = llm.complete(f"propose optimum locations; round={rnd}; tried={tried}")["guesses"]
    hs = [{"id": f"r{rnd}h{i}", "text": f"optimum near x={x}", "x_pred": x, "prediction": 0.9}
          for i, x in enumerate(g)]
    S.check(hs, S.HYPOTHESES)
    belief.add_hypotheses(hs)
    return hs


def pick(belief, hs):
    tried = [e[1] for e in belief.experiments()]
    cands = belief.open_hypotheses() or hs
    h = max(cands, key=lambda h: min([abs(h["x_pred"] - t) for t in tried] or [1]))
    return S.check({"hypothesis_id": h["id"], "x": h["x_pred"], "rationale": "max novelty among open"}, S.PICK), h


def analyze(h, res, tol=0.15):
    err = abs(res["y"] - h["prediction"])
    return S.check({"hypothesis_id": h["id"], "error": err, "supported": err < tol}, S.ANALYSIS)


def decide(oracle, belief, budget):
    best = belief.best()
    if oracle.spent >= budget:
        d = {"action": "stop", "reason": "budget exhausted"}
    elif best is not None and oracle.is_true_hit(max(belief.experiments(), key=lambda e: e[2])[1]):
        d = {"action": "stop", "reason": "hit found"}
    elif best is not None and best > 0.5:
        d = {"action": "exploit", "reason": "promising region"}
    else:
        d = {"action": "explore", "reason": "no promising region yet"}
    return S.check(d, S.DECISION)


def run_round(llm, oracle, belief, rnd, budget=10):
    hs = generate(llm, belief, rnd)
    p, h = pick(belief, hs)
    res = S.check(oracle.run(p["x"]), S.RESULT)
    a = analyze(h, res)
    belief.record(h["id"], res, a)
    d = decide(oracle, belief, budget)
    belief.log_decision(d)
    return {"pick": p, "result": res, "analysis": a, "decision": d}


def run(seed=0, budget=10, db=":memory:", cache_dir=".cache/calls"):
    llm, oracle, belief = LLM(Cache(cache_dir), seed=seed), ToyOracle(seed), Belief(db)
    out = []
    for r in range(budget):
        out.append(run_round(llm, oracle, belief, r, budget))
        if out[-1]["decision"]["action"] == "stop":
            break
    return out


if __name__ == "__main__":
    for o in run():
        print(o["pick"]["x"], round(o["result"]["y"], 3), o["decision"]["action"])
