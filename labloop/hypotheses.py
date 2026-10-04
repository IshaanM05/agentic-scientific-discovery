"""Hypothesis arena: falsifiable hypotheses, critic, and an Elo tournament.

Every hypothesis is machine-checkable: a composition region, a measured property,
and a predicted relation. The kill condition is derived from the prediction, so a
hypothesis cannot be stated without saying what result would falsify it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import math

import numpy as np

from .chemistry import LOG_T80_MIN, composition_space

DIMS = ("cs", "fa", "ma", "sn", "br", "cl")
PROPS = {"eg": "bandgap (eV)", "lt": "log10 T80 (h)"}


@lru_cache(maxsize=1)
def _space_cols() -> dict[str, np.ndarray]:
    sp = composition_space()
    return {d: np.array([getattr(c, d) for c in sp]) for d in DIMS}


def region_mask(region: dict[str, tuple[float, float]]) -> np.ndarray:
    cols = _space_cols()
    m = np.ones(len(composition_space()), dtype=bool)
    for d, (lo, hi) in region.items():
        m &= (cols[d] >= lo - 1e-9) & (cols[d] <= hi + 1e-9)
    return m


def in_region(c, region) -> bool:
    return all(lo - 1e-9 <= getattr(c, d) <= hi + 1e-9 for d, (lo, hi) in region.items())


def describe_region(region: dict) -> str:
    names = {"cs": "Cs", "fa": "FA", "ma": "MA", "sn": "Sn", "br": "Br", "cl": "Cl"}
    parts = []
    for d, (lo, hi) in region.items():
        n = names[d]
        if abs(lo - hi) < 1e-9:
            parts.append(f"{n} = {lo:g}")
        elif lo <= 1e-9:
            parts.append(f"{n} ≤ {hi:g}")
        elif hi >= 1 - 1e-9:
            parts.append(f"{n} ≥ {lo:g}")
        else:
            parts.append(f"{n} {lo:g}–{hi:g}")
    return ", ".join(parts) if parts else "all compositions"


def _fmt_value(prop: str, v: float) -> str:
    return f"{v:.2f} eV" if prop == "eg" else f"{10 ** v:.0f} h"


@dataclass
class Hypothesis:
    id: str
    statement: str
    region: dict
    prop: str
    op: str  # '<', '>', 'between', 'contrast'
    value: float | tuple = 0.0
    region_b: dict | None = None
    origin: str = "literature"   # literature | data | llm
    sources: list[str] = field(default_factory=list)
    rationale: str = ""
    status: str = "proposed"     # proposed | testing | supported | falsified | qualified
    elo: float = 1200.0
    created_round: int = 0
    resolved_round: int | None = None
    critiques: list[str] = field(default_factory=list)
    n_evidence: int = 0
    pass_rate: float | None = None
    confidence: str = "—"
    history: list[dict] = field(default_factory=list)

    @property
    def prediction(self) -> str:
        p = PROPS[self.prop]
        if self.op == "contrast":
            return (f"{p} is higher by >{self.value:.2f} in [{describe_region(self.region)}] "
                    f"than in [{describe_region(self.region_b)}]")
        if self.op == "between":
            lo, hi = self.value
            return f"{p} between {_fmt_value(self.prop, lo)} and {_fmt_value(self.prop, hi)} for {describe_region(self.region)}"
        return f"{p} {self.op} {_fmt_value(self.prop, self.value)} for {describe_region(self.region)}"

    @property
    def kill_condition(self) -> str:
        if self.op == "contrast":
            return "False if, after ≥2 films per arm, the difference is below a third of the predicted effect."
        if self.op == "between":
            lo, hi = self.value
            return f"False if ≥⅔ of ≥3 films in the region fall outside {_fmt_value(self.prop, lo)}–{_fmt_value(self.prop, hi)}."
        flip = ">=" if self.op == "<" else "<="
        return f"False if ≥⅔ of ≥3 films in the region measure {flip} {_fmt_value(self.prop, self.value)}."

    def check(self, value: float) -> bool:
        if self.op == "<":
            return value < self.value
        if self.op == ">":
            return value > self.value
        lo, hi = self.value
        return lo <= value <= hi

    def as_dict(self) -> dict:
        return {
            "id": self.id, "statement": self.statement, "prediction": self.prediction,
            "kill_condition": self.kill_condition, "origin": self.origin, "sources": self.sources,
            "rationale": self.rationale, "status": self.status, "elo": round(self.elo, 1),
            "created_round": self.created_round, "resolved_round": self.resolved_round,
            "critiques": self.critiques, "n_evidence": self.n_evidence,
            "pass_rate": None if self.pass_rate is None else round(self.pass_rate, 2),
            "confidence": self.confidence, "region": {k: list(v) for k, v in self.region.items()},
        }


RESOLVED = ("supported", "falsified", "qualified")


def evaluate(h: Hypothesis, observations: list[dict]) -> None:
    """Update evidence and status; resolved verdicts are revisited only once evidence doubles."""
    prev_status, prev_n = h.status, h.n_evidence
    _evaluate(h, observations)
    if prev_status in RESOLVED and h.status != prev_status:
        locked_n = h.history[-1]["n"] if h.history else prev_n
        if h.n_evidence < 2 * locked_n:
            h.status = prev_status
            return
    if h.status in RESOLVED and h.status != prev_status:
        h.history.append({"status": h.status, "n": h.n_evidence})


def _evaluate(h: Hypothesis, observations: list[dict]) -> None:
    key = "eg" if h.prop == "eg" else "lt"
    pts = [o for o in observations if o["ok"]]
    if h.op == "contrast":
        a = [o[key] for o in pts if in_region(o["comp"], h.region)]
        b = [o[key] for o in pts if in_region(o["comp"], h.region_b)]
        h.n_evidence = len(a) + len(b)
        if len(a) >= 2 and len(b) >= 2:
            diff = float(np.mean(a) - np.mean(b))
            h.pass_rate = diff
            if diff > h.value:
                h.status = "supported"
            elif diff < h.value / 3:
                h.status = "falsified"
            else:
                h.status = "testing"
        elif h.n_evidence:
            h.status = "testing"
        return
    vals = [o[key] for o in pts if in_region(o["comp"], h.region)]
    h.n_evidence = len(vals)
    if not vals:
        return
    rate = sum(h.check(v) for v in vals) / len(vals)
    h.pass_rate = rate
    if len(vals) >= 3 and rate >= 0.85:
        h.status = "supported"
    elif len(vals) >= 3 and rate <= 1 / 3:
        h.status = "falsified"
    elif len(vals) >= 6:
        h.status = "qualified"  # holds broadly, with reproducible exceptions
    else:
        h.status = "testing"


def literature_hypotheses() -> list[Hypothesis]:
    lt = lambda hours: math.log10(hours)
    return [
        Hypothesis("H1", "Bandgap mixes linearly (Vegard's law), so half-Sn iodides sit midway between end members.",
                   {"sn": (0.4, 0.6), "br": (0, 0), "cl": (0, 0)}, "eg", "between", (1.40, 1.56),
                   sources=["textbook interpolation"], rationale="Default assumption for alloy bandgaps."),
        Hypothesis("H2", "Sn-Pb mixing bows the bandgap below both end members.",
                   {"sn": (0.3, 0.7), "br": (0, 0), "fa": (0.6, 1)}, "eg", "<", 1.36,
                   sources=["L2", "L3"], rationale="Reported anomalous bowing in mixed Sn-Pb iodides."),
        Hypothesis("H3", "Any film with ≥30% Sn degrades fast from Sn(II) oxidation.",
                   {"sn": (0.3, 1.0)}, "lt", "<", lt(400),
                   sources=["L4"], rationale="Sn2+ oxidation is the dominant failure mode of Sn perovskites."),
        Hypothesis("H4", "Br-rich mixed halides without Cs segregate and lose stability.",
                   {"br": (0.3, 0.6), "cs": (0, 0.05)}, "lt", "<", lt(250),
                   sources=["L5"], rationale="Light-induced halide segregation."),
        Hypothesis("H5", "Cs/FA double-cation Pb iodides are the stable baseline.",
                   {"cs": (0.1, 0.3), "fa": (0.6, 1.0), "sn": (0, 0), "br": (0, 0.1)}, "lt", ">", lt(600),
                   sources=["L6"], rationale="Entropic stabilisation of the black phase."),
        Hypothesis("H6", "MA-majority films are thermally unstable.",
                   {"ma": (0.5, 1.0)}, "lt", "<", lt(250),
                   sources=["L7"], rationale="MA volatilises under heat."),
    ]


def critique(h: Hypothesis, untested_mask: np.ndarray, hyps: list[Hypothesis]) -> list[str]:
    notes = []
    m = region_mask(h.region)
    frac = m.mean()
    if (m & untested_mask).sum() < 3 and h.status in ("proposed", "testing") and h.n_evidence < 3:
        notes.append("Not testable: fewer than 3 untested films in region.")
    if frac > 0.35:
        notes.append(f"Too broad: region covers {frac:.0%} of the space; a pass/fail says little about mechanism.")
    if not h.sources and h.origin != "data":
        notes.append("No source or data trail.")
    for other in hyps:
        if other is h or other.status != "supported" or other.prop != h.prop:
            continue
        overlap = (m & region_mask(other.region)).sum()
        if overlap and h.op in ("<", ">") and other.op in ("<", ">") and h.op != other.op:
            notes.append(f"Conflicts with supported {other.id} on {overlap} shared compositions.")
    return notes


class Arena:
    """Pairwise tournament with Elo ratings (Co-Scientist style, scaled down)."""

    def __init__(self, rng: np.random.Generator, k: float = 24.0):
        self.rng = rng
        self.k = k
        self.matches: list[dict] = []

    def merit(self, h: Hypothesis, p_hit: np.ndarray, untested: np.ndarray) -> float:
        m = region_mask(h.region)
        if h.region_b is not None:
            m = m | region_mask(h.region_b)
        sel = p_hit[m & untested]
        top = float(np.sort(sel)[-5:].mean()) if sel.size else 0.0
        relevance = top / (float(p_hit[untested].max()) + 1e-9) if untested.any() else 0.0
        info = 1.0 - h.n_evidence / (h.n_evidence + 3)
        novelty = {"data": 1.0, "llm": 0.8, "literature": 0.4}.get(h.origin, 0.4)
        penalty = 0.25 * len([c for c in h.critiques if not c.startswith("Conflicts")])
        return 0.45 * relevance + 0.25 * info + 0.20 * novelty + 0.10 - penalty

    def run(self, hyps: list[Hypothesis], p_hit: np.ndarray, untested: np.ndarray, n_matches: int, rnd: int):
        active = [h for h in hyps if h.status in ("proposed", "testing")]
        if len(active) < 2:
            return
        merits = {h.id: self.merit(h, p_hit, untested) for h in active}
        for _ in range(n_matches):
            a, b = self.rng.choice(len(active), 2, replace=False)
            ha, hb = active[a], active[b]
            diff = merits[ha.id] - merits[hb.id] + self.rng.normal(0, 0.08)
            winner, loser = (ha, hb) if diff >= 0 else (hb, ha)
            exp_w = 1 / (1 + 10 ** ((loser.elo - winner.elo) / 400))
            winner.elo += self.k * (1 - exp_w)
            loser.elo -= self.k * (1 - exp_w)
            self.matches.append({"round": rnd, "winner": winner.id, "loser": loser.id,
                                 "margin": round(abs(diff), 3)})
