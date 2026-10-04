"""LabLoop Omnigent tools: offline, no model. Round trip, one full round with a stub proposer, no-leak,
budget DENY, determinism per (world, seed), policies."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from asd import labloop_tools as L
from labloop.chemistry import set_world, space_arrays, composition_space

ROOT = Path(__file__).resolve().parent.parent

STUB = [
    {"statement": "Cs-rich Pb iodides with little Sn keep T80 above 700 h.", "region": {"cs": [0.1, 0.3], "sn": [0, 0.1]},
     "prop": "lt", "op": ">", "value_t80_h": 700, "sources": ["L6"], "rationale": "stub"},
    {"statement": "Bad: unknown dim", "region": {"zz": [0, 1]}, "prop": "eg", "op": "<", "value": 1.3},
    {"statement": "Bad: whole space", "region": {"sn": [0, 1]}, "prop": "eg", "op": "<", "value": 1.3},
    {"statement": "Bad: empty", "region": {"sn": [0.5, 0.5], "cl": [1, 1]}, "prop": "eg", "op": "<", "value": 1.3},
]
SECRET_TERMS = ("eg_true", "lt_true", "true_hit", "true_hits", '"bow"', '"sn_pen"', '"sn_exp"', '"shield"',
                '"eg_shift"', '"cl_bonus"', '"ma_pen"', '"seg"', "world_params", "WORLD")


@pytest.fixture
def rd(tmp_path, monkeypatch):
    d = tmp_path / "run"
    monkeypatch.setenv("ASD_RUN_DIR", str(d))
    monkeypatch.setenv("ASD_RUN_ID", "t")
    return d


def one_round(budget=60, world=1, seed=0, proposals=STUB):
    outs = {"start": L.ll_start(world, seed, budget)}
    outs["lit"] = L.ll_literature()
    outs["arena"] = L.ll_arena_round(proposals)
    outs["pi"] = L.ll_pi_decide("test rationale")
    outs["design"] = L.ll_design(outs["pi"]["slots"])
    ids = [p["slot_id"] for p in outs["design"]["protocols"] if p["runnable"]][:3]
    outs["run"] = L.ll_run(ids)
    outs["analyse"] = L.ll_analyse()
    outs["judge"] = L.ll_judge()
    outs["status"] = L.ll_status()
    return outs


def test_full_round_with_stub_proposer(rd):
    o = one_round()
    assert all("error" not in v for v in o.values()), {k: v for k, v in o.items() if "error" in v}
    assert o["start"]["n_candidates"] == 2772 and o["start"]["budget"] == 60
    assert len(o["lit"]["hypotheses"]) == 6 and all(h["citation"] for h in o["lit"]["hypotheses"])
    assert len(o["arena"]["admitted"]) == 1 and o["arena"]["admitted"][0]["label"] == "agent-generated"
    assert len(o["arena"]["rejected"]) == 3 and all(r["reason"] for r in o["arena"]["rejected"])
    assert o["pi"]["mode"] == "seed" and len(o["design"]["protocols"]) >= 2
    assert all("safety_review" in p for p in o["design"]["protocols"])
    assert len(o["run"]["results"]) == 3 and o["run"]["units_used"] == o["status"]["units_used"]
    assert o["status"]["budget_left"] == 60 - o["run"]["units_used"] and o["status"]["n_tested"] == 3
    kinds = [json.loads(x)["kind"] for x in (rd / "record.jsonl").read_text().splitlines()]
    assert kinds == ["ll_start", "literature", "arena_round", "pi_decision", "design"] + ["experiment"] * 3 + [
        "analysis", "judge_verdict"]
    assert (rd / "notebook.sqlite").exists() and (rd / "ll_state.json").exists()
    json.dumps(o)


def test_second_round_adapts_and_continues(rd):
    one_round()
    pi = L.ll_pi_decide("round 2")
    assert pi["round"] == 2 and pi["mode"] in ("investigate", "exploit", "seed", "stop")
    d = L.ll_design(pi["slots"] + [{"kind": "explore", "reason": "extra"}])
    assert "error" not in d and len(d["protocols"]) >= 2
    assert L.ll_design([{"kind": "test", "hypothesis": "H99"}])["rejected"]


def test_round_trip_fresh_process(rd, tmp_path):
    one_round()
    here = json.loads((rd / "ll_state.json").read_text())
    code = ("import json,sys; from asd import labloop_tools as L; c=L.Ctx(); c.save(); "
            "print(json.dumps(L.ll_status(), sort_keys=True))")
    env = {**__import__("os").environ, "ASD_RUN_DIR": str(rd), "PYTHONPATH": str(ROOT)}
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT)
    assert p.returncode == 0, p.stderr[-500:]
    assert json.loads((rd / "ll_state.json").read_text()) == here  # reloaded + resaved identical
    assert json.loads(p.stdout) == json.loads(json.dumps(L.ll_status(), sort_keys=True))
    # a fresh process continues the run exactly as an in-process continuation of a copy does
    import shutil
    cp = tmp_path / "copy"
    shutil.copytree(rd, cp)
    env2 = {**env, "ASD_RUN_DIR": str(cp)}
    p2 = subprocess.run([sys.executable, "-c",
                         "import json; from asd import labloop_tools as L; print(json.dumps(L.ll_pi_decide('x'), sort_keys=True))"],
                        capture_output=True, text=True, env=env2, cwd=ROOT)
    assert p2.returncode == 0, p2.stderr[-500:]
    here_pi = json.loads(json.dumps(L.ll_pi_decide("x"), sort_keys=True))
    sub_pi = json.loads(p2.stdout)
    for d in (here_pi, sub_pi):
        d.pop("record_id")
    assert here_pi == sub_pi
    assert (cp / "ll_state.json").read_text() == (rd / "ll_state.json").read_text()


def test_no_hidden_truth_leaks(rd):
    o = one_round()
    blob = json.dumps(o) + (rd / "record.jsonl").read_text() + (rd / "ll_state.json").read_text()
    for t in SECRET_TERMS:
        assert t not in blob, t
    # only compositions that were actually run appear with measurements
    st = json.loads((rd / "ll_state.json").read_text())
    space = composition_space()
    assert len(st["tested_idx"]) == len(st["observations"]) == 3
    assert set(map(int, st["measurements"])) == set(st["tested_idx"])
    eg_true = space_arrays()[3]
    set_world(1)
    untested = [i for i in range(len(space)) if i not in st["tested_idx"]]
    hidden = {round(float(eg_true[i]), 6) for i in untested}
    nums = {round(float(x), 6) for x in __import__("re").findall(r"\d+\.\d{6,}", blob)}
    assert not (nums & hidden)


def test_budget_deny(rd):
    L.ll_start(1, 0, 2.0)
    L.ll_literature()
    pi = L.ll_pi_decide("b")
    d = L.ll_design(pi["slots"])
    ids = [p["slot_id"] for p in d["protocols"] if p["runnable"]]
    r = L.ll_run(ids)
    assert r["units_used"] <= 2.0 + 1e-9 and r["denied"] and "DENY" in r["denied"][0]["reason"]
    assert L.ll_status()["budget_left"] >= 0
    r2 = L.ll_run(ids)
    assert not r2["results"]
    assert L.ll_pi_decide("again")["mode"] in ("stop", "seed", "investigate", "exploit")


def test_determinism_per_world_seed(tmp_path, monkeypatch):
    def go(name, world, seed):
        monkeypatch.setenv("ASD_RUN_DIR", str(tmp_path / name))
        one_round(world=world, seed=seed)
        recs = [json.loads(x) for x in (tmp_path / name / "record.jsonl").read_text().splitlines()]
        return [{k: v for k, v in r.items() if k != "run_id"} for r in recs], \
            (tmp_path / name / "ll_state.json").read_text()
    a, b, c = go("a", 1, 3), go("b", 1, 3), go("c", 2, 3)
    assert a == b and a != c


def test_start_idempotent_and_guard(rd):
    L.ll_start(1, 0, 60)
    assert "error" not in L.ll_start(1, 0, 60)
    assert "error" in L.ll_start(2, 0, 60)


def test_missing_run_dir(monkeypatch):
    monkeypatch.delenv("ASD_RUN_DIR", raising=False)
    monkeypatch.delenv("LC_ASD_RUN_DIR", raising=False)
    assert "error" in L.ll_status()


def test_rule_based_fallback_label(rd):
    one_round()
    st = json.loads((rd / "ll_state.json").read_text())
    st["open_anomalies"] = [{"idx": st["observations"][0]["idx"], "key": st["observations"][0]["key"],
                             "formula": st["observations"][0]["formula"], "prop": "lt", "z": 3.0, "value": 3.0,
                             "predicted": 2.0, "residual": 1.0, "exp_id": "E001", "display": "T80 1000 h",
                             "prior_display": "T80 100 h"}]
    (rd / "ll_state.json").write_text(json.dumps(st))
    out = L.ll_arena_round([])
    assert all(h["label"] == "rule_based" for h in out["rule_based_fallback"])


def test_policies():
    call = lambda tool, **a: {"type": "tool_call", "target": tool, "data": {"arguments": a}, "session_state": {}}
    b = L.ll_budget(limit=3)
    ev = call("ll_run", slot_ids=["a", "b"])
    r = b(ev)
    assert r["result"] == "ALLOW"
    ev["session_state"] = {k: v for u in r["state_updates"] for k, v in [(u["key"], u["value"])]}
    assert b(ev)["result"] == "DENY"
    assert L.ll_safety_gate(call("ll_design", slots=[{"purpose": "run without ppe"}]))["result"] == "DENY"
    assert L.ll_safety_gate(call("ll_design", slots=[{"kind": "explore"}]))["result"] == "ALLOW"
    assert L.ll_human_approval(call("ll_design", slots=[{"kind": "explore", "dopant": "Cd"}]))["result"] == "ASK"
    assert L.ll_human_approval(call("ll_design", slots=[{"kind": "explore", "conc_m": 4}]))["result"] == "ASK"
    assert L.ll_human_approval(call("ll_design", slots=[{"kind": "explore"}]))["result"] == "ALLOW"


def test_restricted_and_scaleup_blocked_without_approval(rd):
    L.ll_start(1, 0, 60)
    L.ll_pi_decide("x")
    d = L.ll_design([{"kind": "explore", "dopant": "Cd", "reason": "r"}, {"kind": "explore", "conc_m": 4.0}])
    assert [p["runnable"] for p in d["protocols"]] == [False, False]
    assert d["protocols"][0]["requires_human_approval"] == ["restricted_element"]
    assert not L.ll_run([p["slot_id"] for p in d["protocols"]])["results"]
    d2 = L.ll_design([{"kind": "explore", "conc_m": 4.0, "human_approved": True}])
    assert d2["protocols"][0]["runnable"]


def test_planner_yaml_loads_and_wires():
    import importlib
    import yaml
    spec = yaml.safe_load((ROOT / "agents" / "labloop_planner.yaml").read_text())
    subs = {k: v for k, v in spec["tools"].items() if v.get("type") == "agent"}
    assert set(subs) == {"ll_literature_agent", "ll_generator", "ll_critic", "ll_analyst", "ll_judge", "ll_safety"}
    models = {k: v["executor"]["model"] for k, v in subs.items()}
    assert models["ll_generator"] == models["ll_analyst"] == "claude-sonnet-5-5"
    assert all(models[k] == "claude-haiku-4-5-20251001" for k in ("ll_literature_agent", "ll_critic", "ll_judge", "ll_safety"))
    assert spec["executor"]["model"] == "claude-sonnet-5-5"
    for d in list(spec["tools"].values()) + [t for s in subs.values() for t in s["tools"].values()]:
        if d.get("type") == "function":
            mod, fn = d["callable"].rsplit(".", 1)
            assert callable(getattr(importlib.import_module(mod), fn))
    assert all(s["tools"] for s in subs.values())  # declared explicitly, never inherited
    for pol in ("ll_budget", "ll_safety_gate", "ll_human_approval"):
        mod, fn = spec["policies"][pol]["handler"].rsplit(".", 1)
        assert callable(getattr(importlib.import_module(mod), fn))
    for needle in ("at least TWO", "ADAPT:", "NEXT-EXPERIMENT"):
        assert needle in spec["prompt"]


def test_planner_yaml_loads_with_omnigent():
    omni = pytest.importorskip("omnigent.spec")
    spec = omni.load(ROOT / "agents" / "labloop_planner.yaml")
    assert spec.name == "labloop_planner"
    assert all(t.path is not None for t in spec.local_tools)
    assert {s.name for s in spec.sub_agents} == {"ll_literature_agent", "ll_generator", "ll_critic", "ll_analyst",
                                                  "ll_judge", "ll_safety"}
