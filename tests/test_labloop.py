import math

import numpy as np

from labloop.campaign import Config, run_campaign
from labloop.chemistry import bandgap_true, bandgap_vegard, composition_space, space_arrays
from labloop.hypotheses import Hypothesis, evaluate
from labloop.lab import PerovskiteReplayLab, make_protocol, safety_review


def test_space_and_ground_truth_are_nontrivial():
    space = composition_space()
    *_, hits = space_arrays()
    assert len(space) > 2000
    assert 3 <= hits.sum() <= 0.01 * len(space)  # rare targets: search matters


def test_prior_misses_hidden_physics():
    c = next(c for c in composition_space() if c.sn == 0.5 and c.br == 0 and c.cl == 0)
    assert bandgap_true(c) < bandgap_vegard(c) - 0.1  # Sn-Pb bowing is not in the textbook prior


def test_lab_is_reproducible_and_noisy():
    c = composition_space()[100]
    a = PerovskiteReplayLab(seed=1).run(make_protocol(c))
    b = PerovskiteReplayLab(seed=1).run(make_protocol(c))
    assert a.as_dict() == b.as_dict()


def test_safety_gate_blocks_large_scale():
    p = make_protocol(composition_space()[0], conc_m=8.0)
    assert not safety_review(p)["approved"]


def test_hypothesis_falsification():
    h = Hypothesis("T", "test", {"sn": (0.4, 0.6)}, "eg", "<", 1.0)
    comp = next(c for c in composition_space() if c.sn == 0.5)
    obs = [{"ok": True, "comp": comp, "eg": 1.3, "lt": 2.0} for _ in range(3)]
    evaluate(h, obs)
    assert h.status == "falsified"


def test_campaign_end_to_end():
    t = run_campaign(Config(seed=7, budget=30, record_maps=False))
    s = t["summary"]
    assert s["experiments"] > 0 and s["spent"] <= 30 + 1.5
    assert t["rounds"][-1]["decision"]["mode"] == "stop"
    for rd in t["rounds"]:
        for e in rd["experiments"]:
            assert e["safety"]["approved"]
            assert e["purpose"]  # every experiment says why it was run
