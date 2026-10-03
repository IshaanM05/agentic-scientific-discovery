import copy
import json
import pathlib
import sys

import pytest
from jsonschema import ValidationError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from asd import arena as A, cli_llm, schemas as S  # noqa: E402
from calibrate_arena import calibrate, perm_test, rel_error, spearman  # noqa: E402

H = {"id": "H1", "hypothesis": "Cobalt rich steels are strong", "mechanism": "precipitation hardening",
     "quantitative_prediction": {"statistic": "mean_yield_MPa", "region": [{"feature": "co", "op": ">=", "value": 5}],
                                 "value": [1800, 2200]},
     "kill_condition": "mean yield below 1500 MPa", "expected_comparison": "versus the pool mean",
     "novelty": {"verdict": "no match found", "citations": [], "note": A.NOTE}, "label": "agent-generated"}


def test_schema_rejects():
    S.check(H, S.ARENA_HYP)
    h = copy.deepcopy(H)
    del h["kill_condition"]
    with pytest.raises(ValidationError):
        S.check(h, S.ARENA_HYP)
    h = copy.deepcopy(H)
    h["quantitative_prediction"]["value"] = "high"
    with pytest.raises(ValidationError):
        S.check(h, S.ARENA_HYP)


def test_critic_names_refuting_test(tmp_path, monkeypatch):
    crit = [{"hypothesis_id": "H1", "attack": "confounded by Mo content", "refuting_test": {
        "name": "cobalt-free control", "description": "compare co>=5 steels with equal Mo",
        "expected_learning": 0.7, "feasibility": 0.9, "cost": 2}}]

    class P:
        returncode = 0
        stdout = json.dumps({"result": json.dumps(crit), "total_cost_usd": 0})
        stderr = ""

    monkeypatch.setattr(A, "CACHE", str(tmp_path))
    monkeypatch.setattr(cli_llm.subprocess, "run", lambda *a, **k: P())
    out = A.critique([H])
    assert out[0]["refuting_test"]["name"]
    with pytest.raises(ValidationError):
        S.check({"hypothesis_id": "H1", "attack": "no good reason"}, S.ARENA_CRITIQUE)


def test_calibration_math():
    assert spearman([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert rel_error({"value": [10, 20]}, 15) == 0 and rel_error({"value": 100}, 150) == 0.5
    rows = [{"co": i, "yield strength": 100.0 * i} for i in range(1, 11)]

    def mk(i, v):
        return {**H, "id": i, "quantitative_prediction": {"statistic": "mean_yield_MPa", "value": v,
                                                          "region": [{"feature": "co", "op": ">=", "value": 6}]}}
    hy = [mk("A", 800), mk("B", 1000), mk("C", 400), mk("D", 100)]  # true mean 800
    r = calibrate(hy, {"A": 1100, "B": 1050, "C": 1000, "D": 900}, rows, n_perm=1000)
    assert r["spearman"] == 1.0 and r["n_testable"] == 4 and r["perm_p_one_sided"] <= 0.1
    obs, p = perm_test([1, 2, 3, 4], [4, 3, 2, 1], n=1000)
    assert obs == -1.0 and p > 0.9
