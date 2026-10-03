import json
import re

from asd import cli_llm, llm_prior


def test_blind_prompt_has_no_domain_words_and_arm_runs_offline(monkeypatch):
    prompts = []

    def fake(prompt, model, seed, cache_dir=None):
        prompts.append(prompt)
        return json.dumps({c: 1000.0 + (hash(c) % 7) for c in re.findall(r"\b(c\d{3}):", prompt.split("Candidates to estimate:")[1])})

    monkeypatch.setattr(cli_llm, "ask", fake)
    r = llm_prior.run("llm_bo", 0, "blind", budget=12)
    assert r["spent"] == 12 and r["prior_missing"] == 0
    for p in prompts:
        assert not re.search(r"steel|yield|MPa|alloy|wt%|Fe\b|matbench|matminer", p, re.I)
        assert "Mn=" not in p


def test_counterfactual_swaps_labels_only_oracle_unchanged():
    from asd.replay import ReplayOracle
    o = ReplayOracle(0, 60)
    ids = o.ids()[:20]
    before = [o.features(c) for c in ids]
    named = llm_prior._view_rows(o, 0, "named", ids)
    cf = llm_prior._view_rows(o, 0, "cfnamed", ids)
    assert [o.features(c) for c in ids] == before
    assert named != cf
    for a, b in zip(named, cf):
        da = dict(p.split("=") for p in a.split(", "))
        db = dict(p.split("=") for p in b.split(", "))
        assert da["Ni"] == db["Mn"] and da["Mn"] == db["Ni"]
        assert {k: v for k, v in da.items() if k not in ("Ni", "Mn")} == {k: v for k, v in db.items() if k not in ("Ni", "Mn")}
    o2, o3 = ReplayOracle(0, 60), ReplayOracle(0, 60)
    llm_prior._view_rows(o2, 0, "cfnamed", o2.ids())
    assert o2.run(ids[0]) == o3.run(ids[0])
