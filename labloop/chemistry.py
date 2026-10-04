"""Halide perovskite composition space (A B X3) and physics models.

Two models live here, on purpose:

* ``literature_prior``  - what a well-read scientist would predict from textbooks:
  Vegard-law (linear) bandgap mixing and known stability rules of thumb.
* ``ground_truth``      - the hidden "nature" used by the replay lab. It adds the
  effects that make discovery non-trivial: strong Pb-Sn bandgap bowing and a
  Cs-driven suppression of Sn2+ oxidation that the literature prior misses.

The agents never see ``ground_truth``; they only see noisy lab measurements.
Numbers are approximate literature values (Eperon 2016, Hao 2014, Saliba 2016,
Hoke 2015) and are good enough for a replayable discovery benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
import itertools
import math

import numpy as np

A_SITES = ("Cs", "FA", "MA")
B_SITES = ("Pb", "Sn")
X_SITES = ("I", "Br", "Cl")

# Effective ionic radii in Angstrom (Kieslich / Shannon)
R_A = {"Cs": 1.88, "FA": 2.53, "MA": 2.17}
R_B = {"Pb": 1.19, "Sn": 1.10}
R_X = {"I": 2.20, "Br": 1.96, "Cl": 1.81}

# End-member bandgaps (eV)  EG[B][X][A]
EG = {
    "Pb": {"I": {"Cs": 1.73, "FA": 1.51, "MA": 1.60},
           "Br": {"Cs": 2.36, "FA": 2.25, "MA": 2.30},
           "Cl": {"Cs": 3.00, "FA": 3.02, "MA": 3.05}},
    "Sn": {"I": {"Cs": 1.30, "FA": 1.41, "MA": 1.30},
           "Br": {"Cs": 1.75, "FA": 2.00, "MA": 2.15},
           "Cl": {"Cs": 2.80, "FA": 2.90, "MA": 2.95}},
}

# --------------------------------------------------------------------------- hidden world
# World 0 is the handcrafted landscape used in the demo. Any other world id draws
# fresh hidden physics (bowing strength, which element protects Sn, penalties,
# end-member offsets) so the benchmark can test on landscapes the agents were
# never tuned on. Agents never read WORLD; only the replay lab does.
WORLD: dict = {}
STABILISERS = ("cs", "fa", "cl")


def _default_world() -> dict:
    return {"id": 0, "bow": 0.75, "sn_pen": 2.2, "sn_exp": 1.1,
            "shield": {"cs": 0.72}, "cl_bonus": 0.25, "ma_pen": 0.9, "seg": 1.2,
            "eg_shift": {}, "description": "Cs protects Sn (FA-rich lattices); Cl passivates Sn-Pb"}


def _random_world(world_id: int) -> dict:
    rng = np.random.default_rng(10_000 + world_id)
    primary = str(rng.choice(STABILISERS))
    others = [x for x in STABILISERS if x != primary]
    secondary = str(rng.choice(others))
    shield = {primary: float(rng.uniform(0.55, 0.85)), secondary: float(rng.uniform(0.0, 0.3))}
    eg_shift = {f"{b}{x}": float(rng.uniform(-0.04, 0.04)) for b in B_SITES for x in X_SITES}
    return {"id": world_id, "bow": float(rng.uniform(0.45, 1.0)), "sn_pen": float(rng.uniform(1.9, 2.6)),
            "sn_exp": float(rng.uniform(0.9, 1.3)), "shield": shield,
            "cl_bonus": float(rng.uniform(0.0, 0.3)), "ma_pen": float(rng.uniform(0.6, 1.2)),
            "seg": float(rng.uniform(0.9, 1.5)), "eg_shift": eg_shift,
            "description": f"{primary} protects Sn (strength {shield[primary]:.2f}); {secondary} weakly ({shield[secondary]:.2f})"}


def set_world(world_id: int = 0) -> dict:
    """Install hidden physics. Non-zero ids redraw until the target has 6-40 hits."""
    global WORLD
    if world_id == 0:
        WORLD = _default_world()
    else:
        attempt = 0
        while True:
            WORLD = _random_world(world_id * 97 + attempt)
            WORLD["id"] = world_id
            space_arrays.cache_clear()
            n = int(space_arrays()[-1].sum())
            if 6 <= n <= 40 or attempt > 50:
                break
            attempt += 1
    space_arrays.cache_clear()
    return WORLD


# Campaign target: single-junction absorber near the Shockley-Queisser optimum
TARGET = {
    "eg_min": 1.24,
    "eg_max": 1.38,
    "t80_min_hours": 500.0,
}
LOG_T80_MIN = math.log10(TARGET["t80_min_hours"])


@dataclass(frozen=True)
class Composition:
    cs: float
    fa: float
    ma: float
    sn: float
    br: float
    cl: float

    @property
    def pb(self) -> float:
        return round(1 - self.sn, 3)

    @property
    def i(self) -> float:
        return round(1 - self.br - self.cl, 3)

    @property
    def key(self) -> str:
        return f"{self.cs:.2f}-{self.fa:.2f}-{self.ma:.2f}-{self.sn:.2f}-{self.br:.2f}-{self.cl:.2f}"

    def formula(self) -> str:
        def part(pairs):
            out = []
            for name, frac in pairs:
                if frac <= 1e-9:
                    continue
                if abs(frac - 1) < 1e-9:
                    out.append(name)
                else:
                    out.append(f"{name}{frac:g}")
            return "".join(out)

        a = part([("Cs", self.cs), ("FA", self.fa), ("MA", self.ma)])
        b = part([("Pb", self.pb), ("Sn", self.sn)])
        xs = [("I", self.i), ("Br", self.br), ("Cl", self.cl)]
        xs = [(n, round(f * 3, 2)) for n, f in xs if f > 1e-9]
        x = "".join(n if abs(f - 3) < 1e-9 else f"{n}{f:g}" for n, f in xs)
        if len(xs) == 1:
            x = f"{xs[0][0]}3"
        return f"{a}{b}{x}"

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(pb=self.pb, i=self.i, formula=self.formula(), key=self.key)
        return d


A_MIXES = [
    (0.00, 0.00, 1.00), (0.00, 1.00, 0.00), (1.00, 0.00, 0.00),
    (0.00, 0.50, 0.50), (0.05, 0.80, 0.15), (0.10, 0.75, 0.15),
    (0.10, 0.90, 0.00), (0.15, 0.60, 0.25), (0.20, 0.80, 0.00),
    (0.30, 0.70, 0.00), (0.50, 0.50, 0.00), (0.25, 0.00, 0.75),
]
SN_LEVELS = [round(0.1 * k, 1) for k in range(11)]
BR_LEVELS = [round(0.1 * k, 1) for k in range(11)]
CL_LEVELS = [0.0, 0.1]


@lru_cache(maxsize=1)
def composition_space() -> tuple[Composition, ...]:
    space = []
    for (cs, fa, ma), sn, br, cl in itertools.product(A_MIXES, SN_LEVELS, BR_LEVELS, CL_LEVELS):
        if br + cl > 1.0 + 1e-9:
            continue
        space.append(Composition(cs, fa, ma, sn, br, cl))
    return tuple(space)


def tolerance_factor(c: Composition) -> float:
    ra = c.cs * R_A["Cs"] + c.fa * R_A["FA"] + c.ma * R_A["MA"]
    rb = c.pb * R_B["Pb"] + c.sn * R_B["Sn"]
    rx = c.i * R_X["I"] + c.br * R_X["Br"] + c.cl * R_X["Cl"]
    return (ra + rx) / (math.sqrt(2) * (rb + rx))


def _a_avg(table: dict, c: Composition) -> float:
    return c.cs * table["Cs"] + c.fa * table["FA"] + c.ma * table["MA"]


def _halide_mix(b: str, c: Composition, bowing: bool) -> float:
    e_i, e_br, e_cl = (_a_avg(EG[b][x], c) for x in X_SITES)
    eg = c.i * e_i + c.br * e_br + c.cl * e_cl
    if bowing:
        eg -= 0.33 * c.i * c.br + 0.20 * c.br * c.cl + 0.60 * c.i * c.cl
    return eg


def bandgap_vegard(c: Composition) -> float:
    """Linear (Vegard-law) interpolation: the naive literature prior."""
    return (1 - c.sn) * _halide_mix("Pb", c, False) + c.sn * _halide_mix("Sn", c, False)


def bandgap_true(c: Composition) -> float:
    w = WORLD
    eg = (1 - c.sn) * _halide_mix("Pb", c, True) + c.sn * _halide_mix("Sn", c, True)
    if w.get("eg_shift"):
        for b, fb in (("Pb", c.pb), ("Sn", c.sn)):
            for x, fx in (("I", c.i), ("Br", c.br), ("Cl", c.cl)):
                eg += fb * fx * w["eg_shift"][f"{b}{x}"]
    eg -= w["bow"] * c.sn * (1 - c.sn)  # anomalous Pb-Sn bowing
    return eg


def sq_efficiency(eg: float) -> float:
    """Shockley-Queisser limit approximation (%), peak ~33.7% at 1.34 eV."""
    if eg <= 0.5:
        return 0.0
    if eg >= 1.34:
        return max(0.0, 33.7 - 12.5 * (eg - 1.34) ** 1.2)
    return max(0.0, 33.7 - 30.0 * (1.34 - eg) ** 1.6)


def _phase_penalty(c: Composition) -> float:
    t = tolerance_factor(c)
    pen = 0.0
    if t < 0.88:
        pen += 25 * (0.88 - t)
    if t > 0.99:
        pen += 25 * (t - 0.99)
    if max(c.cs, c.fa, c.ma) > 0.999:  # single-cation delta-phase / volatility issues
        pen += 0.6
    return pen


def log_t80_prior(c: Composition) -> float:
    """Literature rules of thumb for log10(T80 hours)."""
    lt = 3.0 - _phase_penalty(c)
    lt -= 2.2 * c.sn ** 1.1                      # Sn2+ -> Sn4+ oxidation
    lt -= 0.9 * c.ma                             # MA volatility
    seg = 4 * c.br * (1 - c.br - c.cl)           # halide segregation (Hoke effect)
    lt -= 1.2 * seg * (1 - 0.6 * min(c.cs / 0.25, 1))
    lt += 0.15 * min(c.cl / 0.1, 1) - 3 * max(0.0, c.cl - 0.1)
    return lt


def _shield(c: Composition) -> float:
    """How strongly the hidden stabiliser(s) suppress Sn oxidation, in [0, 0.95]."""
    total = 0.0
    for el, strength in WORLD["shield"].items():
        if el == "cs":
            f = min(max(c.cs - 0.05, 0) / 0.15, 1.0) * (1 if c.fa >= 0.6 else 0.3)
        elif el == "fa":
            f = min(max(c.fa - 0.6, 0) / 0.3, 1.0)
        else:  # cl
            f = min(c.cl / 0.1, 1.0)
        total += strength * f
    return min(total, 0.95)


def log_t80_true(c: Composition) -> float:
    w = WORLD
    lt = 3.0 - _phase_penalty(c)
    lt -= w["sn_pen"] * c.sn ** w["sn_exp"] * (1 - _shield(c))
    lt -= w["ma_pen"] * c.ma
    seg = 4 * c.br * (1 - c.br - c.cl)
    lt -= w["seg"] * seg * (1 - 0.6 * min(c.cs / 0.25, 1))
    lt += 0.15 * min(c.cl / 0.1, 1) - 3 * max(0.0, c.cl - 0.1)
    lt += w["cl_bonus"] * min(c.cl / 0.1, 1) * min(c.sn / 0.4, 1)
    return lt


def failure_probability(c: Composition) -> float:
    return min(0.85, 0.04 + 0.35 * _phase_penalty(c))


def is_hit(eg: float, log_t80: float) -> bool:
    return TARGET["eg_min"] <= eg <= TARGET["eg_max"] and log_t80 >= LOG_T80_MIN


def figure_of_merit(eg: float, log_t80: float) -> float:
    """PCE potential x stability, scaled to ~[0, 1]."""
    stab = 1 / (1 + math.exp(-(log_t80 - LOG_T80_MIN) / 0.2))
    return sq_efficiency(eg) / 33.7 * stab


FEATURE_NAMES = ["cs", "fa", "ma", "sn", "br", "cl", "tol", "sn_bow", "x_mix", "cs_sn"]


def features(c: Composition) -> np.ndarray:
    return np.array([
        c.cs, c.fa, c.ma, c.sn, c.br, c.cl,
        (tolerance_factor(c) - 0.93) * 5,
        c.sn * (1 - c.sn) * 2,
        c.br * (1 - c.br) * 2,
        c.cs * c.sn * 3,
    ])


@lru_cache(maxsize=1)
def space_arrays():
    space = composition_space()
    X = np.stack([features(c) for c in space])
    eg_prior = np.array([bandgap_vegard(c) for c in space])
    lt_prior = np.array([log_t80_prior(c) for c in space])
    eg_true = np.array([bandgap_true(c) for c in space])
    lt_true = np.array([log_t80_true(c) for c in space])
    hits = np.array([is_hit(e, l) for e, l in zip(eg_true, lt_true)])
    return X, eg_prior, lt_prior, eg_true, lt_true, hits


set_world(0)
