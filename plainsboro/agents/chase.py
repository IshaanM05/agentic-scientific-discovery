"""Chase, experiment runner (design 5.3): executes approved TestSpecs reproducibly."""
from __future__ import annotations

import uuid

from ..schemas import TestResult, TestSpec
from ..vetting.registry import run_test


class Chase:
    name = "chase"

    def __init__(self, outcome_cache: dict | None = None):
        self.cache = outcome_cache

    def execute(self, spec: TestSpec, target) -> TestResult:
        wf = float(spec.params.get("window_factor", 3.0))
        cached = None
        if self.cache is not None:
            cached = self.cache.get(target.target_id, {}).get((spec.test_id, wf))
        raw = cached if cached is not None else run_test(spec.test_id, target, wf)
        return TestResult(test_id=spec.test_id, target_id=target.target_id,
                          run_id=f"run-{target.target_id}-{spec.test_id}-{uuid.uuid4().hex[:6]}",
                          metrics=raw["metrics"], uncertainties=raw["uncertainties"],
                          outcome_bin=-1 if raw["outcome_bin"] is None else raw["outcome_bin"],
                          outcome_label=raw["outcome_label"], code_hash=raw["code_hash"], seed=0,
                          runtime_s=raw["runtime_s"], params=raw["params"])
