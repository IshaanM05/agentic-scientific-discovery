"""Print a compact view of a run record: python scripts/show_record.py runs/<name>/record.jsonl"""
import json
import sys

KEYS = ("id", "value", "candidate_id", "level", "supported", "reopened_assumptions", "hypothesis_id",
        "chosen", "status", "predicted", "agent", "handoff_kind")
for line in open(sys.argv[1], encoding="utf-8"):
    e = json.loads(line)
    print(e["record_id"], e.get("seed"), e["kind"], {k: v for k, v in e.items() if k in KEYS})
