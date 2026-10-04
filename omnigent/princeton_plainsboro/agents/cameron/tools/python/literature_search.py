"""Omnigent tool `literature_search` for cameron (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def literature_search(query: str, target_id: str = "") -> dict:
    """
    OpenAlex search for vetting methodology. Target-specific queries are blocked in benchmark mode.

    :param query: Methodology query (never the target name).
    :param target_id: Current case, used by the label-leak guard.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.literature_search(query, target_id)
