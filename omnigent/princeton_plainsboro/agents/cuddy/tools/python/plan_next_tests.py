"""Omnigent tool `plan_next_tests` for cuddy (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def plan_next_tests(target_id: str, contrarian: str = "", house_request: str = "") -> dict:
    """
    Score every untested vetting test by expected information gain per cost (+ bounded contrarian bonus); returns a PlannerRationale with >= 2 candidates, the chosen test(s) and the stopping decision.

    :param target_id: Anonymized ID.
    :param contrarian: House's contrarian hypothesis ID, e.g. "H2".
    :param house_request: Test House asked for, e.g. "T-odd-even".
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.plan_next_tests(target_id, contrarian, house_request)
