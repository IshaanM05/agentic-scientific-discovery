"""Omnigent tool `record_lesson` for wilson (thin wrapper over plainsboro.omnigent_tools)."""

import sys
from pathlib import Path

from omnigent_client import tool

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@tool
def record_lesson(target_id: str, notes: list[str] | None = None) -> dict:
    """
    Write knowledge-graph edges and a LessonLearned for a closed case.

    :param target_id: Anonymized ID.
    :param notes: Extra lessons from the team, tied to run IDs.
    :returns: JSON-serializable handoff payload.
    """
    from plainsboro import omnigent_tools

    return omnigent_tools.record_lesson(target_id, notes)
