"""Summarize an exported omnigent session JSONL: one line per tool call/output (who, tool, result head)."""
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(line)
    t = d.get("type")
    if t == "function_call":
        print("CALL ", d.get("name"), str(d.get("arguments"))[:110].replace("\n", " "))
    elif t == "function_call_output":
        print("  ->", str(d.get("output"))[:140].replace("\n", " "))
    elif t == "message" and d.get("role") == "assistant":
        print("SAY  ", str(d.get("content"))[:140].replace("\n", " "))
