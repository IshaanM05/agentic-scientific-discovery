"""Omnigent tool `resolve_citation` for cameron (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def resolve_citation(arxiv_id: str) -> dict:
    """
    Check that an arXiv ID exists before citing it.

    :param arxiv_id: e.g. "1512.06149".
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.resolve_citation(arxiv_id)
