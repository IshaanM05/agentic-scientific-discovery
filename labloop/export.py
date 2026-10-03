"""Serialise campaign traces for the dashboard."""
from __future__ import annotations

import json
from pathlib import Path

from .campaign import Config, run_campaign
from .chemistry import composition_space, space_arrays
from .literature import CLAIMS


def export_trace(seed: int, budget: float = 60.0, out: str | Path | None = None) -> dict:
    trace = run_campaign(Config(seed=seed, budget=budget))
    space = composition_space()
    *_, eg_true, lt_true, hits = space_arrays()
    trace["space"] = [[c.cs, c.fa, c.ma, c.sn, c.br, c.cl] for c in space]
    trace["ground_truth_hits"] = [int(i) for i in hits.nonzero()[0]]
    trace["literature"] = CLAIMS
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(trace, default=str))
    return trace
