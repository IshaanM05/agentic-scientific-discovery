"""Build the research knowledge graphs and embed them in docs/kg.html.

  python scripts/make_kg.py [--steel-run runs/t011] [--labloop-run runs/ll-w2000] [--world 2000 --seed 7]

Writes runs/kg_steel.json and runs/kg_labloop.json. LabLoop uses an Omnigent run directory when it exists and
has records; otherwise it runs the OFFLINE rule-based campaign on a fixed world and seed and labels the graph so.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asd import kg  # noqa: E402

START, END = "<!--KG-DATA-START-->", "<!--KG-DATA-END-->"


def build_labloop(run_dir, world, seed, budget):
    rd = Path(run_dir) if run_dir else None
    if rd and rd.is_dir() and (rd / "record.jsonl").exists():
        g = kg.build_run(rd)
        g.meta["data_source"] = f"Omnigent run records in {rd}"
        return g
    from labloop.campaign import Config, run_campaign
    trace = run_campaign(Config(seed=seed, budget=budget, world=world, record_maps=False))
    g = kg.build_labloop_trace(trace, note="OFFLINE rule-based LabLoop campaign; no Omnigent run records were "
                                           f"found, so this is the baseline scientist on world {world}, seed {seed}")
    g.meta["data_source"] = f"offline rule-based campaign, world {world}, seed {seed}, budget {budget}"
    return g


def embed(html_path, graphs):
    text = html_path.read_text(encoding="utf-8")
    blocks = "\n".join(f'<script type="application/json" id="kg-{k}">'
                       + json.dumps(v, separators=(",", ":")).replace("</", "<\\/") + "</script>"
                       for k, v in graphs.items())
    new = f"{START}\n{blocks}\n{END}"
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: new, text, flags=re.S)
    else:
        text = text.replace("</body>", new + "\n</body>")
    html_path.write_text(text, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--steel-run", default="runs/t011")
    ap.add_argument("--labloop-run", default="runs/ll-w2000")
    ap.add_argument("--world", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--out-dir", default=str(ROOT / "runs"))
    ap.add_argument("--html", default=str(ROOT / "docs" / "kg.html"))
    a = ap.parse_args(argv)
    steel = kg.build_steel(ROOT / a.steel_run if not Path(a.steel_run).is_absolute() else a.steel_run)
    steel.meta["data_source"] = f"Omnigent run records in {a.steel_run}"
    lab = build_labloop(ROOT / a.labloop_run, a.world, a.seed, a.budget)
    out = {}
    for name, g in (("steel", steel), ("labloop", lab)):
        d = g.to_dict()
        p = Path(a.out_dir) / f"kg_{name}.json"
        p.write_text(json.dumps(d, indent=1) + "\n")
        out[name] = d
        print(p, d["meta"]["counts"])
    if Path(a.html).exists():
        embed(Path(a.html), out)
        print("embedded into", a.html)


if __name__ == "__main__":
    main()
