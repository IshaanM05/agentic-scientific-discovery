"""Omnigent tool `run_vetting_test` for chase (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def run_vetting_test(target_id: str, test_id: str, window_factor: float = 3.0, cost_units: float = 0.0) -> dict:
    """
    Execute one approved registry test on the light curve and record a TestResult (run_id, metrics, code hash).

    :param target_id: Anonymized ID.
    :param test_id: Registry ID, e.g. "T-secondary".
    :param window_factor: Detrending window in transit durations (3 default).
    :param cost_units: Declared cost, for the budget policy.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.run_vetting_test(target_id, test_id, window_factor, cost_units)
