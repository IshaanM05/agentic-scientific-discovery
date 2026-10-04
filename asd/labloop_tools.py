"""Omnigent function tools that drive LabLoop's simulated perovskite lab (agents/labloop_planner.yaml).

Contract: docs/LABLOOP_INTEGRATION.md. Omnigent may run every tool call in a fresh process, so ALL state lives
in the run directory: notebook.sqlite (LabLoop Notebook), ll_state.json (enough to rebuild Surrogate, Arena and
agents deterministically) and record.jsonl (one entry per call, same entry format as asd/tools.py).
Run dir from env ASD_RUN_DIR / LC_ASD_RUN_DIR (required), run id from ASD_RUN_ID / LC_ASD_RUN_ID.

Hidden truth (true bandgap/T80, true hits, world parameters, untested measurements) is never returned, logged
or stored. New hypotheses come from an Omnigent sub-agent (ll_generator) and are validated here against
LabLoop's region DSL; labloop/llm.py is never used.
"""
import json
import os
from pathlib import Path

import numpy as np

from labloop import literature
from labloop.campaign import (AnalystAgent, Config, DesignerAgent, GOAL, HypothesisAgent, JudgeAgent, PIAgent,
                              _admit, _comp_display, _strongest_counterexample)
from labloop.chemistry import TARGET, composition_space, is_hit, set_world, space_arrays
from labloop.hypotheses import (DIMS, Arena, Hypothesis, critique, evaluate, in_region, literature_hypotheses,
                                region_mask)
from labloop.lab import PerovskiteReplayLab, RESTRICTED, make_protocol, safety_review
from labloop.notebook import Notebook
from labloop.surrogate import Surrogate
from .policies import HAZARD_TERMS

MAX_PROPOSALS = 6
MAX_REGION_FRACTION = 0.35  # same breadth cap labloop applies to LLM hypotheses
SCALE_ASK_CONC_M = 2.5      # make_protocol conc above this exceeds LabLoop's 5 mmol safety limit
SLOT_KINDS = ("test", "exploit", "explore", "random")
HUMAN_STATES = ("restricted_element", "scale_up")
DSL = ("hypothesis = {statement, region:{dim:[lo,hi]}, prop:'eg'|'lt', op:'<'|'>'|'between'|'contrast', value, "
       "region_b (contrast only), rationale, sources:[str]}; dims " + "/".join(DIMS) + " are fractions 0..1; "
       "prop eg is bandgap in eV, prop lt is log10 T80 hours (or give value_t80_h in hours); 'between' takes value "
       "[lo,hi]; 'contrast' says region mean exceeds region_b mean by value; region must hold >=3 compositions "
       f"and under {MAX_REGION_FRACTION:.0%} of the space; near-duplicates of existing hypotheses are rejected.")


class LabLoopToolError(Exception):
    pass


class _NoLLM:
    """Stand-in for labloop.llm.LLM: never available, so labloop's direct Anthropic call is never used."""
    available = False
    name = "omnigent"
    calls = 0


# --------------------------------------------------------------------------- run dir, state, record
def _env(name, default=None):
    return os.environ.get("ASD_" + name, os.environ.get("LC_ASD_" + name, default))


def _run_dir():
    d = _env("RUN_DIR")
    if d is None:
        raise LabLoopToolError("ASD_RUN_DIR not set in the tool process; refusing to use a shared run dir")
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clean(x):
    """JSON-serialisable copy (numpy scalars/arrays, tuples)."""
    return json.loads(json.dumps(x, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def _rng_from(state_dict, seed):
    g = np.random.default_rng(seed)
    if state_dict is not None:
        g.bit_generator.state = state_dict
    return g


def _hyp_to_dict(h, extra):
    return _clean({"id": h.id, "statement": h.statement, "region": h.region, "prop": h.prop, "op": h.op,
                   "value": h.value, "region_b": h.region_b, "origin": h.origin, "sources": h.sources,
                   "rationale": h.rationale, "status": h.status, "elo": h.elo, "created_round": h.created_round,
                   "resolved_round": h.resolved_round, "critiques": h.critiques, "n_evidence": h.n_evidence,
                   "pass_rate": h.pass_rate, "confidence": h.confidence, "history": h.history, **extra})


_EXTRA = ("source", "label")


def _hyp_from_dict(d):
    reg = lambda r: None if r is None else {k: (float(v[0]), float(v[1])) for k, v in r.items()}
    val = tuple(d["value"]) if isinstance(d["value"], list) else d["value"]
    h = Hypothesis(d["id"], d["statement"], reg(d["region"]), d["prop"], d["op"], val, region_b=reg(d["region_b"]),
                   origin=d["origin"], sources=list(d["sources"]), rationale=d["rationale"], status=d["status"],
                   elo=d["elo"], created_round=d["created_round"], resolved_round=d["resolved_round"],
                   critiques=list(d["critiques"]), n_evidence=d["n_evidence"], pass_rate=d["pass_rate"],
                   confidence=d["confidence"], history=list(d["history"]))
    return h, {k: d.get(k) for k in _EXTRA}


class Ctx:
    """One tool call's view of the run: state loaded from disk, labloop objects rebuilt deterministically."""

    def __init__(self, need_state=True):
        self.dir = _run_dir()
        self.path = self.dir / "ll_state.json"
        self.rec = self.dir / "record.jsonl"
        self.run_id = _env("RUN_ID", self.dir.name)
        self.st = None
        if self.path.exists():
            self.st = json.loads(self.path.read_text())
        elif need_state:
            raise LabLoopToolError("no ll_state.json in the run dir: call ll_start first")
        if self.st is not None:
            self._build()

    def _build(self):
        st = self.st
        set_world(st["world"])  # global per-process state: every call re-installs the world
        self.space = composition_space()
        self.cfg = Config(seed=st["seed"], budget=st["budget"], world=st["world"])
        self.obs = []
        for o in st["observations"]:
            self.obs.append({**o, "comp": self.space[o["idx"]]})
        self.tested = np.zeros(len(self.space), dtype=bool)
        self.tested[st["tested_idx"]] = True
        self.hyps, self.extra = {}, {}
        for hid, d in st["hyps"].items():
            self.hyps[hid], self.extra[hid] = _hyp_from_dict(d)
        self.rng = _rng_from(st["rng_state"]["planner"], [st["seed"], 1])
        self.lab = PerovskiteReplayLab(seed=st["seed"])
        self.lab.rng = _rng_from(st["rng_state"]["lab"], st["seed"])
        self.arena = Arena(self.rng)
        self.sur = Surrogate()
        self._fit_surrogate()

    def _fit_surrogate(self):
        self.sur = Surrogate()
        for r in self.st["relaxations"]:
            self.sur.relax_prior(r["prop"], self.obs[: r["n_obs"]])
        if self.obs:
            self.sur.fit(self.obs)

    def anomaly(self, a):
        return {**a, "comp": self.space[a["idx"]]}

    def comp_obs_idx(self, idx):
        return [o for o in self.obs if o["idx"] == idx]

    # -- persistence
    def save(self):
        st = self.st
        st["observations"] = [{k: v for k, v in o.items() if k != "comp"} for o in self.obs]
        st["tested_idx"] = [int(i) for i in np.where(self.tested)[0]]
        meas = {}
        for o in st["observations"]:
            meas.setdefault(str(o["idx"]), []).append(o["exp_id"])
        st["measurements"] = meas
        st["hyps"] = {hid: _hyp_to_dict(h, self.extra[hid]) for hid, h in self.hyps.items()}
        st["rng_state"] = {"planner": self.rng.bit_generator.state, "lab": self.lab.rng.bit_generator.state}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_clean(st), sort_keys=True))
        os.replace(tmp, self.path)

    def notebook(self):
        return Notebook(self.dir / "notebook.sqlite")

    def record(self, kind, payload):
        n = sum(1 for _ in open(self.rec)) if self.rec.exists() else 0
        entry = {"record_id": f"rec-{n + 1:04d}", "kind": kind, "seed": self.st["seed"], "run_id": self.run_id,
                 "world": self.st["world"], **payload}
        with open(self.rec, "a") as f:
            f.write(json.dumps(_clean(entry)) + "\n")
        return entry["record_id"]

    @property
    def units_left(self):
        return round(self.st["budget"] - self.st["units_used"], 2)


def _ensure_literature(c, nb=None):
    if c.st["literature_loaded"]:
        return
    for h in literature_hypotheses():
        c.hyps[h.id] = h
        c.extra[h.id] = {"source": "literature", "label": "literature"}
    c.st["literature_loaded"] = True


def _discovery_refresh(c):
    """Judge discovery verdicts from measurements (rubric = labloop JudgeAgent). Returns changed verdicts."""
    judge, changed = JudgeAgent(), []
    by_idx = {}
    for o in c.obs:
        by_idx.setdefault(o["idx"], []).append(o)
    for i, ms in by_idx.items():
        key = str(i)
        if any(m["ok"] and is_hit(m["eg"], m["lt"]) for m in ms) or key in c.st["discoveries"]:
            v = judge.discovery_verdict(ms)
            ok_ms = [m for m in ms if m["ok"]]
            new = {**v, "idx": i, "formula": c.space[i].formula(), "n": len(ms),
                   "eg": round(float(np.mean([m["eg"] for m in ok_ms])), 3) if ok_ms else None,
                   "t80_h": round(float(10 ** np.mean([m["lt"] for m in ok_ms]))) if ok_ms else None,
                   "round": c.st["discoveries"].get(key, {}).get("round", c.st["round"])}
            if c.st["discoveries"].get(key, {}).get("status") != new["status"]:
                changed.append(new)
            c.st["discoveries"][key] = new
    return changed


def _hyp_view(c, h):
    return {"id": h.id, "statement": h.statement, "prediction": h.prediction, "kill_condition": h.kill_condition,
            "status": h.status, "elo": round(h.elo, 1), "origin": h.origin, "label": c.extra[h.id]["label"],
            "source": c.extra[h.id]["source"], "citation": ", ".join(h.sources), "n_evidence": h.n_evidence,
            "pass_rate": None if h.pass_rate is None else round(h.pass_rate, 2), "confidence": h.confidence,
            "region": {k: list(v) for k, v in h.region.items()}}


def _err(e):
    return {"error": str(e)}


# --------------------------------------------------------------------------- tools
def ll_start(world: int, seed: int, budget: float = 60) -> dict:
    """Start (or idempotently re-open) a LabLoop run in the run dir. Returns run id, budget, candidate count, spec."""
    try:
        c = Ctx(need_state=False)
        world, seed, budget = int(world), int(seed), float(budget)
        if c.st is not None:
            have = (c.st["world"], c.st["seed"], c.st["budget"])
            if have != (world, seed, budget):
                return _err(f"run dir already holds run {have}; refusing to overwrite with {(world, seed, budget)}")
        else:
            c.st = {"world": world, "seed": seed, "budget": budget, "units_used": 0.0, "round": 0,
                    "tested_idx": [], "observations": [], "measurements": {}, "discoveries": {}, "hyps": {},
                    "pending_surprises": [], "open_anomalies": [], "seen_surprises": [], "relaxations": [],
                    "experiments": [], "unanalysed": [], "decision": None, "designed": {}, "h_counter": 6,
                    "literature_loaded": False, "rng_state": {"planner": None, "lab": None}}
            c._build()
            c.save()
            c.notebook().commit()
            c.record("ll_start", {"budget": budget, "n_candidates": len(c.space)})
        return _clean({"run_id": c.run_id, "world": world, "budget": budget, "n_candidates": len(c.space),
                       "spec": {"goal": GOAL, "target": TARGET, "hypothesis_dsl": DSL,
                                "unit_cost": "1.0 per Pb film, 1.5 per Sn film",
                                "loop": "ll_literature, ll_arena_round, ll_pi_decide, ll_design, ll_run, ll_analyse, ll_judge",
                                "note": "simulated lab with synthetic hidden physics; a benchmark, not real devices"}})
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_literature() -> dict:
    """Sourced literature claims and the literature hypotheses they motivate (registered in the arena)."""
    try:
        c = Ctx()
        _ensure_literature(c)
        srcs = {x["id"]: x["source"] for x in literature.CLAIMS}
        hyps = [_hyp_view(c, h) for h in c.hyps.values() if c.extra[h.id]["source"] == "literature"]
        for hv in hyps:
            hv["citation"] = "; ".join(srcs.get(s, s) for s in hv["citation"].split(", ") if s)
        out = {"claims": [{"id": x["id"], "claim": x["claim"], "source": x["source"]} for x in literature.CLAIMS],
               "hypotheses": hyps}
        c.save()
        out["record_id"] = c.record("literature", {"claim_ids": [x["id"] for x in literature.CLAIMS],
                                                   "hypothesis_ids": [h["id"] for h in hyps]})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def _validate_proposal(p, hyps):
    """Return (Hypothesis-kwargs, None) or (None, reason). Pure validation against labloop's region DSL."""
    if not isinstance(p, dict):
        return None, "proposal is not an object"
    stmt = p.get("statement")
    if not isinstance(stmt, str) or not stmt.strip():
        return None, "missing statement"
    reg = p.get("region")
    if not isinstance(reg, dict) or not reg:
        return None, "region must be a non-empty object {dim:[lo,hi]}"
    prop, op = p.get("prop"), p.get("op")
    if prop not in ("eg", "lt"):
        return None, "prop must be 'eg' or 'lt'"
    if op not in ("<", ">", "between", "contrast"):
        return None, "op must be one of <, >, between, contrast"

    def parse_region(r, name):
        out = {}
        for d, v in r.items():
            if d not in DIMS:
                raise ValueError(f"{name}: unknown dimension {d!r} (allowed: {', '.join(DIMS)})")
            if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
                raise ValueError(f"{name}.{d} must be [lo, hi] numbers")
            lo, hi = float(v[0]), float(v[1])
            if not (0.0 <= lo <= hi <= 1.0):
                raise ValueError(f"{name}.{d} must satisfy 0 <= lo <= hi <= 1")
            out[d] = (lo, hi)
        return out

    try:
        region = parse_region(reg, "region")
        region_b = parse_region(p["region_b"], "region_b") if p.get("region_b") else None
        raw = p.get("value")
        if raw is None and prop == "lt" and p.get("value_t80_h") is not None:
            raw = float(np.log10(float(p["value_t80_h"])))
        if op == "between":
            if not (isinstance(raw, (list, tuple)) and len(raw) == 2):
                raise ValueError("between needs value [lo, hi]")
            value = (float(raw[0]), float(raw[1]))
            if value[0] > value[1]:
                raise ValueError("between needs lo <= hi")
            nums = list(value)
        else:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError("value must be a number")
            value = float(raw)
            nums = [value]
        if op == "contrast":
            if region_b is None:
                raise ValueError("contrast needs region_b")
            if value <= 0:
                raise ValueError("contrast value must be > 0")
        elif region_b is not None:
            raise ValueError("region_b only valid for contrast")
        if op != "contrast" and not all((0.5 <= n <= 4.5) if prop == "eg" else (-1.0 <= n <= 5.0) for n in nums):
            raise ValueError("value out of range (eg in eV 0.5-4.5; lt is log10 hours -1..5)")
    except (ValueError, TypeError, OverflowError) as e:
        return None, str(e)
    n_a = int(region_mask(region).sum())
    if n_a < 3:
        return None, f"region contains only {n_a} compositions (need >= 3)"
    if region_mask(region).mean() > MAX_REGION_FRACTION:
        return None, f"region too broad ({region_mask(region).mean():.0%} of the space; limit {MAX_REGION_FRACTION:.0%})"
    if region_b is not None and int(region_mask(region_b).sum()) < 3:
        return None, "region_b contains fewer than 3 compositions"
    srcs = [str(s)[:120] for s in (p.get("sources") or []) if isinstance(s, (str, int))][:5]
    return {"statement": stmt.strip()[:220], "region": region, "prop": prop, "op": op, "value": value,
            "region_b": region_b, "rationale": str(p.get("rationale", ""))[:300], "sources": srcs}, None


def _new_id(c):
    c.st["h_counter"] += 1
    return f"H{c.st['h_counter']}"


def ll_arena_round(proposals: list = None) -> dict:
    """Validate generator proposals against the DSL (admit or reject with reason), run critic and one Elo round."""
    try:
        c = Ctx()
        _ensure_literature(c)
        rnd = c.st["round"] + 1
        admitted, rejected = [], []
        for p in (proposals or [])[:]:
            if len(admitted) >= MAX_PROPOSALS:
                rejected.append({"statement": str(p.get("statement", ""))[:80] if isinstance(p, dict) else "",
                                 "reason": f"more than {MAX_PROPOSALS} proposals in one round"})
                continue
            kw, why = _validate_proposal(p, c.hyps)
            if kw is None:
                rejected.append({"statement": str(p.get("statement", ""))[:80] if isinstance(p, dict) else "",
                                 "reason": why})
                continue
            h = Hypothesis(_new_id(c), kw["statement"], kw["region"], kw["prop"], kw["op"], kw["value"],
                           region_b=kw["region_b"], origin="llm", sources=kw["sources"], rationale=kw["rationale"],
                           created_round=rnd)
            if not _admit(h, c.hyps):
                rejected.append({"statement": kw["statement"][:80], "reason": "near-duplicate of an existing hypothesis"})
                continue
            c.hyps[h.id], c.extra[h.id] = h, {"source": "omnigent ll_generator", "label": "agent-generated"}
            admitted.append(h.id)
        fallback = []
        if not proposals and c.st["open_anomalies"]:
            ha = HypothesisAgent(_NoLLM())
            ha.counter = c.st["h_counter"]
            for a in c.st["open_anomalies"][:2]:
                for h in ha.from_anomaly(c.anomaly(a), c.obs, rnd):
                    if _admit(h, c.hyps):
                        c.hyps[h.id], c.extra[h.id] = h, {"source": "rule_based", "label": "rule_based"}
                        fallback.append(h.id)
            c.st["h_counter"] = ha.counter
            c.st["open_anomalies"] = []
        elif admitted:
            c.st["open_anomalies"] = []  # the generator has seen them and answered
        nb = c.notebook()
        for hid in admitted + fallback:
            nb.log_hypothesis(rnd, hid, "proposed", c.hyps[hid].statement)
        untested = ~c.tested
        for h in c.hyps.values():
            h.critiques = critique(h, untested, list(c.hyps.values()))
        c.arena.run(list(c.hyps.values()), c.sur.p_hit(), untested, n_matches=12, rnd=rnd)
        nb.commit()
        nb.db.close()
        c.save()
        out = {"round": rnd, "admitted": [_hyp_view(c, c.hyps[i]) for i in admitted],
               "rule_based_fallback": [_hyp_view(c, c.hyps[i]) for i in fallback], "rejected": rejected,
               "critiques": {h.id: h.critiques for h in c.hyps.values() if h.critiques},
               "elo_table": sorted([{"id": h.id, "elo": round(h.elo, 1), "status": h.status,
                                     "label": c.extra[h.id]["label"]} for h in c.hyps.values()],
                                   key=lambda r: -r["elo"])}
        out["record_id"] = c.record("arena_round", {"admitted": admitted, "rejected": rejected,
                                                    "rule_based_fallback": fallback,
                                                    "elo_table": out["elo_table"],
                                                    "admitted_labels": ["agent-generated"] * len(admitted)})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_pi_decide(rationale: str = "") -> dict:
    """LabLoop PIAgent picks the mode (seed/investigate/exploit/stop) and candidate slots; planner's text is recorded."""
    try:
        c = Ctx()
        _ensure_literature(c)
        _discovery_refresh(c)
        rnd = c.st["round"] + 1
        untested = ~c.tested
        for h in c.hyps.values():
            h.critiques = critique(h, untested, list(c.hyps.values()))
        p = c.sur.p_hit()
        p_opt = c.sur.p_hit(inflate=2.5)
        gmax = float(p_opt[untested].max()) if untested.any() else 0.0

        def relevant(h):
            m = region_mask(h.region) | (region_mask(h.region_b) if h.region_b else False)
            sel = p_opt[m & untested]
            return sel.size > 0 and float(sel.max()) >= 0.25 * gmax

        ranked = sorted([h for h in c.hyps.values() if h.status in ("proposed", "testing")
                         and not any(x.startswith("Not testable") for x in h.critiques) and relevant(h)],
                        key=lambda h: -h.elo)
        parked = [h.id for h in c.hyps.values() if h.status in ("proposed", "testing") and h not in ranked]
        disc = c.st["discoveries"]
        state = {"spent": c.st["units_used"], "confirmed": sum(d["status"] == "confirmed" for d in disc.values()),
                 "unconfirmed_hits": [{"idx": d["idx"], "formula": d["formula"]} for d in disc.values()
                                      if d["status"] == "candidate"],
                 "pending_surprises": c.st["pending_surprises"], "ranked_hypotheses": ranked, "parked": parked,
                 "best_p_hit": float(p[untested].max()) if untested.any() else 0.0}
        d = PIAgent(c.cfg, _NoLLM()).decide(rnd, state)
        c.st["round"] = rnd
        slots = []
        for k, s in enumerate(d["slots"], 1):
            slots.append({**s, "slot_id": f"r{rnd}s{k}"})
        c.st["decision"] = {"round": rnd, "mode": d["mode"], "slots": slots, "labloop_rationale": d["rationale"],
                            "planner_rationale": str(rationale)[:1000]}
        c.st["designed"] = {}
        nb = c.notebook()
        nb.log_decision(rnd, d["mode"], d["rationale"] + " || planner: " + str(rationale)[:500],
                        [s["purpose"] for s in slots])
        nb.commit()
        nb.db.close()
        c.save()
        view = [{"slot_id": s["slot_id"], "kind": s["kind"], "purpose": s["purpose"],
                 **({"hypothesis": s["hypothesis"]} if s.get("hypothesis") else {}),
                 **({"formula": c.space[s["idx"]].formula()} if s["kind"] == "replicate" else {})} for s in slots]
        out = {"round": rnd, "mode": d["mode"], "slots": view, "budget_left": c.units_left,
               "labloop_rationale": d["rationale"]}
        out["record_id"] = c.record("pi_decision", {"mode": d["mode"], "slots": view, "budget_left": c.units_left,
                                                    "labloop_rationale": d["rationale"],
                                                    "planner_rationale": str(rationale)[:1000]})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def _approval_needed(slot):
    """Planner-requested features that need a human: a dopant (restricted-element check) or scale-up."""
    reasons = []
    if slot.get("dopant"):
        reasons.append("restricted_element" if str(slot["dopant"]).strip().capitalize() in RESTRICTED else "dopant")
    if float(slot.get("conc_m", 1.2)) > SCALE_ASK_CONC_M:
        reasons.append("scale_up")
    return reasons


def ll_design(slots: list) -> dict:
    """Turn candidate slots into protocols (composition, purpose, safety_review). Plan >= 2 candidates, run a subset."""
    try:
        c = Ctx()
        if c.st["decision"] is None:
            return _err("call ll_pi_decide first")
        rnd = c.st["round"]
        dec = {s["slot_id"]: s for s in c.st["decision"]["slots"]}
        plan, rejected, extras = [], [], {}
        for k, s in enumerate(slots or [], 1):
            if not isinstance(s, dict):
                rejected.append({"slot": k, "reason": "slot is not an object"})
                continue
            sid = s.get("slot_id")
            if sid in dec:
                base = {x: v for x, v in dec[sid].items()}
            elif sid:
                rejected.append({"slot_id": sid, "reason": "unknown slot_id (use ids from ll_pi_decide or omit it)"})
                continue
            else:
                kind = s.get("kind")
                if kind not in SLOT_KINDS:
                    rejected.append({"slot": k, "reason": f"kind must be one of {', '.join(SLOT_KINDS)} or a slot_id"})
                    continue
                if kind == "test" and (s.get("hypothesis") not in c.hyps
                                       or c.hyps[s["hypothesis"]].status not in ("proposed", "testing")):
                    rejected.append({"slot": k, "reason": "test slot needs an open hypothesis id"})
                    continue
                n = len(dec) + len(plan) + 1
                base = {"kind": kind, "purpose": str(s.get("purpose", kind))[:200], "slot_id": f"r{rnd}s{n}"}
                if kind == "test":
                    base["hypothesis"] = s["hypothesis"]
            if base["slot_id"] in {p["slot_id"] for p in plan}:
                rejected.append({"slot_id": base["slot_id"], "reason": "duplicate slot"})
                continue
            try:
                conc = float(s.get("conc_m", 1.2))
                assert 0.05 <= conc <= 20
            except (TypeError, ValueError, AssertionError):
                rejected.append({"slot_id": base["slot_id"], "reason": "conc_m must be a number in 0.05-20"})
                continue
            extras[base["slot_id"]] = {"conc_m": conc, "dopant": s.get("dopant"), "reason": str(s.get("reason", ""))[:300],
                                       "human_approved": bool(s.get("human_approved", False))}
            plan.append(base)
        designed = DesignerAgent(c.rng).design(plan, c.sur, c.tested, c.hyps)
        protocols, c.st["designed"] = [], {}
        for d in designed:
            ex = extras[d["slot_id"]]
            comp = c.space[d["idx"]]
            proto = make_protocol(comp, purpose=d["purpose"], conc_m=ex["conc_m"])
            if ex["dopant"]:
                proto.precursors.append({"reagent": f"{str(ex['dopant']).strip().capitalize()}I2", "mmol": 0.05})
            sr = safety_review(proto)
            need = _approval_needed({"dopant": ex["dopant"], "conc_m": ex["conc_m"]})
            runnable, why = sr["approved"], ""
            if ex["dopant"]:
                runnable, why = False, "dopants are not modelled by the simulated lab; restricted elements need human sign-off"
            elif not sr["approved"] and ex["human_approved"] and "scale_up" in need:
                runnable, why = True, "scale-up approved by human (Omnigent ASK)"
            elif not sr["approved"]:
                why = f"LabLoop safety_review blocked: {sr.get('reason', 'level 3')}; needs human sign-off"
            c.st["designed"][d["slot_id"]] = {
                "slot_id": d["slot_id"], "idx": d["idx"], "kind": d["kind"], "purpose": d["purpose"],
                "hypothesis": d.get("hypothesis"), "protocol": proto.as_dict(), "safety": sr, "runnable": runnable,
                "block_reason": why, "cost": 1.5 if comp.sn > 0 else 1.0, "reason": ex["reason"],
                "predicted": {"eg": round(d["pred_eg"], 3), "t80_h": round(10 ** d["pred_lt"]),
                              "p_hit": round(d["p_hit"], 3)}, "status": "designed"}
            protocols.append({"slot_id": d["slot_id"], "kind": d["kind"], "composition": comp.formula(),
                              "purpose": d["purpose"], "reason": ex["reason"], "hypothesis": d.get("hypothesis"),
                              "cost": 1.5 if comp.sn > 0 else 1.0, "predicted": c.st["designed"][d["slot_id"]]["predicted"],
                              "protocol": proto.as_dict(), "safety_review": sr, "runnable": runnable,
                              "requires_human_approval": need, "note": why})
        c.save()
        out = {"round": rnd, "protocols": protocols, "rejected": rejected, "budget_left": c.units_left}
        if len(protocols) < 2:
            out["warning"] = "fewer than 2 candidate designs: the planner must compare at least two before running"
        out["record_id"] = c.record("design", {"protocols": protocols, "rejected": rejected})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_run(slot_ids: list) -> dict:
    """Run the chosen designed slots in the simulated lab; DENY a film that would exceed the unit budget."""
    try:
        c = Ctx()
        nb = c.notebook()
        results, denied = [], []
        for sid in slot_ids or []:
            dz = c.st["designed"].get(sid)
            if dz is None:
                denied.append({"slot_id": sid, "reason": "not designed in this round (call ll_design first)"})
                continue
            if dz["status"] == "run":
                denied.append({"slot_id": sid, "reason": "already run"})
                continue
            if not dz["runnable"]:
                denied.append({"slot_id": sid, "reason": dz["block_reason"] or "blocked by safety review"})
                continue
            if c.st["units_used"] + dz["cost"] > c.st["budget"] + 1e-9:
                denied.append({"slot_id": sid, "reason": f"DENY: budget {c.st['budget']:g} units would be exceeded "
                               f"(used {c.st['units_used']:g}, film costs {dz['cost']:g})"})
                continue
            idx, comp = dz["idx"], c.space[dz["idx"]]
            pr = dz["protocol"]
            proto = make_protocol(comp, purpose=dz["purpose"])  # the lab runs the composition (protocol dict is a log)
            was_tested = bool(c.tested[idx])
            res = c.lab.run(proto)
            c.st["units_used"] = round(c.st["units_used"] + res.cost, 4)
            n = len(c.st["experiments"]) + 1
            exp = {"id": f"E{n:03d}", "idx": idx, "key": comp.key, "formula": comp.formula(), "kind": dz["kind"],
                   "purpose": dz["purpose"], "hypothesis": dz["hypothesis"], "protocol": pr, "safety": dz["safety"],
                   "result": res.as_dict(), "predicted": dz["predicted"]}
            obs = {"idx": idx, "key": comp.key, "formula": comp.formula(), "ok": res.ok, "eg": res.bandgap_ev,
                   "lt": res.log_t80, "round": c.st["round"], "exp_id": exp["id"]}
            exp.update(AnalystAgent().analyse({**exp, "idx": idx}, c.sur))
            exp["hit"] = bool(res.ok and is_hit(res.bandgap_ev, res.log_t80))
            exp["round"], exp["replicate"] = c.st["round"], was_tested
            c.obs.append({**obs, "comp": comp})
            c.tested[idx] = True
            c.st["experiments"].append({k: v for k, v in exp.items() if k not in ("protocol", "safety")})
            c.st["unanalysed"].append(exp["id"])
            dz["status"] = "run"
            nb.log_experiment(c.st["round"], {**exp, "surprise": exp["surprise"]})
            row = {"slot_id": sid, "exp_id": exp["id"], "composition": comp.formula(), "ok": res.ok,
                   "bandgap_ev": res.as_dict()["bandgap_ev"], "t80_h": res.as_dict()["t80_h"], "phase": res.phase,
                   "notes": res.notes, "meets_spec": exp["hit"], "cost": res.cost, "predicted": dz["predicted"]}
            row["record_id"] = c.record("experiment", {**row, "round": c.st["round"], "slot_kind": dz["kind"],
                                                       "purpose": dz["purpose"], "hypothesis": dz["hypothesis"],
                                                       "protocol": pr, "safety_review": dz["safety"]})
            results.append(row)
        nb.commit()
        nb.db.close()
        c.save()
        out = {"results": results, "denied": denied, "units_charged": round(sum(r["cost"] for r in results), 2),
               "units_used": c.st["units_used"], "budget_left": c.units_left}
        if denied:
            out["record_id"] = c.record("budget_or_safety_denial", {"denied": denied, "budget_left": c.units_left})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_analyse() -> dict:
    """Findings and surprises for the films run since the last analysis; update hypothesis verdicts and priors."""
    try:
        c = Ctx()
        new = [e for e in c.st["experiments"] if e["id"] in c.st["unanalysed"]]
        rnd = c.st["round"]
        events, findings, surprises, updates, relax = [], [], [], [], []
        replicated_now = {e["idx"] for e in new if e["replicate"]}
        resolved = [a for a in c.st["pending_surprises"] if a["idx"] in replicated_now]
        for a in resolved:
            ms = [m for m in c.comp_obs_idx(a["idx"]) if m["ok"]]
            reproduced = len(ms) >= 2 and abs(ms[-1][a["prop"]] - ms[0][a["prop"]]) < (0.06 if a["prop"] == "eg" else 0.3)
            events.append({"type": "replication", "text": f"{a['formula']}: surprise {'reproduced' if reproduced else 'not reproduced'}"})
            if reproduced:
                c.st["open_anomalies"].append({k: v for k, v in a.items() if k != "comp"})
        c.st["pending_surprises"] = [a for a in c.st["pending_surprises"] if a["idx"] not in {r["idx"] for r in resolved}]
        _, eg_prior, lt_prior, *_ = space_arrays()
        seen = {tuple(x) for x in c.st["seen_surprises"]}
        for e in new:
            findings.append({"exp_id": e["id"], "composition": e["formula"], "finding": e["finding"],
                             "surprise": e["surprise"], "meets_spec": e["hit"], "replicate": e["replicate"]})
            r = e["result"]
            if not r["ok"]:
                continue
            near = TARGET["eg_min"] - 0.2 <= r["bandgap_ev"] <= TARGET["eg_max"] + 0.2
            for prop, z in (("lt", e["z_lt"]), ("eg", e["z_eg"])):
                if (e["idx"], prop) in seen or not (near and (prop == "eg" or r["log_t80"] >= 2.0)):
                    continue
                if abs(z) >= 2.0 and len(c.st["pending_surprises"]) < 3:
                    seen.add((e["idx"], prop))
                    val = r["log_t80"] if prop == "lt" else r["bandgap_ev"]
                    prior = float((lt_prior if prop == "lt" else eg_prior)[e["idx"]])
                    a = {"idx": e["idx"], "key": e["key"], "formula": e["formula"], "prop": prop, "z": z,
                         "value": val, "predicted": prior, "residual": float(val - prior), "exp_id": e["id"],
                         "display": _comp_display(prop, val), "prior_display": _comp_display(prop, prior)}
                    c.st["pending_surprises"].append(a)
                    surprises.append({k: a[k] for k in ("exp_id", "formula", "prop", "z", "display", "prior_display")})
                    events.append({"type": "surprise", "text": f"{e['formula']}: surprise in "
                                   f"{'stability' if prop == 'lt' else 'bandgap'} (z = {z:+.1f}); queued for replication"})
                    break
        c.st["seen_surprises"] = sorted([list(x) for x in seen])
        judge, nb = JudgeAgent(), c.notebook()
        changes = []
        for h in list(c.hyps.values()):
            before = h.status
            evaluate(h, c.obs)
            if h.status != before and h.status == "qualified":
                ex = _strongest_counterexample(h, c.obs)
                if ex is not None:
                    events.append({"type": "qualified", "text": f"{h.id} holds with exceptions; strongest counterexample "
                                   f"{ex['formula']} ({ex['display']} vs prior {ex['prior_display']})"})
                    c.st["open_anomalies"].append({k: v for k, v in ex.items() if k != "comp"})
            if h.status != before and h.status in ("supported", "falsified", "qualified"):
                h.resolved_round = rnd
                h.confidence = judge.hypothesis_verdict(h)
                changes.append(h)
                nb.log_hypothesis(rnd, h.id, h.status, f"n={h.n_evidence}, pass={h.pass_rate}")
                events.append({"type": h.status, "text": f"{h.id} {h.status} (n = {h.n_evidence})"})
            if h.status in ("supported", "falsified", "qualified") or h.id in {x.id for x in changes}:
                updates.append({"id": h.id, "status": h.status, "n_evidence": h.n_evidence,
                                "pass_rate": None if h.pass_rate is None else round(h.pass_rate, 2),
                                "changed_now": h in changes})
        seen_flags = {r["prop"] for r in c.st["relaxations"]}
        for h in changes:
            if h.origin == "literature" and h.status in ("falsified", "qualified") and h.prop not in seen_flags:
                c.st["relaxations"].append({"prop": h.prop, "n_obs": len(c.obs), "after": h.id})
                seen_flags.add(h.prop)
                what = "stability" if h.prop == "lt" else "bandgap"
                relax.append({"prop": what, "after_hypothesis": h.id, "status": h.status})
                events.append({"type": "revision", "text": f"Literature {what} prior relaxed after {h.id} was {h.status}"})
        c._fit_surrogate()
        c.st["unanalysed"] = []
        nb.commit()
        nb.db.close()
        c.save()
        out = {"round": rnd, "findings": findings, "surprises": surprises, "events": events,
               "hypothesis_updates": updates, "prior_relaxations": relax,
               "refuted": [h.id for h in changes if h.status == "falsified"],
               "open_anomalies_for_generator": [{k: a[k] for k in ("exp_id", "formula", "prop", "z", "display", "prior_display")}
                                                for a in c.st["open_anomalies"]],
               "adapt_triggers": bool(relax or any(h.status in ("falsified", "qualified") for h in changes))}
        out["record_id"] = c.record("analysis", {k: out[k] for k in ("findings", "surprises", "events", "hypothesis_updates",
                                                                       "prior_relaxations", "refuted", "adapt_triggers")})
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_judge() -> dict:
    """Rubric verdicts: discovery verdicts (replicated?) and confidence for resolved hypotheses."""
    try:
        c = Ctx()
        judge = JudgeAgent()
        changed = _discovery_refresh(c)
        hv = []
        for h in c.hyps.values():
            if h.status in ("supported", "falsified", "qualified"):
                h.confidence = judge.hypothesis_verdict(h)
                hv.append({"id": h.id, "status": h.status, "confidence": h.confidence, "n_evidence": h.n_evidence})
        c.save()
        disc = [{"formula": d["formula"], "status": d["status"], "confidence": d["confidence"], "reason": d["reason"],
                 "n_films": d["n"], "replicated": d["status"] == "confirmed", "eg": d["eg"], "t80_h": d["t80_h"]}
                for d in c.st["discoveries"].values()]
        out = {"discovery_verdicts": disc, "newly_changed": [d["formula"] for d in changed], "hypothesis_verdicts": hv}
        out["record_id"] = c.record("judge_verdict", out)
        return _clean(out)
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


def ll_status() -> dict:
    """Read-only progress: round, units, budget left, tested count, measured hits, discoveries, open hypotheses."""
    try:
        c = Ctx()
        hits = sorted({o["formula"] for o in c.obs if o["ok"] and is_hit(o["eg"], o["lt"])})
        recent = [{"composition": e["formula"], "ok": e["result"]["ok"], "bandgap_ev": e["result"]["bandgap_ev"],
                   "t80_h": e["result"]["t80_h"], "round": e["round"]} for e in c.st["experiments"][-10:]]
        return _clean({
            "round": c.st["round"], "units_used": c.st["units_used"], "budget": c.st["budget"],
            "budget_left": c.units_left, "n_tested": int(c.tested.sum()), "n_films_run": len(c.obs),
            "measured_hits": hits, "discoveries": list(c.st["discoveries"].values()),
            "open_hypotheses": [_hyp_view(c, h) for h in c.hyps.values() if h.status in ("proposed", "testing")],
            "resolved_hypotheses": [{"id": h.id, "status": h.status} for h in c.hyps.values()
                                    if h.status in ("supported", "falsified", "qualified")],
            "open_anomalies": [{k: a[k] for k in ("exp_id", "formula", "prop", "z", "display", "prior_display")}
                               for a in c.st["open_anomalies"]],
            "recent_results": recent, "unanalysed_films": len(c.st["unanalysed"])})
    except (LabLoopToolError, KeyError, ValueError) as e:
        return _err(e)


# --------------------------------------------------------------------------- Omnigent policies
_ALLOW = {"result": "ALLOW"}
_UNITS_KEY = "_ll_units_requested"


def ll_budget(limit: float = 60.0):
    """DENY ll_run once the session has requested `limit` LabLoop units. Coarse backstop (counts the 1.0 minimum
    film cost per requested slot); ll_run itself enforces the exact 1.0/1.5 per-film charge."""
    def evaluate(event):
        if event.get("type") != "tool_call" or event.get("target") != "ll_run":
            return _ALLOW
        used = float((event.get("session_state") or {}).get(_UNITS_KEY, 0.0))
        args = (event.get("data") or {}).get("arguments") or {}
        n = len(args.get("slot_ids") or [])
        if used + n > limit:
            return {"result": "DENY", "reason": f"LabLoop budget {limit:g} units exhausted ({used:g} requested)"}
        return {"result": "ALLOW", "state_updates": [{"key": _UNITS_KEY, "action": "set", "value": used + n}]}
    return evaluate


def ll_safety_gate(event):
    """Hard gate: DENY ll_design / ll_pi_decide calls whose arguments name a flagged hazard route."""
    if event.get("type") != "tool_call" or event.get("target") not in ("ll_design", "ll_pi_decide", "ll_run"):
        return _ALLOW
    blob = json.dumps((event.get("data") or {}).get("arguments") or {}, default=str).lower()
    hit = [t for t in HAZARD_TERMS if t in blob]
    if hit:
        return {"result": "DENY", "reason": f"safety gate: flagged hazard {hit[0]!r} in LabLoop request"}
    return _ALLOW


def ll_human_approval(event):
    """ASK (human approval) for ll_design requests with a dopant (restricted-element check), scale-up above
    LabLoop's 5 mmol limit, or an explicit human_approved override."""
    if event.get("type") != "tool_call" or event.get("target") != "ll_design":
        return _ALLOW
    args = (event.get("data") or {}).get("arguments") or {}
    for s in args.get("slots") or []:
        if not isinstance(s, dict):
            continue
        try:
            scale = float(s.get("conc_m", 1.2)) > SCALE_ASK_CONC_M
        except (TypeError, ValueError):
            scale = True
        if s.get("dopant") or scale or s.get("human_approved"):
            return {"result": "ASK", "reason": "restricted element, scale-up or approval override requested: "
                    "human sign-off required before design"}
    return _ALLOW
