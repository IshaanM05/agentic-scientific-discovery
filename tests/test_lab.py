"""Unit and integration tests: physics, planner math, policies, leak controls, the full loop."""
from __future__ import annotations

import numpy as np
import pytest

from plainsboro.config import HYP_IDS, experiment
from plainsboro.data.synth import eclipse_deficit, make_target
from plainsboro.planner.posterior import entropy_bits, expected_info_gain, update
from plainsboro.policies import PolicyEngine, default_policies
from plainsboro.vetting.registry import REGISTRY, run_test


# ---------------------------------------------------------------- physics / tests

def test_transit_depth_matches_radius_ratio():
    t = np.linspace(-0.2, 0.2, 2001)
    d = eclipse_deficit(t, 3.0, 0.0, 0.1, 10.0, 0.0, u1=0.0, u2=0.0)
    assert d.max() == pytest.approx(0.01, rel=1e-3)          # uniform disk: depth = k^2


def test_odd_even_flags_half_period_eb():
    hits = 0
    for s in range(12):
        tg, tr = make_target("x", "H2", 100 + s)
        if tr.details["half_period_reported"] and run_test("T-odd-even", tg)["outcome_bin"] == 2:
            hits += 1
    assert hits >= 3


def test_planets_pass_systematics_and_centroid():
    for s in range(6):
        tg, _ = make_target("x", "H1", 500 + s)
        assert run_test("T-centroid", tg)["outcome_bin"] in (0, 1)
        assert run_test("T-systematics", tg)["outcome_bin"] in (0, 1)


def test_artifacts_coincide_with_flagged_cadences():
    tg, _ = make_target("x", "H5", 9)
    assert run_test("T-systematics", tg)["outcome_bin"] == 2


def test_failed_test_is_reported_not_raised():
    tg, _ = make_target("x", "H1", 1)
    tg.lc.time = tg.lc.time[:3]
    tg.lc.flux = tg.lc.flux[:3]
    r = run_test("T-shape", tg)
    assert r["outcome_bin"] is None and r["outcome_label"] == "failed"


# ---------------------------------------------------------------- planner math

def test_bayes_update_and_eig():
    prior = np.full(5, 0.2)
    table = np.array([[0.9, 0.1]] + [[0.1, 0.9]] * 4)          # perfect-ish separator of H1 vs rest
    useless = np.full((5, 2), 0.5)
    assert expected_info_gain(prior, table) > 0.3
    assert expected_info_gain(prior, useless) == pytest.approx(0.0, abs=1e-9)
    post = update(prior, table[:, 0])
    assert post[0] > 0.6 and post.sum() == pytest.approx(1.0)
    flat = update(prior, table[:, 0], weight=0.0)
    assert np.allclose(flat, prior)                           # unreliable result -> no update
    assert entropy_bits(prior) == pytest.approx(np.log2(5))


# ---------------------------------------------------------------- policies

@pytest.fixture
def engine():
    return PolicyEngine(default_policies(experiment(), benchmark_mode=True))


def test_policy_denials(engine):
    assert engine.evaluate("chase", "run_vetting_test", {"target_id": "T", "test_id": "T-bogus"})["result"] == "DENY"
    assert engine.evaluate("house", "run_vetting_test", {"target_id": "T", "test_id": "T-odd-even"})["result"] == "DENY"
    assert engine.evaluate("house", "send_email", {})["result"] == "DENY"
    assert engine.evaluate("house", "gatekeeper_read_label", {"target_id": "T"})["result"] == "DENY"
    assert engine.evaluate("house", "issue_verdict", {"label_text": "confirmed planet", "run_ids": ["r"],
                                                      "top_posterior": 0.99})["result"] == "DENY"
    assert engine.evaluate("house", "issue_verdict", {"label_text": "planet candidate", "run_ids": [],
                                                      "top_posterior": 0.99})["result"] == "DENY"


def test_label_leak_canary(engine):
    """A literature query naming the target is blocked in benchmark mode (design 12.6)."""
    for q in ["KOI-7016.01 disposition", "Kepler-452 b false positive", "T-0042 vetting"]:
        assert engine.evaluate("cameron", "literature_search", {"query": q, "target_id": "T-0042"})["result"] == "DENY"
    ok = engine.evaluate("cameron", "literature_search", {"query": "odd even depth test eclipsing binary"})
    assert ok["result"] == "ALLOW"


def test_budget_cap_asks_human(engine):
    cfg = experiment()
    for i in range(cfg["budget"]["max_tests"]):
        d = engine.evaluate("chase", "run_vetting_test", {"target_id": "T", "test_id": "T-odd-even", "cost_units": 1})
        assert d["result"] == "ALLOW"
        engine.apply(d["state_updates"])
    d = engine.evaluate("chase", "run_vetting_test", {"target_id": "T", "test_id": "T-secondary", "cost_units": 1})
    assert d["result"] == "ASK"


def test_followup_requires_approval(engine):
    assert engine.evaluate("house", "propose_followup", {"kind": "RV"})["result"] == "ASK"


# ---------------------------------------------------------------- full loop

@pytest.fixture(scope="module")
def tables():
    from plainsboro.planner.likelihood import TABLES_PATH, load_tables
    if not TABLES_PATH.exists():
        pytest.skip("run `python -m plainsboro.eval.calibrate` first")
    return load_tables()


def test_full_loop_produces_cited_verdict(tables):
    from plainsboro.lab import Lab
    tg, tr = make_target("T-TEST", "H2", 4242)
    rec = Lab(tables, n_interval_draws=50).run(tg, collect_events=True)
    v = rec["verdict"]
    kinds = {e["kind"] for e in rec["events"]}
    assert {"intake", "plan", "result", "posterior", "verdict", "lesson"} <= kinds
    assert v["run_ids"] and v["label"] in HYP_IDS
    assert v["label"] == max(v["posterior"], key=v["posterior"].get)      # House cannot override the posterior
    assert 0 <= v["interval"][0] <= v["top_posterior"] + 1e-6
    assert rec["tests_used"] <= experiment()["budget"]["max_tests"]
    plans = [e["plan"] for e in rec["events"] if e["kind"] == "plan" and not e["plan"]["stop"]]
    assert all(len(p["candidates"]) >= 2 for p in plans)                 # >= 2 tests compared every round
    assert any(h["origin"] == "agent_generated" for h in rec["whiteboard"]["hypotheses"])


def test_agents_never_read_labels(tables):
    from plainsboro.data.gatekeeper import DataGatekeeper
    from plainsboro.lab import Lab
    tg, tr = make_target("T-LEAK", "H1", 7)
    gk = DataGatekeeper([tg], [tr], "unit")
    Lab(tables, gatekeeper=gk, n_interval_draws=10).run(tg)
    assert gk.label_access_log == []
    with pytest.raises(PermissionError):
        gk._label("T-LEAK", "house")


def test_omnigent_bundle_validates():
    pytest.importorskip("omnigent")
    from pathlib import Path

    from omnigent.spec.parser import parse
    from omnigent.spec.validator import validate
    spec = parse(Path(__file__).resolve().parents[1] / "omnigent" / "princeton_plainsboro", expand_env=False)
    assert validate(spec).valid
    assert {s.name for s in spec.sub_agents} == {"cuddy", "chase", "foreman", "cameron", "wilson"}
    chase = next(s for s in spec.sub_agents if s.name == "chase")
    assert {p.name for p in chase.guardrails.policies} == {"test_allowlist", "budget_cap"}
