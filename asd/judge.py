"""Judge: rubric scoring of an analysis conclusion against the run record (Haiku 4.5, cached CLI path).
The judge sees the conclusion, its hypothesis and the ledger value only; never the oracle outcome label."""
import json

from . import schemas as S
from .cli_llm import ask, parse_json

MODEL = "claude-haiku-4-5-20251001"
RUBRIC = """Judge one analysis conclusion from a research run. Rubric:
1 supported_by_ledger: the conclusion's `supported` flag matches the ledger value versus the hypothesis prediction (supported = within 25 percent relative error).
2 citations_present: the hypothesis has a non-empty citations list.
3 labelled_agent_generated: the hypothesis is labelled as agent-generated.
Then give confidence (low|medium|high) that the conclusion is correct, and a one-sentence reason.
Reply with JSON only: {"conclusion_id": "<id>", "checks": {"supported_by_ledger": bool, "citations_present": bool, "labelled_agent_generated": bool}, "confidence": "low|medium|high", "reason": "<=1 sentence"}
"""


def build_prompt(conclusion, hyp, ledger_value):
    ctx = {"conclusion": {k: conclusion.get(k) for k in ("record_id", "hypothesis_id", "supported", "surprising",
                                                         "reopened_assumptions")},
           "hypothesis": {k: (hyp or {}).get(k) for k in ("id", "text", "predicted_value", "citations", "label")},
           "ledger_value_MPa": ledger_value}
    return RUBRIC + "\n" + json.dumps(ctx, ensure_ascii=False)


def judge(conclusion, hyp, ledger_value, cache_dir="runs/judge_cache", seed=0):
    out = parse_json(ask(build_prompt(conclusion, hyp, ledger_value), model=MODEL, seed=seed, cache_dir=cache_dir))
    out["conclusion_id"] = conclusion["record_id"]
    return S.check(out, S.JUDGE_VERDICT)
