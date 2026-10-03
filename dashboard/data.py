"""Read-only loaders over committed runs/* and results/*. No network, no LLM."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"


def jl(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def jf(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def list_runs():
    return sorted(p.name for p in RUNS.iterdir() if (p / "record.jsonl").exists())


def load_record(run):
    return jl(RUNS / run / "record.jsonl")


def load_judge(run):
    return jl(RUNS / run / "judge.jsonl")


def judge_runs():
    return sorted(p.name for p in RUNS.iterdir() if (p / "judge.jsonl").exists())


def annotate_adapt(record):
    """Mark test_choice entries that follow a surprising/reopened analysis as ADAPT."""
    out, adapt = [], False
    for e in record:
        e = dict(e)
        if e.get("kind") == "analysis":
            adapt = bool(e.get("surprising") or e.get("reopened_assumptions"))
        elif e.get("kind") == "test_choice":
            e["adapt"] = adapt
            adapt = False
        out.append(e)
    return out


def load_arena():
    a = RUNS / "arena"
    return {
        "hypotheses": jl(a / "hypotheses.jsonl"),
        "critiques": {c["hypothesis_id"]: c for c in jl(a / "critiques.jsonl")},
        "elo": jl(a / "elo.jsonl"),
        "calibration": jf(RESULTS / "arena_calibration.json"),
    }


def load_policies():
    deny = []
    for e in jl(RUNS / "policy_demo" / "session.jsonl"):
        if e.get("type") == "function_call_output" and "Denied by policy" in str(e.get("output")):
            deny.append(str(e["output"]))
    ev = RUNS / "t011-repl30" / "APPROVAL_EVIDENCE.md"
    ask_calls = [e for e in jl(RUNS / "t011-ask" / "transcript.jsonl")
                 if e.get("type") in ("function_call", "function_call_output")]
    return {
        "deny": deny,
        "policy_demo_ledger": jl(RUNS / "policy_demo" / "ledger.jsonl"),
        "approval_evidence": ev.read_text(encoding="utf-8") if ev.exists() else "",
        "ask_meta": jf(RUNS / "t011-ask" / "meta.json"),
        "ask_calls": ask_calls,
    }


def load_results():
    return {"summary": jf(RUNS / "t009" / "summary.json"),
            "blind20": jf(RUNS / "t009" / "blind20_summary.json"),
            "headline": DOCS / "headline.png"}


def readme_section(title):
    """Exact README text of a '## title' section (caveats are shown verbatim)."""
    txt = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"^## " + re.escape(title) + r"\n(.*?)(?=^## |\Z)", txt, re.S | re.M)
    return m.group(1).strip() if m else ""


def parse_all():
    """Parse every run directory; return entry counts (used by the smoke test)."""
    n = {}
    for r in list_runs():
        n[r] = len(annotate_adapt(load_record(r)))
    for r in judge_runs():
        n["judge:" + r] = len(load_judge(r))
    load_arena(), load_policies(), load_results()
    return n
