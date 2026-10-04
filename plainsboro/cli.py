"""Terminal demo.

    python -m plainsboro.cli investigate T-0167 [--set blind|real] [--interactive] [--live-literature]
    python -m plainsboro.cli list
"""
from __future__ import annotations

import argparse
import sys
import textwrap

from .config import HYP_LABELS
from .data.gatekeeper import load_set
from .lab import Lab
from .planner.likelihood import load_tables
from .record.ledger import Ledger
from .config import RUNS

NAMES = {"house": "HOUSE", "cuddy": "CUDDY", "chase": "CHASE", "foreman": "FOREMAN", "cameron": "CAMERON",
         "wilson": "WILSON", "gatekeeper": "GATEKEEPER", "whiteboard": "WHITEBOARD", "safety": "SAFETY",
         "human": "SCIENTIST"}


def _print(ev):
    who = NAMES.get(ev["agent"], ev["agent"]).ljust(10)
    body = textwrap.fill(ev["text"], 110, subsequent_indent=" " * 13)
    print(f"[{who}] {body}")


def investigate(target_id: str, set_name: str, interactive: bool, live_lit: bool):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    gk = load_set(set_name)
    lab = Lab(load_tables(), live_literature=live_lit, ledger=Ledger(RUNS / f"cli_{target_id}.jsonl"),
              n_interval_draws=300)
    gen = lab.investigate(gk.get_target(target_id))
    answer = None
    try:
        ev = next(gen)
        while True:
            _print(ev)
            answer = None
            if ev["kind"] == "approval":
                if interactive:
                    answer = "approve" if input("   approve? [y/N] ").strip().lower() == "y" else "deny"
                else:
                    answer = "deny"
            ev = gen.send(answer)
    except StopIteration as stop:
        rec = stop.value
    v = rec["verdict"]
    truth = gk._label(target_id, "evaluator")
    print("\n" + "=" * 100)
    print(f"Verdict: {v['label_text']}  P={v['top_posterior']:.3f}  90% CI {v['interval']}  needs_human={v['needs_human']}")
    print(f"Tests {v['tests_used']}, cost {v['cost_used']}. Ground truth (revealed by gatekeeper): {truth} "
          f"({' / '.join(HYP_LABELS[h] for h in truth.split('|'))}) -> {'CORRECT' if gk.score(target_id, v['label']) else 'WRONG'}")
    print(f"Ledger: runs/cli_{target_id}.jsonl ({len(lab.ledger.events)} events)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("investigate")
    a.add_argument("target_id")
    a.add_argument("--set", default="blind")
    a.add_argument("--interactive", action="store_true")
    a.add_argument("--live-literature", action="store_true")
    b = sub.add_parser("list")
    b.add_argument("--set", default="blind")
    args = ap.parse_args()
    if args.cmd == "list":
        print("\n".join(load_set(args.set).target_ids()))
    else:
        investigate(args.target_id, args.set, args.interactive, args.live_literature)


if __name__ == "__main__":
    main()
