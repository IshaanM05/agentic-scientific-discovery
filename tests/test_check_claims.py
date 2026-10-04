"""Tests for scripts/check_claims.py: a passing fixture, deliberate failures, and the real claims file."""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_claims as cc  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def make_tree(tmp_path, doc_text="Blind arm: 8.75 hits vs 6.40 (OFAT), paired CI [+1.75, +3.00].\n", claims=None):
    (tmp_path / "docs").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "README.md").write_text(doc_text, encoding="utf-8")
    (tmp_path / "runs" / "res.json").write_text(json.dumps(
        {"mean": 8.75, "arms/ofat": {"mean": 6.4, "ci": [1.75, 3.0]}, "hits": [3, 4, 5]}), encoding="utf-8")
    base = dict(doc="README.md", source="runs/res.json", tol=0.005)
    claims = claims or [
        dict(base, id="a", text="8.75 hits", value=8.75, key="mean"),
        dict(base, id="b", text="6.40 (OFAT)", value=6.40, key="arms/ofat/mean"),  # key containing "/"
        dict(base, id="c", text="[+1.75, +3.00]", value=3.00, key="arms/ofat/ci/1"),
        dict(base, id="d", text="+3.00]", value=3, key="hits/#len", tol=0),  # list length
    ]
    path = tmp_path / "docs" / "claims.yaml"
    path.write_text(yaml.safe_dump({"claims": claims, "scan": ["README.md"]}), encoding="utf-8")
    return path


def test_fixture_passes(tmp_path):
    path = make_tree(tmp_path)
    _, results, warnings, failed = cc.run(path, tmp_path)
    assert [r["status"] for r in results] == ["OK"] * 4
    assert failed == [] and warnings == []
    assert cc.main(["--root", str(tmp_path)]) == 0


def test_changed_number_fails(tmp_path):
    path = make_tree(tmp_path, doc_text="Blind arm: 8.95 hits vs 6.40 (OFAT), paired CI [+1.75, +3.00].\n")
    claims = yaml.safe_load(path.read_text())["claims"]
    claims[0].update(text="8.95 hits", value=8.95)  # document edited, source unchanged
    path.write_text(yaml.safe_dump({"claims": claims, "scan": ["README.md"]}), encoding="utf-8")
    _, results, _, failed = cc.run(path, tmp_path)
    assert [r["id"] for r in failed] == ["a"] and failed[0]["status"] == "MISMATCH"
    assert cc.main(["--root", str(tmp_path)]) == 1


def test_text_edited_in_document_is_caught(tmp_path):
    path = make_tree(tmp_path, doc_text="Blind arm: 9.10 hits vs 6.40 (OFAT), paired CI [+1.75, +3.00].\n")
    _, _, _, failed = cc.run(path, tmp_path)
    assert [(r["id"], r["status"]) for r in failed] == [("a", "TEXT-MISSING")]


def test_value_must_appear_in_text(tmp_path):
    claims = [dict(doc="README.md", source="runs/res.json", tol=0.005, id="x", text="8.75 hits", value=6.4,
                   key="arms/ofat/mean")]
    _, results, _, failed = cc.run(make_tree(tmp_path, claims=claims), tmp_path)
    assert failed[0]["status"] == "NUMBER-NOT-IN-TEXT"


def test_missing_source_key_and_skip(tmp_path):
    base = dict(doc="README.md", source="runs/res.json", tol=0)
    claims = [dict(base, id="k", text="8.75 hits", value=8.75, key="nope"),
              dict(base, id="s", text="8.75 hits", value=8.75, key="mean", source="runs/gone.json"),
              dict(base, id="b", text="8.75 hits", value=8.75, key="mean", source="runs/gone.json", branch="w2/x"),
              dict(base, id="d", text="8.75 hits", value=8.75, key="mean", doc="docs/absent.md")]
    _, results, _, failed = cc.run(make_tree(tmp_path, claims=claims), tmp_path)
    assert [r["status"] for r in results] == ["KEY-ERROR", "SOURCE-MISSING", "SKIP", "SKIP"]
    assert [r["id"] for r in failed] == ["k", "s"]
    _, _, _, strict_failed = cc.run(tmp_path / "docs" / "claims.yaml", tmp_path, strict=True)
    assert len(strict_failed) == 4


def test_bound_scale_and_pattern(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("p<0.001 and 87% found; held 22.2 s; 2 hits\n", encoding="utf-8")
    (tmp_path / "ev.md").write_text("Measured hold: 22.2 s\nhit hit\n", encoding="utf-8")
    (tmp_path / "r.json").write_text(json.dumps({"p": 4e-5, "frac": 0.87}), encoding="utf-8")
    base = dict(doc="README.md", tol=0.05)
    claims = [dict(base, id="p", text="p<0.001", value=0.001, source="r.json", key="p", op="lt"),
              dict(base, id="pct", text="87% found", value=87, source="r.json", key="frac", scale=100),
              dict(base, id="re", text="22.2 s", value=22.2, source="ev.md", pattern=r"hold: ([\d.]+) s"),
              dict(base, id="cnt", text="2 hits", value=2, source="ev.md", pattern="hit", count=True, tol=0)]
    path = tmp_path / "docs" / "claims.yaml"
    path.write_text(yaml.safe_dump({"claims": claims}), encoding="utf-8")
    _, results, _, failed = cc.run(path, tmp_path)
    assert failed == [] and [r["status"] for r in results] == ["OK"] * 4
    claims[0]["value"] = 0.00001  # p is no longer below the stated bound
    path.write_text(yaml.safe_dump({"claims": claims}), encoding="utf-8")
    assert cc.run(path, tmp_path)[1][0]["status"] == "MISMATCH"


def test_uncovered_number_is_a_warning_not_a_failure(tmp_path):
    path = make_tree(tmp_path, doc_text="Blind arm: 8.75 hits vs 6.40 (OFAT), paired CI [+1.75, +3.00]. Also 12.34 hits.\n")
    _, _, warnings, failed = cc.run(path, tmp_path)
    assert failed == [] and [w[2] for w in warnings] == ["12.34"]
    assert cc.main(["--root", str(tmp_path)]) == 0


def test_markdown_report(tmp_path):
    path = make_tree(tmp_path)
    out = tmp_path / "audit.md"
    assert cc.main(["--root", str(tmp_path), "--md", str(out)]) == 0
    assert "None: every sourced claim matches" in out.read_text(encoding="utf-8")


def test_bad_claims_file_rejected(tmp_path):
    bad = tmp_path / "c.yaml"
    bad.write_text(yaml.safe_dump({"claims": [{"id": "x", "text": "t", "doc": "d", "value": 1, "source": "s"}]}))
    with pytest.raises(ValueError, match="needs 'key' or 'pattern'"):
        cc.load_claims(bad)


def test_real_claims_file_loads():
    data = cc.load_claims(REPO / "docs" / "claims.yaml")
    assert len(data["claims"]) > 100 and data["unsourced"]
    assert {"README.md"} <= set(data["scan"])


def test_real_claims_match_committed_results():
    _, results, _, failed = cc.run(REPO / "docs" / "claims.yaml", REPO)
    assert not failed, [(r["id"], r["status"], r["note"]) for r in failed]
    assert sum(r["status"] == "OK" for r in results) > 100
