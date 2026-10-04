"""Omnigent tool `list_targets` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def list_targets(limit: int = 10) -> dict:
    """
    List anonymized candidate IDs served by the Data Gatekeeper.

    :param limit: How many IDs to return, e.g. 5.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.list_targets(limit)
