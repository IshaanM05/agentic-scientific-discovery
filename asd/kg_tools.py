"""Omnigent function tools for the knowledge-graph agent: kg_update and kg_query.

Stateless per call (Omnigent may run each call in a fresh process). State lives in the run directory:
  record.jsonl / ledger.jsonl / notebook.sqlite   written by the other tools; the base graph is rebuilt from them
  kg.jsonl                                        append-only overlay of nodes and links added by kg_update
Run dir from env, as in asd/tools.py: ASD_RUN_DIR or LC_ASD_RUN_DIR (required).
Plain-JSON in and out. Hidden ground truth is never accepted (kg_update rejects it) and never returned.
"""
import json
import os
import re
from pathlib import Path

from . import kg

FORBIDDEN_TEXT = re.compile(r"true_hit|true_hits|eg_true|lt_true|ground[_ ]truth|world[_ ]param", re.I)
_OVERLAY = "kg.jsonl"


class KGConfigError(Exception):
    pass


def _env(name, default=None):
    return os.environ.get("ASD_" + name, os.environ.get("LC_ASD_" + name, default))


def _run_dir():
    rd = _env("RUN_DIR")
    if rd is None:
        raise KGConfigError("ASD_RUN_DIR not set in the tool process; refusing to fall back to a shared run dir")
    p = Path(rd)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _overlay(rd):
    return kg._jsonl(rd / _OVERLAY)


def _graph(rd):
    """Base graph from the run's own records plus the kg_update overlay, as a plain dict."""
    d = kg.build_run(rd).to_dict()
    nodes = {n["id"]: n for n in d["nodes"]}
    for i, op in enumerate(_overlay(rd)):
        if op["op"] == "node":
            nodes[op["node"]["id"]] = {**op["node"], "order": 100_000 + i}
        elif op["op"] == "edge" and op["edge"]["src"] in nodes and op["edge"]["dst"] in nodes:
            d["edges"].append(op["edge"])
    d["nodes"] = sorted(nodes.values(), key=lambda n: (n["order"], n["id"]))
    d["meta"]["counts"] = _counts(d)
    return d


def _counts(d):
    c = {t: 0 for t in kg.NODE_TYPES}
    for n in d["nodes"]:
        c[n["type"]] += 1
    c["edges"] = len(d["edges"])
    c["inferred_edges"] = sum(e["inferred"] for e in d["edges"])
    return c


def _record_ids(rd):
    return {e.get("record_id") for e in kg._jsonl(rd / "record.jsonl")}


def _append_record(rd, payload):
    """Append one kg_update entry to the shared research record, only when the run dir already has an owner
    (meta.json or record.jsonl): writing record.jsonl into an unowned dir would trip the run-id guard in asd/tools."""
    rec = rd / "record.jsonl"
    if not ((rd / "meta.json").exists() or rec.exists()):
        return None
    meta = kg._json(rd / "meta.json")
    n = len(kg._jsonl(rec)) + 1
    entry = {"record_id": f"rec-{n:04d}", "kind": "kg_update", "seed": meta.get("seed"),
             "run_id": meta.get("run_id", _env("RUN_ID", "")), **payload}
    with open(rec, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["record_id"]


def _as_obj(x, default):
    if x in (None, ""):
        return default
    if isinstance(x, str):
        return json.loads(x)
    return x


def kg_update(node_type: str = "", node_id: str = "", label: str = "", evidence: str = "", source: str = "",
              links: list = None) -> dict:
    """Knowledge-graph agent: add one node and/or typed links from a result.
    node_type: question|hypothesis|experiment|citation|finding|decision (empty = links only).
    node_id: id for the new node; ids without ':' get a 'kgx:' prefix. Link to existing nodes by their full id
    (e.g. 'hyp:H1', 'find:rec-0015').
    evidence: JSON object (string or dict) with the numbers/text behind the node. source: the record id,
    ledger step or citation id it comes from (checked against record.jsonl).
    links: list of {src, dst, type, basis}; type is one of tests|supports|refutes|cites|caused_decision|reopens.
    A link is marked inferred unless its basis is a record id that exists in record.jsonl.
    Rejects unknown ids/types and anything naming hidden ground truth."""
    rd = _run_dir()
    try:
        ev = _as_obj(evidence, {})
        links = _as_obj(links, [])
        if not isinstance(ev, dict) or not isinstance(links, list):
            raise ValueError("evidence must be an object and links a list")
        kg.check_clean({"evidence": ev, "links": links})
        if FORBIDDEN_TEXT.search(json.dumps([label, ev, links, source])):
            raise ValueError("text names hidden ground truth")
    except (ValueError, json.JSONDecodeError) as e:
        return {"accepted": False, "error": f"rejected: {str(e)[:200]}"}
    g = _graph(rd)
    ids = {n["id"] for n in g["nodes"]}
    recs = _record_ids(rd)
    ops, new_id = [], None
    if node_type:
        if node_type not in kg.NODE_TYPES:
            return {"accepted": False, "error": f"node_type must be one of {list(kg.NODE_TYPES)}"}
        if not label or not node_id:
            return {"accepted": False, "error": "node_id and label are required to add a node"}
        new_id = node_id if ":" in node_id else "kgx:" + node_id
        if new_id in ids:
            return {"accepted": False, "error": f"node {new_id!r} already exists"}
        ids.add(new_id)
        node = {"id": new_id, "type": node_type, "label": kg._short(label, 140), "source": source,
                "evidence": ev, "added_by": "kg_update", "source_verified": source in recs}
        if node_type == "hypothesis":
            node.update(agent_generated=True, status="open",
                        label_note="agent-generated hypothesis (unvalidated); added via kg_update")
        ops.append({"op": "node", "node": node})
    added = []
    for ln in links:
        src, dst, t = ln.get("src") or new_id, ln.get("dst") or new_id, ln.get("type")
        if t not in kg.EDGE_TYPES or src not in ids or dst not in ids or src == dst:
            return {"accepted": False, "error": f"bad link {ln!r}: unknown type or node id"}
        basis = str(ln.get("basis", ""))
        edge = {"src": src, "dst": dst, "type": t, "inferred": basis not in recs,
                "basis": basis if basis in recs else (basis or "asserted by the knowledge-graph agent, no record cited")}
        ops.append({"op": "edge", "edge": edge})
        added.append(edge)
    if not ops:
        return {"accepted": False, "error": "nothing to add: give a node_type or links"}
    with open(rd / _OVERLAY, "a") as f:
        for op in ops:
            f.write(json.dumps(op) + "\n")
    rid = _append_record(rd, {"node": new_id, "node_type": node_type or None, "links": added})
    return {"accepted": True, "node_id": new_id, "links_added": len(added), "record_id": rid}


def kg_query(query: str = "summary", node_id: str = "", node_type: str = "", limit: int = 30) -> dict:
    """Knowledge-graph agent: read the graph. query: summary | list (optionally node_type) | node (node_id) |
    chain (node_id: upstream evidence and downstream decisions) | why (decision node_id: what caused it) |
    open (hypotheses still unresolved, and those reopened)."""
    d = _graph(_run_dir())
    by_id = {n["id"]: n for n in d["nodes"]}

    def brief(n):
        return {"id": n["id"], "type": n["type"], "label": n["label"], "status": n.get("status"),
                "source": n.get("source")}
    if query == "summary":
        out = kg.summary(d)
    elif query == "list":
        out = {"nodes": [brief(n) for n in d["nodes"] if not node_type or n["type"] == node_type][:max(1, int(limit))]}
    elif query in ("node", "chain", "why"):
        if node_id not in by_id:
            return {"error": f"unknown node {node_id!r}"}
        if query == "node":
            out = {"node": by_id[node_id], "edges": [e for e in d["edges"] if node_id in (e["src"], e["dst"])]}
        elif query == "chain":
            c = kg.chain(d, node_id)
            out = {"nodes": [brief(by_id[i]) for i in c["nodes"]], "edges": c["edges"]}
        else:
            out = {"decision": brief(by_id[node_id]),
                   "caused_by": [{**brief(by_id[e["src"]]), "inferred": e["inferred"], "basis": e["basis"]}
                                 for e in d["edges"] if e["dst"] == node_id and e["type"] == "caused_decision"],
                   "led_to": [brief(by_id[e["dst"]]) for e in d["edges"] if e["src"] == node_id and e["type"] == "led_to"]}
    elif query == "open":
        reopened = {e["dst"] for e in d["edges"] if e["type"] == "reopens"}
        out = {"unresolved": [brief(n) for n in d["nodes"] if n["type"] == "hypothesis"
                              and n.get("status") in (None, "open", "proposed", "testing", "qualified")],
               "reopened": [brief(by_id[i]) for i in sorted(reopened) if i in by_id]}
    else:
        return {"error": "query must be summary|list|node|chain|why|open"}
    kg.check_clean(out)
    return out
