"""Multi-fidelity LabLoop: determinism, budget accounting, no leakage, fresh-process state. Offline."""
import json

import numpy as np
import pytest

from asd import labloop_mf_tools as T
from labloop.chemistry import set_world, space_arrays
from labloop.multifidelity import (
    SCREEN_COST, MFLab, MFSurrogate, expected_info_gain, plan_actions, run_mf_campaign, synth_cost,
)


@pytest.fixture(autouse=True)
def _reset_world():
    yield
    set_world(0)


@pytest.fixture
def rundir(tmp_path, monkeypatch):
    monkeypatch.setenv("ASD_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("ASD_RUN_ID", "t")
    return tmp_path


def test_lab_deterministic_and_order_independent():
    a, b = MFLab(1000, 3), MFLab(1000, 3)
    x = [a.screen(5), a.synthesize(7), a.screen(9)]
    y = [b.screen(9), b.synthesize(7), b.screen(5)]
    assert x[0] == y[2] and x[1] == y[1] and x[2] == y[0]
    assert MFLab(1000, 3).screen(5) != MFLab(1000, 4).screen(5)
    assert a.screen(5)["eg"] != x[0]["eg"] or a.screen(5)["lt"] != x[0]["lt"]  # repeat draws fresh noise


def test_screen_is_noisy_and_cheap():
    set_world(1000)
    eg_true = space_arrays()[3]
    lab = MFLab(1000, 0)
    errs = [lab.screen(i)["eg"] - eg_true[i] for i in range(0, 600, 3)]
    assert 0.03 < np.std(errs) < 0.10
    assert lab.screen(1)["cost"] == SCREEN_COST == 0.2
    assert lab.synthesize(1)["cost"] in (1.0, 1.5)


def test_mf_surrogate_downweights_screens():
    set_world(1000)
    i = 100
    truth = space_arrays()[3][i]
    prior = space_arrays()[1][i]
    far = prior + 0.5
    s_screen, s_synth = MFSurrogate(), MFSurrogate()
    s_screen.fit([{"idx": i, "fid": "screen", "ok": True, "eg": far, "lt": 2.0}])
    s_synth.fit([{"idx": i, "fid": "synth", "ok": True, "eg": far, "lt": 2.0}])
    assert abs(s_synth.mu_eg[i] - far) < abs(s_screen.mu_eg[i] - far)  # screen moves the mean less
    assert s_screen.sd_eg[i] > s_synth.sd_eg[i]
    assert truth is not None


def test_info_gain_synth_exceeds_screen_and_is_nonnegative():
    set_world(1000)
    sur = MFSurrogate()
    idx = np.arange(len(sur.X))
    syn = expected_info_gain(sur, idx, 0.015, 0.1, True)
    scr = expected_info_gain(sur, idx, 0.06, 0.35, False)
    assert (syn >= 0).all() and (scr >= 0).all()
    assert syn.mean() > scr.mean()


def test_plan_respects_budget_and_one_action_per_film():
    set_world(1000)
    sur = MFSurrogate()
    n = len(sur.X)
    acts = plan_actions(sur, np.zeros(n, bool), np.zeros(n, bool), n=8, budget_left=1.3)
    assert sum(a["cost"] for a in acts) <= 1.3 + 1e-9
    assert len({a["idx"] for a in acts}) == len(acts)


def test_campaign_deterministic_and_budget_accounting():
    a = run_mf_campaign(1000, 1, 30.0, "mf")
    b = run_mf_campaign(1000, 1, 30.0, "mf")
    assert a == b
    assert a["spent"] <= 30.0 + 1e-9
    assert a["n_screen"] > 0
    sf = run_mf_campaign(1000, 1, 30.0, "sf_eig")
    assert sf["n_screen"] == 0 and sf["spent"] <= 30.0 + 1e-9
    # spend identity: screens at 0.2 plus syntheses at 1 or 1.5
    assert a["spent"] >= 0.2 * a["n_screen"] + a["n_synth"] - 1e-6
    assert a["spent"] <= 0.2 * a["n_screen"] + 1.5 * a["n_synth"] + 1e-6


def test_tools_round_trip_across_processes_and_budget_deny(rundir):
    T.ll_mf_start(1000, 2, budget=3.0)
    plan = T.ll_mf_plan(3)
    assert plan["options"] and all("alternative" in o for o in plan["options"])
    r1 = T.ll_screen([10, 11])
    assert r1["units_used"] == pytest.approx(0.4)
    st1 = json.loads((rundir / "ll_mf_state.json").read_text())
    # a "new process" has no memory: everything comes from the files
    r2 = T.ll_run_mf([{"candidate_id": 12, "fidelity": "synth"}, {"candidate_id": 13, "fidelity": "auto"}])
    st2 = json.loads((rundir / "ll_mf_state.json").read_text())
    assert st2["units_used"] == pytest.approx(st1["units_used"] + sum(
        o["cost"] for o in st2["observations"][len(st1["observations"]):]))
    assert r2["units_used"] <= 3.0 + 1e-9
    big = T.ll_run_mf([{"candidate_id": i, "fidelity": "synth"} for i in range(20, 30)])
    assert any(r.get("denied") for r in big["results"])
    assert big["units_used"] <= 3.0 + 1e-9
    assert T.ll_screen([10])["results"][0]["denied"]  # one screen per film
    kinds = [json.loads(l)["kind"] for l in (rundir / "record.jsonl").read_text().splitlines()]
    assert {"ll_mf_start", "mf_plan", "screen", "experiment"} <= set(kinds)


def test_tools_deterministic_per_world_seed(tmp_path, monkeypatch):
    outs = []
    for k in range(2):
        d = tmp_path / str(k)
        monkeypatch.setenv("ASD_RUN_DIR", str(d))
        T.ll_mf_start(1001, 5, budget=20)
        T.ll_screen([3, 4])
        outs.append(T.ll_run_mf([{"candidate_id": 4, "fidelity": "synth"}]))
        outs.append(T.ll_mf_plan(3)["options"])
    assert outs[0] == outs[2] and outs[1] == outs[3]


def test_no_hidden_truth_in_outputs(rundir):
    world = 1000
    T.ll_mf_start(world, 0, budget=30)
    set_world(world)
    _, _, _, eg_t, lt_t, hits = space_arrays()
    outs = [T.ll_mf_plan(5), T.ll_screen([1, 2, 3]), T.ll_run_mf([{"candidate_id": 4, "fidelity": "synth"},
                                                                   {"candidate_id": 5, "fidelity": "auto"}]),
            T.ll_mf_plan(5)]
    text = json.dumps(outs) + (rundir / "record.jsonl").read_text() + (rundir / "ll_mf_state.json").read_text()
    for banned in ("eg_true", "lt_true", "true_hit", "true_hits", "bow", "sn_pen", "shield", "eg_shift", "hits_per_world"):
        assert banned not in text
    # measurements are noisy: never equal to the exact hidden value
    for o in json.loads((rundir / "ll_mf_state.json").read_text())["observations"]:
        if o["ok"]:
            assert o["eg"] != round(float(eg_t[o["idx"]]), 3) or o["fid"] == "synth"
            assert o["lt"] != round(float(lt_t[o["idx"]]), 3) or o["fid"] == "synth"
    set_world(world)  # tools must not have changed the hidden world
    assert (space_arrays()[5] == hits).all()


def test_start_required_and_run_dir_required(tmp_path, monkeypatch):
    monkeypatch.delenv("ASD_RUN_DIR", raising=False)
    monkeypatch.delenv("LC_ASD_RUN_DIR", raising=False)
    with pytest.raises(T.MFConfigError):
        T.ll_screen([1])
    monkeypatch.setenv("ASD_RUN_DIR", str(tmp_path))
    with pytest.raises(T.MFConfigError):
        T.ll_screen([1])
    assert synth_cost(0) in (1.0, 1.5)
