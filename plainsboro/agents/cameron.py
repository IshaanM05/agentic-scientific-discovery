"""Cameron, literature and evidence agent (design 5.2), plus source-reliability safety check.

Owns: which published evidence bears on the current differential. Every citation
is resolved (arXiv API) before use; unresolvable sources are dropped and flagged.
"""
from __future__ import annotations

from ..config import HYP_LABELS
from ..literature import KNOWLEDGE_BASE, resolve_arxiv
from ..schemas import Evidence
from ..vetting.registry import REGISTRY


class Cameron:
    name = "cameron"

    def __init__(self, enabled: bool = True, live: bool = False):
        self.enabled = enabled
        self.live = live
        self._evidence: dict[str, Evidence] = {}
        self.dropped: list[str] = []

    def evidence_for_key(self, key: str) -> Evidence | None:
        if key in self._evidence:
            return self._evidence[key]
        kb = KNOWLEDGE_BASE[key]
        res = resolve_arxiv(kb["arxiv"], offline=not self.live)
        if res["resolved"] is False:
            self.dropped.append(key)
            return None
        ev = Evidence(id=f"EV-{key}", source_id=f"arXiv:{kb['arxiv']}", source_type="arxiv",
                      title=res.get("title") or kb["title"], claim=kb["claim"], supports=kb["supports"],
                      confidence=0.8, resolved=res["resolved"], url=f"https://arxiv.org/abs/{kb['arxiv']}")
        self._evidence[key] = ev
        return ev

    def intake_pack(self) -> list[Evidence]:
        if not self.enabled:
            return []
        return [e for e in (self.evidence_for_key(k) for k in ("ricker2015", "kovacs2002", "thompson2018")) if e]

    def evidence_for_tests(self, test_ids) -> list[Evidence]:
        if not self.enabled:
            return []
        out = []
        for tid in test_ids:
            for key in REGISTRY[tid].method_refs:
                ev = self.evidence_for_key(key)
                if ev and ev not in out:
                    out.append(ev)
        return out

    def methodology_query(self, leader: str, contrarian: str) -> str:
        return (f"transit false positive vetting {HYP_LABELS[leader].split('(')[0]} versus "
                f"{HYP_LABELS[contrarian].split('(')[0]} Kepler").replace("/", " ")
