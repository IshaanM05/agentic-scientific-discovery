"""Omnigent tool `assess_result` for foreman (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def assess_result(target_id: str, run_id: str) -> dict:
    """
    Grade a result (ok/marginal/unreliable), update the posterior, flag surprises and open/resolve critiques.

    :param target_id: Anonymized ID.
    :param run_id: Run ID returned by Chase.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.assess_result(target_id, run_id)
