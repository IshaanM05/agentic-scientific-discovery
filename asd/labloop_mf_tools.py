"""Omnigent function tools for the multi-fidelity LabLoop extension (screen vs synthesis).

State lives in the run directory (Omnigent may run each tool call in a fresh process):
  ll_mf_state.json  {world, seed, budget, units_used, round, counts, observations[]}
  record.jsonl      one entry per tool call, same layout as asd/tools.py (record_id, kind, seed, run_id, ...)
Run dir from ASD_RUN_DIR / LC_ASD_RUN_DIR (required). Tools return JSON-serialisable dicts only and never
return hidden truth (true bandgap or T80, hit lists, world parameters). Screens and syntheses return the
noisy measurements the lab would hand over, nothing else.

Tools: ll_mf_start, ll_mf_plan, ll_screen, ll_run_mf.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from labloop.chemistry import composition_space, is_hit, set_world, space_arrays
from labloop.lab import make_protocol, safety_review
from labloop.multifidelity import (
    SCREEN_COST, MFLab, MFSurrogate, action_scores, plan_actions, synth_cost,
)

BETA = 1.0  # discovery bonus (nats per expected hit) in the synthesis score; see docs/RESULTS_MULTIFIDELITY.md


class MFConfigError(Exception):
    pass


def _env(name, default=None):
    return os.environ.get("ASD_" + name, os.environ.get("LC_ASD_" + name, default))


def _run_dir() -> Path:
    d = _env("RUN_DIR")
    if d is None:
        raise MFConfigError("ASD_RUN_DIR not set in the tool process; refusing to fall back to a shared run dir")
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> dict:
    p = _run_dir() / "ll_mf_state.json"
    if not p.exists():
        raise MFConfigError("no multi-fidelity run here: call ll_mf_start first")
    st = json.loads(p.read_text())
    set_world(st["world"])  # global per-process state
    return st


def _save(st: dict) -> None:
    (_run_dir() / "ll_mf_state.json").write_text(json.dumps(st))


def _record(st: dict, kind: str, payload: dict) -> str:
    rec = _run_dir() / "record.jsonl"
    n = len(rec.read_text().splitlines()) if rec.exists() else 0
    entry = {"record_id": f"rec-{n + 1:04d}", "kind": kind, "seed": st["seed"],
             "run_id": _env("RUN_ID", ""), **payload}
    with open(rec, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["record_id"]


def _surrogate(st: dict) -> MFSurrogate:
    sur = MFSurrogate()
    if st["observations"]:
        sur.fit(st["observations"])
    return sur


def _masks(st: dict):
    n = len(composition_space())
    tested, screened = np.zeros(n, bool), np.zeros(n, bool)
    for o in st["observations"]:
        (tested if o["fid"] == "synth" else screened)[o["idx"]] = True
    return tested, screened


def _view(o: dict) -> dict:
    """What a tool may show about one measurement."""
    keep = ("idx", "fid", "ok", "eg", "lt", "cost", "phase")
    out = {k: o[k] for k in keep if k in o}
    out["formula"] = composition_space()[o["idx"]].formula()
    if o["ok"] and o["lt"] is not None:
        out["t80_h_est"] = round(10 ** o["lt"])
    return out


def _budget_left(st):
    return round(st["budget"] - st["units_used"], 3)


def ll_mf_start(world: int, seed: int, budget: float = 60.0) -> dict:
    """Start a multi-fidelity LabLoop run: screen (cost 0.2, noisy) and synthesis (cost 1 to 1.5) share one budget."""
    set_world(int(world))
    st = {"world": int(world), "seed": int(seed), "budget": float(budget), "units_used": 0.0, "round": 0,
          "counts": {"synth": {}, "screen": {}}, "observations": []}
    _save(st)
    out = {"world": st["world"], "budget": st["budget"], "n_candidates": len(composition_space()),
           "tests": {"screen": {"cost": SCREEN_COST, "gives": "noisy bandgap estimate (sd 0.06 eV), coarse stability proxy"},
                     "synthesis": {"cost": "1.0 (1.5 with Sn)", "gives": "film QC, bandgap (sd 0.015 eV), T80 (sd 0.1 dex)"}}}
    out["record_id"] = _record(st, "ll_mf_start", {k: out[k] for k in ("world", "budget", "n_candidates")})
    return out


def ll_mf_plan(n: int = 5) -> dict:
    """Rank the next n actions by expected information gain per unit cost; each lists both fidelities."""
    st = _load()
    sur = _surrogate(st)
    tested, screened = _masks(st)
    acts = plan_actions(sur, tested, screened, int(n), True, BETA, budget_left=st["budget"] - st["units_used"])
    space = composition_space()
    options = [{"candidate_id": a["idx"], "formula": space[a["idx"]].formula(), "choice": a["fid"],
                "cost": round(a["cost"], 2), "score_per_cost": round(a["score_per_cost"], 3),
                "alternative": {"fidelity": a["alt_fid"], "score_per_cost": None if not np.isfinite(a["alt_score_per_cost"]) else round(a["alt_score_per_cost"], 3)},
                "eig_screen_nats": round(a["eig_screen"], 4), "eig_synth_nats": round(a["eig_synth"], 4),
                "p_hit_belief": round(a["p_hit"], 3),
                "reason": ("screen: cheaper per nat of learning; re-plan after its result" if a["fid"] == "screen"
                           else "synthesis: highest information plus discovery value per unit cost")} for a in acts]
    out = {"options": options, "budget_left": _budget_left(st)}
    out["record_id"] = _record(st, "mf_plan", {"options": options, "budget_left": out["budget_left"]})
    return out


def _do(st: dict, idx: int, fid: str, lab: MFLab) -> dict:
    cost = SCREEN_COST if fid == "screen" else synth_cost(idx)
    if st["units_used"] + cost > st["budget"] + 1e-9:
        return {"candidate_id": idx, "denied": True, "reason": f"budget: {cost} units needed, {_budget_left(st)} left"}
    if fid == "synth":
        sr = safety_review(make_protocol(composition_space()[idx]))
        if not sr["approved"]:
            return {"candidate_id": idx, "denied": True, "requires_human_approval": True,
                    "reason": f"safety review: {sr.get('reason', 'level 3')}"}
    o = lab.screen(idx) if fid == "screen" else lab.synthesize(idx)
    st["units_used"] = round(st["units_used"] + o["cost"], 6)
    st["observations"].append({k: o[k] for k in ("idx", "fid", "ok", "eg", "lt", "cost") if k in o} | {"round": st["round"]})
    if fid == "synth":
        st["observations"][-1]["phase"] = o.get("phase")
    out = _view(o)
    out["measured_hit"] = bool(fid == "synth" and o["ok"] and is_hit(o["eg"], o["lt"]))
    return out


def _run(actions: list[dict], kind: str) -> dict:
    st = _load()
    lab = MFLab(st["world"], st["seed"], st["counts"])
    st["round"] += 1
    tested, screened = _masks(st)
    results = []
    sc = None
    for a in actions:
        idx, fid = int(a["candidate_id"]), a.get("fidelity", "auto")
        if not 0 <= idx < len(tested):
            results.append({"candidate_id": idx, "denied": True, "reason": "unknown candidate id"})
            continue
        if fid == "auto":
            if tested[idx]:
                results.append({"candidate_id": idx, "denied": True, "reason": "already synthesised"})
                continue
            sc = sc or action_scores(_surrogate(st), tested, screened, True, BETA)
            fid = "screen" if sc["screen"][idx] >= sc["synth"][idx] else "synth"
        if fid == "screen" and screened[idx]:
            results.append({"candidate_id": idx, "denied": True, "reason": "already screened"})
            continue
        if fid == "synth" and tested[idx]:
            results.append({"candidate_id": idx, "denied": True, "reason": "already synthesised"})
            continue
        r = _do(st, idx, fid, lab)
        if not r.get("denied"):
            (tested if fid == "synth" else screened)[idx] = True
        results.append(r)
    st["counts"] = lab.export_counts()
    _save(st)
    out = {"results": results, "units_used": round(st["units_used"], 3), "budget_left": _budget_left(st),
           "measured_hits_so_far": sum(o["fid"] == "synth" and o["ok"] and is_hit(o["eg"], o["lt"])
                                       for o in st["observations"])}
    for r in results:
        _record(st, "experiment" if not r.get("denied") and r["fid"] == "synth" else
                ("screen" if not r.get("denied") else "denied"), r)
    return out


def ll_screen(candidate_ids: list) -> dict:
    """Run cheap screens (0.2 units each, noisy) on candidates; one screen per film."""
    return _run([{"candidate_id": i, "fidelity": "screen"} for i in candidate_ids], "screen")


def ll_run_mf(actions: list) -> dict:
    """Run actions [{candidate_id, fidelity: auto|screen|synth}]. 'auto' picks the fidelity by information gain per cost.
    Synthesis passes the safety review first; actions beyond the budget are DENIED and not charged."""
    return _run(list(actions), "run_mf")
