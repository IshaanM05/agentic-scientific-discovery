"""Compact, read-only summary of committed LabLoop Omnigent runs (runs/ll-*/record.jsonl).

No network, no LLM. Shared by dashboard/app.py and scripts/build_dashboard.py. Field names follow the
W1 record kinds (ll_start, literature, arena_round, pi_decision, design, experiment, analysis,
judge_verdict) and are read defensively, so a missing field never crashes the replay. Hidden ground
truth is dropped even if a record carried it."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIDDEN = {"eg_true", "lt_true", "true_hits", "world_params", "params", "truth"}
KEEP = ("record_id", "kind", "round", "mode", "rationale", "slot_id", "purpose", "composition", "formula",
        "bandgap", "eg", "t80", "meets_spec", "hit", "cost", "units_charged", "budget_left", "hypothesis_id",
        "verdict", "verdicts", "findings", "surprises", "relaxations", "replicated", "discoveries", "source",
        "label", "agent_generated", "decision")


def _jl(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _clean(e):
    return {k: e[k] for k in KEEP if k in e and k not in HIDDEN}


def _is_hit(e):
    return bool(e.get("meets_spec") or e.get("hit"))


def _units(e):
    v = e.get("units_charged", e.get("cost", 0))
    return float(v) if isinstance(v, (int, float)) else 0.0


def list_ll_runs(runs_dir=None):
    d = Path(runs_dir) if runs_dir else ROOT / "runs"
    return sorted(p.name for p in d.glob("ll-*") if (p / "record.jsonl").exists())


def summarize(run, runs_dir=None):
    d = (Path(runs_dir) if runs_dir else ROOT / "runs") / run
    rec = _jl(d / "record.jsonl")
    start = next((e for e in rec if e.get("kind") == "ll_start"), {})
    exps = [e for e in rec if e.get("kind") == "experiment"]
    units, first_hit, hits, curve = 0.0, None, 0, []
    for e in exps:
        units += _units(e)
        if _is_hit(e):
            hits += 1
            if first_hit is None:
                first_hit = round(units, 2)
        curve.append([round(units, 2), hits])
    refuted, adapt, pending = 0, [], None
    for e in rec:
        k = e.get("kind")
        if k == "analysis":
            if isinstance(e.get("refuted"), list):  # live asd.labloop_tools schema: ids refuted in this analysis
                n_ref = len(e["refuted"])
            else:
                vs = e.get("verdicts") or e.get("hypothesis_verdicts") or []
                n_ref = sum(1 for v in vs if "refuted" in json.dumps(v).lower()) if isinstance(vs, list) else 0
            relaxed = bool(e.get("relaxations") or e.get("prior_relaxations"))
            refuted += n_ref
            pending = {"after": e.get("record_id"), "refuted": n_ref, "relaxed": relaxed} if (n_ref or relaxed) else pending
        elif k == "pi_decision" and (pending or "ADAPT" in str(e.get("planner_rationale") or "")):
            base = pending or {"after": None, "refuted": 0, "relaxed": False}
            adapt.append({**base, "next_decision": e.get("record_id"), "mode": e.get("mode"),
                          "planner_adapt_line": "ADAPT" in str(e.get("planner_rationale") or "")})
            pending = None
    judge = [e for e in rec if e.get("kind") == "judge_verdict"]
    disc = (judge[-1].get("discovery_verdicts") or judge[-1].get("discoveries") or []) if judge else []
    n_disc = sum(1 for x in disc if isinstance(x, dict) and x.get("replicated")) if isinstance(disc, list) else 0
    return {
        "run": run, "world": start.get("world"), "seed": start.get("seed"), "budget": start.get("budget"),
        "n_records": len(rec), "n_experiments": len(exps), "units_used": round(units, 2), "hits": hits,
        "first_hit_units": first_hit, "curve": curve, "hypotheses_refuted": refuted,
        "adapt_events": adapt, "discoveries_replicated": n_disc,
        "timeline": [_clean(e) for e in rec if e.get("kind") != "ll_start"],
    }


def summarize_all(runs_dir=None):
    return [summarize(r, runs_dir) for r in list_ll_runs(runs_dir)]
