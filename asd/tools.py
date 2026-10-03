"""Python function tools for the Omnigent agents (agents/planner.yaml).

All tools are plain functions (JSON in, JSON-able dict out). They wrap asd.replay.ReplayOracle and
append every decision to a shared research record (JSONL, one run-record id per entry).
Every input and output is validated against a JSON schema (asd/schemas.py).
Session config via env: ASD_SEED (0), ASD_BUDGET (60), ASD_RUN_DIR (required), ASD_RUN_ID.
"""
import hashlib
import json
import math
import os
from pathlib import Path

from . import schemas as S
from .replay import BudgetExceeded, ReplayOracle, HIT_THRESHOLD

_STATE = {}
SURPRISE_REL = 0.25  # |value - predicted| / predicted above this reopens assumptions


class RunConfigError(Exception):
    pass


def _env(name, default=None):
    """Read ASD_<name>, or LC_ASD_<name>: Omnigent's host daemon strips unknown env vars before the
    runner, but forwards the LC_ prefix (host/connect.py _RUNNER_ENV_ALLOWLIST_PREFIXES)."""
    return os.environ.get("ASD_" + name, os.environ.get("LC_ASD_" + name, default))


def _guard(run_dir, seed, budget, run_id):
    """Run-id guard: a run dir is bound to one (run_id, seed, budget) via meta.json. A tool refuses a
    dir whose ledger/record belong to another run (stops spent budget leaking across runs)."""
    meta_p = run_dir / "meta.json"
    want = {"run_id": run_id, "seed": seed, "budget": budget}
    if meta_p.exists():
        have = json.loads(meta_p.read_text())
        if have != want:
            raise RunConfigError(f"run dir {run_dir} belongs to {have}, this process is {want}; refusing")
    else:
        if (run_dir / "ledger.jsonl").exists() or (run_dir / "record.jsonl").exists():
            raise RunConfigError(f"run dir {run_dir} has a ledger but no meta.json (unknown owner); refusing")
        meta_p.write_text(json.dumps(want))


def reset(seed=None, budget=None, run_dir=None, run_id=None):
    """Session config comes from args or ASD_SEED/ASD_BUDGET/ASD_RUN_DIR/ASD_RUN_ID. With no explicit
    args, ASD_RUN_DIR is REQUIRED (no silent fallback to a shared dir)."""
    if run_dir is None and _env("RUN_DIR") is None:
        raise RunConfigError("ASD_RUN_DIR not set in the tool process (env passthrough failed); refusing "
                             "to fall back to a shared run dir")
    seed = int(_env("SEED", 0)) if seed is None else seed
    budget = int(_env("BUDGET", 60)) if budget is None else budget
    run_id = run_id or _env("RUN_ID", "")
    run_dir = Path(run_dir or _env("RUN_DIR"))
    run_dir.mkdir(parents=True, exist_ok=True)
    _guard(run_dir, seed, budget, run_id)
    rec = run_dir / "record.jsonl"
    _STATE.clear()
    _STATE.update(oracle=ReplayOracle(seed, budget, ledger_path=run_dir / "ledger.jsonl"), rec=rec,
                  n=0, hyps={}, assumptions={}, seed=seed)
    return _STATE


def _sync(st):
    """Rebuild session state from the on-disk record + ledger. Omnigent runs each agent session's tool
    calls possibly in a different process, so the files, not memory, are the source of truth."""
    o = st["oracle"]
    led = Path(o.ledger_path) if o.ledger_path else None
    if led and led.exists():
        lp, o.ledger_path = o.ledger_path, None
        for line in led.read_text().splitlines():
            cid = json.loads(line)["id"]
            if cid not in o._revealed:
                o.run(cid)
        o.ledger_path = lp
    hyps, assumptions, n = {}, {}, 0
    if st["rec"].exists():
        for line in st["rec"].read_text().splitlines():
            e = json.loads(line)
            n += 1
            if e["kind"] == "hypothesis":
                hyps[e["id"]] = e
                assumptions.setdefault(e["assumption"], "active")
            elif e["kind"] == "analysis":
                for a in e.get("reopened_assumptions", []):
                    assumptions[a] = "reopened"
    st.update(n=n, hyps=hyps, assumptions=assumptions)


def _st():
    st = _STATE or reset()
    _sync(st)
    return st


def _record(kind, payload):
    st = _st()
    st["n"] += 1
    entry = {"record_id": f"rec-{st['n']:04d}", "kind": kind, **payload}
    with open(st["rec"], "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["record_id"]


def _fetch_openalex(query, n):
    import urllib.parse
    import urllib.request
    url = "https://api.openalex.org/works?per-page=%d&search=%s&select=id,title,publication_year,doi" % (
        n, urllib.parse.quote(query))
    with urllib.request.urlopen(url, timeout=15) as r:
        return [{"id": w["id"], "title": w.get("title"), "year": w.get("publication_year"),
                 "doi": w.get("doi"), "source": "OpenAlex"} for w in json.loads(r.read())["results"]]


def _fetch_europepmc(query, n):
    import urllib.parse
    import urllib.request
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite"
           "&pageSize=%d&query=%s" % (n, urllib.parse.quote(query)))
    with urllib.request.urlopen(url, timeout=15) as r:
        return [{"id": f"{w.get('source')}:{w.get('id')}", "title": w.get("title"),
                 "year": w.get("pubYear"), "doi": w.get("doi"), "source": "EuropePMC"}
                for w in json.loads(r.read())["resultList"]["result"]]


def literature_search(query: str, max_results: int = 5) -> dict:
    """Literature agent: search OpenAlex, falling back to Europe PMC (cached on disk). Returns
    citations with ids. Never invents citations: on failure returns an error and no citations."""
    cache = Path(os.environ.get("ASD_CACHE", ".cache/lit"))
    cache.mkdir(parents=True, exist_ok=True)
    key = cache / (hashlib.sha256(f"{query}|{max_results}".encode()).hexdigest()[:16] + ".json")
    if key.exists():
        cites = json.loads(key.read_text())
    else:
        errs = []
        cites = []
        for fetch in (_fetch_openalex, _fetch_europepmc):
            try:
                cites = fetch(query, max_results)
                if cites:
                    break
            except Exception as e:
                errs.append(f"{fetch.__name__}: {type(e).__name__} {e}")
        if not cites:
            return {"citations": [], "error": "; ".join(errs) or "no results",
                    "record_id": _record("literature", {"query": query, "citations": [], "errors": errs})}
        key.write_text(json.dumps(cites))
    rid = _record("literature", {"query": query, "citations": cites})
    return S.check({"citations": cites, "record_id": rid}, S.LIT_OUT)


def get_features(candidate_ids: list) -> dict:
    """Return the 13 composition features for candidate ids (never the measured strengths)."""
    o = _st()["oracle"]
    return {cid: o.features(cid) for cid in candidate_ids[:50]}


def propose_hypothesis(text: str, candidate_ids: list, predicted_value: float, assumption: str,
                       citations: list) -> dict:
    """Insight agent: register an AGENT-GENERATED hypothesis (needs citations, a prediction in MPa)."""
    st = _st()
    h = {"id": f"H{len(st['hyps']) + 1}", "text": text, "candidate_ids": candidate_ids,
         "predicted_value": predicted_value, "assumption": assumption, "citations": citations,
         "label": "agent-generated hypothesis (unvalidated)"}
    S.check(h, S.HYP_REC)
    h["record_id"] = _record("hypothesis", h)
    st["hyps"][h["id"]] = h
    st["assumptions"].setdefault(assumption, "active")
    return {"hypothesis_id": h["id"], "record_id": h["record_id"]}


def design_tests(tests: list) -> dict:
    """Planner: submit >=2 candidate tests with expected_learning, feasibility (0..1) and cost
    (experiments). Picks max expected_learning*feasibility/cost and logs reasons."""
    S.check(tests, S.TESTS)
    for t in tests:
        t["score"] = round(t["expected_learning"] * t["feasibility"] / max(t["cost"], 1), 4)
    best = max(tests, key=lambda t: t["score"])
    reasons = [f"{t['name']}: learning={t['expected_learning']} feasibility={t['feasibility']} "
               f"cost={t['cost']} -> score={t['score']}" for t in tests]
    rid = _record("test_choice", {"options": tests, "chosen": best["name"], "reasons": reasons})
    return S.check({"chosen": best["name"], "scores": {t["name"]: t["score"] for t in tests},
                    "record_id": rid}, S.CHOICE)


def select_next(k: int = 3, kappa: float = 0.5) -> dict:
    """Selector (surrogate-UCB): rank unrevealed candidates by kNN-predicted strength plus a
    distance-based exploration bonus. Cold start returns spread-out candidates."""
    o = _st()["oracle"]
    seen = {cid: r for cid, r in o._revealed.items()}
    ids = [c for c in o.ids() if c not in seen]
    feats = {c: [o.features(c)[f] for f in sorted(o.features(c))] for c in ids}

    def d(a, b):
        return math.dist(a, b)
    if not seen:
        pool = ids[:]
        out = [pool[0]]
        while len(out) < k:
            out.append(max(pool, key=lambda c: min(d(feats[c], feats[x]) for x in out)))
        scored = [(c, 0.0) for c in out]
    else:
        sf = {c: [o.features(c)[f] for f in sorted(o.features(c))] for c in seen}
        scored = []
        for c in ids:
            ds = sorted((d(feats[c], sf[s]), seen[s]["value"]) for s in seen)[:3]
            w = [1 / (x + 1e-6) for x, _ in ds]
            mu = sum(wi * v for wi, (_, v) in zip(w, ds)) / sum(w)
            scored.append((c, mu + kappa * 100 * ds[0][0]))
        scored.sort(key=lambda t: -t[1])
    picks = [{"candidate_id": c, "score": round(s, 2)} for c, s in scored[:k]]
    return S.check({"picks": picks, "record_id": _record("selector", {"picks": picks})}, S.SELECT)


def run_experiment(candidate_id: str, hypothesis_id: str = "") -> dict:
    """Runner: reveal the measured yield strength of one candidate (costs 1 experiment).
    Gated by Omnigent policies (experiment budget + human approval)."""
    st = _st()
    try:
        r = st["oracle"].run(candidate_id)
    except BudgetExceeded as e:
        return {"error": str(e), "budget_used": st["oracle"].spent}
    r["record_id"] = _record("experiment", {**r, "hypothesis_id": hypothesis_id})
    return S.check(r, S.RUN_OUT)


def analyze_result(hypothesis_id: str, candidate_id: str) -> dict:
    """Analysis agent: compare the revealed value with the hypothesis prediction. A surprise
    (relative error > 25%) reopens the hypothesis's underlying assumption."""
    st = _st()
    h = st["hyps"].get(hypothesis_id)
    if h is None:
        return {"error": f"unknown hypothesis {hypothesis_id!r}; call propose_hypothesis first"}
    if candidate_id not in st["oracle"]._revealed:
        return {"error": "candidate not yet run; call run_experiment first"}
    r = st["oracle"].run(candidate_id)  # already revealed -> free
    rel = abs(r["value"] - h["predicted_value"]) / max(h["predicted_value"], 1e-9)
    surprising = rel > SURPRISE_REL
    reopened = []
    if surprising and st["assumptions"].get(h["assumption"]) == "active":
        st["assumptions"][h["assumption"]] = "reopened"
        reopened.append(h["assumption"])
    out = {"hypothesis_id": hypothesis_id, "value": r["value"], "predicted": h["predicted_value"],
           "rel_error": round(rel, 3), "supported": not surprising, "is_hit": r["value"] >= HIT_THRESHOLD,
           "surprising": surprising, "reopened_assumptions": reopened}
    out["record_id"] = _record("analysis", out)
    return S.check(out, S.ANALYSIS_R)


def flag_risk(candidate_id: str, level: str, notes: str) -> dict:
    """Safety agent: flag risk for a candidate (level low|medium|high)."""
    out = {"candidate_id": candidate_id, "level": level, "notes": notes}
    S.check(out, S.RISK)
    return {"record_id": _record("safety", out), "requires_human_approval": level != "low"}


def recommend_for_validation(candidate_id: str, rationale: str) -> dict:
    """Recommend a candidate for REAL-WORLD synthesis/validation. Always needs human approval
    (Omnigent ASK policy). Output is a hypothesis-grade recommendation, not a result."""
    return {"record_id": _record("recommendation", {"candidate_id": candidate_id, "rationale": rationale,
                                                   "status": "needs wet-lab validation"})}


HANDOFF_SCHEMAS = {
    "literature": S.LIT_OUT_IN, "hypotheses": S.HANDOFF_HYPS, "analysis": S.HANDOFF_ANALYSIS,
    "safety": S.RISK,
}


def record_step(agent: str, kind: str, payload_json: str) -> dict:
    """Validated handoff: a sub-agent submits its structured output as a JSON string. It is checked
    against the schema for `kind` (literature|hypotheses|analysis|safety) and appended to the
    shared research record. Invalid payloads are rejected, not recorded."""
    if kind not in HANDOFF_SCHEMAS:
        return {"accepted": False, "error": f"unknown kind {kind!r}; use {sorted(HANDOFF_SCHEMAS)}"}
    try:
        payload = json.loads(payload_json)
        S.check(payload, HANDOFF_SCHEMAS[kind])
    except Exception as e:
        return {"accepted": False, "error": f"schema validation failed: {str(e).splitlines()[0][:200]}"}
    return {"accepted": True, "record_id": _record("handoff", {"agent": agent, "handoff_kind": kind,
                                                               "payload": payload})}


def research_record(last_n: int = 20) -> dict:
    """Return the last N entries of the shared research record."""
    p = _st()["rec"]
    lines = p.read_text().splitlines()[-last_n:] if p.exists() else []
    return {"entries": [json.loads(x) for x in lines], "budget_used": _st()["oracle"].spent}
