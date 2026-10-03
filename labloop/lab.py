"""Lab adapters. One interface, swappable backends (replay oracle, simulator, robot API)."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Protocol as TypingProtocol

import numpy as np

from .chemistry import (
    Composition, bandgap_true, failure_probability, log_t80_true, tolerance_factor,
)


@dataclass
class Protocol:
    composition: Composition
    precursors: list[dict]
    solvent: str
    antisolvent: str
    anneal_c: int
    anneal_min: int
    additives: list[str]
    atmosphere: str
    purpose: str = ""

    def as_dict(self) -> dict:
        return {
            "formula": self.composition.formula(),
            "precursors": self.precursors,
            "solvent": self.solvent,
            "antisolvent": self.antisolvent,
            "anneal": f"{self.anneal_c} °C, {self.anneal_min} min",
            "additives": self.additives,
            "atmosphere": self.atmosphere,
            "purpose": self.purpose,
        }


@dataclass
class Result:
    ok: bool
    bandgap_ev: float | None
    log_t80: float | None
    phase: str
    cost: float
    duration_h: float
    notes: str = ""
    raw: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "bandgap_ev": None if self.bandgap_ev is None else round(self.bandgap_ev, 3),
            "log_t80": None if self.log_t80 is None else round(self.log_t80, 3),
            "t80_h": None if self.log_t80 is None else round(10 ** self.log_t80),
            "phase": self.phase,
            "cost": self.cost,
            "duration_h": self.duration_h,
            "notes": self.notes,
        }


def make_protocol(c: Composition, purpose: str = "", conc_m: float = 1.2) -> Protocol:
    """Stoichiometric precursor recipe for 1 mL of solution."""
    mmol = conc_m
    xs = {"I": c.i, "Br": c.br, "Cl": c.cl}
    precursors: list[dict] = []
    for a, fa in (("Cs", c.cs), ("FA", c.fa), ("MA", c.ma)):
        for x, fx in xs.items():
            amt = mmol * fa * fx
            if amt > 1e-4:
                precursors.append({"reagent": f"{a}{x}", "mmol": round(amt, 3)})
    for b, fb in (("Pb", c.pb), ("Sn", c.sn)):
        for x, fx in xs.items():
            amt = mmol * fb * fx
            if amt > 1e-4:
                precursors.append({"reagent": f"{b}{x}2", "mmol": round(amt, 3)})
    additives = []
    atmosphere = "N2 glovebox" if c.sn > 0 else "dry air (<20% RH)"
    if c.sn > 0:
        additives.append(f"SnF2 {10 * c.sn:.1f} mol%")
    return Protocol(
        composition=c, precursors=precursors, solvent="DMF:DMSO 4:1",
        antisolvent="chlorobenzene", anneal_c=100 if c.sn > 0 else 150,
        anneal_min=10, additives=additives, atmosphere=atmosphere, purpose=purpose,
    )


RESTRICTED = {"Cd", "Hg", "Tl", "As"}  # out-of-policy elements for this lab
SAFETY_LEVELS = {
    0: "routine",
    1: "PPE + fume hood",
    2: "glovebox + toxic-metal waste stream",
    3: "requires human sign-off",
}


def safety_review(p: Protocol) -> dict:
    """Screen a protocol before it reaches hardware."""
    reagents = " ".join(r["reagent"] for r in p.precursors)
    if any(el in reagents for el in RESTRICTED):
        return {"approved": False, "level": 3, "reason": "restricted element"}
    level = 1
    flags = []
    if p.composition.pb > 0:
        level = 2
        flags.append("lead salts: toxic-metal waste stream")
    if p.composition.sn > 0:
        flags.append("Sn(II) air-sensitive: glovebox")
        level = 2
    total = sum(r["mmol"] for r in p.precursors)
    if total > 5:
        level = 3
        flags.append("scale above 5 mmol")
    return {"approved": level < 3, "level": level, "label": SAFETY_LEVELS[level], "flags": flags}


class LabAdapter(TypingProtocol):
    name: str

    def run(self, protocol: Protocol) -> Result: ...


class PerovskiteReplayLab:
    """Hidden-physics lab: returns noisy measurements, failed films, cost and time.

    In production this class is replaced by an adapter over a robot / self-driving
    lab API with the same ``run`` signature.
    """

    name = "perovskite-replay-lab"

    def __init__(self, seed: int = 0, eg_noise: float = 0.015, lt_noise: float = 0.10):
        self.rng = np.random.default_rng(seed)
        self.eg_noise = eg_noise
        self.lt_noise = lt_noise
        self.runs = 0

    def run(self, protocol: Protocol) -> Result:
        c = protocol.composition
        self.runs += 1
        cost = 1.5 if c.sn > 0 else 1.0
        duration = 26.0 + (8.0 if c.sn > 0 else 0.0) + float(self.rng.uniform(-2, 2))
        if self.rng.random() < failure_probability(c):
            t = tolerance_factor(c)
            phase = "δ-phase + PbI2 peaks" if t < 0.88 else "hexagonal non-perovskite phase" if t > 0.99 else "pinholes, incomplete coverage"
            return Result(False, None, None, phase, cost, round(duration * 0.4, 1),
                          notes=f"Film failed QC (XRD: {phase}); t = {t:.3f}")
        eg = bandgap_true(c) + float(self.rng.normal(0, self.eg_noise))
        lt = log_t80_true(c) + float(self.rng.normal(0, self.lt_noise))
        return Result(True, eg, lt, "phase-pure perovskite (XRD)", cost, round(duration, 1),
                      notes=f"PL peak {1240 / eg:.0f} nm; T80 ≈ {10 ** lt:.0f} h at 1-sun, 65 °C")
