"""Omnigent tool `open_case` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def open_case(target_id: str) -> dict:
    """
    Open a case: serve the anonymized signal, priors and House's agent-generated hypotheses.

    :param target_id: Anonymized ID, e.g. "T-0007".
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.open_case(target_id)
