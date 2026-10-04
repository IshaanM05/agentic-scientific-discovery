"""Omnigent tool `get_whiteboard` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def get_whiteboard(target_id: str) -> dict:
    """
    Read the shared Differential Whiteboard (posterior, budget, tests, critiques).

    :param target_id: Anonymized ID.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.get_whiteboard(target_id)
