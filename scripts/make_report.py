"""One command, no model calls: turn a run directory into a traceable Markdown report.

    python scripts/make_report.py steel runs/t011 -o docs/REPORT_STEEL.md
    python scripts/make_report.py labloop runs/ll-offline-w3100 -o docs/REPORT_LABLOOP.md
    python scripts/make_report.py simulate --world 3100 --seed 0 --out runs/ll-offline-w3100   # offline LabLoop run
    python scripts/make_report.py all                  # both committed reports (simulates the LabLoop run if absent)
    python scripts/make_report.py steel runs/t011 --polish mymod:rewrite   # optional prose hook, facts frozen

The text comes from templates. `--polish module:function` lets a model reword prose (`function(text) -> text`);
asd.report.polish keeps a rewrite only if it adds no number, keeps every quote and source tag, and the line still
passes the checker. The whole report is re-checked at the end and the command fails if the check does not pass.
"""
import argparse
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asd import report as R  # noqa: E402

DEFAULTS = {"steel": ("runs/t011", "docs/REPORT_STEEL.md"),
            "labloop": ("runs/ll-offline-w3100", "docs/REPORT_LABLOOP.md")}
SIM = {"world": 3100, "seed": 0, "budget": 60.0}


def simulate(world, seed, budget, out):
    """Offline LabLoop campaign through the Omnigent tool layer with no proposer: rule-based PI, designer, analyst
    and judge on a fixed world and seed. Writes notebook.sqlite, ll_state.json and record.jsonl into `out`."""
    from asd import labloop_tools as L
    out = R.resolve(out)
    if (out / "record.jsonl").exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    os.environ["ASD_RUN_DIR"], os.environ["ASD_RUN_ID"] = str(out), out.name
    L.ll_start(world, seed, budget)
    L.ll_literature()
    for _ in range(40):
        L.ll_arena_round([])
        pi = L.ll_pi_decide("offline rule-based run: no planner model; the LabLoop PI rules choose the mode")
        if pi.get("mode") == "stop" or "error" in pi:
            break
        d = L.ll_design(pi["slots"])
        ids = [p["slot_id"] for p in d["protocols"] if p["runnable"]]
        if not ids:
            break
        r = L.ll_run(ids)
        L.ll_analyse()
        L.ll_judge()
        if not r["results"] or r["budget_left"] < 1.0:  # nothing affordable or runnable: the campaign is over
            break
    return out


def build(kind, run_dir, polish_spec=None):
    if kind == "steel":
        md = R.render_steel(run_dir)
    else:
        from labloop.report import render_labloop
        md = render_labloop(run_dir)
    src = R.load_sources(kind, run_dir)
    if polish_spec:
        mod, fn = polish_spec.split(":")
        md = R.polish(md, getattr(importlib.import_module(mod), fn), src)
    problems = R.check_markdown(md, src)
    if problems:
        raise SystemExit("report failed its own check:\n" + "\n".join(f"  line {n}: {p}: {l}" for n, p, l in problems[:10]))
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["steel", "labloop", "simulate", "all"])
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("--polish")
    ap.add_argument("--world", type=int, default=SIM["world"])
    ap.add_argument("--seed", type=int, default=SIM["seed"])
    ap.add_argument("--budget", type=float, default=SIM["budget"])
    ap.add_argument("--out", default=DEFAULTS["labloop"][0])
    a = ap.parse_args(argv)
    if a.kind == "simulate":
        print("wrote", simulate(a.world, a.seed, a.budget, a.out))
        return 0
    kinds = ["steel", "labloop"] if a.kind == "all" else [a.kind]
    for k in kinds:
        rd, outp = (a.run_dir or DEFAULTS[k][0]) if a.kind != "all" else DEFAULTS[k][0], (a.output or DEFAULTS[k][1]) if a.kind != "all" else DEFAULTS[k][1]
        if k == "labloop" and not (R.resolve(rd) / "notebook.sqlite").exists():
            simulate(SIM["world"], SIM["seed"], SIM["budget"], rd)
        md = build(k, rd, a.polish)
        out = R.resolve(outp)
        out.write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {outp} ({len(md.splitlines())} lines) from {rd}; check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
