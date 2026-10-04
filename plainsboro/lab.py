"""The Princeton-Plainsboro lab: one discovery loop per target.

Question -> Evidence -> Hypothesis -> Experiment -> Result -> Updated decision,
repeated until Cuddy's stopping rule fires (design 9).

`Lab.investigate()` is a generator of events (agent messages, planner
rationales, results, posterior updates, approval requests). A UI can step
through it and answer approval requests with `gen.send("approve"|"deny")`;
`Lab.run()` drives it with an automatic approver for batch benchmarking.

Every agent action is a tool call routed through the PolicyEngine (Omnigent
policy semantics) and written to the Run Ledger.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Generator

import numpy as np

from .agents.cameron import Cameron
from .agents.chase import Chase
from .agents.cuddy import Cuddy
from .agents.foreman import Foreman
from .agents.house import House
from .agents.wilson import Wilson
from .config import HYP_IDS, HYP_LABELS, experiment
from .literature import openalex_search
from .planner.posterior import update
from .policies import PolicyEngine, default_policies
from .record.ledger import Ledger
from .record.whiteboard import Whiteboard
from .schemas import TestSpec
from .vetting.registry import REGISTRY


def auto_approver(event: dict) -> str:
    """Batch-mode human proxy: deny budget extensions and queue follow-ups (never auto-approve)."""
    return "deny"


class Lab:
    def __init__(self, tables, cfg: dict | None = None, *, name: str = "P", strategy: str = "eig",
                 use_foreman: bool = True, use_house: bool = True, use_cameron: bool = True,
                 exploration_bonus: float | None = None, parallel: bool = True, adaptive: bool = False,
                 threshold: float | None = None, benchmark_mode: bool = True, outcome_cache: dict | None = None,
                 ledger: Ledger | None = None, approver: Callable = auto_approver, live_literature: bool = False,
                 rng_seed: int = 7, n_interval_draws: int = 100, gatekeeper=None, kg_path=None,
                 narrator=None, max_workers: int = 2, research: bool = False):
        self.cfg = cfg or experiment()
        self.name = name
        self.tables = tables.copy() if adaptive else tables
        self.adaptive = adaptive
        self.gatekeeper = gatekeeper
        self.threshold = self.cfg["stopping"]["posterior_threshold"] if threshold is None else threshold
        self.ledger = ledger or Ledger()
        self.approver = approver
        self.policy = PolicyEngine(default_policies(self.cfg, benchmark_mode))
        self.house = House(use_house)
        self.foreman = Foreman(self.cfg, use_foreman)
        self.cameron = Cameron(use_cameron, live_literature)
        self.chase = Chase(outcome_cache)
        self.cuddy = Cuddy(self.cfg, self.tables, strategy, exploration_bonus if use_house else 0.0,
                           parallel, self.threshold, rng_seed)
        self.wilson = Wilson(kg_path)
        self.live_literature = live_literature
        self.n_draws = n_interval_draws
        self.narrator = narrator
        self.research = research  # live LLM literature brief (needs an API key)
        self.max_workers = max_workers
        self.rng = np.random.default_rng(rng_seed)
        self.escalations = 0

    # ------------------------------------------------------------------ plumbing
    def _msg(self, agent: str, text: str, target_id: str, kind: str = "message", **payload) -> dict:
        if self.narrator is not None and kind == "message" and agent in ("house", "foreman", "cuddy", "cameron"):
            text = self.narrator.voice(agent, text)
        ev = {"kind": kind, "agent": agent, "text": text, "target_id": target_id, **payload}
        self.ledger.log(agent, kind, target_id, outputs={"text": text, **{k: v for k, v in payload.items()
                                                                          if k != "figure"}})
        return ev

    def _tool(self, actor: str, tool: str, args: dict, target_id: str) -> Generator:
        """Policy-checked tool call. Yields an approval request on ASK; returns (allowed, decision)."""
        dec = self.policy.evaluate(actor, tool, args)
        pol = {"result": dec["result"], "reasons": dec["reasons"], "evaluated": dec["evaluated"]}
        if dec["result"] == "DENY":
            self.ledger.log(actor, f"tool_call:{tool}", target_id, inputs=args, policy=pol, outcome="denied")
            yield self._msg("safety", f"DENIED {actor} -> {tool}: {' '.join(dec['reasons'])}", target_id,
                            kind="policy", tool=tool, decision="DENY")
            return False, dec
        if dec["result"] == "ASK":
            self.escalations += 1
            req = self._msg("safety", f"Approval needed for {actor} -> {tool}: {' '.join(dec['reasons'])}",
                            target_id, kind="approval", tool=tool, args=args, reasons=dec["reasons"])
            answer = yield req
            if answer is None:
                answer = self.approver(req)
            approved = answer in ("approve", "approved", True)
            self.ledger.log("human", "approval_decision", target_id, inputs={"tool": tool, "args": args},
                            outputs={"decision": "approved" if approved else "denied"}, policy=pol)
            yield self._msg("human", f"Scientist {'APPROVED' if approved else 'DENIED'} {tool}.", target_id,
                            kind="policy", tool=tool, decision="APPROVED" if approved else "DENIED_BY_HUMAN")
            if not approved:
                return False, dec
        self.policy.apply(dec["state_updates"])
        self.ledger.log(actor, f"tool_call:{tool}", target_id, inputs=args, policy=pol, outcome="allowed",
                        cost_units=float(args.get("cost_units", 0) or 0))
        return True, dec

    def _interval(self, wb) -> tuple[float, float]:
        """Credible interval on the top class: Dirichlet bootstrap over the likelihood tables."""
        label = HYP_IDS.index(wb.leader())
        runs = [(t["test_id"], t["outcome_bin"], t["weight"]) for t in wb.tests_run if t["outcome_bin"] >= 0]
        if self.n_draws <= 0:
            return (0.0, 1.0)
        logp = np.tile(np.log(self.tables.prior()), (self.n_draws, 1))
        for tid, b, w in runs:
            lik = self.tables.sample_likelihoods(tid, b, self.n_draws, self.rng)
            logp += w * self.tables.temper * np.log(lik)
        logp -= np.logaddexp.reduce(logp, axis=1, keepdims=True)
        vals = np.exp(logp[:, label])
        return (round(float(np.percentile(vals, 5)), 4), round(float(np.percentile(vals, 95)), 4))

    def _add_critique(self, wb, text: str, test_id: str, permanent: bool = False):
        wb.open_critiques.append({"id": f"C{len(wb.open_critiques) + 1}", "text": text, "test_id": test_id,
                                  "permanent": permanent})

    def _research(self, wb, tid: str, leader: str, contrarian: str) -> Generator:
        """Cameron researches leader vs contrarian live: arXiv + OpenAlex, then an LLM reads the abstracts."""
        from . import research
        q = research.queries(leader, contrarian)[1]
        ok, _ = yield from self._tool("cameron", "literature_search", {"query": q, "target_id": tid}, tid)
        if not ok:
            return
        _, papers = research.gather(leader, contrarian)
        try:
            b = research.brief(leader, contrarian, papers)
        except Exception as exc:  # a failed LLM call is reported, never hidden
            b = {"text": f"LLM brief failed ({type(exc).__name__}: {str(exc)[:200]}). Papers listed unread.",
                 "model": None, "cited": [], "stripped": []}
        wb.evidence.extend({"id": f"LIT-{p['id']}", "source_id": p["id"], "title": p["title"], "url": p["url"],
                            "role": "context"} for p in papers if p["id"] in b["cited"])
        yield self._msg("cameron", f"Live research: {HYP_LABELS[leader]} vs {HYP_LABELS[contrarian]}. Read "
                                   f"{len(papers)} papers via {b['model'] or 'no LLM'}; cited {len(b['cited'])}.",
                        tid, kind="research", query=q, papers=papers, brief=b, leader=leader, contrarian=contrarian)

    # ------------------------------------------------------------------ discovery loop
    def investigate(self, target) -> Generator:
        t_start = time.perf_counter()
        tid = target.target_id
        s = target.signal
        yield self._msg("gatekeeper", f"Anonymized target {tid}: P = {s['period_d']:.4f} d, depth = "
                                      f"{s['depth_ppm']:.0f} ppm, duration = {s['duration_h']:.2f} h, SNR = "
                                      f"{s['snr']:.1f}. Labels withheld.", tid, kind="intake",
                        signal=s, stellar=target.stellar)
        wb = Whiteboard.new(target, self.tables.prior(), self.cfg["budget"])
        yield self._msg("whiteboard", "Priors from calibration-set base rates.", tid, kind="posterior",
                        posterior=dict(wb.posterior), after=None)

        trust = None
        if self.foreman.enabled:
            trust = self.foreman.data_trust(target)
            txt = "Everybody lies, including the data. " + (
                "Sanity checks pass." if not trust["issues"] else "Issues: " + "; ".join(trust["issues"]) + ".")
            txt += f" {trust['n_transits']} transits covered, scatter {trust['scatter_ppm']:.0f} ppm."
            yield self._msg("foreman", txt, tid, kind="message", trust=trust)
            if trust["n_transits"] < 3:
                self._add_critique(wb, f"Only {trust['n_transits']} transits in the data.", "data", permanent=True)

        proposals = []
        if self.house.enabled:
            proposals = self.house.differential(target)
            for p in proposals:
                wb.hypotheses.append(p.model_dump())
            yield self._msg("house", "Differential: H1-H5 default, plus my own: " + "; ".join(
                f"{p.id} '{p.name}' (-> {p.parent})" for p in proposals) + ". All agent-generated hypotheses "
                "are labeled and roll up into a default class.", tid, kind="hypotheses",
                proposals=[p.model_dump() for p in proposals])

        if self.cameron.enabled:
            pack = self.cameron.intake_pack()
            wb.evidence.extend(e.model_dump() for e in pack)
            yield self._msg("cameron", "Context: " + "; ".join(f"{e.source_id} ({e.claim[:70]}...)" for e in pack),
                            tid, kind="evidence", evidence=[e.model_dump() for e in pack])
            if self.research:
                order = sorted(wb.posterior, key=wb.posterior.get, reverse=True)
                yield from self._research(wb, tid, order[0], order[1])
            elif self.live_literature:
                lead0 = wb.leader()
                order = sorted(wb.posterior, key=wb.posterior.get, reverse=True)
                q = self.cameron.methodology_query(lead0, order[1])
                ok, _ = yield from self._tool("cameron", "literature_search", {"query": q, "target_id": tid}, tid)
                if ok:
                    hits = openalex_search(q)
                    yield self._msg("cameron", f"OpenAlex '{q}': " + ("; ".join(
                        f"{h['title']} ({h['year']}, {h['openalex_id']})" for h in hits) or "no results"),
                        tid, kind="evidence", openalex=hits)

        round_no = 0
        rationales = []
        while True:
            round_no += 1
            contr = self.house.contrarian(wb, proposals, self.tables) if self.house.enabled else None
            if contr:
                yield self._msg("house", contr["text"], tid, kind="message", contrarian=contr)
            plan = self.cuddy.plan(wb, round_no, (contr["leader"], contr["contrarian"]) if contr else None,
                                   contr["request"] if contr else None)
            rationales.append(plan.model_dump())
            if plan.stop:
                yield self._msg("cuddy", f"STOP: {plan.stop_reason}.", tid, kind="plan", plan=plan.model_dump())
                break
            top = sorted(plan.candidates, key=lambda c: -c.score)[:3]
            ctext = ", ".join(f"{c.test_id} (EIG {c.eig_bits:.2f} b, cost {c.cost:g}, score {c.score:.2f})" for c in top)
            yield self._msg("cuddy", f"Round {round_no}: compared {len(plan.candidates)} tests: {ctext}. Chosen: "
                                     f"{', '.join(plan.chosen)}{' (in parallel)' if len(plan.chosen) > 1 else ''}. "
                                     f"Budget left: {plan.budget_left}.", tid, kind="plan", plan=plan.model_dump())
            if self.foreman.enabled:
                yield self._msg("foreman", " ".join(self.foreman.pre_test_critique(t, target, trust)
                                                    for t in plan.chosen), tid)
            evs = self.cameron.evidence_for_tests(plan.chosen)
            have = {e["id"] for e in wb.evidence}
            for e in evs:
                if e.id not in have:
                    wb.evidence.append(e.model_dump())
            if evs:
                yield self._msg("cameron", "Method evidence: " + "; ".join(f"[{e.id}] {e.source_id}: {e.claim}" for e in evs),
                                tid, kind="evidence", evidence=[e.model_dump() for e in evs])

            # ---- Chase executes (policy-gated, parallel when Cuddy dispatched a batch)
            specs = []
            for test_id in plan.chosen:
                spec = TestSpec(test_id=test_id, target_id=tid, params={"window_factor": 3.0},
                                cost_units=REGISTRY[test_id].cost,
                                expected_discriminates=list(REGISTRY[test_id].separates),
                                rationale_ref=f"plan:{tid}:r{round_no}")
                ok, _ = yield from self._tool("chase", "run_vetting_test",
                                              {"target_id": tid, "test_id": test_id, "window_factor": 3.0,
                                               "cost_units": spec.cost_units}, tid)
                if ok:
                    specs.append(spec)
                    wb.budget["used"] += 1
                    wb.budget["cost_units_used"] += spec.cost_units
            if not specs:
                break
            if len(specs) > 1 and self.chase.cache is None:
                with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                    results = list(ex.map(lambda sp: self.chase.execute(sp, target), specs))
            else:
                results = [self.chase.execute(sp, target) for sp in specs]

            for res in results:
                self.ledger.log("chase", "test_result", tid, outputs=res.model_dump(), cost_units=REGISTRY[res.test_id].cost)
                prior_post = wb.post_array()
                assess = self.foreman.assess(res, target, self.tables, prior_post)
                weight, quality = assess.weight, assess.quality
                yield self._msg("chase", f"{res.test_id} -> {res.outcome_label} "
                                         f"({', '.join(f'{k}={v}' for k, v in list(res.metrics.items())[:3])}). "
                                         f"run_id {res.run_id}, code {res.code_hash}.", tid, kind="result",
                                result=res.model_dump())
                if self.foreman.enabled:
                    yield self._msg("foreman", assess.critique, tid, kind="assessment", assessment=assess.model_dump())
                rerun_record = None
                if assess.follow_up_request is not None:
                    cer = assess.follow_up_request
                    rcost = round(self.cfg["foreman"]["rerun_cost_fraction"] * REGISTRY[res.test_id].cost, 2)
                    yield self._msg("foreman", f"Counter-experiment request: {cer.reason} (cost {rcost}).", tid,
                                    kind="counter", request=cer.model_dump())
                    ok, _ = yield from self._tool("chase", "rerun_vetting_test",
                                                  {"target_id": tid, "test_id": res.test_id, "window_factor": 5.0,
                                                   "cost_units": rcost}, tid)
                    if ok:
                        wb.budget["cost_units_used"] += rcost
                        rr = self.chase.execute(TestSpec(test_id=res.test_id, target_id=tid,
                                                         params={"window_factor": 5.0}, cost_units=rcost), target)
                        same, txt = self.foreman.compare_rerun(res, rr)
                        yield self._msg("foreman", txt, tid, kind="assessment", rerun=rr.model_dump())
                        rerun_record = {"test_id": res.test_id, "run_id": rr.run_id, "outcome_bin": rr.outcome_bin,
                                        "outcome_label": rr.outcome_label, "quality": "ok" if same else "marginal",
                                        "weight": 0.0, "rerun": True, "evidence_ids": []}
                        if not same:
                            quality, weight = "marginal", self.cfg["foreman"]["weights"]["marginal"]
                            self._add_critique(wb, f"{res.test_id} is detrending-sensitive.", res.test_id)
                    else:
                        self._add_critique(wb, f"Counter-experiment on {res.test_id} was not run (budget).",
                                           res.test_id)
                elif assess.surprise and self.foreman.enabled:
                    self._add_critique(wb, f"Surprising {res.test_id} result needs independent corroboration.",
                                       res.test_id)

                old_leader = wb.leader()
                lik = self.tables.likelihood(res.test_id, res.outcome_bin) if res.outcome_bin >= 0 else np.ones(5)
                post = update(prior_post, lik, weight, self.tables.temper)
                wb.set_posterior(post, after=res.test_id)
                wb.trajectory[-1].update(tests=wb.budget["used"], cost=round(wb.budget["cost_units_used"], 3))
                ev_ids = [f"EV-{k}" for k in REGISTRY[res.test_id].method_refs if self.cameron.enabled]
                wb.tests_run.append({"test_id": res.test_id, "run_id": res.run_id, "outcome_bin": res.outcome_bin,
                                     "outcome_label": res.outcome_label, "metrics": res.metrics,
                                     "quality": quality, "weight": weight, "evidence_ids": ev_ids})
                if rerun_record:
                    wb.tests_run.append(rerun_record)
                new_leader = wb.leader()
                # corroboration resolves earlier critiques from *other* tests
                if quality == "ok" and wb.open_critiques and lik[HYP_IDS.index(new_leader)] >= 0.5 * lik.max():
                    before = len(wb.open_critiques)
                    wb.open_critiques = [c for c in wb.open_critiques
                                         if c["permanent"] or c["test_id"] == res.test_id]
                    if len(wb.open_critiques) < before:
                        yield self._msg("foreman", f"{res.test_id} independently corroborates "
                                                   f"{HYP_LABELS[new_leader]}; earlier critique resolved.", tid)
                yield self._msg("whiteboard", f"Posterior after {res.test_id}: " + ", ".join(
                    f"{h} {p:.2f}" for h, p in wb.posterior.items()), tid, kind="posterior",
                    posterior=dict(wb.posterior), after=res.test_id)
                if new_leader != old_leader and self.house.enabled:
                    yield self._msg("house", self.house.reopen(old_leader, new_leader, wb.posterior), tid,
                                    kind="reopen", old=old_leader, new=new_leader)
                    if self.research and self.cameron.enabled:
                        runner_up = sorted(wb.posterior, key=wb.posterior.get, reverse=True)[1]
                        yield from self._research(wb, tid, new_leader, runner_up)

        # ---- verdict
        interval = self._interval(wb)
        run_ids = [t["run_id"] for t in wb.tests_run]
        evidence_ids = sorted({e for t in wb.tests_run for e in t.get("evidence_ids", [])})
        critiques = list(wb.open_critiques) if self.foreman.enabled else []
        verdict = self.house.verdict(wb, interval, self.threshold, run_ids, evidence_ids, critiques)
        ok, _ = yield from self._tool("house", "issue_verdict", {
            "target_id": tid, "label": verdict.label, "label_text": verdict.label_text,
            "top_posterior": verdict.top_posterior, "needs_human": verdict.needs_human,
            "run_ids": run_ids, "evidence_ids": evidence_ids}, tid)
        if not ok:  # policy refused (e.g. no provenance): escalate rather than guess
            verdict.needs_human = True
            verdict.claim_strength = "undetermined"
        wb.status = "closed"
        yield self._msg("house", f"VERDICT: {verdict.label_text}. P = {verdict.top_posterior:.3f} "
                                 f"(90% CI {interval[0]:.2f}-{interval[1]:.2f}), {verdict.tests_used} tests, "
                                 f"{verdict.cost_used} cost units. Needs human: {verdict.needs_human}.", tid,
                        kind="verdict", verdict=verdict.model_dump())
        if self.house.enabled and verdict.label == "H1" and verdict.top_posterior >= self.threshold:
            ok, _ = yield from self._tool("house", "propose_followup",
                                          {"target_id": tid, "kind": "high-resolution imaging + RV",
                                           "justification": verdict.label_text}, tid)
            verdict.required_followup = ([f"[APPROVED] {f}" for f in verdict.required_followup] if ok
                                         else [f"[QUEUED for human] {f}" for f in verdict.required_followup])
        lesson = self.wilson.record_case(wb, verdict)
        yield self._msg("wilson", lesson.lesson, tid, kind="lesson", lesson=lesson.model_dump())
        if self.adaptive and self.gatekeeper is not None:
            true = self.gatekeeper._label(tid, "wilson_adaptive")
            self.wilson.adapt(self.tables, wb, true)
        return {"target_id": tid, "condition": self.name, "verdict": verdict.model_dump(), "whiteboard": wb.to_json(),
                "rationales": rationales, "tests_used": wb.budget["used"], "cost_used": wb.budget["cost_units_used"],
                "trajectory": wb.trajectory, "wall_clock_s": round(time.perf_counter() - t_start, 4),
                "escalations": self.escalations}

    def run(self, target, collect_events: bool = False):
        gen = self.investigate(target)
        events = []
        self.escalations = 0
        try:
            ev = next(gen)
            while True:
                if collect_events:
                    events.append(ev)
                answer = self.approver(ev) if ev.get("kind") == "approval" else None
                ev = gen.send(answer)
        except StopIteration as stop:
            rec = stop.value
        if collect_events:
            rec["events"] = events
        return rec
