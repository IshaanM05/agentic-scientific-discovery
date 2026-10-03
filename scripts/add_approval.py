"""One-off: append the explicit human_approval entry to runs/t011-ask/record.jsonl (T011)."""
import json

rec = {
    "record_id": "rec-0004", "kind": "human_approval", "seed": 31, "run_id": "t011-ask",
    "source": "chat message", "decision": "approve",
    "gates": "recommend_for_validation (policy ASK)",
    "transcript": "runs/t011-ask/transcript.jsonl",
    "transcript_item": "c97c2d77e2cd4ae38357207967ac5171",
    "transcript_item_note": "user message 'approve' (created_at 1791055396); the next recommend_for_validation call "
                            "(item 0e44aeaceede424db165d26cf10f053d, created_at 1791055407) produced rec-0003",
    "enforcement": "recorded, NOT enforced as a hard block: no Approve/Deny card appeared, the first ASK was rejected "
                   "instantly, the second call ran after the human typed approve in chat",
    "note": "entry added post hoc by the Builder from the human's confirmation; rec-0004 is written after rec-0003 "
            "but the decision preceded it",
}
with open("runs/t011-ask/record.jsonl", "a", encoding="utf-8") as f:
    f.write("\n" + json.dumps(rec) + "\n")
