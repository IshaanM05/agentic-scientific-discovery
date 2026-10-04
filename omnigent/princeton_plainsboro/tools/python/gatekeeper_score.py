"""Omnigent tool `gatekeeper_score` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def gatekeeper_score(target_id: str, label: str) -> dict:
    """
    Evaluator-only label check. Agents are denied by the no_label_access policy.

    :param target_id: Anonymized ID.
    :param label: H1..H5.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.gatekeeper_score(target_id, label)
