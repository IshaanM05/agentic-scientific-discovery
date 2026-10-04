"""Differential Whiteboard (design 6.1): the current shared state for one target."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from ..config import HYP_IDS, HYPOTHESES
from ..planner.posterior import as_dict


@dataclass
class Whiteboard:
    target_id: str
    signal: dict
    stellar: dict
    prior: dict
    posterior: dict
    budget: dict
    hypotheses: list = field(default_factory=list)          # default + agent-generated proposals
    tests_run: list = field(default_factory=list)            # [{test_id, run_id, outcome, quality, ...}]
    evidence: list = field(default_factory=list)             # Evidence dicts
    open_critiques: list = field(default_factory=list)
    trajectory: list = field(default_factory=list)           # posterior after each step
    status: str = "investigating"
    history_ref: str = ""

    @classmethod
    def new(cls, target, prior: np.ndarray, budget: dict) -> "Whiteboard":
        pr = as_dict(prior)
        hyps = [{"id": h, "name": HYPOTHESES[h], "prior": pr[h], "posterior": pr[h], "origin": "default"}
                for h in HYP_IDS]
        return cls(target_id=target.target_id, signal=dict(target.signal),
                   stellar={k: v for k, v in target.stellar.items()}, prior=pr, posterior=dict(pr),
                   budget={"max_tests": budget["max_tests"], "used": 0, "cost_units_used": 0.0,
                           "cost_units_max": budget["cost_units_max"]},
                   hypotheses=hyps, trajectory=[{"step": 0, "after": None, "posterior": dict(pr)}],
                   history_ref=f"ledger://{target.target_id}")

    def post_array(self) -> np.ndarray:
        return np.array([self.posterior[h] for h in HYP_IDS])

    def set_posterior(self, p: np.ndarray, after: str):
        self.posterior = as_dict(p)
        for h in self.hypotheses:
            if h["origin"] == "default":
                h["posterior"] = self.posterior[h["id"]]
        self.trajectory.append({"step": len(self.trajectory), "after": after, "posterior": dict(self.posterior)})

    def leader(self) -> str:
        return max(self.posterior, key=self.posterior.get)

    def tested(self) -> set:
        return {t["test_id"] for t in self.tests_run if not t.get("rerun")}

    def to_json(self) -> dict:
        return asdict(self)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, indent=1, default=str)

    @classmethod
    def load(cls, path: Path) -> "Whiteboard":
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))
