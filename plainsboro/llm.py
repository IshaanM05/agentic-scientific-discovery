"""Optional LLM layer (OpenAI-compatible). The lab runs fully without it.

* `Narrator` voices agent messages in character for the demo. It never changes
  structured outputs: decisions, numbers and IDs come from the deterministic agents.
* `single_agent_diagnose` is baseline B0 (design 12.1): one LLM with the same
  test tools, data and budget that picks its own tests and verdict.

Configure with OPENAI_API_KEY (and optionally OPENAI_BASE_URL, PP_LLM_MODEL).
"""
from __future__ import annotations

import json
import os

from .config import HYP_IDS, HYP_LABELS
from .vetting.registry import REGISTRY

DEFAULT_MODEL = os.environ.get("PP_LLM_MODEL", "gpt-4o-mini")

PERSONAS = {
    "house": "Dr. Gregory House: sardonic, contrarian, brilliant; assumes the obvious answer is wrong.",
    "foreman": "Dr. Eric Foreman: rigorous skeptic who demands controls.",
    "cuddy": "Dr. Lisa Cuddy: decisive administrator who guards the budget.",
    "cameron": "Dr. Allison Cameron: careful,  evidence-first.",
}


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _client():
    from openai import OpenAI
    return OpenAI()


class Narrator:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = _client()
        self.failures = 0

    def voice(self, agent: str, text: str) -> str:
        if self.failures > 2:
            return text
        try:
            r = self.client.chat.completions.create(
                model=self.model, temperature=0.4, max_tokens=160,
                messages=[{"role": "system", "content":
                           f"Rewrite the message in the voice of {PERSONAS[agent]} in at most 2 sentences. "
                           "Keep EVERY number, test ID, hypothesis ID, run ID and citation exactly. "
                           "Do not add facts or claims."},
                          {"role": "user", "content": text}])
            return r.choices[0].message.content.strip() + "   [LLM-voiced]"
        except Exception:
            self.failures += 1
            return text


B0_SYSTEM = """You are an expert exoplanet vetter working alone. A transit-like signal must be classified as one of:
H1 planet; H2 eclipsing binary on target; H3 blended background eclipsing binary; H4 stellar variability/spots;
H5 instrumental artifact. You can run diagnostic tests (tool run_test) under a budget of {max_tests} tests and
{max_cost} cost units. Choose tests wisely; stop when confident. Finish by calling final_answer with your label and
a probability for each class."""


def single_agent_diagnose(target, outcomes: dict, budget: dict, model: str = DEFAULT_MODEL, max_turns: int = 12):
    """Baseline B0. Uses the same cached outcomes (matched evidence) as every other condition."""
    client = _client()
    tools = [
        {"type": "function", "function": {
            "name": "run_test", "description": "Run one vetting test. Available: " + "; ".join(
                f"{t} (cost {d.cost:g}): {d.description}; outcomes {list(d.bin_labels)}" for t, d in REGISTRY.items()),
            "parameters": {"type": "object", "properties": {"test_id": {"type": "string", "enum": list(REGISTRY)}},
                           "required": ["test_id"]}}},
        {"type": "function", "function": {
            "name": "final_answer", "description": "Submit the classification.",
            "parameters": {"type": "object", "properties": {
                "label": {"type": "string", "enum": HYP_IDS},
                "probabilities": {"type": "object", "properties": {h: {"type": "number"} for h in HYP_IDS}},
                "rationale": {"type": "string"}}, "required": ["label", "probabilities"]}}}]
    s = target.signal
    msgs = [{"role": "system", "content": B0_SYSTEM.format(max_tests=budget["max_tests"], max_cost=budget["cost_units_max"])},
            {"role": "user", "content": f"Signal: period {s['period_d']:.4f} d, depth {s['depth_ppm']:.0f} ppm, duration "
                                        f"{s['duration_h']:.2f} h, SNR {s['snr']:.1f}. Star: {json.dumps(target.stellar)}."}]
    used, cost, run = 0, 0.0, []
    for _ in range(max_turns):
        r = client.chat.completions.create(model=model, messages=msgs, tools=tools, temperature=0)
        m = r.choices[0].message
        msgs.append(m.model_dump(exclude_none=True))
        if not m.tool_calls:
            msgs.append({"role": "user", "content": "Call run_test or final_answer."})
            continue
        for tc in m.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            if tc.function.name == "final_answer":
                probs = {h: float(args.get("probabilities", {}).get(h, 0)) for h in HYP_IDS}
                z = sum(probs.values()) or 1.0
                return {"label": args["label"], "posterior": {h: v / z for h, v in probs.items()}, "tests": used,
                        "cost": cost, "tests_run": run, "rationale": args.get("rationale", "")}
            tid = args.get("test_id")
            if tid not in REGISTRY or tid in run:
                out = {"error": "unknown or already-run test"}
            elif used + 1 > budget["max_tests"] or cost + REGISTRY[tid].cost > budget["cost_units_max"]:
                out = {"error": "budget exceeded; call final_answer"}
            else:
                o = outcomes[target.target_id][(tid, 3.0)]
                used += 1
                cost += REGISTRY[tid].cost
                run.append(tid)
                out = {"test_id": tid, "outcome": o["outcome_label"], "metrics": o["metrics"]}
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out)})
    return {"label": None, "posterior": {h: 0.2 for h in HYP_IDS}, "tests": used, "cost": cost, "tests_run": run,
            "rationale": "no answer within turn limit"}


def run_b0(n: int = 40, model: str = DEFAULT_MODEL):
    """python -c "from plainsboro.llm import run_b0; run_b0(40)" -> results/benchmark/b0_llm.jsonl"""
    from .config import RESULTS, experiment
    from .data.gatekeeper import load_set
    from .planner.outcomes import load_outcomes
    gk = load_set("blind")
    oc = load_outcomes(gk)
    out = RESULTS / "benchmark" / "b0_llm.jsonl"
    rows = []
    with open(out, "w", encoding="utf-8") as f:
        for i in gk.target_ids()[:n]:
            res = single_agent_diagnose(gk.get_target(i), oc, experiment()["budget"], model=model)
            truth = gk._label(i, "evaluator")
            row = {"target_id": i, "condition": "B0-single-llm", "model": model, "truth": truth,
                   "correct": res["label"] == truth, **res}
            rows.append(row)
            f.write(json.dumps(row) + "\n")
            print(i, truth, res["label"], res["tests_run"], flush=True)
    acc = sum(r["correct"] for r in rows) / len(rows)
    print(f"B0 ({model}) on {len(rows)}: acc={acc:.3f} mean cost={sum(r['cost'] for r in rows) / len(rows):.2f}")
    return rows
