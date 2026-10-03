"""Omnigent integration tests that need no model: spec loads, tools run, policies gate."""
import json
from pathlib import Path

import pytest

from asd import policies as P
from asd import tools as T

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setenv("ASD_CACHE", str(tmp_path / "lit"))
    T.reset(seed=0, budget=60, run_dir=tmp_path / "run")
    return tmp_path / "run"


@pytest.mark.parametrize("name", ["hello", "planner"])
def test_yaml_loads_with_omnigent(name):
    omni = pytest.importorskip("omnigent.spec")
    spec = omni.load(ROOT / "agents" / f"{name}.yaml")
    assert spec.name == name
    paths = [t.path for t in spec.local_tools]
    assert paths and all(p is not None for p in paths), "tool import failed (callable silently None)"
    if name == "planner":
        assert {s.name for s in spec.sub_agents} == {"literature", "insight", "analysis", "safety"}


def hyp(ids, pred=2100.0, assumption="Ni-Co raises yield"):
    return T.propose_hypothesis("High Co and Ni steels exceed 2000 MPa", ids, pred, assumption,
                                ["https://openalex.org/W1"])


def test_tools_end_to_end_with_surprise_and_record(run):
    ids = T.select_next(2)["picks"]
    cid = ids[0]["candidate_id"]
    h = hyp([cid], pred=2400.0)
    assert h["hypothesis_id"] == "H1"
    ch = T.design_tests([
        {"name": "exploit-top-pick", "expected_learning": 0.5, "feasibility": 0.9, "cost": 1},
        {"name": "screen-10", "expected_learning": 0.8, "feasibility": 0.9, "cost": 10}])
    assert ch["chosen"] == "exploit-top-pick"
    r = T.run_experiment(cid, "H1")
    assert r["cost"] == 1
    a = T.analyze_result("H1", cid)
    if a["surprising"]:
        assert a["reopened_assumptions"] == ["Ni-Co raises yield"]
    kinds = [e["kind"] for e in T.research_record(50)["entries"]]
    assert kinds == ["selector", "hypothesis", "test_choice", "experiment", "analysis"]
    lines = (run / "record.jsonl").read_text().splitlines()
    assert len({json.loads(x)["record_id"] for x in lines}) == len(lines)


def test_surprise_reopens_assumption(run):
    cid = T.select_next(1)["picks"][0]["candidate_id"]
    hyp([cid], pred=1.0)  # absurdly low prediction -> must be surprising
    T.run_experiment(cid, "H1")
    a = T.analyze_result("H1", cid)
    assert a["surprising"] and a["reopened_assumptions"] == ["Ni-Co raises yield"]
    assert T._st()["assumptions"]["Ni-Co raises yield"] == "reopened"


def test_schema_blocks_unlabeled_or_uncited(run):
    with pytest.raises(Exception):
        T.propose_hypothesis("some hypothesis", ["c000"], 2000, "assumption x", [])
    with pytest.raises(Exception):
        T.design_tests([{"name": "only-one", "expected_learning": 0.5, "feasibility": 0.5, "cost": 1}])


def test_oracle_budget_enforced_in_tool(tmp_path):
    T.reset(seed=0, budget=2, run_dir=tmp_path / "r")
    ids = T._st()["oracle"].ids()
    T.run_experiment(ids[0]); T.run_experiment(ids[1])
    assert "error" in T.run_experiment(ids[2])


def ev(tool, n=0):
    return {"type": "tool_call", "target": tool, "data": {"name": tool, "arguments": {}},
            "session_state": {P._KEY: n}}


def test_budget_policy_denies():
    f = P.experiment_budget(limit=3)
    assert f(ev("run_experiment", 2))["result"] == "ALLOW"
    assert f(ev("run_experiment", 3))["result"] == "DENY"
    assert f(ev("select_next", 99))["result"] == "ALLOW"


def test_approval_policy_asks():
    f = P.human_approval(ask_after=30)
    assert f(ev("recommend_for_validation"))["result"] == "ASK"
    assert f(ev("run_experiment", 29))["result"] == "ALLOW"
    assert f(ev("run_experiment", 30))["result"] == "ASK"


def test_policy_gates_through_omnigent_shim():
    shim = pytest.importorskip("omnigent.spec._omnigent_legacy_shim")
    f = shim.build(target="asd.policies.experiment_budget", factory_kwargs={"limit": 2})
    assert f(ev("run_experiment", 2))["result"] == "DENY"
    g = shim.build(target="asd.policies.human_approval", factory_kwargs={"ask_after": 5})
    assert g(ev("recommend_for_validation"))["result"] == "ASK"


def test_every_yaml_callable_resolves_and_is_callable():
    import importlib

    import yaml
    for name in ("hello", "planner"):
        spec = yaml.safe_load((ROOT / "agents" / f"{name}.yaml").read_text())
        for tool, d in spec["tools"].items():
            if d.get("type") == "function":
                mod, fn = d["callable"].rsplit(".", 1)
                assert callable(getattr(importlib.import_module(mod), fn)), tool
        for pol, d in (spec.get("policies") or {}).items():
            mod, fn = d["handler"].rsplit(".", 1)
            assert callable(getattr(importlib.import_module(mod), fn)), pol


def test_record_step_rejects_bad_payload_and_accepts_good(run):
    bad = T.record_step("literature", "literature", json.dumps({"citations": [], "claims": ["x"]}))
    assert bad["accepted"] is False and "schema" in bad["error"]
    assert T.record_step("x", "nonsense", "{}")["accepted"] is False
    assert T.record_step("x", "analysis", "not json")["accepted"] is False
    assert not (run / "record.jsonl").exists()
    ok = T.record_step("literature", "literature", json.dumps({"citations": ["W1"], "claims": ["c"]}))
    assert ok["accepted"] and ok["record_id"].startswith("rec-")


def test_no_tool_leaks_unrevealed_yield(run):
    o = T._st()["oracle"]
    cid = o.ids()[0]
    secret = str(o._rows[cid]["yield strength"])
    outs = json.dumps([T.get_features([cid]), T.select_next(3), T.research_record()])
    assert secret not in outs and "yield strength" not in outs and "tensile" not in outs
    assert "error" in T.analyze_result("H9", cid)


def test_state_survives_new_process(run):
    cid = T.select_next(1)["picks"][0]["candidate_id"]
    hyp([cid], pred=2400.0)
    T.run_experiment(cid, "H1")
    T.reset(seed=0, budget=60, run_dir=run)  # simulates another process: memory empty, files kept
    a = T.analyze_result("H1", cid)
    assert a["hypothesis_id"] == "H1" and T._st()["oracle"].spent == 1
    assert T.research_record(50)["entries"][-1]["record_id"] == a["record_id"]


def test_builtin_cost_policy_resolves():
    pytest.importorskip("omnigent")
    from omnigent.policies.builtins.cost import cost_budget
    assert callable(cost_budget(max_cost_usd=1.0))
