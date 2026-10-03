"""Optional LLM backend.

If ``ANTHROPIC_API_KEY`` is set, agents use Claude for language-heavy steps
(new hypotheses in the DSL, PI rationale, notebook summaries). Every response must
be JSON and is validated before it touches the belief state. Without a key the
system runs a deterministic rule-based scientist, so the demo always works.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from .chemistry import TARGET

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("LABLOOP_MODEL", "claude-sonnet-4-5")


class LLM:
    def __init__(self):
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        self.calls = 0

    @property
    def available(self) -> bool:
        return bool(self.key) and os.environ.get("LABLOOP_OFFLINE") != "1"

    @property
    def name(self) -> str:
        return MODEL if self.available else "rule-based scientist (offline)"

    def json(self, system: str, prompt: str, max_tokens: int = 900) -> dict | list | None:
        if not self.available:
            return None
        body = json.dumps({
            "model": MODEL, "max_tokens": max_tokens,
            "system": system + "\nRespond with JSON only. No prose, no markdown fences.",
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(API_URL, data=body, headers={
            "content-type": "application/json", "x-api-key": self.key,
            "anthropic-version": "2023-06-01",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            self.calls += 1
            text = "".join(b.get("text", "") for b in data.get("content", []))
            text = re.sub(r"```(json)?", "", text).strip()
            return json.loads(text)
        except Exception:
            return None


HYPOTHESIS_SYSTEM = f"""You are the hypothesis generator in an autonomous materials lab searching
A(Cs,FA,MA) B(Pb,Sn) X(I,Br,Cl)3 perovskites for a {TARGET['eg_min']}-{TARGET['eg_max']} eV absorber with T80 >= {TARGET['t80_min_hours']:.0f} h.
Propose falsifiable hypotheses in this exact schema (a list of objects):
{{"statement": str, "region": {{dim: [lo, hi]}}, "prop": "eg"|"lt", "op": "<"|">",
 "value": float, "rationale": str}}
dims are cs, fa, ma, sn, br, cl (fractions 0-1). prop "lt" is log10(T80 hours).
Regions must be narrow enough to be informative (cover < 30% of the space)."""

PI_SYSTEM = f"""You are the PI of an autonomous lab. Given the state, write a two-sentence
rationale for the chosen next action. Schema: {{"rationale": str}}"""
