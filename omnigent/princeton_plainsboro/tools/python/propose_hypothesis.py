"""Omnigent tool `propose_hypothesis` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def propose_hypothesis(target_id: str, hypothesis_id: str, name: str, parent: str, mechanism: str, predicted_test: str, expected_outcome: str) -> dict:
    """
    Add an agent-generated hypothesis (labeled origin=agent_generated) that rolls up into a default class H1-H5.

    :param target_id: Anonymized ID.
    :param hypothesis_id: Short ID, e.g. "H2-2P".
    :param name: Name.
    :param parent: One of H1..H5.
    :param mechanism: Physical mechanism.
    :param predicted_test: Registry test that would reveal it, e.g. "T-odd-even".
    :param expected_outcome: Predicted outcome bin label.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.propose_hypothesis(target_id, hypothesis_id, name, parent, mechanism, predicted_test, expected_outcome)
