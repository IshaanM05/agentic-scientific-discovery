"""Cameron's literature tools: curated method references, a live ID resolver and OpenAlex search.

Every reference here is a *candidate*: Cameron resolves the arXiv ID (arXiv API)
or DOI (OpenAlex) before citing it. Unresolvable references are dropped and the
failure is recorded, never papered over. Resolver results are cached in
data/citation_cache.json so benchmark runs are offline-reproducible.
"""
from __future__ import annotations

import json
import re
import threading
import xml.etree.ElementTree as ET

import requests

from .config import DATA

# Method references that ground each vetting test. Claims are paraphrased summaries.
KNOWLEDGE_BASE = {
    "coughlin2016": dict(arxiv="1512.06149", title="Planetary Candidates Observed by Kepler. VII. The First Fully "
                         "Uniform Catalog Based on the Entire 48-month Data Set (Q1-Q17 DR24)",
                         claim="Automated Robovetter metrics (odd/even depth, secondary eclipse, shape) separate "
                               "eclipsing binaries from planet candidates in Kepler TCEs.",
                         supports=["H2"], tests=["T-odd-even", "T-secondary"]),
    "thompson2018": dict(arxiv="1710.06758", title="Planetary Candidates Observed by Kepler. VIII. A Fully Automated "
                         "Catalog With Measured Completeness and Reliability Based on Data Release 25",
                         claim="DR25 vetting quantifies reliability against instrumental false alarms; systematics "
                               "and depth consistency checks are needed to reject artifact TCEs.",
                         supports=["H5"], tests=["T-systematics", "T-consistency", "T-odd-even"]),
    "seager2003": dict(arxiv="astro-ph/0206228", title="On the Unique Solution of Planet and Star Parameters from an "
                       "Extrasolar Planet Transit Light Curve",
                       claim="Transit shape (total and flat-bottom durations, depth) yields impact parameter and "
                             "stellar density; inconsistency with the catalog star indicates a non-planet or blend.",
                       supports=["H1", "H3"], tests=["T-shape", "T-density"]),
    "bryson2013": dict(arxiv="1303.0052", title="Identification of Background False Positives from Kepler Data",
                       claim="In-transit centroid shifts identify background eclipsing binaries diluting the target.",
                       supports=["H3"], tests=["T-centroid"]),
    "mcquillan2014": dict(arxiv="1402.5694", title="Rotation Periods of 34,030 Kepler Main-Sequence Stars: "
                          "The Full Autocorrelation Sample",
                          claim="Starspot modulation produces quasi-periodic signals at the rotation period "
                                "that can mimic periodic dips.",
                          supports=["H4"], tests=["T-periodogram"]),
    "shallue2018": dict(arxiv="1712.05044", title="Identifying Exoplanets with Deep Learning: A Five Planet "
                        "Resonant Chain around Kepler-80 and an Eighth Planet around Kepler-90",
                        claim="Learned vetting classifiers can rank TCEs, but still rely on human-verified "
                              "dispositions for training and validation.",
                        supports=[], tests=[]),
    "kovacs2002": dict(arxiv="astro-ph/0206099", title="A box-fitting algorithm in the search for periodic transits",
                       claim="Box Least Squares detects periodic transit-like dips; detection alone does not "
                             "establish a planetary origin.",
                       supports=[], tests=[]),
    "ricker2015": dict(arxiv="1406.0151", title="The Transiting Exoplanet Survey Satellite",
                       claim="TESS produces tens of thousands of threshold-crossing events, making vetting "
                             "throughput a bottleneck.",
                       supports=[], tests=[]),
}

_CACHE_PATH = DATA / "citation_cache.json"
_lock = threading.Lock()


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(c: dict):
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1)


def resolve_arxiv(arxiv_id: str, offline: bool = False, timeout: float = 10.0) -> dict:
    """Check that an arXiv ID exists. Returns {resolved, title, source}."""
    with _lock:
        cache = _load_cache()
    key = f"arxiv:{arxiv_id}"
    if key in cache:
        return cache[key]
    if offline:
        return {"resolved": None, "title": "", "source": "not-checked (offline)"}
    try:
        r = requests.get("https://export.arxiv.org/api/query", params={"id_list": arxiv_id}, timeout=timeout)
        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = root.findall("a:entry", ns)
        title = ""
        ok = False
        for e in entries:
            t = e.find("a:title", ns)
            idel = e.find("a:id", ns)
            if t is not None and idel is not None and "api/errors" not in (idel.text or ""):
                title = re.sub(r"\s+", " ", t.text or "").strip()
                ok = bool(title) and title.lower() != "error"
        res = {"resolved": ok, "title": title, "source": "arxiv-api"}
    except Exception as exc:  # network failure is recorded, not hidden
        return {"resolved": None, "title": "", "source": f"resolver-error: {type(exc).__name__}"}
    with _lock:
        cache = _load_cache()
        cache[key] = res
        _save_cache(cache)
    return res


TARGET_NAME_PATTERN = re.compile(r"\b(KOI|Kepler|KIC|TOI|TIC|EPIC|K2)[-\s]?\d+", re.I)


def openalex_search(query: str, per_page: int = 3, timeout: float = 10.0) -> list[dict]:
    """Live OpenAlex works search (methodology context). Returns [] on failure."""
    try:
        r = requests.get("https://api.openalex.org/works",
                         params={"search": query, "per-page": per_page, "sort": "cited_by_count:desc",
                                 "select": "id,doi,display_name,publication_year,cited_by_count"},
                         timeout=timeout)
        r.raise_for_status()
        out = []
        for w in r.json().get("results", []):
            out.append({"openalex_id": w.get("id", "").rsplit("/", 1)[-1], "doi": w.get("doi"),
                        "title": w.get("display_name"), "year": w.get("publication_year"),
                        "cited_by": w.get("cited_by_count")})
        return out
    except Exception:
        return []
