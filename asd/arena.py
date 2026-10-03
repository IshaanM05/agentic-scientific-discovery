"""Hypothesis arena (T004): generator (Sonnet 5.5), critic and Elo ranker (Haiku 4.5), literature novelty step.
All LLM calls go through the cached CLI path. Agents see feature names and pool feature ranges only: no candidate
ids and no strengths. Ground truth (oracle region means) is used offline in scripts/calibrate_arena.py only."""
import itertools
import json

from . import schemas as S
from .cli_llm import ask, parse_json
from .replay import FEATURES, load_pool

GEN_MODEL, FAST_MODEL = "claude-sonnet-5-5", "claude-haiku-4-5-20251001"
CACHE = "runs/arena/cache"
NOTE = "shallow keyword check, not proof of novelty"
ELEM = {"c": "carbon", "mn": "manganese", "si": "silicon", "cr": "chromium", "ni": "nickel", "mo": "molybdenum",
        "v": "vanadium", "n": "nitrogen", "nb": "niobium", "co": "cobalt", "w": "tungsten", "al": "aluminium",
        "ti": "titanium"}


def feature_ranges():
    rows = load_pool()
    return {f: [round(min(r[f] for r in rows), 3), round(max(r[f] for r in rows), 3)] for f in FEATURES}


def gen_prompt(n=5):
    return (f"A pool of 312 steel compositions (wt%) with features {FEATURES} and ranges {json.dumps(feature_ranges())} "
            "has a measured yield strength (MPa) per steel. Question: which compositions are strongest? "
            f"Propose {n} diverse, falsifiable hypotheses. Each is a JSON object with keys: id (H1..), hypothesis, "
            "quantitative_prediction {statistic:'mean_yield_MPa', region:[1-3 conditions {feature, op:'>='|'<=', "
            "value}] defining a feature region of the pool, value: a number or [low, high] MPa}, mechanism, "
            "kill_condition (the observation that would refute it), expected_comparison (versus what baseline or region), "
            "novelty {verdict:'no match found', citations:[], note:'" + NOTE + "'}, label:'agent-generated'. "
            "Reply with a JSON array only.")


def critic_prompt(hyps):
    return ("Attack each hypothesis adversarially (confounders, extrapolation, correlated features). For each name ONE "
            "refuting test: a concrete experiment or pool query that would refute it. Reply with a JSON array of "
            "{hypothesis_id, attack, refuting_test{name, description, expected_learning 0..1, feasibility 0..1, "
            "cost (experiments, >=1)}}, one per hypothesis.\n" + json.dumps(hyps))


def rank_prompt(hyps, crits):
    pairs = [[a["id"], b["id"]] for a, b in itertools.combinations(hyps, 2)]
    slim = [{k: h[k] for k in ("id", "hypothesis", "quantitative_prediction", "mechanism", "kill_condition")}
            for h in hyps]
    return ("Pairwise tournament. For each listed pair choose the hypothesis more likely to be correct, testable and "
            "informative, given its critique. Reply with a JSON array of {a, b, winner} for exactly these pairs: "
            + json.dumps(pairs) + "\nHypotheses: " + json.dumps(slim) + "\nCritiques: " + json.dumps(crits))


def _ask(prompt, model, seed):
    return parse_json(ask(prompt, model=model, seed=seed, cache_dir=CACHE))


def generate(seed=0, n=5):
    hyps = _ask(gen_prompt(n), GEN_MODEL, seed)
    for h in hyps:
        h["label"] = "agent-generated"
        h["novelty"] = {"verdict": "no match found", "citations": [], "note": NOTE}
    return hyps


def novelty(h, search):
    """Literature step: one OpenAlex search per hypothesis (cached literature_search) + shallow title-match verdict."""
    feats = [c["feature"] for c in h["quantitative_prediction"]["region"]]
    names = [ELEM[f] for f in dict.fromkeys(feats)]
    res = search("steel yield strength " + " ".join(names), 5)
    cites = res.get("citations", [])
    low = lambda c: (c.get("title") or "").lower()
    full = [c for c in cites if "steel" in low(c) and all(n in low(c) for n in names)]
    anyel = [c for c in cites if any(n in low(c) for n in names)]
    v = "already reported" if len(full) >= 2 else "partly reported" if (full or len(anyel) >= 3) else "no match found"
    return {"verdict": v, "citations": [c["id"] for c in (full or anyel)[:3]], "note": NOTE}


def critique(hyps, seed=0):
    out = _ask(critic_prompt(hyps), FAST_MODEL, seed)
    for c in out:  # normalise a key alias the critic sometimes uses
        t = c.get("refuting_test", {})
        if "cost" not in t and "cost_experiments" in t:
            t["cost"] = max(1, t.pop("cost_experiments"))
    return [S.check(c, S.ARENA_CRITIQUE) for c in out]


def elo_round(hyps, crits, seed=0, k=32, base=1000.0):
    ids = {h["id"] for h in hyps}
    ms = _ask(rank_prompt(hyps, crits), FAST_MODEL, seed)
    elo = {i: base for i in ids}
    for m in ms:
        S.check(m, S.ARENA_MATCH)
        if not {m["a"], m["b"]} <= ids or m["winner"] not in (m["a"], m["b"]):
            continue
        ea = 1 / (1 + 10 ** ((elo[m["b"]] - elo[m["a"]]) / 400))
        sa = 1.0 if m["winner"] == m["a"] else 0.0
        elo[m["a"]] += k * (sa - ea)
        elo[m["b"]] -= k * (sa - ea)
    return elo, ms
