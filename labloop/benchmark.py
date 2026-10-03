"""Controlled comparison on the same replay lab and budget, averaged over seeds.

Strategies
----------
random        pick untested films uniformly at random (the floor)
grad-student  one-factor-at-a-time sweeps from the best literature composition
pure BO       GP + P(hit) acquisition, no literature prior, no hypotheses
LLM-style     literature prior + hypothesis tests, but no model updates (no BO)
LabLoop       full system; plus ablations that remove one component each
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .campaign import Config, run_campaign
from .chemistry import composition_space, is_hit, set_world, space_arrays
from .lab import PerovskiteReplayLab, make_protocol


def _curve_from(costs: list[float], hits_flags: list[bool], budget: float) -> list[int]:
    """Cumulative distinct true hits as a function of integer budget units spent."""
    out, spent, found = [], 0.0, 0
    k = 0
    for b in range(int(budget) + 1):
        while k < len(costs) and spent + costs[k] <= b + 1e-9:
            spent += costs[k]
            found += hits_flags[k]
            k += 1
        out.append(found)
    return out


def run_random(seed: int, budget: float) -> list[int]:
    rng = np.random.default_rng(1000 + seed)
    lab = PerovskiteReplayLab(seed=seed)
    *_, true_hits = space_arrays()
    order = rng.permutation(len(true_hits))
    costs, flags = [], []
    spent = 0.0
    for i in order:
        r = lab.run(make_protocol(composition_space()[i]))
        if spent + r.cost > budget:
            break
        spent += r.cost
        costs.append(r.cost)
        flags.append(bool(true_hits[i]))
    return _curve_from(costs, flags, budget)


def run_ofat(seed: int, budget: float) -> list[int]:
    """Greedy one-factor-at-a-time from Cs0.1FA0.9PbI3, keeping the best measured film."""
    rng = np.random.default_rng(2000 + seed)
    lab = PerovskiteReplayLab(seed=seed)
    space = composition_space()
    *_, true_hits = space_arrays()
    index = {c.key: i for i, c in enumerate(space)}
    from .chemistry import figure_of_merit
    cur = next(i for i, c in enumerate(space) if (c.cs, c.fa, c.sn, c.br, c.cl) == (0.1, 0.9, 0.0, 0.0, 0.0))
    tested, costs, flags = set(), [], []
    spent, best_score = 0.0, -1.0
    axes = ["sn", "br", "a", "cl"]
    from .chemistry import A_MIXES, SN_LEVELS, BR_LEVELS, CL_LEVELS
    while spent < budget:
        progressed = False
        for ax in axes:
            c0 = space[cur]
            if ax == "sn":
                cands = [replace(c0, sn=v) for v in SN_LEVELS]
            elif ax == "br":
                cands = [replace(c0, br=v) for v in BR_LEVELS if v + c0.cl <= 1]
            elif ax == "cl":
                cands = [replace(c0, cl=v) for v in CL_LEVELS if v + c0.br <= 1]
            else:
                cands = [replace(c0, cs=a[0], fa=a[1], ma=a[2]) for a in A_MIXES]
            for c in cands:
                i = index.get(c.key)
                if i is None or i in tested:
                    continue
                r = lab.run(make_protocol(c))
                if spent + r.cost > budget:
                    return _curve_from(costs, flags, budget)
                spent += r.cost
                tested.add(i)
                costs.append(r.cost)
                flags.append(bool(true_hits[i]))
                if r.ok:
                    score = figure_of_merit(r.bandgap_ev, r.log_t80)
                    if score > best_score:
                        best_score, cur, progressed = score, i, True
        if not progressed:
            untested = [i for i in range(len(space)) if i not in tested]
            cur = int(rng.choice(untested))
    return _curve_from(costs, flags, budget)


def _from_campaign(cfg: Config) -> tuple[list[int], dict]:
    trace = run_campaign(cfg)
    costs, flags, seen = [], [], set()
    for rd in trace["rounds"]:
        for e in rd["experiments"]:
            costs.append(e["result"]["cost"])
            new = e["true_hit"] and e["idx"] not in seen
            seen.add(e["idx"])
            flags.append(bool(new))
    curve = _curve_from(costs, flags, cfg.budget)
    # a campaign that stops early keeps its final count for the rest of the budget
    return curve, trace["summary"]


STRATEGIES = {
    "Random": None,
    "Grad-student OFAT": None,
    "Pure BO (no literature)": dict(use_prior=False, use_arena=False),
    "LLM-style (no BO)": dict(use_bo=False),
    "LabLoop − arena": dict(use_arena=False),
    "LabLoop − negative memory": dict(use_failures=False),
    "LabLoop − literature prior": dict(use_prior=False),
    "LabLoop (full)": dict(),
}


def run_benchmark(seeds: int = 20, budget: float = 60.0, target: int = 99, unseen_worlds: bool = False) -> dict:
    """``unseen_worlds=True`` gives every seed freshly drawn hidden physics (world id 1000 + seed)."""
    out = {}
    world_of = (lambda s: 1000 + s) if unseen_worlds else (lambda s: 0)
    totals = []
    for s in range(seeds):
        set_world(world_of(s))
        totals.append(int(space_arrays()[-1].sum()))
    for name, flags in STRATEGIES.items():
        curves = []
        for s in range(seeds):
            set_world(world_of(s))
            if name == "Random":
                c = run_random(s, budget)
            elif name == "Grad-student OFAT":
                c = run_ofat(s, budget)
            else:
                c, _ = _from_campaign(Config(seed=s, budget=budget, target_discoveries=target,
                                             record_maps=False, label=name, world=world_of(s), **flags))
            curves.append(c)
        arr = np.array(curves, dtype=float)
        first = [next((b for b, v in enumerate(c) if v >= 1), None) for c in curves]
        three = [next((b for b, v in enumerate(c) if v >= 3), None) for c in curves]
        out[name] = {
            "mean": arr.mean(0).round(3).tolist(),
            "lo": np.percentile(arr, 25, axis=0).round(3).tolist(),
            "hi": np.percentile(arr, 75, axis=0).round(3).tolist(),
            "final_mean": float(arr[:, -1].mean()),
            "first_hit_median": _median(first, budget),
            "three_hits_median": _median(three, budget),
            "success_3": float(np.mean([t is not None for t in three])),
            "found_frac": float(np.mean([c[-1] / t for c, t in zip(curves, totals)])),
        }
    set_world(0)
    # Random search rarely reaches 3 hits inside the budget, so also report its analytic
    # expectation: drawing without replacement, E[draws to k-th hit] = k (N + 1) / (K + 1).
    space = composition_space()
    n, k_hits = len(space), int(space_arrays()[-1].sum())
    mean_cost = float(np.mean([1.5 if c.sn > 0 else 1.0 for c in space]))
    analytic = {k: round(k * (n + 1) / (k_hits + 1) * mean_cost, 1) for k in (1, 3)}
    return {"seeds": seeds, "budget": budget, "strategies": out, "unseen_worlds": unseen_worlds,
            "hits_per_world": totals, "random_expected_budget": analytic,
            "true_hits_total": int(space_arrays()[-1].sum()), "space_size": len(composition_space())}


def _median(xs, budget):
    vals = [x if x is not None else np.inf for x in xs]
    m = float(np.median(vals))
    return None if not np.isfinite(m) else m
