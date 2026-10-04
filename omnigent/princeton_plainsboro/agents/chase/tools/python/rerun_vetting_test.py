"""Omnigent tool `rerun_vetting_test` for chase (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def rerun_vetting_test(target_id: str, test_id: str, window_factor: float = 5.0, cost_units: float = 0.0) -> dict:
    """
    Counter-experiment: rerun a test with alternate detrending (costs half the test).

    :param target_id: Anonymized ID.
    :param test_id: Registry ID.
    :param window_factor: Alternate window, default 5.
    :param cost_units: Declared cost.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.rerun_vetting_test(target_id, test_id, window_factor, cost_units)
