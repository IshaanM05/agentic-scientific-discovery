"""Literature agent.

Offline mode ships a curated claim base so the demo is deterministic. Online mode
(``LABLOOP_ONLINE=1``) adds Semantic Scholar search results as extra context for
the LLM backend. Every claim carries a citation; nothing un-sourced enters the
belief state from this agent.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

CLAIMS = [
    {
        "id": "L1",
        "claim": "Single-junction efficiency peaks for absorbers near 1.34 eV (detailed-balance limit ≈33.7%).",
        "source": "Shockley & Queisser, J. Appl. Phys. 32, 510 (1961)",
        "tags": ["target", "bandgap"],
    },
    {
        "id": "L2",
        "claim": "Mixed Sn-Pb iodide perovskites show anomalous bandgap bowing: mixed films absorb further into the IR than either end member.",
        "source": "Hao et al., J. Am. Chem. Soc. 136, 8094 (2014)",
        "tags": ["bandgap", "sn"],
    },
    {
        "id": "L3",
        "claim": "FA/Cs Sn-Pb (≈50% Sn) films reach ≈1.2-1.25 eV and serve as low-gap tandem subcells.",
        "source": "Eperon et al., Science 354, 861 (2016)",
        "tags": ["bandgap", "sn", "cs"],
    },
    {
        "id": "L4",
        "claim": "Sn(II) readily oxidises to Sn(IV), creating p-doping and fast degradation; stability drops with Sn content.",
        "source": "Noel et al., Energy Environ. Sci. 7, 3061 (2014)",
        "tags": ["stability", "sn"],
    },
    {
        "id": "L5",
        "claim": "Mixed I/Br films phase-segregate under illumination (Hoke effect) when Br ≳ 20%.",
        "source": "Hoke et al., Chem. Sci. 6, 613 (2015)",
        "tags": ["stability", "br"],
    },
    {
        "id": "L6",
        "claim": "Adding a small fraction of Cs to FA/MA perovskites improves phase stability and reproducibility.",
        "source": "Saliba et al., Energy Environ. Sci. 9, 1989 (2016)",
        "tags": ["stability", "cs"],
    },
    {
        "id": "L7",
        "claim": "MA-based perovskites are intrinsically thermally unstable at 85 °C.",
        "source": "Conings et al., Adv. Energy Mater. 5, 1500477 (2015)",
        "tags": ["stability", "ma"],
    },
    {
        "id": "L8",
        "claim": "3D perovskite formability is predicted by the Goldschmidt tolerance factor, roughly 0.8 < t < 1.0.",
        "source": "Kieslich et al., Chem. Sci. 5, 4712 (2014)",
        "tags": ["phase"],
    },
]


def retrieve(tags: list[str] | None = None) -> list[dict]:
    if not tags:
        return list(CLAIMS)
    return [c for c in CLAIMS if set(tags) & set(c["tags"])]


def search_semantic_scholar(query: str, limit: int = 5) -> list[dict]:
    """Best-effort online search; returns [] when offline."""
    if os.environ.get("LABLOOP_ONLINE") != "1":
        return []
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(
        {"query": query, "limit": limit, "fields": "title,year,abstract,externalIds"}
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.load(r)
        return [
            {"title": p.get("title"), "year": p.get("year"), "abstract": (p.get("abstract") or "")[:600]}
            for p in data.get("data", [])
        ]
    except Exception:
        return []
