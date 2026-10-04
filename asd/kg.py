"""Research knowledge graph: hypotheses, experiments, citations, findings and decisions, linked by typed edges.

Built offline from files a run already wrote (steel: record.jsonl + ledger.jsonl; LabLoop: notebook.sqlite,
record.jsonl, or an offline campaign trace). Nothing is invented: every node carries a `source` id (record id,
ledger step, notebook row, or citation id) and every edge says whether it is read from a structured field
(`inferred: false`) or reconstructed from order or text (`inferred: true`, with a `basis`).

Epistemic edge types: tests, supports, refutes, cites, caused_decision, reopens.
Structural edge types (added so a chain can be followed end to end): yields (experiment -> finding),
led_to (decision -> experiment it scheduled), addresses (hypothesis -> question).
Hidden ground truth is never read: only whitelisted fields are copied, and `Graph.check_clean` rejects
forbidden keys.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

NODE_TYPES = ("question", "hypothesis", "experiment", "citation", "finding", "decision")
EDGE_TYPES = ("tests", "supports", "refutes", "cites", "caused_decision", "reopens", "yields", "led_to",
              "addresses")
FORBIDDEN_KEYS = {"true_hit", "true_hits", "true_hits_found", "true_hits_total", "eg_true", "lt_true",
                  "ground_truth_hits", "ground_truth", "world_params", "hidden", "truth"}


class Graph:
    def __init__(self, kind: str, title: str):
        self.meta = {"kind": kind, "title": title, "warnings": []}
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self._seen = set()

    def node(self, nid, ntype, label, source="", order=0, **extra):
        assert ntype in NODE_TYPES, ntype
        evidence = extra.pop("evidence", {})
        n = {"id": nid, "type": ntype, "label": _short(label, 140), "source": source, "order": order,
             "evidence": evidence, **extra}
        self.nodes[nid] = n
        return n

    def edge(self, src, dst, etype, inferred=False, basis=""):
        assert etype in EDGE_TYPES, etype
        key = (src, dst, etype)
        if src not in self.nodes or dst not in self.nodes or key in self._seen or src == dst:
            return
        self._seen.add(key)
        self.edges.append({"src": src, "dst": dst, "type": etype, "inferred": bool(inferred), "basis": basis})

    def warn(self, msg):
        self.meta["warnings"].append(msg)

    def to_dict(self):
        nodes = sorted(self.nodes.values(), key=lambda n: (n["order"], n["id"]))
        d = {"meta": {**self.meta, "counts": self.counts()}, "nodes": nodes, "edges": self.edges}
        check_clean(d)
        return d

    def counts(self):
        c = {t: 0 for t in NODE_TYPES}
        for n in self.nodes.values():
            c[n["type"]] += 1
        c["edges"] = len(self.edges)
        c["inferred_edges"] = sum(e["inferred"] for e in self.edges)
        return c


def _short(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def check_clean(obj, path="$"):
    """Raise if a forbidden (hidden ground truth) key appears anywhere in the structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"hidden-truth key {k!r} at {path}")
            check_clean(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_clean(v, f"{path}[{i}]")


def _jsonl(p: Path):
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def _json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except json.JSONDecodeError:
        return {}


def _wid(x):
    """Normalise an OpenAlex id/url to its short W-id."""
    return str(x).rstrip("/").rsplit("/", 1)[-1]


# ----------------------------------------------------------------------------------------- steel

def build_steel(run_dir) -> Graph:
    rd = Path(run_dir)
    rec, led, meta = _jsonl(rd / "record.jsonl"), _jsonl(rd / "ledger.jsonl"), _json(rd / "meta.json")
    run_id = meta.get("run_id") or rd.name
    g = Graph("steel", f"Steel strength run {run_id}")
    g.meta.update(run_dir=str(rd), run_id=run_id, seed=meta.get("seed"), budget=meta.get("budget"),
                  backend="Omnigent run records (replay oracle on public Matbench steels)")
    if not rec:
        g.warn("record.jsonl missing or empty: no research record to link")
    if not led:
        g.warn("ledger.jsonl missing or empty: experiment values come from the record only")
    g.node("q:1", "question", "Which steel compositions reach yield strength >= 2000 MPa within the "
           "experiment budget?", source="task", order=-1,
           evidence={"hit_threshold_mpa": 2000, "budget": meta.get("budget")})
    ledger = {r["id"]: r for r in led}
    explicit = {}  # (hypothesis_id, value) -> candidate_id, from analysis handoffs that name the candidate
    for e in rec:
        p = e.get("payload") or {}
        if e["kind"] == "handoff" and e.get("handoff_kind") == "analysis" and p.get("candidate_id"):
            explicit[(p.get("hypothesis_id"), p.get("value"))] = p["candidate_id"]
    judge = {e["payload"]["conclusion_id"]: e["payload"] for e in rec
             if e["kind"] == "handoff" and e.get("handoff_kind") == "judge_verdict"
             and (e.get("payload") or {}).get("conclusion_id")}
    safety = {e["candidate_id"]: e for e in rec if e["kind"] == "safety"}

    hyps, exps_seen, findings, decisions = {}, {}, [], []
    last_decision, consumed, prev_rec = None, set(), None
    for i, e in enumerate(rec):
        k, rid = e["kind"], e.get("record_id", f"rec-{i}")
        if k == "literature":
            for c in e.get("citations", []):
                cid = "cit:" + _wid(c["id"])
                if cid not in g.nodes:
                    g.node(cid, "citation", f"{c.get('title') or c['id']} ({c.get('year')})", source=rid, order=i,
                           used=False, evidence={"title": c.get("title"), "year": c.get("year"),
                                                 "doi": c.get("doi"), "id": c["id"], "found_by_query": e.get("query"),
                                                 "retrieved_by": c.get("source")})
        elif k == "hypothesis":
            hid = "hyp:" + e["id"]
            text = re.sub(r"^agent-generated hypothesis:\s*", "", e.get("text", ""))
            g.node(hid, "hypothesis", f"{e['id']}: {text}", source=rid, order=i, status="open",
                   agent_generated=True, label_note=e.get("label", "agent-generated hypothesis (unvalidated)"),
                   evidence={"text": e.get("text"), "predicted_value_mpa": e.get("predicted_value"),
                             "assumption": e.get("assumption"), "candidate_ids": e.get("candidate_ids"),
                             "citations": e.get("citations")})
            hyps[e["id"]] = hid
            g.edge(hid, "q:1", "addresses", basis="hypothesis registered for this question")
            for c in e.get("citations", []):
                cid = "cit:" + _wid(c)
                if cid not in g.nodes:
                    g.node(cid, "citation", f"{_wid(c)} (cited by {e['id']}; not in a literature call of this run)",
                           source=rid, order=i, used=True, evidence={"id": c, "retrieved_in_run": False})
                g.nodes[cid]["used"] = True
                g.edge(hid, cid, "cites")
            m = re.search(r"Revised after ([^.(]*)", e.get("text", ""))
            if m:  # the agent says this hypothesis was revised because earlier ones were refuted
                g.nodes[hid]["revised_after"] = re.findall(r"H\d+", m.group(1))
        elif k == "experiment":
            cand = e["id"]
            led_row = ledger.get(cand, {})
            nid = "exp:" + cand
            mism = led_row and abs(led_row.get("value", e["value"]) - e["value"]) > 1e-6
            g.node(nid, "experiment", f"{cand}: yield {e['value']:.0f} MPa" + (" (HIT)" if e.get("is_hit") else ""),
                   source=f"{rid}; ledger step {led_row.get('step', '?')}", order=i, value_mpa=e["value"],
                   evidence={"candidate": cand, "value_mpa": e["value"], "is_hit": e.get("is_hit"),
                             "cost": e.get("cost"), "budget_used": e.get("budget_used"),
                             "ledger_step": led_row.get("step"), "ledger_value_mpa": led_row.get("value"),
                             "ledger_mismatch": bool(mism), "hypothesis_id": e.get("hypothesis_id") or None,
                             "safety": ({"level": safety[cand]["level"], "notes": safety[cand]["notes"]}
                                        if cand in safety else None), "judge": judge.get(cand)})
            exps_seen[cand] = nid
            if e.get("hypothesis_id") in hyps:
                g.edge(nid, hyps[e["hypothesis_id"]], "tests", basis="experiment record names the hypothesis")
            else:
                for hid_, hn in hyps.items():
                    if cand in (g.nodes[hn]["evidence"].get("candidate_ids") or []):
                        g.edge(nid, hn, "tests", True, "candidate is listed in the hypothesis candidate_ids")
            if last_decision and last_decision["cand"] in (None, cand) and not last_decision.get("done"):
                g.edge(last_decision["id"], nid, "led_to", last_decision["cand"] is None,
                       "decision names this candidate" if last_decision["cand"] else
                       "temporal: first experiments run after the decision (record does not name the candidate)")
        elif k == "analysis":
            hid_s = e["hypothesis_id"]
            ok = e.get("supported")
            fid = f"find:{rid}"
            cand = explicit.get((hid_s, e.get("value")))
            inferred_link = cand is None
            if cand is None:  # match the analysed value to the experiment that measured it
                cand = next((c for c in reversed(list(exps_seen)) if abs(g.nodes[exps_seen[c]]["value_mpa"]
                                                                          - e["value"]) < 1e-6), None)
            g.node(fid, "finding", f"{hid_s} {'supported' if ok else 'refuted'}: measured {e['value']:.0f} MPa vs "
                   f"predicted {e['predicted']:.0f} ({e['rel_error'] * 100:.0f}% off)", source=rid, order=i,
                   status="supported" if ok else "refuted", surprising=e.get("surprising"),
                   evidence={k2: e.get(k2) for k2 in ("hypothesis_id", "value", "predicted", "rel_error", "supported",
                                                      "is_hit", "surprising", "reopened_assumptions")})
            findings.append(fid)
            if hid_s in hyps:
                g.edge(fid, hyps[hid_s], "supports" if ok else "refutes", basis="analysis record verdict")
                g.nodes[hyps[hid_s]]["status"] = "supported" if ok else "refuted"
            if cand and cand in exps_seen:
                g.edge(exps_seen[cand], fid, "yields", inferred_link,
                       "analysis value equals this experiment's measured value" if inferred_link else
                       "analysis handoff names the candidate")
                g.edge(exps_seen[cand], hyps.get(hid_s, ""), "tests", inferred_link,
                       "analysis compared this experiment with the hypothesis")
            for a in e.get("reopened_assumptions") or []:
                owners = [hn for hn in hyps.values() if g.nodes[hn]["evidence"].get("assumption") == a] or \
                    [hyps[hid_s]] if hid_s in hyps else []
                for hn in owners:
                    g.edge(fid, hn, "reopens", basis="analysis reopened this hypothesis's stated assumption")
        elif k == "test_choice":
            did = f"dec:{rid}"
            chosen = next((o for o in e.get("options", []) if o.get("name") == e.get("chosen")), {})
            cand = chosen.get("candidate_id") or (re.search(r"\bc\d{3}\b", e.get("chosen", "")) or [None])[0]
            g.node(did, "decision", f"Chose: {e.get('chosen')}", source=rid, order=i,
                   evidence={"chosen": e.get("chosen"), "options": e.get("options"), "reasons": e.get("reasons")})
            text = json.dumps([e.get("chosen"), e.get("reasons")])
            fresh = [f for f in findings if f not in consumed]
            for f in fresh:  # findings recorded since the previous decision
                h = g.nodes[f]["evidence"].get("hypothesis_id") or ""
                cited = bool(h) and re.search(rf"\b{h}\b", text)
                g.edge(f, did, "caused_decision", not cited,
                       f"decision text cites {h}" if cited else
                       "temporal: finding recorded after the previous decision; the record does not name causes")
                consumed.add(f)
            if not fresh:  # first decision rests on the hypotheses registered so far
                for hn in hyps.values():
                    g.edge(hn, did, "caused_decision", True, "temporal: hypothesis registered before this decision")
            if last_decision:
                last_decision["done"] = True
            last_decision = {"id": did, "cand": cand}
            decisions.append(did)
        elif k == "recommendation":
            did = f"dec:{rid}"
            g.node(did, "decision", f"Recommend {e['candidate_id']} for wet-lab validation (needs human approval)",
                   source=rid, order=i, evidence={k2: e.get(k2) for k2 in ("candidate_id", "rationale", "status")})
            if "exp:" + e["candidate_id"] in g.nodes:
                g.edge("exp:" + e["candidate_id"], did, "caused_decision", True,
                       "recommendation names this candidate; the record does not name the evidence used")
            prev_rec = did
        elif k == "human_approval":
            did = f"dec:{rid}"
            g.node(did, "decision", f"Human approval: {e.get('decision')}", source=rid, order=i,
                   evidence={k2: e.get(k2) for k2 in ("decision", "source", "gates", "enforcement", "note")})
            if prev_rec:
                g.edge(prev_rec, did, "caused_decision", True, "temporal: approval recorded after the recommendation")
    for c, row in ledger.items():  # experiments paid for in the ledger but absent from the record
        if "exp:" + c not in g.nodes:
            g.node("exp:" + c, "experiment", f"{c}: yield {row['value']:.0f} MPa" + (" (HIT)" if row.get("is_hit") else ""),
                   source=f"ledger step {row['step']}", order=10_000 + row["step"], value_mpa=row["value"],
                   evidence={"candidate": c, "value_mpa": row["value"], "is_hit": row.get("is_hit"),
                             "ledger_step": row["step"], "budget_used": row.get("budget_used"),
                             "note": "in the ledger but not in the research record"})
    # hypotheses the text says were revised after earlier refutations: the refuting findings reopened them
    for hid, hn in hyps.items():
        for old in g.nodes[hn].get("revised_after", []):
            for f in findings:
                if g.nodes[f]["evidence"].get("hypothesis_id") == old and g.nodes[f]["status"] == "refuted":
                    g.edge(f, hn, "reopens", True, f"{hid} text says it was revised after {old} was refuted")
    for e in g.edges:
        if e["type"] == "cites":
            g.nodes[e["dst"]]["used"] = True
    return g


# ----------------------------------------------------------------------------------------- LabLoop

def _in_region(comp, region):
    return bool(region) and all(lo - 1e-9 <= comp.get(d, 0) <= hi + 1e-9 for d, (lo, hi) in region.items())


def _origin_label(origin, backend):
    how = "LLM" if origin == "llm" else "rule-based"
    src = {"literature": "adapted from literature claims", "data": "proposed from an anomaly in the data",
           "llm": "proposed from an anomaly in the data"}.get(origin, origin)
    return f"agent-generated hypothesis ({how}, {src}); unvalidated. Backend: {backend}"


def _claims():
    try:
        from labloop.literature import CLAIMS
        return {c["id"]: c for c in CLAIMS}
    except Exception:
        return {}


def build_labloop_trace(trace: dict, note: str = "") -> Graph:
    """Graph from a labloop.campaign.run_campaign trace. Hidden-truth fields of the trace (true_hit, true_hits_*,
    the world description, the ground-truth curve) are never read."""
    wid = (trace.get("world") or {}).get("id")
    cfg = trace.get("config") or {}
    backend = trace.get("backend", "unknown")
    g = Graph("labloop", f"LabLoop campaign (world {wid}, seed {cfg.get('seed')})")
    g.meta.update(world_id=wid, seed=cfg.get("seed"), budget=cfg.get("budget"), backend=backend, note=note)
    g.node("q:1", "question", trace.get("goal", "LabLoop goal"), source="campaign goal", order=-1,
           evidence={"target": trace.get("target")})
    claims = _claims()
    rounds = trace.get("rounds", [])
    final = {h["id"]: h for r in rounds for h in r.get("hypotheses", [])}  # last state per hypothesis id
    created = {}
    order = 0
    for r in rounds:
        for h in r.get("hypotheses", []):
            created.setdefault(h["id"], r["round"])
    for hid, h in final.items():
        cr = h.get("created_round", created[hid])
        g.node("hyp:" + hid, "hypothesis", f"{hid}: {h['statement']}", source=f"campaign hypothesis {hid}",
               order=cr * 1000, round=cr, status=h["status"], agent_generated=True,
               label_note=_origin_label(h.get("origin"), backend),
               evidence={"statement": h["statement"], "prediction": h["prediction"],
                         "kill_condition": h["kill_condition"], "origin": h.get("origin"), "elo": h.get("elo"),
                         "n_evidence": h.get("n_evidence"), "pass_rate": h.get("pass_rate"),
                         "judge_confidence": h.get("confidence"), "sources": h.get("sources"),
                         "rationale": h.get("rationale"), "region": h.get("region")})
        g.edge("hyp:" + hid, "q:1", "addresses", basis="hypothesis proposed for this goal")
        for s in h.get("sources") or []:
            if s in claims:
                cid = "cit:" + s
                if cid not in g.nodes:
                    g.node(cid, "citation", f"{s}: {claims[s]['claim']}", source=claims[s]["source"], order=-0.5,
                           used=True, evidence={"claim": claims[s]["claim"], "source": claims[s]["source"]})
                g.edge("hyp:" + hid, cid, "cites", basis="hypothesis lists this literature claim as its source")
    exp_node, exp_round, prev_f = {}, {}, []
    disc = []
    for r in rounds:
        rn = r["round"]
        base = rn * 1000
        d = r["decision"]
        did = f"dec:R{rn}"
        g.node(did, "decision", f"R{rn} {d['mode']}: {d['rationale']}", source=f"notebook decisions round {rn}",
               order=base + 1, round=rn, evidence={"mode": d["mode"], "rationale": d["rationale"],
                                                    "slots": [{"kind": s.get("kind"), "purpose": s.get("purpose"),
                                                               "hypothesis": s.get("hypothesis")}
                                                              for s in d.get("slots", [])]})
        text = d["rationale"] + " " + " ".join(s.get("purpose", "") for s in d.get("slots", []))
        for f in prev_f:
            n = g.nodes[f]
            tok = n["evidence"].get("formula") or n["evidence"].get("hypothesis_id") or ""
            cited = bool(tok) and tok in text
            g.edge(f, did, "caused_decision", not cited,
                   f"decision text mentions {tok}" if cited else
                   "temporal: finding from the previous round; the decision rule's inputs are not logged per finding")
        if rn == 1:
            for hn in [n for n in g.nodes if n.startswith("hyp:")]:
                if g.nodes[hn].get("round", 0) == 0:
                    g.edge(hn, did, "caused_decision", True, "temporal: literature hypothesis available at round 1")
        cur = []
        for j, e in enumerate(r.get("experiments", [])):
            res = e["result"]
            nid = "exp:" + e["id"]
            exp_node[e["id"]], exp_round[e["id"]] = nid, rn
            val = (f"Eg {res['bandgap_ev']:.3f} eV, T80 {res['t80_h']} h" if res.get("ok") else "failed film")
            g.node(nid, "experiment", f"{e['id']} {e['formula']}: {val}" + (" (meets spec)" if e.get("hit") else ""),
                   source=f"notebook experiments {e['id']}", order=base + 10 + j, round=rn, hit=bool(e.get("hit")),
                   evidence={"notebook_id": e["id"], "formula": e["formula"], "purpose": e["purpose"],
                             "kind": e.get("kind"), "bandgap_ev": res["bandgap_ev"], "t80_h": res.get("t80_h"),
                             "ok": res["ok"], "phase": res.get("phase"), "cost": res["cost"],
                             "predicted": e.get("predicted"), "surprise": e.get("surprise"),
                             "finding": e.get("finding"), "safety": {"approved": e["safety"]["approved"],
                                                                      "label": e["safety"].get("label")},
                             "hypothesis": e.get("hypothesis")})
            g.edge(did, nid, "led_to", basis="experiment ran in this decision's round")
            if e.get("hypothesis") and "hyp:" + e["hypothesis"] in g.nodes:
                g.edge(nid, "hyp:" + e["hypothesis"], "tests", basis="slot names the hypothesis")
            if e.get("flag"):
                fid = f"find:{e['id']}:surprise"
                g.node(fid, "finding", f"{e['formula']}: {e['flag']}", source=f"notebook experiments {e['id']}",
                       order=base + 20 + j, round=rn, status="surprise",
                       evidence={"formula": e["formula"], "flag": e["flag"], "z_eg": e.get("z_eg"),
                                 "z_lt": e.get("z_lt"), "predicted": e.get("predicted"), "measured": val})
                g.edge(nid, fid, "yields", basis="surprise flagged on this measurement")
                cur.append(fid)
        for ev in r.get("events", []):
            m = re.match(r"(H\d+) (supported|falsified|qualified)", ev["text"])
            if ev["type"] in ("supported", "falsified", "qualified") and m:
                hid = m.group(1)
                fid = f"find:R{rn}:{hid}"
                h = final.get(hid, {})
                g.node(fid, "finding", f"{ev['text']}", source=f"notebook hypothesis_events R{rn} {hid}",
                       order=base + 30, round=rn, status=ev["type"], evidence={
                           "hypothesis_id": hid, "event": ev["text"], "n_evidence": h.get("n_evidence"),
                           "pass_rate": h.get("pass_rate"), "kill_condition": h.get("kill_condition"),
                           "note": "holds with exceptions" if ev["type"] == "qualified" else ""})
                g.edge(fid, "hyp:" + hid, "refutes" if ev["type"] == "falsified" else "supports",
                       basis="judge/evaluator verdict logged at this round" +
                             ("; holds with exceptions" if ev["type"] == "qualified" else ""))
                region = [h.get("region")] + [h.get("region_b")]
                for eid, en in exp_node.items():
                    comp = next((x["comp"] for rr in rounds for x in rr.get("experiments", []) if x["id"] == eid), {})
                    explicit = g.nodes[en]["evidence"].get("hypothesis") == hid
                    if explicit or (exp_round[eid] <= rn and any(_in_region(comp, rg) for rg in region)):
                        g.edge(en, fid, "yields", not explicit,
                               "experiment was run to test this hypothesis" if explicit else
                               "experiment composition falls inside the hypothesis region (evaluator uses such films)")
                cur.append(fid)
            if ev["type"] == "revision":
                rid_ = f"dec:R{rn}:revision"
                g.node(rid_, "decision", ev["text"], source=f"notebook R{rn} event", order=base + 35, round=rn,
                       evidence={"event": ev["text"]})
                for f in [x for x in cur if g.nodes[x].get("status") in ("falsified", "qualified")]:
                    if g.nodes[f]["evidence"].get("hypothesis_id") in ev["text"]:
                        g.edge(f, rid_, "caused_decision", False, "event text names the hypothesis")
                        g.edge(f, "hyp:" + g.nodes[f]["evidence"]["hypothesis_id"], "reopens", False,
                               "literature prior relaxed after this verdict")
                    else:
                        g.edge(f, rid_, "caused_decision", True, "temporal: verdict in the same round")
        # hypotheses proposed from an anomaly reopen the question the anomaly raised
        for h in r.get("new_hypotheses", []):
            for s in final.get(h, {}).get("sources") or []:
                for f in (x for x in g.nodes if x.startswith(f"find:{s}:")):
                    g.edge(f, "hyp:" + h, "reopens", False, "hypothesis lists this experiment as its source")
                if s in exp_node:  # no surprise finding: the counterexample finding of its round, if any
                    for f in cur:
                        if g.nodes[f].get("status") == "qualified":
                            g.edge(f, "hyp:" + h, "reopens", True, "proposed in the round a hypothesis was qualified")
        for dsc in r.get("discoveries", []):
            fid = f"find:D:{dsc['formula']}"
            if fid in g.nodes:
                g.nodes[fid]["status"], g.nodes[fid]["label"] = dsc["status"], _short(
                    f"{dsc['formula']} {dsc['status']} ({dsc['reason']})", 140)
                continue
            g.node(fid, "finding", f"{dsc['formula']} {dsc['status']} ({dsc['reason']})", source=f"notebook R{rn}",
                   order=base + 40, round=rn, status=dsc["status"],
                   evidence={"formula": dsc["formula"], "confidence": dsc.get("confidence"),
                             "eg_ev": dsc.get("eg"), "t80_h": dsc.get("t80_h"), "n_measurements": dsc.get("n"),
                             "reason": dsc.get("reason")})
            disc.append((fid, dsc["formula"], rn))
            if dsc["status"] == "confirmed":
                g.edge(fid, "q:1", "supports", basis="replicated spec-meeting film")
            cur.append(fid)
        prev_f = cur
    for fid, formula, rn in disc:
        for rr in rounds:
            for e_ in rr.get("experiments", []):
                if e_["formula"] == formula and rr["round"] <= rn:
                    g.edge(exp_node[e_["id"]], fid, "yields", basis="film of this composition")
    return g


def build_labloop_record(rec: list[dict], g: Graph | None = None) -> Graph:
    """Best-effort graph from an Omnigent-run LabLoop record.jsonl (kinds per docs/LABLOOP_INTEGRATION.md).
    Tolerant of missing keys; unknown kinds are ignored."""
    g = g or Graph("labloop", "LabLoop Omnigent run")
    if "q:1" not in g.nodes:
        g.node("q:1", "question", "Find a stable, lead-reduced perovskite absorber meeting the bandgap and T80 target",
               source="task", order=-1)
    last_dec, new_f = None, []
    for i, e in enumerate(rec):
        k, rid = e.get("kind"), e.get("record_id", f"rec-{i}")
        if k == "ll_start":
            g.meta.update(world_id=e.get("world"), budget=e.get("budget"), run_id=e.get("run_id"))
        elif k == "literature":
            for c in e.get("claims") or e.get("citations") or []:
                cid = "cit:" + str(c.get("id") or c.get("source"))
                g.node(cid, "citation", f"{c.get('id', '')}: {c.get('claim') or c.get('title')}",
                       source=c.get("source") or rid, order=i, used=True,
                       evidence={k2: c.get(k2) for k2 in ("claim", "title", "source", "year")})
            for h in e.get("hypotheses") or []:
                _rec_hyp(g, h, i, rid, "literature")
        elif k == "arena_round":
            for h in e.get("admitted") or e.get("hypotheses") or []:
                _rec_hyp(g, h, i, rid, h.get("source", "agent"))
        elif k == "pi_decision":
            did = f"dec:{rid}"
            g.node(did, "decision", f"{e.get('mode')}: {e.get('rationale', '')}", source=rid, order=i,
                   evidence={"mode": e.get("mode"), "rationale": e.get("rationale"), "budget_left": e.get("budget_left")})
            for f in new_f:
                g.edge(f, did, "caused_decision", True, "temporal: finding recorded before this decision")
            new_f, last_dec = [], did
        elif k == "experiment":
            res = e.get("result") or e
            nid = "exp:" + str(e.get("id") or e.get("slot_id") or rid)
            bg, t80 = res.get("bandgap_ev"), res.get("t80_h")
            fml = e.get("formula") or (e.get("composition") if isinstance(e.get("composition"), str) else None)
            g.node(nid, "experiment", f"{fml or nid}: " + (f"Eg {bg} eV, T80 {t80} h" if bg else "no film"),
                   source=rid, order=i, evidence={k2: res.get(k2) for k2 in ("bandgap_ev", "t80_h", "ok", "phase", "cost")}
                   | {"formula": fml, "purpose": e.get("purpose")})
            if last_dec:
                g.edge(last_dec, nid, "led_to", True, "temporal: ran after this decision")
            h = e.get("hypothesis")
            if h and "hyp:" + str(h) in g.nodes:
                g.edge(nid, "hyp:" + str(h), "tests", basis="experiment record names the hypothesis")
        elif k == "analysis":
            for j, f in enumerate(e.get("findings") or []):
                txt = f if isinstance(f, str) else f.get("text") or json.dumps(f)
                fid = f"find:{rid}:{j}"
                g.node(fid, "finding", txt, source=rid, order=i + j / 100, status="finding", evidence={"text": txt})
                new_f.append(fid)
            for hid, v in (e.get("verdicts") or e.get("hypothesis_updates") or {}).items():
                v = v.get("verdict") if isinstance(v, dict) else v
                fid = f"find:{rid}:{hid}"
                g.node(fid, "finding", f"{hid} {v}", source=rid, order=i, status=str(v), evidence={"hypothesis_id": hid})
                et = "refutes" if "refut" in str(v) else "supports"
                g.edge(fid, "hyp:" + hid, et, basis="analysis verdict update")
                new_f.append(fid)
            for r_ in e.get("prior_relaxations") or []:
                fid = f"find:{rid}:relax"
                g.node(fid, "finding", f"Prior relaxed: {r_}", source=rid, order=i, status="reopened",
                       evidence={"text": str(r_)})
                new_f.append(fid)
    return g


def _rec_hyp(g, h, i, rid, src):
    hid = "hyp:" + str(h.get("id"))
    g.node(hid, "hypothesis", f"{h.get('id')}: {h.get('prediction') or h.get('statement')}", source=rid, order=i,
           status=h.get("status", "open"), agent_generated=True,
           label_note=("agent-generated hypothesis (" + ("rule-based fallback" if src == "rule_based" else "model-written")
                       + "); unvalidated"),
           evidence={k2: h.get(k2) for k2 in ("region", "prediction", "kill_condition", "citation", "source")})
    g.edge(hid, "q:1", "addresses", basis="hypothesis proposed for this goal")
    c = h.get("citation")
    if c and "cit:" + str(c) in g.nodes:
        g.edge(hid, "cit:" + str(c), "cites")


def build_labloop_notebook(path, g: Graph | None = None) -> Graph:
    """Graph (or additions to g) from a LabLoop SQLite notebook: experiments, hypothesis events, decisions."""
    g = g or Graph("labloop", "LabLoop notebook")
    if "q:1" not in g.nodes:
        g.node("q:1", "question", "Find a stable, lead-reduced perovskite absorber meeting the bandgap and T80 target",
               source="task", order=-1)
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    try:
        for r in db.execute("SELECT * FROM decisions ORDER BY round"):
            g.node(f"dec:R{r['round']}", "decision", f"R{r['round']} {r['mode']}: {r['rationale']}",
                   source=f"notebook decisions round {r['round']}", order=r["round"] * 1000 + 1, round=r["round"],
                   evidence={"mode": r["mode"], "rationale": r["rationale"], "slots": json.loads(r["slots"] or "[]")})
        for r in db.execute("SELECT * FROM experiments ORDER BY round, id"):
            nid = "exp:" + r["id"]
            val = f"Eg {r['bandgap']:.3f} eV, T80 {10 ** r['log_t80']:.0f} h" if r["ok"] else "failed film"
            g.node(nid, "experiment", f"{r['id']} {r['formula']}: {val}", source=f"notebook experiments {r['id']}",
                   order=r["round"] * 1000 + 10, round=r["round"],
                   evidence={"notebook_id": r["id"], "formula": r["formula"], "purpose": r["purpose"],
                             "bandgap_ev": r["bandgap"], "log_t80": r["log_t80"], "phase": r["phase"],
                             "cost": r["cost"], "surprise": r["surprise"], "hypothesis": r["hypothesis"]})
            g.edge(f"dec:R{r['round']}", nid, "led_to", True, "temporal: same round as the decision")
            if r["hypothesis"] and "hyp:" + r["hypothesis"] in g.nodes:
                g.edge(nid, "hyp:" + r["hypothesis"], "tests", basis="notebook row names the hypothesis")
        for j, r in enumerate(db.execute("SELECT * FROM hypothesis_events ORDER BY round")):
            hid = "hyp:" + r["hypothesis"]
            if hid not in g.nodes:
                g.node(hid, "hypothesis", f"{r['hypothesis']}: {r['detail']}", source="notebook hypothesis_events",
                       order=r["round"] * 1000, round=r["round"], status=r["event"], agent_generated=True,
                       label_note="agent-generated hypothesis; unvalidated", evidence={"detail": r["detail"]})
                g.edge(hid, "q:1", "addresses", basis="hypothesis proposed for this goal")
            if r["event"] in ("supported", "falsified", "qualified"):
                fid = f"find:R{r['round']}:{r['hypothesis']}"
                g.node(fid, "finding", f"{r['hypothesis']} {r['event']} ({r['detail']})",
                       source=f"notebook hypothesis_events R{r['round']}", order=r["round"] * 1000 + 30,
                       round=r["round"], status=r["event"], evidence={"hypothesis_id": r["hypothesis"], "detail": r["detail"]})
                g.edge(fid, hid, "refutes" if r["event"] == "falsified" else "supports", basis="notebook hypothesis event")
    finally:
        db.close()
    return g


# ----------------------------------------------------------------------------------------- dispatch

def build_run(run_dir) -> Graph:
    """Build the right graph for a run directory (steel record/ledger, or LabLoop notebook/record)."""
    rd = Path(run_dir)
    rec = _jsonl(rd / "record.jsonl")
    if (rd / "notebook.sqlite").exists() or (rd / "ll_state.json").exists() or any(
            e.get("kind", "").startswith("ll_") or e.get("kind") in ("pi_decision", "arena_round") for e in rec):
        g = Graph("labloop", f"LabLoop Omnigent run {rd.name}")
        g.meta["backend"] = "Omnigent run records (LabLoop simulator)"
        if (rd / "notebook.sqlite").exists():
            build_labloop_notebook(rd / "notebook.sqlite", g)
        else:
            g.warn("notebook.sqlite missing")
        if rec:
            build_labloop_record(rec, g)
        else:
            g.warn("record.jsonl missing")
        return g
    return build_steel(rd)


# ----------------------------------------------------------------------------------------- queries

def adjacency(d: dict):
    out, inn = {}, {}
    for e in d["edges"]:
        out.setdefault(e["src"], []).append(e)
        inn.setdefault(e["dst"], []).append(e)
    return out, inn


def chain(d: dict, nid: str) -> dict:
    """Evidence chain around a node. Upstream: the experiment that yielded a finding, what that experiment tested
    and what the hypotheses cite. Downstream: the hypotheses the finding moved (supports/refutes/reopens), the
    decisions it caused, and the experiments those decisions scheduled."""
    out, inn = adjacency(d)
    nodes, edges = {nid}, []

    def take(es, end):
        for e in es:
            edges.append(e)
            nodes.add(e[end])
            yield e[end]
    for x in list(take([e for e in inn.get(nid, []) if e["type"] == "yields"], "src")):
        for h in list(take([e for e in out.get(x, []) if e["type"] == "tests"], "dst")):
            list(take([e for e in out.get(h, []) if e["type"] == "cites"], "dst"))
    for dec in list(take([e for e in out.get(nid, []) if e["type"] in ("supports", "refutes", "reopens",
                                                                       "caused_decision")], "dst")):
        list(take([e for e in out.get(dec, []) if e["type"] == "led_to"], "dst"))
    return {"nodes": sorted(nodes), "edges": edges}


def summary(d: dict) -> dict:
    nodes = d["nodes"]
    hyps = [n for n in nodes if n["type"] == "hypothesis"]
    by_status = {}
    for h in hyps:
        by_status[h.get("status", "open")] = by_status.get(h.get("status", "open"), 0) + 1
    reopened = sorted({e["dst"] for e in d["edges"] if e["type"] == "reopens"})
    kind = {n["id"]: n["type"] for n in nodes}
    cd = [e for e in d["edges"] if e["type"] == "caused_decision" and kind[e["src"]] == "finding"]
    decided = sorted({e["src"] for e in cd if not e["inferred"]})
    inferred_only = sorted({e["src"] for e in cd if e["inferred"]} - set(decided))
    return {"counts": d["meta"]["counts"], "hypotheses_by_status": by_status, "reopened_hypotheses": reopened,
            "findings_that_changed_a_decision": decided,
            "findings_linked_to_a_decision_by_order_only": inferred_only, "warnings": d["meta"]["warnings"]}
