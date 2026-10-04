"""Omnigent tool `evidence_for_tests` for cameron (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def evidence_for_tests(target_id: str, test_ids: list[str]) -> dict:
    """
    Attach resolved method citations (arXiv IDs checked live) for the given tests to the whiteboard.

    :param target_id: Anonymized ID.
    :param test_ids: Registry test IDs.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.evidence_for_tests(target_id, test_ids)
