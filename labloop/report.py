"""Traceable research report for a LabLoop run directory (notebook.sqlite, ll_state.json, record.jsonl).

Works on the offline rule-based campaign and on Omnigent runs (runs/ll-*). Core, checker and claim syntax live in
asd/report.py. The loader reads measured values only: it never touches hidden truth (true bandgap/T80, world
parameters, true hits), and refuses a run directory whose files mention any hidden-truth key.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from asd.report import Doc, ReportError, Sources, _jsonl, code, q, resolve
from labloop import literature
from labloop.chemistry import TARGET, is_hit

FILES = ("docs/CLOUD_WORKER_CONTEXT.md", "docs/CHALLENGE_BRIEF.md", "docs/LABLOOP_INTEGRATION.md",
         "asd/labloop_tools.py", "labloop/chemistry.py", "scripts/make_report.py")
RESOLVED = ("supported", "falsified", "qualified")


def _hyp_views(state: dict) -> dict:
    """Prediction and kill condition are properties of labloop's Hypothesis; rebuild them from ll_state.json."""
    from asd.labloop_tools import _hyp_from_dict
    out = {}
    for hid, d in state["hyps"].items():
        h, extra = _hyp_from_dict(d)
        out[hid] = {"id": hid, "statement": h.statement, "prediction": h.prediction, "kill_condition": h.kill_condition,
                    "status": h.status, "elo": round(h.elo, 1), "origin": h.origin, "label": extra.get("label"),
                    "source": extra.get("source"), "n_evidence": h.n_evidence, "created_round": h.created_round,
                    "pass_rate": None if h.pass_rate is None else round(h.pass_rate, 2), "confidence": h.confidence,
                    "sources": ", ".join(h.sources)}
    return out


def _short(detail: str) -> str:
    """Show long floats to two decimals (the checker allows display rounding)."""
    return re.sub(r"\d+\.\d{3,}", lambda m: str(round(float(m.group(0)), 2)), detail)


def load_labloop(run_dir) -> tuple[Sources, dict]:
    run_dir = resolve(run_dir)
    nbp, stp = run_dir / "notebook.sqlite", run_dir / "ll_state.json"
    if not nbp.exists():
        raise ReportError(f"{run_dir}: no notebook.sqlite")
    src, d = Sources(), {"dir": run_dir}
    db = sqlite3.connect(str(nbp))
    cols = ("id", "round", "formula", "purpose", "hypothesis", "ok", "bandgap", "log_t80", "phase", "cost", "surprise")
    d["nb_exp"] = [dict(zip(cols, r)) for r in db.execute(
        f"SELECT {', '.join(cols)} FROM experiments ORDER BY id")]
    d["nb_dec"] = [dict(zip(("round", "mode", "rationale", "slots"), r)) for r in db.execute(
        "SELECT round, mode, rationale, slots FROM decisions ORDER BY round")]
    d["nb_hyp"] = [dict(zip(("n", "round", "hypothesis", "event", "detail"), (i + 1,) + tuple(r))) for i, r in enumerate(
        db.execute("SELECT round, hypothesis, event, detail FROM hypothesis_events ORDER BY rowid"))]
    db.close()
    d["state"] = json.loads(stp.read_text()) if stp.exists() else None
    d["rec"] = _jsonl(run_dir / "record.jsonl")
    rnd = 0
    for e in d["rec"]:  # round of a record = number of pi_decision records so far
        rnd += e["kind"] == "pi_decision"
        e["_round"] = rnd
    for e in d["nb_exp"]:
        src.add(f"nb:{e['id']}", e)
    for e in d["nb_dec"]:
        src.add(f"nb:decision-{e['round']}", e)
    for e in d["nb_hyp"]:
        src.add(f"nb:hyp-{e['n']}", e)
    for e in d["rec"]:
        src.add(e["record_id"], {k: v for k, v in e.items() if k != "_round"})
    for c in literature.CLAIMS:
        src.add(f"lit:{c['id']}", c)
    d["hyps"] = {}
    if d["state"]:
        src.add("state:run", {k: d["state"][k] for k in ("world", "seed", "budget", "units_used", "round")})
        d["hyps"] = _hyp_views(d["state"])
        for hid, v in d["hyps"].items():
            src.add(f"state:{hid}", v)
    for f in FILES:
        src.file(f)
    hits = [e for e in d["nb_exp"] if e["ok"] and is_hit(e["bandgap"], e["log_t80"])]
    for e in d["nb_exp"]:
        e["hit"] = bool(e["ok"] and is_hit(e["bandgap"], e["log_t80"]))
    units, first = 0.0, None
    for e in d["nb_exp"]:
        units += e["cost"]
        if e["hit"] and first is None:
            first = (e["id"], round(units, 2))
    d["first_hit"] = first
    calcs = {"n_films": len(d["nb_exp"]), "n_failed": sum(1 for e in d["nb_exp"] if not e["ok"]),
             "n_spec_films": len(hits), "n_miss": sum(1 for e in d["nb_exp"] if e["ok"] and not e["hit"]),
             "n_formulas": len({e["formula"] for e in d["nb_exp"]}), "n_rounds": len(d["nb_dec"]),
             "units_nb": round(sum(e["cost"] for e in d["nb_exp"]), 2),
             "n_hyps": len(d["hyps"]), "n_refuted": sum(1 for h in d["hyps"].values() if h["status"] == "falsified"),
             "n_qualified": sum(1 for h in d["hyps"].values() if h["status"] == "qualified"),
             "n_supported": sum(1 for h in d["hyps"].values() if h["status"] == "supported"),
             "n_open": sum(1 for h in d["hyps"].values() if h["status"] in ("proposed", "testing")),
             "target_eg_min": TARGET["eg_min"], "target_eg_max": TARGET["eg_max"], "target_t80_h": TARGET["t80_min_hours"],
             "n_design_blocked": sum(1 for e in d["rec"] if e["kind"] == "design" for p in e["protocols"] if not p["runnable"]),
             "n_denials": sum(1 for e in d["rec"] if e["kind"] == "budget_or_safety_denial")}
    jl = [e for e in d["rec"] if e["kind"] == "judge_verdict"]
    ar = [e for e in d["rec"] if e["kind"] == "arena_round"]
    calcs.update(n_discoveries=len(jl[-1]["discovery_verdicts"]) if jl else 0,
                 n_replicated=sum(1 for x in jl[-1]["discovery_verdicts"] if x["replicated"]) if jl else 0,
                 n_arena_rounds=len(ar), n_admitted=sum(len(e["admitted"]) for e in ar),
                 n_fallback=sum(len(e["rule_based_fallback"]) for e in ar))
    for lab in ("literature", "rule_based", "agent-generated"):
        calcs[f"n_{lab.replace('-', '_')}"] = sum(1 for h in d["hyps"].values() if h["label"] == lab)
    if first:
        calcs["first_hit_units"] = first[1]
    for k, v in calcs.items():
        src.calc(k, v)
    for e in d["rec"]:
        if e["kind"] == "analysis":
            src.calc(f"nevents_{e['record_id']}", len(e["events"]))
        if e["kind"] == "arena_round":
            src.calc(f"nadm_{e['record_id']}", len(e["admitted"]))
    leaks = src.leaks()
    if leaks:
        raise ReportError("hidden-truth term in run sources: " + "; ".join(leaks[:3]))
    d["calcs"] = calcs
    return src, d


def render_labloop(run_dir) -> str:
    src, d = load_labloop(run_dir)
    rec, hyps, nbx, dec = d["rec"], d["hyps"], d["nb_exp"], d["nb_dec"]
    by = lambda k: [e for e in rec if e["kind"] == k]
    st = d["state"] or {}
    doc = Doc(src, {"kind": "labloop", "run_dir": str(Path(run_dir).as_posix())})
    CTX, INT, BRIEF = "file:docs/CLOUD_WORKER_CONTEXT.md", "file:docs/LABLOOP_INTEGRATION.md", "file:docs/CHALLENGE_BRIEF.md"
    pis = by("pi_decision")
    offline = bool(pis) and all("offline rule-based run" in e.get("planner_rationale", "") for e in pis)
    doc.raw(f"# Research report: LabLoop simulated perovskite lab ({Path(run_dir).name})")
    doc.raw()
    doc.raw("> Auto-generated from the run notebook and records by a template; no model wrote this text [src: file:scripts/make_report.py]")
    doc.raw("> LabLoop is a team-built simulator with synthetic hidden physics: a benchmark, not evidence about real devices [src: file:docs/LABLOOP_INTEGRATION.md]")
    doc.h(2, "1. Question and run type")
    doc.claim("Which halide-perovskite compositions have a bandgap of 1.24 to 1.38 eV and a T80 of at least 500 h in a simulated lab, "
              "when the textbook prior says none qualify", "calc:target_eg_min", "calc:target_eg_max", "calc:target_t80_h", CTX)
    if st:
        doc.claim(f"The run used world {st['world']}, seed {st['seed']} and a budget of {st['budget']} units", "state:run",
                  *( [rec[0]["record_id"]] if rec else []))
    if offline:
        doc.claim("This is an offline rule-based run: no Omnigent planner and no model took part, so it shows the LabLoop baseline loop, not the Omnigent system",
                  pis[0]["record_id"])
        doc.claim(f"The recorded planner text reads {q(pis[0]['planner_rationale'], 100)}", pis[0]["record_id"])
    elif pis:
        doc.claim("This run was orchestrated through the Omnigent tools and records a planner rationale for each decision", pis[0]["record_id"])
    doc.claim(f"The notebook holds {len(nbx)} films across {len(dec)} rounds and {st.get('units_used', 'n/a')} units were spent"
              if st else f"The notebook holds {len(nbx)} films across {len(dec)} rounds",
              "calc:n_films", "calc:n_rounds", *(["state:run"] if st else []))
    # evidence
    doc.h(2, "2. Evidence: sourced literature claims the agents started from")
    doc.table(["id", "claim", "citation"], [([c["id"], q(c["claim"], 120), q(c["source"], 80)], [f"lit:{c['id']}"])
                                            for c in literature.CLAIMS])
    # hypotheses
    doc.h(2, "3. Hypotheses (all produced by agents; none validated)")
    doc.claim(f"The arena holds {len(hyps)} hypotheses, each labelled with its origin: literature-seeded by a rule-based agent, rule-based from an anomaly, or model-written",
              "calc:n_hyps", "calc:n_literature", "calc:n_rule_based", "calc:n_agent_generated")
    rows = []
    for h in hyps.values():
        lab = {"agent-generated": "agent-generated (model)", "rule_based": "agent-generated (rule-based, no model)",
               "literature": "agent-generated (rule-based, from cited literature)"}.get(h["label"], str(h["label"]))
        ev = f"n={h['n_evidence']}" + (f", pass rate {h['pass_rate']}" if h["pass_rate"] is not None else "")
        rows.append(([h["id"], lab, q(h["prediction"], 110), q(h["kill_condition"], 110), h["status"], ev], [f"state:{h['id']}"]))
    doc.table(["id", "label", "prediction", "kill condition", "final status", "evidence"], rows)
    for ev in [e for e in d["nb_hyp"] if e["event"] in RESOLVED]:
        doc.claim(f"Round {ev['round']}: hypothesis {ev['hypothesis']} was recorded as {ev['event']} ({_short(ev['detail'])})", f"nb:hyp-{ev['n']}")
    # experiments
    doc.h(2, "4. Experiments and measured values")
    doc.claim("Each row is one simulated film: the notebook id, the measured bandgap and log10 T80, and the surrogate's bandgap prediction made before the run",
              "nb:E001")
    recx = {e["exp_id"]: e for e in by("experiment")}
    rows = []
    for e in nbx:
        r = recx.get(e["id"])
        out = "failed film" if not e["ok"] else ("meets spec" if e["hit"] else "misses spec")
        pred = r["predicted"]["eg"] if r else "n/a"
        rows.append(([e["id"], e["round"], code(e["formula"]), e["bandgap"] if e["ok"] else "n/a", e["log_t80"] if e["ok"] else "n/a",
                      pred, out, e["cost"]], [f"nb:{e['id']}"] + ([r["record_id"]] if r else [])))
    doc.table(["id", "round", "composition", "bandgap (eV)", "log10 T80", "predicted bandgap (eV)", "outcome", "cost"], rows)
    hit_ids = [e["id"] for e in nbx if e["hit"]]
    doc.claim(f"{len(hit_ids)} of {len(nbx)} films met the spec ({TARGET['eg_min']} to {TARGET['eg_max']} eV and T80 of at least {TARGET['t80_min_hours']:.0f} h)",
              "calc:n_spec_films", "calc:n_films", "calc:target_eg_min", "calc:target_eg_max", "calc:target_t80_h")
    doc.claim(f"These {len(hit_ids)} films cover {len({e['formula'] for e in nbx if e['hit']})} distinct compositions, so repeats are not new discoveries",
              "calc:n_spec_films", *[f"nb:{i}" for i in hit_ids[:6]])
    if d["first_hit"]:
        doc.claim(f"The first spec-meeting film was {d['first_hit'][0]} after {d['first_hit'][1]} units", f"nb:{d['first_hit'][0]}", "calc:first_hit_units")
    else:
        doc.claim("No film met the spec in this run", "calc:n_spec_films")
    # discoveries
    judges = by("judge_verdict")
    doc.h(2, "5. Discovery verdicts (replication rubric)")
    if judges:
        jv = judges[-1]
        doc.table(["composition", "status", "confidence", "films", "bandgap (eV)", "T80 (h)", "reason"],
                  [([code(x["formula"]), x["status"], x["confidence"], x["n_films"], x["eg"], x["t80_h"], q(x["reason"], 80)], [jv["record_id"]])
                   for x in jv["discovery_verdicts"]])
        nconf = sum(1 for x in jv["discovery_verdicts"] if x["replicated"])
        doc.claim(f"{nconf} of {len(jv['discovery_verdicts'])} discovery candidates were replicated at the final judge call",
                  jv["record_id"], "calc:n_discoveries", "calc:n_replicated")
    else:
        doc.claim("No judge verdict was recorded", "calc:n_rounds")
    # negative results
    doc.h(2, "6. Negative results (kept, not hidden)")
    doc.claim(f"{d['calcs']['n_failed']} films failed to form a usable phase", "calc:n_failed")
    for e in [e for e in nbx if not e["ok"]][:12]:
        doc.claim(f"Film {e['id']} ({code(e['formula'])}) failed with phase {q(e['phase'], 60)}", f"nb:{e['id']}")
    doc.claim(f"{d['calcs']['n_miss']} measured films missed the spec", "calc:n_miss")
    for h in [h for h in hyps.values() if h["status"] == "falsified"]:
        doc.claim(f"Hypothesis {h['id']} was falsified after {h['n_evidence']} films: {q(h['prediction'], 100)}", f"state:{h['id']}")
    for h in [h for h in hyps.values() if h["status"] == "qualified"]:
        doc.claim(f"Hypothesis {h['id']} holds only with exceptions after {h['n_evidence']} films", f"state:{h['id']}")
    # decisions
    doc.h(2, "7. What changed the planner's decisions")
    arena = by("arena_round")
    doc.table(["round", "mode", "LabLoop rationale", "planner rationale"],
              [([x["round"], x["mode"], q(x["rationale"].split(" || planner:")[0], 130), q(x["rationale"].split(" || planner:")[1].strip(), 80) if " || planner:" in x["rationale"] else "none"],
                [f"nb:decision-{x['round']}"]) for x in dec])
    for a, b in zip(dec, dec[1:]):
        if a["mode"] != b["mode"]:
            doc.claim(f"The PI mode changed from {a['mode']} in round {a['round']} to {b['mode']} in round {b['round']}",
                      f"nb:decision-{a['round']}", f"nb:decision-{b['round']}")
    relax = [(a, r) for a in by("analysis") for r in a["prior_relaxations"]]
    for a in by("analysis"):
        evs = [ev for ev in a["events"] if ev["type"] in ("surprise", "falsified", "qualified", "revision")]
        for ev in evs[:4]:
            doc.claim(f"Round {a['_round']} analysis reported a {ev['type']} event: {q(ev['text'], 120)}", a["record_id"])
    for a, r in relax:
        doc.claim(f"ADAPT: the {r['prop']} prior was relaxed after hypothesis {r['after_hypothesis']} was {r['status']}", a["record_id"])
    if not relax:
        doc.claim("No literature prior was relaxed in this run", "calc:n_rounds")
    for e in arena:
        for rj in e["rejected"]:
            doc.claim(f"A proposed hypothesis was rejected: {q(rj['reason'], 100)}", e["record_id"])
    nadm = sum(len(e["admitted"]) for e in arena)
    nfb = sum(len(e["rule_based_fallback"]) for e in arena)
    doc.claim(f"Across {len(arena)} arena rounds {nadm} model proposals were admitted and {nfb} rule-based anomaly hypotheses were added",
              "calc:n_arena_rounds", "calc:n_admitted", "calc:n_fallback")
    # safety
    doc.h(2, "8. Safety, controls and human approval")
    doc.claim(f"{d['calcs']['n_design_blocked']} designed protocols were marked not runnable by the safety review", "calc:n_design_blocked")
    doc.claim(f"The budget gate recorded {d['calcs']['n_denials']} denial record(s) when a film would exceed the unit budget", "calc:n_denials")
    for e in [e for e in by("budget_or_safety_denial")][:3]:
        for x in e["denied"][:2]:
            doc.claim(f"Denied slot {code(x['slot_id'])}: {q(x['reason'], 110)}", e["record_id"])
    doc.claim("Restricted elements and scale-up need human approval before a run, and runs past the unit budget are denied", INT, "file:asd/labloop_tools.py")
    # uncertainty
    doc.h(2, "9. Uncertainty and limits")
    doc.claim(f"This is one run on one world with one seed ({len(nbx)} films), so it supports no rate or improvement claim", "calc:n_films",
              *(["state:run"] if st else []))
    doc.claim("The simulator was designed by the team, so a measured value is a property of the model world, not of a real device", INT)
    doc.claim("Benchmark numbers from the LabLoop README stay unverified until rerun", CTX)
    doc.claim(f"Hypothesis verdicts rest on few films: {d['calcs']['n_qualified']} of {len(hyps)} hypotheses are only qualified", "calc:n_qualified", "calc:n_hyps")
    doc.claim(f"{d['calcs']['n_open']} hypotheses never reached a verdict", "calc:n_open")
    if offline:
        doc.claim("No Omnigent planner or generator agent was involved, so nothing here measures agent collaboration", pis[0]["record_id"])
    # next
    doc.h(2, "10. Recommended next experiment and validation needed")
    jv = judges[-1] if judges else None
    cand = [x for x in (jv["discovery_verdicts"] if jv else []) if not x["replicated"]]
    openh = sorted([h for h in hyps.values() if h["status"] in ("proposed", "testing")], key=lambda h: -h["elo"])
    if cand:
        doc.claim(f"Next experiment: replicate {code(cand[0]['formula'])}, which has {cand[0]['n_films']} film so far and status {cand[0]['status']}", jv["record_id"])
    elif openh:
        doc.claim(f"Next experiment: test hypothesis {openh[0]['id']}, the open hypothesis with the highest Elo: {q(openh[0]['prediction'], 100)}", f"state:{openh[0]['id']}")
    else:
        doc.claim("No open hypothesis or unreplicated candidate remains; the next step is a wider search", "calc:n_open")
    doc.claim("Before any real use a confirmed composition must be made and measured in a physical lab, with human sign-off", BRIEF)
    doc.claim("The simulator's physics would have to be checked against real device data before any conclusion transfers", INT)
    return doc.text()
