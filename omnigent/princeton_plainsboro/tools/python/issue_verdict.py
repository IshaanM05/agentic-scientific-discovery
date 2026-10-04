"""Omnigent tool `issue_verdict` for house (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def issue_verdict(target_id: str, run_ids: list[str], evidence_ids: list[str] | None = None, label_text: str = "", needs_human: bool = False) -> dict:
    """
    Issue the final verdict. The label is forced to the posterior's top class; strong claims are blocked by policy.

    :param target_id: Anonymized ID.
    :param run_ids: run_ids of the results the verdict relies on (provenance).
    :param evidence_ids: Evidence IDs (EV-...) cited.
    :param label_text: Your wording (replaced if inconsistent).
    :param needs_human: Escalate to a human even if confident.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.issue_verdict(target_id, run_ids, evidence_ids, label_text, needs_human)
