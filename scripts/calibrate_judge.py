"""Offline calibration of judge confidence vs the oracle outcome (never shown to the judge).
Outcome = the conclusion's `supported` claim equals the truth |true-pred|/pred <= 0.25, with the true value taken
from the run ledger (the oracle's revealed yield), matched by value."""
import json
import pathlib

P = {"low": 0.25, "medium": 0.5, "high": 0.85}
BINS = ["low", "medium", "high"]


def calibrate(items):
    """items: list of (confidence, correct bool)."""
    n = len(items)
    if not n:
        return {"n": 0}
    acc = sum(c for _, c in items) / n
    brier = sum((P[k] - float(c)) ** 2 for k, c in items) / n
    table = {}
    for b in BINS:
        xs = [c for k, c in items if k == b]
        table[b] = {"count": len(xs), "mean_stated": P[b], "observed_accuracy": (sum(xs) / len(xs)) if xs else None}
    return {"n": n, "accuracy": round(acc, 3), "brier": round(brier, 3), "reliability": table}


def collect(runs_dir="runs"):
    items = []
    for jf in sorted(pathlib.Path(runs_dir).glob("*/judge.jsonl")):
        d = jf.parent
        rec = {e["record_id"]: e for e in map(json.loads, open(d / "record.jsonl"))}
        truth = {round(json.loads(x)["value"], 1) for x in open(d / "ledger.jsonl")}
        for v in map(json.loads, open(jf)):
            a = rec[v["conclusion_id"]]
            if round(a["value"], 1) not in truth:
                continue
            truly = abs(a["value"] - a["predicted"]) / a["predicted"] <= 0.25
            items.append((v["confidence"], a["supported"] == truly))
    return items


if __name__ == "__main__":
    r = calibrate(collect())
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path("results/judge_calibration.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r))
