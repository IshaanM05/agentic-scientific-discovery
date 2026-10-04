"""Cameron's live research desk: search the literature now, then have an LLM read it.

For the current question (leader vs. contrarian), Cameron searches arXiv and OpenAlex
live, hands the retrieved titles and abstracts to the configured LLM (Anthropic,
Gemini or OpenAI, see `llm.py`), and gets back a short brief on how to tell the two
hypotheses apart. Guardrails:

* Queries are methodology-only and pass the `no_target_specific_lookup` policy first.
* The LLM may cite only papers that were actually retrieved; any other ID is stripped.
* The brief is context and provenance. It never moves the posterior.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from . import llm
from .config import HYP_LABELS
from .literature import arxiv_search, openalex_search

# what to search for when each hypothesis is in play
TOPIC = {
    "H1": "transiting planet candidate",
    "H2": "eclipsing binary odd even secondary eclipse",
    "H3": "background eclipsing binary blend centroid",
    "H4": "starspot rotation stellar variability",
    "H5": "instrumental systematics false alarm",
}

TESTS = ["odd/even depth", "secondary eclipse", "transit shape", "stellar density", "centroid shift",
         "rotation periodogram", "systematics", "depth consistency"]

SYSTEM = f"""You are Dr. Allison Cameron, the literature specialist on an exoplanet vetting team.
You receive papers (ID, title, abstract) retrieved live for one question. Brief the team on the observable
diagnostics that separate the two hypotheses, using only what these papers say.
Reply with JSON only, in exactly this shape:
{{"points": [{{"text": "<one plain sentence>", "ids": ["<paper ID from the list>"]}}],
  "suggested_test": "<one of: {', '.join(TESTS)}>", "coverage": "<one sentence: how well the papers cover this>"}}
Give 2 to 4 points. Every point needs at least one ID copied exactly from the list. If the papers do not
address the question, return fewer points and say so in coverage. Never name a specific star or catalog object."""


def queries(leader: str, contrarian: str) -> tuple[str, str]:
    a = f"{TOPIC[leader]} {TOPIC[contrarian]} transit vetting"
    b = f"distinguishing {HYP_LABELS[leader].split('(')[0].strip()} from {HYP_LABELS[contrarian].split('(')[0].strip()} transit light curve"
    return a.replace("/", " "), b.replace("/", " ")


def gather(leader: str, contrarian: str, per_source: int = 4) -> tuple[str, list[dict]]:
    """Live search. Returns (the query shown to the policy engine, de-duplicated papers)."""
    q, papers = _gather(*sorted((leader, contrarian)), per_source)
    return q, [dict(p) for p in papers]


@lru_cache(maxsize=64)
def _gather(leader: str, contrarian: str, per_source: int) -> tuple:
    qa, qb = queries(leader, contrarian)
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(arxiv_search, f"{TOPIC[leader]} {TOPIC[contrarian]}", per_source)
        f2 = ex.submit(openalex_search, qb, per_source)
        f3 = ex.submit(openalex_search, qa, per_source)
        hits = f1.result() + f2.result() + f3.result()
    papers, seen = [], set()
    for h in hits:
        pid = h.get("id") or (f"doi:{h['doi'].split('doi.org/')[-1]}" if h.get("doi") else f"OpenAlex:{h.get('openalex_id')}")
        key = re.sub(r"\W", "", (h.get("title") or "").lower())[:60]
        if not h.get("title") or key in seen:
            continue
        seen.add(key)
        papers.append({"id": pid, "title": h["title"], "year": h.get("year"), "abstract": h.get("abstract", ""),
                       "url": h.get("url") or "", "source": h.get("source", "openalex")})
    return qb, tuple(papers[: 2 * per_source])


def brief(leader: str, contrarian: str, papers: list[dict]) -> dict:
    """Ask the LLM to read the retrieved papers. Citations outside the retrieved set are removed."""
    if not papers:
        return {"text": "No papers came back from arXiv or OpenAlex, so there is nothing to read.", "model": None,
                "cited": [], "stripped": []}
    return dict(_brief(leader, contrarian, json.dumps(papers, sort_keys=True)))


@lru_cache(maxsize=64)
def _brief(leader: str, contrarian: str, papers_json: str) -> tuple:
    papers = json.loads(papers_json)
    listing = "\n\n".join(f"ID: {p['id']}\nTitle: {p['title']} ({p['year']})\nAbstract: "
                           f"{p['abstract'] or '(no abstract available)'}" for p in papers)
    user = (f"Leading hypothesis: {HYP_LABELS[leader]}. Contrarian: {HYP_LABELS[contrarian]}.\n"
            f"What do these papers say about telling them apart?\n\n{listing}")
    raw, model = llm.complete(SYSTEM, user, max_tokens=900, json_mode=True)
    m = re.search(r"\{.*\}", raw, re.S)
    data = json.loads(m.group(0) if m else raw)
    allowed = {p["id"] for p in papers}
    cited, stripped, lines = [], [], []
    for pt in data.get("points", []):
        ids = [str(i).strip().strip("[]") for i in pt.get("ids", [])]
        good = [i for i in ids if i in allowed]
        stripped += [i for i in ids if i not in allowed]
        if not good:  # an unsupported claim is dropped, not shown
            continue
        cited += [i for i in good if i not in cited]
        lines.append(f"- {pt.get('text', '').strip()} [{', '.join(good)}]")
    if data.get("coverage"):
        lines.append(f"\n*Coverage:* {data['coverage'].strip()}")
    if data.get("suggested_test") in TESTS:
        lines.append(f"\n**Suggested test:** {data['suggested_test']}")
    return tuple({"text": "\n".join(lines) or "The model returned no supported points.", "model": model,
                  "cited": cited, "stripped": stripped, "suggested_test": data.get("suggested_test")}.items())
