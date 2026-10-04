"""Cuddy, test planner and budget/approval gatekeeper (design 5.6).

Owns: which test runs next, and whether to stop. Scores every untested test by
expected information gain per cost, adds House's bounded contrarian bonus, and
always records at least two candidates in the PlannerRationale.
"""
from __future__ import annotations

import numpy as np

from ..config import HYP_IDS
from ..planner.posterior import expected_info_gain, pairwise_info
from ..schemas import PlannerCandidate, PlannerRationale
from ..vetting.registry import REGISTRY, TEST_IDS

FIXED_ORDER = ["T-odd-even", "T-secondary", "T-shape", "T-density", "T-periodogram", "T-systematics",
               "T-consistency", "T-centroid"]   # Robovetter-like canonical checklist


class Cuddy:
    name = "cuddy"

    def __init__(self, cfg: dict, tables, strategy: str = "eig", exploration_bonus: float | None = None,
                 parallel: bool = True, threshold: float | None = None, rng_seed: int = 7):
        self.cfg = cfg
        self.tables = tables
        self.strategy = strategy
        self.beta = cfg["planner"]["exploration_bonus"] if exploration_bonus is None else exploration_bonus
        self.parallel = parallel
        self.threshold = cfg["stopping"]["posterior_threshold"] if threshold is None else threshold
        self.min_eig = cfg["stopping"]["min_eig_bits"]
        self.rng = np.random.default_rng(rng_seed)

    def remaining(self, wb) -> tuple[int, float]:
        b = wb.budget
        return b["max_tests"] - b["used"], b["cost_units_max"] - b["cost_units_used"]

    def should_stop(self, wb, best_eig: float, n_affordable: int) -> tuple[bool, str]:
        top = max(wb.posterior.values())
        if top >= self.threshold and not wb.open_critiques:
            return True, f"top posterior {top:.3f} >= {self.threshold} and no open critiques"
        if n_affordable == 0:
            return True, "budget exhausted (no affordable test left)"
        if self.strategy == "eig" and best_eig < self.min_eig:
            return True, f"max EIG {best_eig:.3f} bits < {self.min_eig}: nothing more is learnable"
        return False, ""

    def plan(self, wb, round_no: int, contrarian: tuple | None = None, house_request: str | None = None
             ) -> PlannerRationale:
        post = wb.post_array()
        tests_left, cost_left = self.remaining(wb)
        tested = wb.tested()
        cands = []
        for tid in TEST_IDS:
            if tid in tested:
                continue
            tab = self.tables.table(tid)
            eig = expected_info_gain(post, tab, self.tables.temper)
            cbits = 0.0
            if contrarian is not None and self.beta > 0:
                i, j = HYP_IDS.index(contrarian[0]), HYP_IDS.index(contrarian[1])
                cbits = pairwise_info(post, tab, i, j, self.tables.temper)
            cost = REGISTRY[tid].cost
            affordable = tests_left >= 1 and cost <= cost_left + 1e-9
            bonus = self.beta * cbits
            if house_request == tid:
                bonus *= 1.5
            score = (eig + bonus) / cost if affordable else 0.0
            cands.append(PlannerCandidate(test_id=tid, eig_bits=round(eig, 4), contrarian_bits=round(cbits, 4),
                                          cost=cost, score=round(score, 4)))
        affordable = [c for c in cands if c.score > 0 or (self.strategy != "eig" and
                                                          c.cost <= cost_left + 1e-9 and tests_left >= 1)]
        best_eig = max([c.eig_bits for c in affordable], default=0.0)
        budget_left = {"tests": tests_left, "cost_units": round(cost_left, 2)}
        stop, why = self.should_stop(wb, best_eig, len(affordable))
        if stop:
            return PlannerRationale(round=round_no, candidates=cands, chosen=[], budget_left=budget_left,
                                    stop=True, stop_reason=why)

        if self.strategy == "eig":
            ranked = sorted(affordable, key=lambda c: -c.score)
            chosen = [ranked[0].test_id]
            runner = ranked[1].test_id if len(ranked) > 1 else None
            if (self.parallel and len(ranked) > 1 and tests_left >= 2
                    and ranked[1].score >= self.cfg["planner"]["parallel_ratio"] * ranked[0].score
                    and ranked[0].cost + ranked[1].cost <= cost_left + 1e-9):
                chosen.append(ranked[1].test_id)
                runner = ranked[2].test_id if len(ranked) > 2 else None
        elif self.strategy == "fixed":
            order = [t for t in FIXED_ORDER if t in {c.test_id for c in affordable}]
            chosen, runner = [order[0]], (order[1] if len(order) > 1 else None)
        elif self.strategy == "random":
            ids = [c.test_id for c in affordable]
            self.rng.shuffle(ids)
            chosen, runner = [ids[0]], (ids[1] if len(ids) > 1 else None)
        else:
            raise ValueError(self.strategy)
        return PlannerRationale(round=round_no, candidates=cands, chosen=chosen, runner_up=runner,
                                budget_left=budget_left)
