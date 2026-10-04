"""Omnigent tool `data_trust_check` for foreman (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def data_trust_check(target_id: str) -> dict:
    """
    Everybody lies: sanity-check the light curve (scale, gaps, outliers, duplicate cadences, transit coverage).

    :param target_id: Anonymized ID.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.data_trust_check(target_id)
