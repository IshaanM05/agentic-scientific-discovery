import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ll_summary as L  # noqa: E402


def test_summary_and_no_hidden_truth(tmp_path):
    d = tmp_path / "ll-x"
    d.mkdir()
    rows = [{"record_id": "r1", "kind": "ll_start", "world": 2000, "seed": 1, "budget": 60},
            {"record_id": "r2", "kind": "experiment", "cost": 1.0, "meets_spec": False, "eg_true": 1.3},
            {"record_id": "r3", "kind": "experiment", "cost": 1.5, "meets_spec": True, "true_hits": [1]},
            {"record_id": "r4", "kind": "analysis", "verdicts": [{"verdict": "refuted"}]},
            {"record_id": "r5", "kind": "pi_decision", "mode": "exploit"}]
    (d / "record.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    S = L.summarize("ll-x", tmp_path)
    assert (S["hits"], S["first_hit_units"], S["units_used"]) == (1, 2.5, 2.5)
    assert len(S["adapt_events"]) == 1 and L.list_ll_runs(tmp_path) == ["ll-x"]
    assert "eg_true" not in json.dumps(S) and "true_hits" not in json.dumps(S)


def test_no_runs_is_empty(tmp_path):
    assert L.summarize_all(tmp_path) == []
