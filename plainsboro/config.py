"""Paths and experiment configuration."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RUNS = ROOT / "runs"

HYPOTHESES = {
    "H1": "planet",
    "H2": "eclipsing_binary",
    "H3": "blended_background_eb",
    "H4": "stellar_variability",
    "H5": "instrumental_artifact",
}
HYP_IDS = list(HYPOTHESES)

HYP_LABELS = {
    "H1": "Transiting planet (candidate)",
    "H2": "Eclipsing binary on target",
    "H3": "Blended background EB",
    "H4": "Stellar variability / spots",
    "H5": "Instrumental artifact",
}


@lru_cache(maxsize=1)
def experiment() -> dict:
    path = Path(os.environ.get("PP_EXPERIMENT", CONFIGS / "experiment.yaml"))
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


for _d in (DATA, RESULTS, RUNS):
    _d.mkdir(parents=True, exist_ok=True)
