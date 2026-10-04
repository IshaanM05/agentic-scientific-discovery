"""The closed loop: PI -> Literature -> Hypothesis arena -> Designer(BO) -> Lab -> Analyst -> Judge -> Notebook.

``run_campaign`` returns a full JSON-serialisable trace that the dashboard replays.
Flags let the benchmark switch components off for ablations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

from . import literature
from .chemistry import (
    LOG_T80_MIN, TARGET, composition_space, set_world, figure_of_merit, is_hit, space_arrays,
    sq_efficiency,
)
from .hypotheses import (
    DIMS, Arena, Hypothesis, critique, describe_region, evaluate, in_region,
    literature_hypotheses, region_mask,
)
from .lab import PerovskiteReplayLab, make_protocol, safety_review
from .llm import HYPOTHESIS_SYSTEM, LLM, PI_SYSTEM
from .notebook import Notebook
from .surrogate import Surrogate

LABEL = {"cs": "Cs", "fa": "FA", "ma": "MA", "sn": "Sn", "br": "Br", "cl": "Cl"}

GOAL = ("Find a stable, lead-reduced perovskite absorber for single-junction solar cells: "
        f"bandgap {TARGET['eg_min']}–{TARGET['eg_max']} eV with T80 ≥ {TARGET['t80_min_hours']:.0f} h.")


@dataclass
class Config:
    seed: int = 7
    budget: float = 60.0
    batch: int = 5
    target_discoveries: int = 4
    use_prior: bool = True
    use_bo: bool = True
    use_arena: bool = True
    use_failures: bool = True
    use_replication: bool = True
    record_maps: bool = True
    label: str = "LabLoop (full)"
    world: int = 0  # 0 = demo landscape; other ids draw unseen hidden physics


# --------------------------------------------------------------------------- agents

class AnalystAgent:
    """Turns raw results into findings; flags surprises against the current belief."""

    def analyse(self, exp: dict, sur: Surrogate) -> dict:
        r = exp["result"]
        i = exp["idx"]
        if not r["ok"]:
            pred_lt = sur.mu_lt[i]
            return {"finding": f"Negative result: {r['phase']}. Model expected T80 ≈ {10 ** pred_lt:.0f} h.",
                    "z_eg": 0.0, "z_lt": 0.0, "surprise": 0.0}
        z_eg = (r["bandgap_ev"] - sur.mu_eg[i]) / math.sqrt(sur.sd_eg[i] ** 2 + 0.02 ** 2)
        z_lt = (r["log_t80"] - sur.mu_lt[i]) / math.sqrt(sur.sd_lt[i] ** 2 + 0.12 ** 2)
        hit = is_hit(r["bandgap_ev"], r["log_t80"])
        parts = [f"Eg {r['bandgap_ev']:.3f} eV (pred {sur.mu_eg[i]:.2f}±{sur.sd_eg[i]:.2f})",
                 f"T80 {10 ** r['log_t80']:.0f} h (pred {10 ** sur.mu_lt[i]:.0f} h)"]
        if hit:
            parts.append("meets full spec")
        return {"finding": "; ".join(parts), "z_eg": round(float(z_eg), 2),
                "z_lt": round(float(z_lt), 2), "surprise": round(float(max(abs(z_eg), abs(z_lt))), 2)}


class HypothesisAgent:
    """Generates new hypotheses from anomalies (rule-based) or via the LLM."""

    def __init__(self, llm: LLM):
        self.llm = llm
        self.counter = 6

    def _next_id(self) -> str:
        self.counter += 1
        return f"H{self.counter}"

    def from_anomaly(self, anomaly: dict, observations: list[dict], rnd: int) -> list[Hypothesis]:
        llm_h = self._llm_hypotheses(anomaly, observations, rnd)
        if llm_h:
            return llm_h
        c = anomaly["comp"]
        prop = anomaly["prop"]
        _, eg_prior, lt_prior, *_ = space_arrays()
        prior = eg_prior if prop == "eg" else lt_prior
        ok = [o for o in observations if o["ok"]]
        resid = np.array([o[prop] - prior[o["idx"]] for o in ok])
        F = np.array([[getattr(o["comp"], d) for d in DIMS] for o in ok])
        # driver = composition dimension most correlated with the residual near the anomaly
        near = np.array([abs(o["comp"].sn - c.sn) <= 0.3 for o in ok])
        # Sn's stability penalty is already in the prior, so for stability look for what modulates it
        candidates = [d for d in DIMS if not (prop == "lt" and d == "sn") and getattr(c, d) > 0]
        driver, best = None, 0.0
        if near.sum() >= 4:
            # multivariate (ridge) attribution: separates co-varying axes like Cs vs FA
            cols = [j for j, d in enumerate(DIMS) if F[near, j].std() > 1e-6]
            if cols:
                Z = F[near][:, cols]
                Z = (Z - Z.mean(0)) / Z.std(0)
                yv = resid[near] - resid[near].mean()
                w = np.linalg.solve(Z.T @ Z + 1.0 * np.eye(len(cols)), Z.T @ yv)
                sign = 1 if anomaly["residual"] > 0 else -1
                for k, j in enumerate(cols):
                    d = DIMS[j]
                    if d in candidates and sign * w[k] > best:
                        driver, best = d, float(sign * w[k])
        if driver is None:  # fall back to nearest non-anomalous neighbour
            others = [o for o in ok if o["key"] != anomaly["key"]]
            driver = None
            if others and candidates:
                nb = min(others, key=lambda o: sum((getattr(o["comp"], d) - getattr(c, d)) ** 2 for d in DIMS))
                driver = max(candidates, key=lambda d: abs(getattr(nb["comp"], d) - getattr(c, d)))
            if driver is None:
                driver = "sn"
        v = getattr(c, driver)
        sn_lo, sn_hi = max(0.0, round(c.sn - 0.2, 1)), min(1.0, round(c.sn + 0.2, 1))
        lo, hi = (max(0.0, round(v - 0.1, 2)), min(1.0, round(v + 0.15, 2))) if v > 0 else (0.0, 0.0)
        direction = "raises" if anomaly["residual"] > 0 else "lowers"
        pname = "stability" if prop == "lt" else "bandgap"
        out = []
        if prop == "lt":
            value = min(LOG_T80_MIN, anomaly["value"] - 0.25) if anomaly["residual"] > 0 else anomaly["value"] + 0.3
            op = ">" if anomaly["residual"] > 0 else "<"
        else:
            value = round(anomaly["predicted"] - 0.08, 2) if anomaly["residual"] < 0 else round(anomaly["predicted"] + 0.08, 2)
            op = "<" if anomaly["residual"] < 0 else ">"
        if driver == "sn":
            lo, hi = sn_lo, sn_hi
        # hold the other halide/cation axes near the anomaly so the test isolates the driver
        base = {"sn": (sn_lo, sn_hi), "br": (max(0.0, round(c.br - 0.1, 1)), min(1.0, round(c.br + 0.1, 1)))}
        if driver != "fa" and c.fa >= 0.6:
            base["fa"] = (0.6, 1.0)
        region = {**base, driver: (lo, hi)}
        out.append(Hypothesis(
            self._next_id(),
            (f"Sn content near {v:g} {direction} the bandgap beyond the linear-mixing expectation." if driver == "sn" else
             f"{LABEL[driver]} content near {v:g} {direction} {pname} in Sn {sn_lo:g}–{sn_hi:g} films beyond literature expectation."),
            region, prop, op, value, origin="data", sources=[anomaly["exp_id"]],
            rationale=(f"{anomaly['formula']} measured {anomaly['display']} vs prior {anomaly['prior_display']} "
                       f"(z = {anomaly['z']:.1f}); ridge attribution points to {LABEL[driver]} (weight {best:.2f})."),
            created_round=rnd))
        if v > 0 and prop == "lt" and driver != "sn":
            out.append(Hypothesis(
                self._next_id(),
                f"In Sn {sn_lo:g}–{sn_hi:g} films, adding {LABEL[driver]} (≥{max(lo, 0.05):g}) {direction} T80 by more than 2×.",
                {**base, driver: (max(lo, 0.05), 1.0)}, "lt", "contrast", 0.25,
                region_b={**{k: v for k, v in base.items() if k != "fa"}, driver: (0.0, max(lo - 0.1, 0.0))},
                origin="data", sources=[anomaly["exp_id"]],
                rationale="Contrast test isolates the driver from Sn content.", created_round=rnd))
        return out

    def _llm_hypotheses(self, anomaly, observations, rnd) -> list[Hypothesis]:
        if not self.llm.available:
            return []
        recent = [{"formula": o["formula"], "ok": o["ok"], "eg": o.get("eg"), "t80_h": None if not o["ok"] else round(10 ** o["lt"])}
                  for o in observations[-20:]]
        prompt = (f"Literature: {[c['claim'] for c in literature.CLAIMS]}\n"
                  f"Recent results: {recent}\nAnomaly: {anomaly['formula']} measured {anomaly['display']} "
                  f"vs prior {anomaly['prior_display']}. Propose 2 hypotheses that explain it.")
        data = self.llm.json(HYPOTHESIS_SYSTEM, prompt)
        out = []
        for h in data if isinstance(data, list) else []:
            try:
                region = {k: (float(v[0]), float(v[1])) for k, v in h["region"].items() if k in DIMS}
                if not region or h["prop"] not in ("eg", "lt") or h["op"] not in ("<", ">"):
                    continue
                if region_mask(region).mean() > 0.35:
                    continue
                out.append(Hypothesis(self._next_id(), str(h["statement"])[:220], region, h["prop"], h["op"],
                                      float(h["value"]), origin="llm", sources=[anomaly["exp_id"]],
                                      rationale=str(h.get("rationale", ""))[:300], created_round=rnd))
            except (KeyError, TypeError, ValueError, IndexError):
                continue
        return out


class DesignerAgent:
    """LLM/hypotheses constrain the pool; the acquisition function picks the films."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng
        self.X = space_arrays()[0]

    def _pick(self, score: np.ndarray, allowed: np.ndarray, chosen: list[int]) -> int | None:
        s = np.where(allowed, score, -np.inf)
        for j in chosen:  # diversity: discourage near-duplicates in a batch
            d = np.linalg.norm(self.X - self.X[j], axis=1)
            s = np.where(d < 0.12, -np.inf, s)
        if not np.isfinite(s).any():
            return None
        return int(np.argmax(s))

    def design(self, slots: list[dict], sur: Surrogate, tested: np.ndarray, hyps: dict) -> list[dict]:
        p = sur.p_hit()
        p_opt = sur.p_hit(inflate=2.5)
        u = sur.uncertainty()
        un = u / (u.max() + 1e-9)
        pn = p / (p.max() + 1e-9)
        untested = ~tested
        jitter = self.rng.uniform(0, 1e-3, len(p))
        chosen, out = [], []
        for slot in slots:
            kind = slot["kind"]
            idx = None
            if kind == "replicate":
                idx = slot["idx"]
            elif kind == "test":
                h = hyps[slot["hypothesis"]]
                region = h.region
                if h.op == "contrast":
                    # feed whichever arm has less evidence
                    na = sum(1 for k in np.where(tested)[0] if in_region(composition_space()[k], h.region))
                    nb = sum(1 for k in np.where(tested)[0] if in_region(composition_space()[k], h.region_b))
                    region = h.region if na <= nb else h.region_b
                allowed = untested & region_mask(region)
                idx = self._pick(0.6 * pn + 0.4 * un + jitter, allowed, chosen)
            elif kind == "exploit":
                idx = self._pick(p + 0.02 * un + jitter, untested, chosen)
            elif kind == "explore":
                # optimistic P(hit) under doubled uncertainty: goal-directed exploration
                idx = self._pick(p_opt + jitter, untested, chosen)
            elif kind == "random":
                idx = self._pick(jitter, untested, chosen)
            if idx is None:
                idx = self._pick(p_opt + jitter, untested, chosen)
            if idx is None:
                continue
            chosen.append(idx)
            out.append({**slot, "idx": idx, "p_hit": float(p[idx]),
                        "pred_eg": float(sur.mu_eg[idx]), "pred_lt": float(sur.mu_lt[idx])})
        return out


class JudgeAgent:
    """Rubric verifier: replication, sample size, physical sanity, prediction match."""

    def hypothesis_verdict(self, h: Hypothesis) -> str:
        if h.status not in ("supported", "falsified", "qualified"):
            return "—"
        if h.op == "contrast":
            return "High" if h.n_evidence >= 6 else "Medium"
        if h.status == "qualified":
            return "Medium"
        if h.n_evidence >= 6 and (h.pass_rate >= 0.85 or h.pass_rate <= 0.15):
            return "High"
        if h.n_evidence >= 3:
            return "Medium"
        return "Low"

    def discovery_verdict(self, measurements: list[dict]) -> dict:
        ok = [m for m in measurements if m["ok"]]
        sane = all(0.8 < m["eg"] < 3.6 for m in ok)
        hits = [m for m in ok if is_hit(m["eg"], m["lt"])]
        if not sane:
            return {"status": "rejected", "confidence": "—", "reason": "physically implausible reading"}
        if len(hits) >= 2:
            spread = max(m["eg"] for m in hits) - min(m["eg"] for m in hits)
            return {"status": "confirmed", "confidence": "High" if spread < 0.05 else "Medium",
                    "reason": f"replicated {len(hits)}×, Eg spread {spread * 1000:.0f} meV"}
        if len(hits) == 1 and len(ok) >= 2:
            return {"status": "not reproduced", "confidence": "Low", "reason": "replicate missed spec"}
        return {"status": "candidate", "confidence": "Low", "reason": "single measurement, replication queued"}


class PIAgent:
    """Owns the goal, budget and stopping rule; chooses one strategy per round."""

    def __init__(self, cfg: Config, llm: LLM):
        self.cfg = cfg
        self.llm = llm

    def decide(self, rnd: int, state: dict) -> dict:
        cfg = self.cfg
        slots: list[dict] = []
        reasons = []
        remaining = cfg.budget - state["spent"]
        if state["confirmed"] >= cfg.target_discoveries:
            return {"mode": "stop", "slots": [], "rationale":
                    f"{state['confirmed']} confirmed discoveries meet the goal; stopping to save {remaining:.1f} units of budget."}
        if remaining < 1.0:
            return {"mode": "stop", "slots": [], "rationale": "Budget exhausted. Writing the report with what we have."}
        n = cfg.batch
        if cfg.use_replication:
            for c in state["unconfirmed_hits"][:2]:
                slots.append({"kind": "replicate", "idx": c["idx"], "purpose": f"Replicate candidate {c['formula']}"})
            if slots:
                reasons.append(f"replicate {len(slots)} spec-meeting film(s) before claiming a discovery")
            for a in state["pending_surprises"][:1]:
                if len(slots) < n:
                    slots.append({"kind": "replicate", "idx": a["idx"], "purpose": f"Replicate surprise in {a['formula']}"})
                    reasons.append(f"re-run the surprising {a['formula']} result (z = {a['z']:.1f}) to rule out noise")
        active = state["ranked_hypotheses"]
        best_p = state["best_p_hit"]
        if rnd == 1 and cfg.use_arena:
            mode = "seed"
            for h in active[: n - len(slots)]:
                slots.append({"kind": "test", "hypothesis": h.id, "purpose": f"Test {h.id}: {h.statement}"})
            while len(slots) < n:
                slots.append({"kind": "explore", "purpose": "Probe where a hit is still plausible"})
            reasons.append(f"no data yet, so slots test the goal-relevant literature hypotheses ({', '.join(h.id for h in active[:n]) or 'none'})")
            if state.get("parked"):
                reasons.append(f"{', '.join(state['parked'])} parked because their regions cannot meet the spec")
        elif best_p >= 0.3:
            mode = "exploit"
            if cfg.use_arena and active and len(slots) < n - 1:
                h = active[0]
                slots.append({"kind": "test", "hypothesis": h.id, "purpose": f"Test {h.id}: {h.statement}"})
            while len(slots) < n:
                slots.append({"kind": "exploit", "purpose": "Highest probability of meeting spec"})
            reasons.append(f"model now gives P(hit) up to {best_p:.0%}, so most films go to exploitation")
        else:
            mode = "investigate"
            if cfg.use_arena:
                for h in active[:2]:
                    if len(slots) < n:
                        slots.append({"kind": "test", "hypothesis": h.id, "purpose": f"Test {h.id}: {h.statement}"})
                if active:
                    reasons.append(f"best P(hit) is only {best_p:.0%}; testing {', '.join(h.id for h in active[:2])} to sharpen the model")
            while len(slots) < n:
                slots.append({"kind": "explore", "purpose": "Reduce model uncertainty where hits are plausible"})
            if not cfg.use_arena:
                reasons.append("exploring where the model is uncertain")
        if not reasons:
            reasons.append("no open hypotheses worth a film; exploring where a hit is still plausible")
        rationale = "; ".join(reasons)
        rationale = rationale[0].upper() + rationale[1:] + "."
        if self.llm.available and rnd <= 12:
            data = self.llm.json(PI_SYSTEM, f"Round {rnd}. Mode {mode}. Facts: {rationale} Budget left {remaining:.1f}.")
            if isinstance(data, dict) and isinstance(data.get("rationale"), str):
                rationale = data["rationale"][:400]
        return {"mode": mode, "slots": slots[:n], "rationale": rationale}


# --------------------------------------------------------------------------- campaign

def _comp_display(prop, v):
    return f"Eg {v:.2f} eV" if prop == "eg" else f"T80 {10 ** v:.0f} h"


def _admit(h: Hypothesis, hyps: dict) -> bool:
    """Proximity check: drop near-duplicates of an existing hypothesis."""
    m = region_mask(h.region)
    for o in hyps.values():
        if o.prop != h.prop or o.op != h.op or (o.region_b is None) != (h.region_b is None):
            continue
        om = region_mask(o.region)
        inter = (m & om).sum()
        union = (m | om).sum()
        if union and inter / union > 0.4:
            return False
    return True


def _strongest_counterexample(h: Hypothesis, observations: list[dict]) -> dict | None:
    if h.op not in ("<", ">"):
        return None
    _, eg_prior, lt_prior, *_ = space_arrays()
    prior = lt_prior if h.prop == "lt" else eg_prior
    best = None
    for o in observations:
        if not o["ok"] or not in_region(o["comp"], h.region) or h.check(o[h.prop]):
            continue
        resid = o[h.prop] - prior[o["idx"]]
        if best is None or abs(resid) > abs(best["residual"]):
            best = {"idx": o["idx"], "key": o["key"], "formula": o["formula"], "comp": o["comp"],
                    "prop": h.prop, "z": resid / (0.4 if h.prop == "lt" else 0.08), "value": o[h.prop],
                    "predicted": float(prior[o["idx"]]), "residual": float(resid), "exp_id": o["exp_id"],
                    "display": _comp_display(h.prop, o[h.prop]), "prior_display": _comp_display(h.prop, prior[o["idx"]])}
    return best


def run_campaign(cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    world = set_world(cfg.world)
    rng = np.random.default_rng(cfg.seed)
    llm = LLM()
    lab = PerovskiteReplayLab(seed=cfg.seed)
    nb = Notebook()
    space = composition_space()
    _, _, _, eg_true, lt_true, true_hits = space_arrays()
    sur = Surrogate(use_prior=cfg.use_prior, use_failures=cfg.use_failures)
    arena = Arena(rng)
    hyp_agent = HypothesisAgent(llm)
    designer = DesignerAgent(rng)
    analyst = AnalystAgent()
    judge = JudgeAgent()
    pi = PIAgent(cfg, llm)

    hyps = {h.id: h for h in (literature_hypotheses() if cfg.use_arena else [])}
    observations: list[dict] = []
    tested = np.zeros(len(space), dtype=bool)
    measurements: dict[int, list[dict]] = {}
    discoveries: dict[int, dict] = {}
    pending_surprises: list[dict] = []
    seen_surprises: set = set()
    spent = 0.0
    exp_counter = 0
    clock_h = 0.0
    rounds = []
    curve = []
    found_true = set()

    for rnd in range(1, 40):
        p = sur.p_hit()
        untested = ~tested
        if cfg.use_arena:
            for h in hyps.values():
                h.critiques = critique(h, untested, list(hyps.values()))
            arena.run(list(hyps.values()), p, untested, n_matches=12, rnd=rnd)
        # goal-relevance gate: only fund tests of hypotheses whose region could still contain a hit
        p_opt = sur.p_hit(inflate=2.5)
        gmax = float(p_opt[untested].max()) if untested.any() else 0.0
        def relevant(h):
            m = region_mask(h.region) | (region_mask(h.region_b) if h.region_b else False)
            sel = p_opt[m & untested]
            return sel.size > 0 and float(sel.max()) >= 0.25 * gmax
        ranked = sorted([h for h in hyps.values() if h.status in ("proposed", "testing")
                         and not any(c.startswith("Not testable") for c in h.critiques) and relevant(h)],
                        key=lambda h: -h.elo)
        parked = [h.id for h in hyps.values() if h.status in ("proposed", "testing") and h not in ranked]
        unconfirmed = [{"idx": i, "formula": space[i].formula()} for i, d in discoveries.items()
                       if d["status"] == "candidate"]
        state = {
            "spent": spent, "confirmed": sum(d["status"] == "confirmed" for d in discoveries.values()),
            "unconfirmed_hits": unconfirmed, "pending_surprises": pending_surprises,
            "ranked_hypotheses": ranked, "parked": parked, "best_p_hit": float(p[untested].max()) if untested.any() else 0.0,
        }
        decision = pi.decide(rnd, state)
        nb.log_decision(rnd, decision["mode"], decision["rationale"], [s["purpose"] for s in decision["slots"]])
        if decision["mode"] == "stop":
            rounds.append({"round": rnd, "decision": decision, "experiments": [], "events": [],
                           "hypotheses": [h.as_dict() for h in hyps.values()], "spent": spent,
                           "p_map": None})
            break

        plan = designer.design(decision["slots"], sur if cfg.use_bo or cfg.use_prior else sur, tested, hyps)
        replicated_now = set()
        exps, events = [], []
        # two synthesis stations run in parallel; agents keep working meanwhile
        station_free = [clock_h, clock_h]
        for slot in plan:
            if spent >= cfg.budget:
                break
            c = space[slot["idx"]]
            proto = make_protocol(c, purpose=slot["purpose"])
            safety = safety_review(proto)
            if not safety["approved"]:
                events.append({"type": "safety", "text": f"Blocked {c.formula()}: {safety['reason']}"})
                continue
            res = lab.run(proto)
            spent += res.cost
            exp_counter += 1
            st = int(np.argmin(station_free))
            start = station_free[st]
            station_free[st] = start + res.duration_h
            obs = {"idx": slot["idx"], "key": c.key, "comp": c, "formula": c.formula(), "ok": res.ok,
                   "eg": res.bandgap_ev, "lt": res.log_t80, "round": rnd}
            exp = {
                "id": f"E{exp_counter:03d}", "idx": slot["idx"], "key": c.key, "formula": c.formula(),
                "comp": c.as_dict(), "kind": slot["kind"], "purpose": slot["purpose"],
                "hypothesis": slot.get("hypothesis"), "protocol": proto.as_dict(), "safety": safety,
                "result": res.as_dict(), "predicted": {"eg": round(slot["pred_eg"], 3),
                                                       "t80_h": round(10 ** slot["pred_lt"]),
                                                       "p_hit": round(slot["p_hit"], 3)},
                "station": st + 1, "start_h": round(start, 1), "end_h": round(start + res.duration_h, 1),
                "true_hit": bool(true_hits[slot["idx"]]),
            }
            analysis = analyst.analyse(exp, sur)
            exp.update(analysis)
            obs["exp_id"] = exp["id"]
            observations.append(obs)
            measurements.setdefault(slot["idx"], []).append(obs)
            if tested[slot["idx"]]:
                replicated_now.add(slot["idx"])
            tested[slot["idx"]] = True
            if true_hits[slot["idx"]]:
                found_true.add(slot["idx"])
            exp["hit"] = bool(res.ok and is_hit(res.bandgap_ev, res.log_t80))
            exps.append(exp)
            nb.log_experiment(rnd, {**exp, "surprise": analysis["surprise"]})
            curve.append({"n": exp_counter, "spent": round(spent, 2), "true_hits": len(found_true)})

        # Analyst: surprise detection (only first measurements create new surprises)
        new_hyps = []
        resolved_surprise = {a["idx"] for a in pending_surprises if a["idx"] in replicated_now}
        for a in [a for a in pending_surprises if a["idx"] in resolved_surprise]:
            ms = [m for m in measurements[a["idx"]] if m["ok"]]
            reproduced = len(ms) >= 2 and abs(ms[-1][a["prop"]] - ms[0][a["prop"]]) < (0.06 if a["prop"] == "eg" else 0.3)
            events.append({"type": "replication", "text": f"{a['formula']}: surprise {'reproduced' if reproduced else 'not reproduced'}"})
            if reproduced and cfg.use_arena:
                for h in hyp_agent.from_anomaly(a, observations, rnd):
                    if _admit(h, hyps):
                        hyps[h.id] = h
                        new_hyps.append(h.id)
                        nb.log_hypothesis(rnd, h.id, "proposed", h.statement)
                        events.append({"type": "proposed", "text": f"{h.id} proposed from {a['formula']}: {h.statement}"})
        pending_surprises = [a for a in pending_surprises if a["idx"] not in resolved_surprise]
        for e in exps:
            if not e["result"]["ok"]:
                continue
            r = e["result"]
            # only goal-relevant surprises earn a replicate: near the bandgap window and not dead films
            near_window = TARGET["eg_min"] - 0.2 <= r["bandgap_ev"] <= TARGET["eg_max"] + 0.2
            for prop, z in (("lt", e["z_lt"]), ("eg", e["z_eg"])):
                relevant = near_window and (prop == "eg" or r["log_t80"] >= 2.0)
                if (e["idx"], prop) in seen_surprises or not relevant:
                    continue
                if abs(z) >= 2.0 and len(pending_surprises) < 3:
                    seen_surprises.add((e["idx"], prop))
                    val = e["result"]["log_t80"] if prop == "lt" else e["result"]["bandgap_ev"]
                    prior = (space_arrays()[2] if prop == "lt" else space_arrays()[1])[e["idx"]]
                    a = {"idx": e["idx"], "key": e["key"], "formula": e["formula"], "comp": space[e["idx"]],
                         "prop": prop, "z": z, "value": val, "predicted": float(prior),
                         "residual": float(val - prior), "exp_id": e["id"],
                         "display": _comp_display(prop, val), "prior_display": _comp_display(prop, prior)}
                    if not cfg.use_replication and cfg.use_arena:
                        for h in hyp_agent.from_anomaly(a, observations, rnd):
                            if _admit(h, hyps):
                                hyps[h.id] = h
                                new_hyps.append(h.id)
                    else:
                        pending_surprises.append(a)
                    e["flag"] = f"surprise in {'stability' if prop == 'lt' else 'bandgap'} (z = {z:+.1f})"
                    events.append({"type": "surprise", "text": f"{e['formula']}: {e['flag']}"})
                    break

        # Hypothesis evaluation + judge
        status_changes = []
        for h in list(hyps.values()):
            before = h.status
            evaluate(h, observations)
            if h.status != before and h.status == "qualified" and cfg.use_arena:
                # counterexamples to a partly-true law are the most informative data we have
                ex = _strongest_counterexample(h, observations)
                if ex is not None:
                    events.append({"type": "qualified", "text": f"{h.id} holds with exceptions; strongest counterexample {ex['formula']} ({ex['display']} vs prior {ex['prior_display']})"})
                    for nh in hyp_agent.from_anomaly(ex, observations, rnd):
                        if _admit(nh, hyps):
                            hyps[nh.id] = nh
                            new_hyps.append(nh.id)
                            nb.log_hypothesis(rnd, nh.id, "proposed", nh.statement)
                            events.append({"type": "proposed", "text": f"{nh.id} proposed from counterexample: {nh.statement}"})
            if h.status != before and h.status in ("supported", "falsified", "qualified"):
                h.resolved_round = rnd
                h.confidence = judge.hypothesis_verdict(h)
                status_changes.append({"id": h.id, "status": h.status, "confidence": h.confidence})
                nb.log_hypothesis(rnd, h.id, h.status, f"n={h.n_evidence}, pass={h.pass_rate}")
                events.append({"type": h.status, "text": f"{h.id} {h.status} (n = {h.n_evidence}, judge: {h.confidence})"})
            elif h.status in ("supported", "falsified", "qualified"):
                h.confidence = judge.hypothesis_verdict(h)
        # Discoveries
        for e in exps:
            i = e["idx"]
            ms = measurements[i]
            if any(m["ok"] and is_hit(m["eg"], m["lt"]) for m in ms) or i in discoveries:
                prev = discoveries.get(i, {}).get("status")
                v = judge.discovery_verdict(ms) if cfg.use_replication else (
                    {"status": "confirmed", "confidence": "Low", "reason": "single measurement"} if any(m["ok"] and is_hit(m["eg"], m["lt"]) for m in ms) else {"status": "candidate"})
                ok_ms = [m for m in ms if m["ok"]]
                discoveries[i] = {**v, "idx": i, "formula": space[i].formula(), "round": rnd,
                                  "eg": round(float(np.mean([m["eg"] for m in ok_ms])), 3) if ok_ms else None,
                                  "t80_h": round(float(10 ** np.mean([m["lt"] for m in ok_ms]))) if ok_ms else None,
                                  "n": len(ms), "true_hit": bool(true_hits[i]),
                                  "sq_limit": round(sq_efficiency(float(np.mean([m["eg"] for m in ok_ms]))), 1) if ok_ms else None}
                if v["status"] != prev and v["status"] in ("confirmed", "not reproduced"):
                    events.append({"type": "discovery" if v["status"] == "confirmed" else "rejected",
                                   "text": f"{space[i].formula()}: {v['status']} ({v['reason']})"})

        # Belief revision: a literature claim that failed in our lab loosens that part of the prior
        if cfg.use_prior and cfg.use_bo:
            for ch in status_changes:
                h = hyps[ch["id"]]
                if h.origin == "literature" and ch["status"] in ("falsified", "qualified"):
                    flag = "relaxed_lt" if h.prop == "lt" else "relaxed_eg"
                    if not getattr(sur, flag):
                        sur.relax_prior(h.prop, observations)
                        what = "stability" if h.prop == "lt" else "bandgap"
                        events.append({"type": "revision", "text": f"Literature {what} prior relaxed after {h.id} was {ch['status']}; trusting lab data over textbook rules"})
        if cfg.use_bo:
            sur.fit(observations)
        p_after = sur.p_hit()
        # simulated async agent work while films were in the lab
        t0, t1 = clock_h, max(station_free)
        agent_tasks = [
            {"agent": "Analyst", "task": "fit GP to new spectra and stability curves", "start_h": round(t0 + 0.2 * (t1 - t0), 1)},
            {"agent": "Ranker", "task": f"{len([m for m in arena.matches if m['round'] == rnd])} Elo matches", "start_h": round(t0 + 0.05 * (t1 - t0), 1)},
            {"agent": "Critic", "task": "re-check hypotheses against new evidence", "start_h": round(t0 + 0.5 * (t1 - t0), 1)},
            {"agent": "Literature", "task": "re-query claims for flagged anomalies", "start_h": round(t0 + 0.7 * (t1 - t0), 1)},
        ]
        clock_h = t1
        top_idx = np.argsort(-p_after)[:8]
        rounds.append({
            "round": rnd, "decision": decision, "experiments": exps, "events": events,
            "new_hypotheses": new_hyps, "status_changes": status_changes,
            "hypotheses": [h.as_dict() for h in hyps.values()],
            "discoveries": sorted(discoveries.values(), key=lambda d: d["round"]),
            "spent": round(spent, 2), "clock_h": round(clock_h, 1), "agent_tasks": agent_tasks,
            "belief_top": [{"formula": space[i].formula(), "p_hit": round(float(p_after[i]), 3),
                            "eg": round(float(sur.mu_eg[i]), 3), "t80_h": round(float(10 ** sur.mu_lt[i])),
                            "tested": bool(tested[i])} for i in top_idx],
            "p_map": [round(float(x), 2) for x in p_after] if cfg.record_maps else None,
        })
        nb.commit()
        if spent >= cfg.budget:
            rounds.append({"round": rnd + 1, "decision": {"mode": "stop", "slots": [], "rationale": "Budget exhausted. Writing the report."},
                           "experiments": [], "events": [], "hypotheses": [h.as_dict() for h in hyps.values()],
                           "spent": spent, "p_map": None})
            break

    confirmed = [d for d in discoveries.values() if d["status"] == "confirmed"]
    return {
        "config": cfg.__dict__, "world": {"id": world["id"], "description": world["description"]}, "goal": GOAL, "target": TARGET, "backend": llm.name, "llm_calls": llm.calls,
        "rounds": rounds, "curve": curve, "arena": arena.matches,
        "summary": {
            "experiments": exp_counter, "spent": round(spent, 2), "confirmed": len(confirmed),
            "true_hits_found": len(found_true), "true_hits_total": int(true_hits.sum()),
            "negative_results": len(nb.negative_results()), "hypotheses": len(hyps),
            "supported": sum(h.status == "supported" for h in hyps.values()),
            "falsified": sum(h.status == "falsified" for h in hyps.values()),
            "clock_h": round(clock_h, 1),
        },
    }
