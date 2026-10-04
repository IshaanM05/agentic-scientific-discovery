"""Omnigent tool `propose_followup` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def propose_followup(target_id: str, kind: str, justification: str) -> dict:
    """
    Propose follow-up observations. Always requires human approval (policy).

    :param target_id: Anonymized ID.
    :param kind: e.g. "high-resolution imaging + RV".
    :param justification: Why, citing run IDs.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.propose_followup(target_id, kind, justification)
