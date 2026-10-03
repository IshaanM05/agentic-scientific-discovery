"""Terminal runner: watch the loop think, round by round.

    python -m labloop                 # offline rule-based scientist, seed 7
    python -m labloop --seed 3 --budget 40
    ANTHROPIC_API_KEY=... python -m labloop   # Claude writes hypotheses + PI rationale
"""
from __future__ import annotations

import argparse
import time

from .campaign import GOAL, Config, run_campaign

C = {"dim": "\033[2m", "b": "\033[1m", "g": "\033[32m", "r": "\033[31m", "y": "\033[33m",
     "c": "\033[36m", "m": "\033[35m", "x": "\033[0m"}
EVENT_COLOR = {"supported": "g", "discovery": "g", "falsified": "r", "rejected": "r",
               "surprise": "y", "qualified": "y", "revision": "y", "proposed": "m", "replication": "c", "safety": "r"}


def main():
    ap = argparse.ArgumentParser(description="Run one LabLoop discovery campaign")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--target", type=int, default=4, help="confirmed discoveries before stopping")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds between printed lines (stage mode)")
    a = ap.parse_args()

    trace = run_campaign(Config(seed=a.seed, budget=a.budget, batch=a.batch, target_discoveries=a.target))
    say = lambda s="": (print(s), time.sleep(a.delay))
    say(f"{C['b']}LabLoop{C['x']}  backend: {trace['backend']}")
    say(f"{C['dim']}Goal: {GOAL}{C['x']}\n")
    for rd in trace["rounds"]:
        d = rd["decision"]
        say(f"{C['b']}Round {rd['round']}  [{d['mode']}]{C['x']}  spent {rd['spent']:.1f}/{a.budget:.0f}")
        say(f"  {C['c']}PI:{C['x']} {d['rationale']}")
        for e in rd["experiments"]:
            r = e["result"]
            if r["ok"]:
                m = f"Eg {r['bandgap_ev']:.3f} eV, T80 {r['t80_h']} h"
                tag = f"{C['g']}HIT{C['x']}" if e["hit"] else "   "
            else:
                m, tag = f"{C['r']}failed: {r['phase']}{C['x']}", "   "
            say(f"  {tag} {e['id']} {e['formula']:<28} {m}  {C['dim']}({e['kind']}){C['x']}")
        for ev in rd["events"]:
            col = C[EVENT_COLOR.get(ev["type"], "dim")]
            say(f"  {col}• {ev['text']}{C['x']}")
        say()
    s = trace["summary"]
    say(f"{C['b']}Done.{C['x']} {s['confirmed']} confirmed discoveries in {s['experiments']} experiments "
        f"({s['spent']:.1f} budget units, {s['clock_h'] / 24:.1f} lab-days); "
        f"{s['supported']} hypotheses supported, {s['falsified']} falsified, {s['negative_results']} negative results kept.")


if __name__ == "__main__":
    main()
