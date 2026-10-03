import json
import pathlib
import sys

import pytest
from jsonschema import ValidationError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from asd import cli_llm, judge as J, schemas as S  # noqa: E402
from calibrate_judge import calibrate  # noqa: E402

V = {"conclusion_id": "rec-1", "checks": {"supported_by_ledger": True, "citations_present": True,
                                          "labelled_agent_generated": True}, "confidence": "high", "reason": "ok fine"}


def test_schema():
    S.check(V, S.JUDGE_VERDICT)
    with pytest.raises(ValidationError):
        S.check({**V, "confidence": "certain"}, S.JUDGE_VERDICT)


def test_cached_and_no_ids(tmp_path, monkeypatch):
    calls = []

    class P:
        returncode = 0
        stdout = json.dumps({"result": json.dumps(V), "total_cost_usd": 0.0})
        stderr = ""

    monkeypatch.setattr(cli_llm.subprocess, "run", lambda *a, **k: calls.append(1) or P())
    c = {"record_id": "rec-1", "hypothesis_id": "H1", "supported": True, "surprising": False, "reopened_assumptions": []}
    h = {"id": "H1", "text": "t", "predicted_value": 2000, "citations": ["x"], "label": "agent-generated"}
    a = J.judge(c, h, 2100.0, cache_dir=str(tmp_path))
    b = J.judge(c, h, 2100.0, cache_dir=str(tmp_path))
    assert a == b and len(calls) == 1
    assert "c0" not in J.RUBRIC and "c1" not in J.RUBRIC


def test_calibration_math():
    r = calibrate([("high", True), ("high", False), ("low", False), ("medium", True)])
    assert r["n"] == 4 and r["accuracy"] == 0.5
    assert r["brier"] == round((0.15**2 + 0.85**2 + 0.25**2 + 0.5**2) / 4, 3)
    assert r["reliability"]["high"]["count"] == 2 and r["reliability"]["high"]["observed_accuracy"] == 0.5
