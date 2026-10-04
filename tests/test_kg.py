"""Knowledge graph: construction on a fixture, no hidden truth, fresh-process round trip for the tools."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from asd import kg

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = ("true_hit", "eg_true", "lt_true", "ground_truth", "true_hits")


def _write(p, rows):
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def steel_fixture(d):
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps({"run_id": "fx", "seed": 1, "budget": 10}))
    _write(d / "ledger.jsonl", [{"step": 1, "id": "c001", "value": 1000.0, "is_hit": False, "budget_used": 1},
                                {"step": 2, "id": "c002", "value": 2100.0, "is_hit": True, "budget_used": 2}])
    rec = [
        {"record_id": "rec-0001", "kind": "literature", "query": "q", "citations": [
            {"id": "https://openalex.org/W111", "title": "Paper A", "year": 2020, "doi": "d", "source": "OpenAlex"},
            {"id": "https://openalex.org/W222", "title": "Paper B", "year": 2021, "doi": "d", "source": "OpenAlex"}]},
        {"record_id": "rec-0002", "kind": "hypothesis", "id": "H1", "text": "agent-generated hypothesis: c001 is strong",
         "candidate_ids": ["c001"], "predicted_value": 2000, "assumption": "peak aged", "citations": ["W111"],
         "label": "agent-generated hypothesis (unvalidated)"},
        {"record_id": "rec-0003", "kind": "test_choice", "chosen": "run c001 (tests H1)", "options": [
            {"name": "run c001 (tests H1)", "candidate_id": "c001", "score": 0.7},
            {"name": "run c002", "candidate_id": "c002", "score": 0.5}], "reasons": ["r1", "r2"]},
        {"record_id": "rec-0004", "kind": "experiment", "id": "c001", "value": 1000.0, "is_hit": False, "cost": 1,
         "budget_used": 1, "hypothesis_id": "H1"},
        {"record_id": "rec-0005", "kind": "analysis", "hypothesis_id": "H1", "value": 1000.0, "predicted": 2000,
         "rel_error": 0.5, "supported": False, "is_hit": False, "surprising": True, "reopened_assumptions": ["peak aged"]},
        {"record_id": "rec-0006", "kind": "test_choice", "chosen": "run c002 after H1 failed", "options": [
            {"name": "run c002 after H1 failed", "candidate_id": "c002", "score": 0.6}], "reasons": ["H1 refuted"]},
        {"record_id": "rec-0007", "kind": "experiment", "id": "c002", "value": 2100.0, "is_hit": True, "cost": 1,
         "budget_used": 2, "hypothesis_id": ""},
    ]
    _write(d / "record.jsonl", rec)
    return d


def types(d, t):
    return [e for e in d["edges"] if e["type"] == t]


def test_steel_fixture_graph(tmp_path):
    d = kg.build_steel(steel_fixture(tmp_path / "run")).to_dict()
    ids = {n["id"] for n in d["nodes"]}
    assert {"q:1", "hyp:H1", "exp:c001", "exp:c002", "find:rec-0005", "dec:rec-0003", "dec:rec-0006"} <= ids
    assert [(e["src"], e["dst"], e["inferred"]) for e in types(d, "refutes")] == [("find:rec-0005", "hyp:H1", False)]
    assert ("hyp:H1", "cit:W111") in [(e["src"], e["dst"]) for e in types(d, "cites")]
    assert any(e["src"] == "exp:c001" and e["dst"] == "hyp:H1" and not e["inferred"] for e in types(d, "tests"))
    assert any(e["src"] == "find:rec-0005" and e["dst"] == "hyp:H1" for e in types(d, "reopens"))
    # the refuting finding caused the next decision; the decision text cites H1, so the link is not inferred
    cd = [e for e in types(d, "caused_decision") if e["src"] == "find:rec-0005"]
    assert cd and cd[0]["dst"] == "dec:rec-0006" and not cd[0]["inferred"]
    assert any(e["src"] == "dec:rec-0006" and e["dst"] == "exp:c002" for e in types(d, "led_to"))
    node = {n["id"]: n for n in d["nodes"]}
    assert node["hyp:H1"]["agent_generated"] and "agent-generated" in node["hyp:H1"]["label_note"]
    assert node["exp:c001"]["evidence"]["ledger_value_mpa"] == 1000.0 and node["exp:c001"]["source"].endswith("ledger step 1")
    assert node["cit:W222"]["used"] is False and node["cit:W111"]["used"] is True
    assert {e["type"] for e in d["edges"]} <= set(kg.EDGE_TYPES)
    c = kg.chain(d, "find:rec-0005")
    assert {"exp:c001", "hyp:H1", "cit:W111", "dec:rec-0006", "exp:c002"} <= set(c["nodes"])


def test_missing_inputs_are_graceful(tmp_path):
    g = kg.build_steel(tmp_path / "nothing").to_dict()
    assert g["meta"]["warnings"] and g["meta"]["counts"]["question"] == 1
    d = steel_fixture(tmp_path / "r2")
    (d / "ledger.jsonl").unlink()
    assert kg.build_steel(d).to_dict()["meta"]["counts"]["experiment"] == 2
    assert kg.build_run(tmp_path / "empty").to_dict()["nodes"]


def test_committed_runs_build():
    for rd in sorted((ROOT / "runs").iterdir()):
        if rd.is_dir() and (rd / "record.jsonl").exists() and not rd.name.startswith("ll-"):
            d = kg.build_steel(rd).to_dict()
            ids = {n["id"] for n in d["nodes"]}
            assert all(e["src"] in ids and e["dst"] in ids for e in d["edges"]), rd


def test_labloop_trace_graph_has_no_hidden_truth():
    from labloop.campaign import Config, run_campaign
    t = run_campaign(Config(seed=7, budget=30, world=2000, record_maps=False))
    assert "true_hits_found" in t["summary"]  # the trace itself carries truth; the graph must not
    d = kg.build_labloop_trace(t).to_dict()
    s = json.dumps(d).lower()
    assert not any(k in s for k in FORBIDDEN)
    assert t["world"]["description"] not in s
    assert d["meta"]["counts"]["experiment"] == t["summary"]["experiments"]  # only tested compositions appear
    ids = {n["id"] for n in d["nodes"]}
    assert all(e["src"] in ids and e["dst"] in ids for e in d["edges"])
    assert all(n["agent_generated"] for n in d["nodes"] if n["type"] == "hypothesis")
    assert any(e["inferred"] for e in d["edges"]) and any(not e["inferred"] for e in d["edges"])


def test_check_clean_rejects_truth_keys():
    with pytest.raises(ValueError):
        kg.check_clean({"a": [{"true_hit": True}]})


def test_notebook_and_record_builders(tmp_path):
    from labloop.notebook import Notebook
    nb = Notebook(tmp_path / "notebook.sqlite")
    nb.log_decision(1, "seed", "start", ["s"])
    nb.log_experiment(1, {"id": "E001", "formula": "CsPbI3", "key": "k", "purpose": "p", "hypothesis": "H1",
                          "result": {"ok": True, "bandgap_ev": 1.3, "log_t80": 2.8, "phase": "pure", "cost": 1.0},
                          "surprise": 0.1, "protocol": {}})
    nb.log_hypothesis(1, "H1", "falsified", "n=3")
    nb.commit()
    nb.db.close()
    rec = [{"kind": "ll_start", "world": 2000, "budget": 60},
           {"kind": "arena_round", "admitted": [{"id": "H1", "prediction": "p", "source": "rule_based"}]},
           {"kind": "pi_decision", "mode": "seed", "rationale": "start"}]
    _write(tmp_path / "record.jsonl", rec)
    d = kg.build_run(tmp_path).to_dict()
    ids = {n["id"] for n in d["nodes"]}
    assert {"exp:E001", "dec:R1", "find:R1:H1", "hyp:H1"} <= ids
    assert any(e["type"] == "refutes" for e in d["edges"])
    assert all(e["src"] in ids and e["dst"] in ids for e in d["edges"])


def run_py(code, env):
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**os.environ, **env}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_tools_fresh_process_round_trip(tmp_path):
    rd = steel_fixture(tmp_path / "run")
    env = {"ASD_RUN_DIR": str(rd)}
    upd = ("import json;from asd.kg_tools import kg_update;print(json.dumps(kg_update('finding','replicate',"
           "'c001 re-measured at 1010 MPa','{\"value_mpa\":1010}','rec-0004',"
           "[{'dst':'hyp:H1','type':'supports','basis':'rec-0004'},{'dst':'dec:rec-0006','type':'caused_decision'}])))")
    a = run_py(upd, env)
    assert a["accepted"] and a["links_added"] == 2 and a["record_id"] == "rec-0008"
    q = run_py("import json;from asd.kg_tools import kg_query;print(json.dumps(kg_query('why','dec:rec-0006')))", env)
    caused = {c["id"]: c for c in q["caused_by"]}
    assert "kgx:replicate" in caused and caused["kgx:replicate"]["inferred"] is True  # no record cited as basis
    n = run_py("import json;from asd.kg_tools import kg_query;print(json.dumps(kg_query('node','kgx:replicate')))", env)
    assert n["node"]["source_verified"] is True
    assert any(e["type"] == "supports" and e["inferred"] is False for e in n["edges"])  # basis is a real record id
    s = run_py("import json;from asd.kg_tools import kg_query;print(json.dumps(kg_query('summary')))", env)
    assert s["counts"]["finding"] == 2
    assert (rd / "kg.jsonl").exists() and json.loads((rd / "record.jsonl").read_text().splitlines()[-1])["kind"] == "kg_update"


def test_tools_reject_bad_input_and_hidden_truth(tmp_path, monkeypatch):
    from asd import kg_tools as T
    monkeypatch.setenv("ASD_RUN_DIR", str(steel_fixture(tmp_path / "run")))
    assert not T.kg_update("finding", "x", "ok", '{"true_hit": true}')["accepted"]
    assert not T.kg_update("finding", "x", "uses eg_true values")["accepted"]
    assert not T.kg_update("finding", "x", "ok", "", "", [{"dst": "nope", "type": "supports"}])["accepted"]
    assert not T.kg_update("finding", "x", "ok", "", "", [{"dst": "hyp:H1", "type": "made_up"}])["accepted"]
    assert not T.kg_update("bogus", "x", "ok")["accepted"]
    assert not T.kg_update("finding", "hyp:H1", "dup")["accepted"]
    assert "error" in T.kg_query("node", "missing")
    out = json.dumps([T.kg_query("summary"), T.kg_query("open"), T.kg_query("list", node_type="experiment")]).lower()
    assert not any(k in out for k in FORBIDDEN)
    monkeypatch.delenv("ASD_RUN_DIR")
    monkeypatch.delenv("LC_ASD_RUN_DIR", raising=False)
    with pytest.raises(T.KGConfigError):
        T.kg_query("summary")


def test_unowned_run_dir_gets_no_record_file(tmp_path, monkeypatch):
    from asd import kg_tools as T
    monkeypatch.setenv("ASD_RUN_DIR", str(tmp_path / "fresh"))
    assert T.kg_update("question", "q9", "A question")["record_id"] is None
    assert not (tmp_path / "fresh" / "record.jsonl").exists()


def test_make_kg_embeds_idempotently(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_kg
    html = tmp_path / "kg.html"
    html.write_text((ROOT / "docs" / "kg.html").read_text())
    for _ in range(2):
        make_kg.main(["--steel-run", str(steel_fixture(tmp_path / "s")), "--labloop-run", str(tmp_path / "none"),
                      "--budget", "15", "--out-dir", str(tmp_path), "--html", str(html)])
    text = html.read_text()
    assert text.count('id="kg-steel"') == 1 and text.count('id="kg-labloop"') == 1
    lab = json.loads((tmp_path / "kg_labloop.json").read_text())
    assert "OFFLINE" in lab["meta"]["note"]
    assert not any(k in text.lower() for k in FORBIDDEN)
