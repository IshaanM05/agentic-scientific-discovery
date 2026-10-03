import json

import jsonschema
import pytest

from asd import schemas as S
from asd.belief import Belief
from asd.cache import Cache
from asd.llm import LLM
from asd.loop import run, run_round
from asd.oracle import ToyOracle


def test_one_round_end_to_end(tmp_path):
    llm, o, b = LLM(Cache(str(tmp_path / "c")), seed=1), ToyOracle(1), Belief()
    out = run_round(llm, o, b, 0)
    S.check(out["pick"], S.PICK)
    S.check(out["result"], S.RESULT)
    S.check(out["analysis"], S.ANALYSIS)
    S.check(out["decision"], S.DECISION)
    assert len(b.experiments()) == 1 and o.spent == 1


def test_deterministic_and_cached(tmp_path):
    a = run(seed=3, budget=5, cache_dir=str(tmp_path / "c"))
    b = run(seed=3, budget=5, cache_dir=str(tmp_path / "c2"))
    assert json.dumps(a) == json.dumps(b)
    assert len(list((tmp_path / "c").glob("*.json"))) >= 1


def test_loop_terminates_within_budget(tmp_path):
    out = run(seed=0, budget=6, cache_dir=str(tmp_path / "c"))
    assert 1 <= len(out) <= 6


def test_schema_rejects_bad():
    with pytest.raises(jsonschema.ValidationError):
        S.check({"action": "dance", "reason": "x"}, S.DECISION)
