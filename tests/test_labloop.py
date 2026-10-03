"""Smoke, determinism and generalisation tests. Run: pytest -q"""
import json

import numpy as np

from labloop.campaign import Config, run_campaign
from labloop.chemistry import composition_space, set_world, space_arrays
from labloop.hypotheses import literature_hypotheses
from labloop.lab import PerovskiteReplayLab, make_protocol, safety_review


def test_space_and_demo_world():
    set_world(0)
    assert len(composition_space()) == 2772
    assert int(space_arrays()[-1].sum()) == 11


def test_campaign_runs_and_is_serialisable():
    t = run_campaign(Config(seed=1))
    json.dumps(t, default=str)
    s = t["summary"]
    assert s["spent"] <= 60 + 1.5
    assert s["confirmed"] >= 1
    assert all(r["decision"]["rationale"] for r in t["rounds"])


def test_deterministic():
    a = run_campaign(Config(seed=3, record_maps=False))
    b = run_campaign(Config(seed=3, record_maps=False))
    ids = lambda t: [(e["formula"], e["result"]["bandgap_ev"]) for r in t["rounds"] for e in r["experiments"]]
    assert ids(a) == ids(b)


def test_hypotheses_are_falsifiable():
    for h in literature_hypotheses():
        assert h.prediction and h.kill_condition and h.sources


def test_safety_gate_blocks_scale_up():
    set_world(0)
    p = make_protocol(composition_space()[0], conc_m=10.0)
    assert not safety_review(p)["approved"]


def test_lab_reports_failures_and_costs():
    lab = PerovskiteReplayLab(seed=0)
    res = [lab.run(make_protocol(c)) for c in composition_space()[:200]]
    assert any(not r.ok for r in res) and all(r.cost > 0 for r in res)


def test_unseen_worlds_differ_and_agents_still_find_hits():
    found = []
    for w in (101, 102, 103):
        world = set_world(w)
        assert 6 <= int(space_arrays()[-1].sum()) <= 40
        t = run_campaign(Config(seed=w, world=w, record_maps=False))
        found.append(t["summary"]["true_hits_found"])
    set_world(0)
    assert np.mean(found) >= 2
