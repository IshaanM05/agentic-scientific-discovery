"""Data Gatekeeper (design 5.7): the only component that holds ground-truth labels.

Agents receive anonymized Target objects. The gatekeeper exposes `score()` to the
evaluator; every label access is written to the ledger by the caller.
"""
from __future__ import annotations

import pickle
from pathlib import Path

from ..config import DATA, experiment
from .synth import Target, Truth, make_set


class DataGatekeeper:
    def __init__(self, targets: list[Target], truths: list[Truth], name: str):
        self.name = name
        self._targets = {t.target_id: t for t in targets}
        self._truth = {t.target_id: t for t in truths}
        self.label_access_log: list[dict] = []

    # --- agent-facing -----------------------------------------------------
    def target_ids(self) -> list[str]:
        return list(self._targets)

    def get_target(self, target_id: str) -> Target:
        return self._targets[target_id]

    # --- evaluator-only ---------------------------------------------------
    def score(self, target_id: str, label: str, caller: str = "evaluator") -> bool:
        self.label_access_log.append({"caller": caller, "target_id": target_id, "op": "score"})
        return label in self._truth[target_id].label.split("|")

    def _label(self, target_id: str, caller: str) -> str:
        if caller not in ("evaluator", "calibration", "wilson_adaptive"):
            raise PermissionError(f"{caller} may not read labels (policy no_label_access)")
        self.label_access_log.append({"caller": caller, "target_id": target_id, "op": "read_label"})
        return self._truth[target_id].label

    def truth_details(self, target_id: str, caller: str) -> dict:
        self._label(target_id, caller)
        return self._truth[target_id].details


def _cache_path(name: str) -> Path:
    return DATA / f"{name}_set.pkl"


def load_set(name: str, rebuild: bool = False) -> DataGatekeeper:
    """name in {'calibration', 'blind'}; cached to data/ for reproducibility and speed."""
    cfg = experiment()
    path = _cache_path(name)
    if name == "real":
        if not path.exists():
            raise FileNotFoundError("Real Kepler set not built; run `python -m plainsboro.data.kepler`.")
        with open(path, "rb") as f:
            targets, truths = pickle.load(f)
        return DataGatekeeper(targets, truths, name)
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            targets, truths = pickle.load(f)
    else:
        n = cfg["data"][f"n_{name}"]
        seed = cfg["seeds"][name]
        prefix = "C" if name == "calibration" else "T"
        pairs = make_set(n, seed, cfg["data"]["class_mix"], prefix=prefix,
                         baseline_days=cfg["data"]["baseline_days"], cadence_min=cfg["data"]["cadence_min"])
        targets = [p[0] for p in pairs]
        truths = [p[1] for p in pairs]
        with open(path, "wb") as f:
            pickle.dump((targets, truths), f)
    return DataGatekeeper(targets, truths, name)
