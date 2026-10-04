"""Function tools exposed to Omnigent agents (omnigent/princeton_plainsboro/**/tools/python/*.py).

Omnigent runs each specialist as its own conversation, so shared state lives on
disk: one Differential Whiteboard JSON per target under runs/omnigent/, plus the
append-only ledger. Every function returns JSON-serializable dicts (the typed
handoff payloads of design Section 7). The tools reuse the same agent classes
as the local runtime (plainsboro.lab), so the science is identical in both paths;
Omnigent supplies the LLM reasoning, routing, policies and approvals.
"""
from __future__ import annotations

import json
import os
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np

from .agents.cameron import Cameron
from .agents.chase import Chase
from .agents.cuddy import Cuddy
from .agents.foreman import Foreman
from .agents.house import House
from .agents.wilson import Wilson
from .config import HYP_IDS, HYP_LABELS, RUNS, experiment
from .literature import openalex_search, resolve_arxiv
from .planner.likelihood import load_tables
from .planner.posterior import update
from .policies import TARGET_NAME_PATTERN
from .record.ledger import Ledger
from .record.whiteboard import Whiteboard
from .schemas import TestSpec
from .vetting.registry import REGISTRY

STATE = Path(os.environ.get("PP_OMNIGENT_STATE", RUNS / "omnigent"))
_lock = threading.RLock()


@lru_cache(maxsize=1)
def _ctx():
    from .data.gatekeeper import load_set
    cfg = experiment()
    gk = load_set(os.environ.get("PP_CASE_SET", "blind"))
    tables = load_tables()
    return dict(cfg=cfg, gk=gk, tables=tables, ledger=Ledger(STATE / "ledger.jsonl"),
                house=House(), foreman=Foreman(cfg), cameron=Cameron(live=True), chase=Chase(),
                cuddy=Cuddy(cfg, tables), wilson=Wilson(STATE / "knowledge_graph.jsonl"))


def _wb_path(target_id: str) -> Path:
    return STATE / "whiteboards" / f"{target_id}.json"


def _load(target_id: str) -> Whiteboard:
    p = _wb_path(target_id)
    if not p.exists():
        raise FileNotFoundError(f"No open case for {target_id}; call open_case first.")
    return Whiteboard.load(p)


def _save(wb: Whiteboard):
    wb.save(_wb_path(wb.target_id))


def _log(agent, action, target_id, inputs=None, outputs=None, **kw):
    _ctx()["ledger"].log(agent, action, target_id, inputs=inputs, outputs=outputs, runtime="omnigent", **kw)


def _summary(wb: Whiteboard) -> dict:
    return {"target_id": wb.target_id, "posterior": wb.posterior, "leader": wb.leader(),
            "leader_label": HYP_LABELS[wb.leader()], "budget": wb.budget, "tests_run": [
                {k: t[k] for k in ("test_id", "run_id", "outcome_label", "quality") if k in t} for t in wb.tests_run],
            "open_critiques": wb.open_critiques, "status": wb.status,
            "agent_hypotheses": [h for h in wb.hypotheses if h.get("origin") == "agent_generated"]}


# ---------------------------------------------------------------- intake (House / Gatekeeper)

def list_targets(limit: int = 10) -> dict:
    gk = _ctx()["gk"]
    return {"targets": gk.target_ids()[:limit], "note": "anonymized IDs; labels withheld by the Data Gatekeeper"}


def open_case(target_id: str) -> dict:
    c = _ctx()
    with _lock:
        t = c["gk"].get_target(target_id)
        wb = Whiteboard.new(t, c["tables"].prior(), c["cfg"]["budget"])
        props = c["house"].differential(t)
        wb.hypotheses += [p.model_dump() for p in props]
        _save(wb)
    _log("gatekeeper", "open_case", target_id, outputs={"signal": t.signal})
    return {"target_id": target_id, "signal": t.signal, "stellar": t.stellar, "prior": wb.posterior,
            "default_hypotheses": {h: HYP_LABELS[h] for h in HYP_IDS},
            "house_agent_generated": [p.model_dump() for p in props]}


def get_whiteboard(target_id: str) -> dict:
    return _summary(_load(target_id))


def propose_hypothesis(target_id: str, hypothesis_id: str, name: str, parent: str, mechanism: str,
                       predicted_test: str, expected_outcome: str) -> dict:
    if parent not in HYP_IDS:
        return {"error": f"parent must be one of {HYP_IDS}"}
    if predicted_test not in REGISTRY:
        return {"error": f"predicted_test must be one of {list(REGISTRY)}"}
    with _lock:
        wb = _load(target_id)
        h = {"id": hypothesis_id, "name": name, "parent": parent, "mechanism": mechanism, "origin": "agent_generated",
             "proposed_by": "house", "predicted_signatures": [{"test_id": predicted_test,
                                                                "expected_outcome": expected_outcome}]}
        wb.hypotheses.append(h)
        _save(wb)
    _log("house", "propose_hypothesis", target_id, inputs=h)
    return {"accepted": True, "hypothesis": h}


# ---------------------------------------------------------------- Cuddy

def plan_next_tests(target_id: str, contrarian: str = "", house_request: str = "") -> dict:
    """Score every untested test (EIG/cost + bounded contrarian bonus); return PlannerRationale."""
    c = _ctx()
    wb = _load(target_id)
    lead = wb.leader()
    contr = (lead, contrarian) if contrarian in HYP_IDS and contrarian != lead else None
    plan = c["cuddy"].plan(wb, len(wb.tests_run) + 1, contr, house_request or None)
    _log("cuddy", "plan", target_id, outputs=plan.model_dump())
    return plan.model_dump()


# ---------------------------------------------------------------- Chase

def run_vetting_test(target_id: str, test_id: str, window_factor: float = 3.0, cost_units: float = 0.0) -> dict:
    c = _ctx()
    if test_id not in REGISTRY:
        return {"error": f"{test_id} not in registry (test_allowlist)"}
    with _lock:
        wb = _load(target_id)
        rerun = test_id in wb.tested()
        cost = (c["cfg"]["foreman"]["rerun_cost_fraction"] if rerun else 1.0) * REGISTRY[test_id].cost
        b = wb.budget
        if (not rerun and b["used"] + 1 > b["max_tests"]) or b["cost_units_used"] + cost > b["cost_units_max"] + 1e-9:
            return {"error": "budget_cap: request a human-approved budget extension", "budget": b}
        t = c["gk"].get_target(target_id)
        res = c["chase"].execute(TestSpec(test_id=test_id, target_id=target_id,
                                          params={"window_factor": float(window_factor)}, cost_units=cost), t)
        if not rerun:
            b["used"] += 1
        b["cost_units_used"] += cost
        wb.tests_run.append({"test_id": test_id, "run_id": res.run_id, "outcome_bin": res.outcome_bin,
                             "outcome_label": res.outcome_label, "metrics": res.metrics, "quality": "pending",
                             "weight": 0.0, "rerun": rerun, "window_factor": float(window_factor),
                             "evidence_ids": [f"EV-{k}" for k in REGISTRY[test_id].method_refs]})
        _save(wb)
    _log("chase", "run_vetting_test", target_id, inputs={"test_id": test_id, "window_factor": window_factor},
         outputs=res.model_dump(), cost_units=cost)
    return res.model_dump()


def rerun_vetting_test(target_id: str, test_id: str, window_factor: float = 5.0, cost_units: float = 0.0) -> dict:
    return run_vetting_test(target_id, test_id, window_factor, cost_units)


# ---------------------------------------------------------------- Foreman

def data_trust_check(target_id: str) -> dict:
    c = _ctx()
    out = c["foreman"].data_trust(c["gk"].get_target(target_id))
    _log("foreman", "data_trust_check", target_id, outputs=out)
    return out


def assess_result(target_id: str, run_id: str) -> dict:
    """Grade a result, update the posterior, open/resolve critiques, flag surprises."""
    c = _ctx()
    tab = c["tables"]
    with _lock:
        wb = _load(target_id)
        tr = next((t for t in wb.tests_run if t["run_id"] == run_id), None)
        if tr is None:
            return {"error": f"unknown run_id {run_id}"}
        if tr["quality"] != "pending":
            return {"error": "already assessed", "quality": tr["quality"]}
        target = c["gk"].get_target(target_id)
        from .schemas import TestResult
        res = TestResult(test_id=tr["test_id"], target_id=target_id, run_id=run_id, metrics=tr["metrics"],
                         outcome_bin=tr["outcome_bin"], outcome_label=tr["outcome_label"],
                         params={"window_factor": tr.get("window_factor", 3.0)})
        if tr.get("rerun"):
            orig = next(t for t in wb.tests_run if t["test_id"] == tr["test_id"] and not t.get("rerun"))
            same = orig["outcome_bin"] == tr["outcome_bin"]
            tr["quality"] = "ok" if same else "marginal"
            if not same:
                # retro-actively downgrade the original result's weight
                w_old, w_new = orig["weight"], c["cfg"]["foreman"]["weights"]["marginal"]
                if orig["outcome_bin"] >= 0:
                    lik = tab.likelihood(orig["test_id"], orig["outcome_bin"])
                    post = update(wb.post_array(), lik, w_new - w_old, tab.temper)
                    wb.set_posterior(post, after=f"{orig['test_id']}@downgrade")
                orig["weight"], orig["quality"] = w_new, "marginal"
                wb.open_critiques.append({"id": f"C{len(wb.open_critiques) + 1}", "test_id": orig["test_id"],
                                          "text": f"{orig['test_id']} is detrending-sensitive.", "permanent": False})
            else:
                wb.open_critiques = [x for x in wb.open_critiques if x["test_id"] != tr["test_id"]]
            _save(wb)
            out = {"rerun_agrees": same, "posterior": wb.posterior, "open_critiques": wb.open_critiques}
            _log("foreman", "assess_rerun", target_id, outputs=out)
            return out
        a = c["foreman"].assess(res, target, tab, wb.post_array())
        lik = tab.likelihood(tr["test_id"], tr["outcome_bin"]) if tr["outcome_bin"] >= 0 else np.ones(5)
        post = update(wb.post_array(), lik, a.weight, tab.temper)
        old = wb.leader()
        wb.set_posterior(post, after=tr["test_id"])
        tr["quality"], tr["weight"] = a.quality, a.weight
        if a.surprise and a.follow_up_request is None:
            wb.open_critiques.append({"id": f"C{len(wb.open_critiques) + 1}", "test_id": tr["test_id"],
                                      "text": f"Surprising {tr['test_id']} needs corroboration.", "permanent": False})
        elif a.quality == "ok" and lik[HYP_IDS.index(wb.leader())] >= 0.5 * lik.max():
            wb.open_critiques = [x for x in wb.open_critiques if x["permanent"] or x["test_id"] == tr["test_id"]]
        _save(wb)
    out = a.model_dump()
    out.update(posterior=wb.posterior, leader_flipped=old != wb.leader(), new_leader=wb.leader(),
               open_critiques=wb.open_critiques)
    _log("foreman", "assess_result", target_id, outputs=out)
    return out


# ---------------------------------------------------------------- Cameron

def literature_search(query: str, target_id: str = "") -> dict:
    # Defense in depth: the no_target_specific_lookup policy blocks this at the Omnigent layer too.
    if os.environ.get("PP_BENCHMARK_MODE", "1") == "1" and (
            TARGET_NAME_PATTERN.search(query) or (target_id and target_id.lower() in query.lower())):
        _log("cameron", "literature_search_blocked", target_id, inputs={"query": query})
        return {"error": "no_target_specific_lookup: query names the target"}
    hits = openalex_search(query)
    _log("cameron", "literature_search", target_id or None, inputs={"query": query}, outputs=hits)
    return {"query": query, "results": hits, "source": "OpenAlex"}


def evidence_for_tests(target_id: str, test_ids: list[str]) -> dict:
    cam = _ctx()["cameron"]
    evs = cam.evidence_for_tests([t for t in test_ids if t in REGISTRY])
    with _lock:
        wb = _load(target_id)
        have = {e["id"] for e in wb.evidence}
        wb.evidence += [e.model_dump() for e in evs if e.id not in have]
        _save(wb)
    return {"evidence": [e.model_dump() for e in evs], "dropped_unresolvable": cam.dropped}


def resolve_citation(arxiv_id: str) -> dict:
    return resolve_arxiv(arxiv_id)


# ---------------------------------------------------------------- verdict, follow-up, memory

def issue_verdict(target_id: str, run_ids: list[str] | None = None, evidence_ids: list[str] | None = None,
                  label_text: str = "", needs_human: bool = False) -> dict:
    """House's verdict. The label is forced to the posterior's top class (no override without approval).

    House must cite the run_ids it relies on (provenance_required); unknown IDs are rejected.
    """
    c = _ctx()
    with _lock:
        wb = _load(target_id)
        known = {t["run_id"] for t in wb.tests_run}
        bad = [r for r in (run_ids or []) if r not in known]
        if bad:
            return {"error": f"unknown run_ids cited: {bad}", "known_run_ids": sorted(known)}
        lab_tmp = __import__("plainsboro.lab", fromlist=["Lab"]).Lab(c["tables"], c["cfg"], n_interval_draws=200)
        wb_runs = [t for t in wb.tests_run if t["quality"] != "pending"]
        wb.tests_run = wb_runs
        interval = lab_tmp._interval(wb)
        v = c["house"].verdict(wb, interval, c["cfg"]["stopping"]["posterior_threshold"],
                               [t["run_id"] for t in wb_runs],
                               sorted({e for t in wb_runs for e in t.get("evidence_ids", [])}), wb.open_critiques)
        v.needs_human = v.needs_human or bool(needs_human)
        wb.status = "closed"
        _save(wb)
    out = v.model_dump()
    if label_text and label_text != v.label_text:
        out["note"] = "label_text replaced by the posterior-consistent wording"
    _log("house", "issue_verdict", target_id, outputs=out)
    return out


def propose_followup(target_id: str, kind: str, justification: str) -> dict:
    _log("house", "propose_followup", target_id, inputs={"kind": kind, "justification": justification})
    return {"queued": True, "kind": kind, "note": "Human-approved proposal recorded; the lab never requests "
                                                  "telescope time itself (no_external_writes)."}


def record_lesson(target_id: str) -> dict:
    c = _ctx()
    wb = _load(target_id)
    from .schemas import Verdict
    post = wb.posterior
    label = max(post, key=post.get)
    v = Verdict(target_id=target_id, label=label, label_text=HYP_LABELS[label], posterior=post,
                top_posterior=post[label], interval=(0, 1), evidence_ids=[], run_ids=[],
                tests_used=wb.budget["used"], cost_used=wb.budget["cost_units_used"])
    ll = c["wilson"].record_case(wb, v)
    return ll.model_dump()


def gatekeeper_score(target_id: str, label: str) -> dict:
    """Evaluator-only (blocked for agents by no_label_access). Present to demonstrate the policy."""
    return {"correct": _ctx()["gk"].score(target_id, label)}
