"""Wilson, knowledge graph / memory agent (design 5.5).

Owns: what the lab has learned across targets. Writes target -> hypothesis ->
test -> result -> evidence edges and a LessonLearned per case. In the clearly
separated adaptive mode, delayed labels refine the likelihood tables online.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..config import HYP_IDS, HYP_LABELS
from ..schemas import LessonLearned


def _kl(p: dict, q: dict) -> float:
    a = np.array([p[h] for h in HYP_IDS]) + 1e-12
    b = np.array([q[h] for h in HYP_IDS]) + 1e-12
    return float(np.sum(a * np.log2(a / b)))


class Wilson:
    name = "wilson"

    def __init__(self, kg_path: Path | None = None):
        self.kg_path = kg_path
        self.nodes: dict = {}
        self.edges: list = []
        self.stats = defaultdict(lambda: {"runs": 0, "decisive": 0, "unreliable": 0, "marginal": 0})

    def _node(self, nid, kind, **attrs):
        self.nodes.setdefault(nid, {"id": nid, "kind": kind, **attrs})

    def record_case(self, wb, verdict) -> LessonLearned:
        t = wb.target_id
        self._node(t, "target", signal=wb.signal)
        self._node(f"{t}:{verdict.label}", "hypothesis", label=verdict.label, posterior=verdict.top_posterior)
        self.edges.append({"src": t, "dst": f"{t}:{verdict.label}", "rel": "diagnosed_as"})
        decisive, best = None, -1.0
        traj = wb.trajectory
        for i in range(1, len(traj)):
            d = _kl(traj[i]["posterior"], traj[i - 1]["posterior"])
            if d > best:
                best, decisive = d, traj[i]["after"]
        for tr in wb.tests_run:
            rid = tr["run_id"]
            self._node(rid, "result", test_id=tr["test_id"], outcome=tr["outcome_label"], quality=tr["quality"])
            self.edges.append({"src": t, "dst": rid, "rel": "tested_by"})
            for ev in tr.get("evidence_ids", []):
                self.edges.append({"src": rid, "dst": ev, "rel": "method_reference"})
            s = self.stats[tr["test_id"]]
            s["runs"] += 1
            if tr["quality"] in ("unreliable", "marginal"):
                s[tr["quality"]] += 1
        if decisive:
            base = decisive.split("@")[0]
            self.stats[base]["decisive"] += 1
        lesson = (f"{verdict.label_text} after {verdict.tests_used} tests ({verdict.cost_used} cost units). "
                  f"Most decisive evidence: {decisive} ({best:.2f} bits of belief shift).")
        snr = wb.signal.get("snr", 0)
        bad = [tr["test_id"] for tr in wb.tests_run if tr["quality"] != "ok"]
        if bad:
            lesson += f" Low-quality results at SNR {snr:.0f}: {', '.join(bad)}."
        ll = LessonLearned(target_id=t, lesson=lesson, decisive_test=decisive,
                           stats={"decisive_bits": round(best, 3), "verdict": HYP_LABELS[verdict.label]})
        if self.kg_path:
            self.kg_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.kg_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"target": t, "lesson": ll.model_dump(),
                                    "edges": [e for e in self.edges if e["src"] == t or e["src"].startswith(f"run-{t}-")]},
                                   default=str) + "\n")
        return ll

    def adapt(self, tables, wb, true_label: str):
        """Adaptive mode only: add this case's outcomes (with its delayed label) to the tables."""
        for tr in wb.tests_run:
            if tr["outcome_bin"] >= 0 and not tr.get("rerun"):
                tables.add_observation(tr["test_id"], true_label, tr["outcome_bin"])

    def summary(self) -> dict:
        return {k: dict(v) for k, v in self.stats.items()}
