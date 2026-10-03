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
