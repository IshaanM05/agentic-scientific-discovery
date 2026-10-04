"""Compare the rule-based LabLoop scientist with Omnigent run records on golden worlds.

    python scripts/ll_compare.py                       # baseline + runs/ll-w2000, ll-w2001, ll-w2002 (clear message if missing)
    python scripts/ll_compare.py --fixture             # use the committed synthetic fixture instead of live runs
    python scripts/ll_compare.py --make-fixture        # regenerate the fixture (deterministic)
    python scripts/ll_compare.py --selftest            # parser check, no runs needed

Baseline: labloop.campaign.run_campaign (rule-based, offline) on worlds 2000-2002, which the
benchmark (worlds 1000-1019) never used. Omnigent side: runs/ll-*/record.jsonl written by the
live runs. Hidden truth is read here only to SCORE (is a measured film a true hit); it never
reaches an agent. Writes runs/ll_compare.json. The simulator is team-designed, worlds are
synthetic, Omnigent n is small: treat as a benchmark, not evidence about real devices.

The fixture (scripts/ll_fixtures/ll-w2000/record.jsonl) is SYNTHETIC: a rule-based run on world 2000
re-written into the assumed record schema. It tests the parser; it is not an Omnigent result.

Record schema assumed (contract in docs/LABLOOP_INTEGRATION.md; parsing is tolerant, and any
run whose fields it cannot read is reported as `unparsed` rather than guessed):
  ll_start      world, seed, budget
  experiment    one per film: composition (cs,fa,ma,sn,br,cl, or key) and measured result, cost
  analysis      verdict updates (refuted / falsified), prior relaxations
  judge_verdict discovery verdicts (replicated / confirmed)
  adapt         optional explicit ADAPT entries (otherwise derived from analysis)
"""
import argparse, glob, json, os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LABLOOP_OFFLINE"] = "1"

import numpy as np  # noqa: E402

from labloop.campaign import Config, run_campaign  # noqa: E402
from labloop.chemistry import composition_space, set_world, space_arrays  # noqa: E402

WORLDS = (2000, 2001, 2002)
CHECKPOINTS = (20, 40, 60)
KEY_FIELDS = ("cs", "fa", "ma", "sn", "br", "cl")


def _hits_at(curve: list[tuple[float, bool]], budget: float) -> int:
    """curve: (cumulative units, is new true hit) per film."""
    return sum(1 for spent, new in curve if new and spent <= budget + 1e-9)


def _first_hit(curve):
    return next((s for s, new in curve if new), None)


# ---------- baseline: rule-based scientist ----------
def baseline(world: int, seed: int, budget: float) -> dict:
    set_world(world)
    tr = run_campaign(Config(seed=seed, budget=budget, target_discoveries=99, record_maps=False,
                             label="rule", world=world))
    curve, seen, events = [], set(), []
    for rd in tr["rounds"]:
        for e in rd["experiments"]:
            new = bool(e["true_hit"]) and e["idx"] not in seen
            seen.add(e["idx"])
            curve.append((None, new, e["result"]["cost"]))
        events += rd["events"]
    spent, cc = 0.0, []
    for _, new, cost in curve:
        spent += cost
        cc.append((spent, new))
    adapt = [x for x in events if x["type"] in ("revision", "qualified")] + \
            [x for x in events if x["type"] == "falsified"]
    return _metrics(cc, tr["summary"]["confirmed"], tr["summary"]["falsified"], len(adapt),
                    tr["summary"]["true_hits_total"], tr["summary"]["spent"])


def _metrics(cc, confirmed, refuted, adapt, total_hits, spent):
    m = {f"hits@{b}": _hits_at(cc, b) for b in CHECKPOINTS}
    m.update(first_hit_units=_first_hit(cc), discoveries_replicated=confirmed,
             hypotheses_refuted=refuted, adapt_events=adapt, true_hits_in_world=total_hits,
             units_spent=round(spent, 2), films=len(cc))
    return m


# ---------- Omnigent record parsing ----------
def _get(d, *names):
    """First value among ``names`` found at any depth of a dict/list."""
    stack = [d]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            for n in names:
                if n in x and x[n] is not None:
                    return x[n]
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
    return None


def _count(d, words) -> int:
    """Count status-like strings (verdict/status/outcome fields) that contain one of ``words``."""
    n = 0
    stack = [d]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("verdict", "status", "outcome", "result") and isinstance(v, str) \
                        and any(w in v.lower() for w in words):
                    n += 1
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(x, list):
            stack.extend(x)
    return n


def _comp_key(rec):
    c = _get(rec, "composition", "comp") or rec
    if isinstance(c, dict) and all(k in c for k in KEY_FIELDS):
        return "-".join(f"{float(c[k]):.2f}" for k in KEY_FIELDS)
    k = _get(rec, "key")
    return k if isinstance(k, str) and k.count("-") == 5 else None


def parse_run(path: Path) -> dict:
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    start = next((r for r in recs if r.get("kind") == "ll_start"), None)
    world = _get(start, "world") if start else None
    if not isinstance(world, int):
        return {"run": path.parent.name, "unparsed": "no ll_start with integer world"}
    budget = float(_get(start, "budget") or 60.0)
    set_world(world)
    keys = {c.key: i for i, c in enumerate(composition_space())}
    by_formula = {c.formula(): c.key for c in composition_space()}  # live records store the formula string
    truth = space_arrays()[-1]
    curve, seen, spent, bad = [], set(), 0.0, 0
    for r in recs:
        if r.get("kind") != "experiment":
            continue
        k = _comp_key(r)
        if k is None and isinstance(r.get("composition"), str):
            k = by_formula.get(r["composition"])
        cost = _get(r, "cost", "units_charged")
        if k not in keys or cost is None:
            bad += 1
            continue
        spent += float(cost)
        new = bool(truth[keys[k]]) and k not in seen
        seen.add(k)
        curve.append((spent, new))
    if bad and not curve:
        return {"run": path.parent.name, "unparsed": f"{bad} experiment records without composition/cost"}
    adapt_explicit = sum(1 for r in recs if r.get("kind") == "adapt")
    # live asd.labloop_tools schema: ADAPT lines live in pi_decision.planner_rationale
    adapt_explicit += sum(1 for r in recs if r.get("kind") == "pi_decision"
                          and "ADAPT" in str(r.get("planner_rationale") or ""))
    analyses = [r for r in recs if r.get("kind") == "analysis"]
    relax = sum(1 for r in analyses if _get(r, "prior_relaxations", "relaxations"))
    judge = [r for r in recs if r.get("kind") == "judge_verdict"]
    last = judge[-1] if judge else {}
    if isinstance(last.get("discovery_verdicts"), list) or isinstance(last.get("hypothesis_verdicts"), list):
        # each judge record restates the full state: read the LAST one, dedupe by formula / id
        dv = last.get("discovery_verdicts") or []
        replicated = len({d.get("formula") for d in dv if isinstance(d, dict)
                          and (d.get("replicated") is True or str(d.get("status", "")).lower() == "confirmed")})
        hv = last.get("hypothesis_verdicts") or []
        refuted = len({h.get("id") for h in hv if isinstance(h, dict)
                       and any(w in str(h.get("status", "")).lower() for w in ("refuted", "falsified"))})
    else:  # fallback: assumed fixture schema
        refuted = sum(_count(r, ("refuted", "falsified")) for r in analyses)
        replicated = sum(_count(r, ("replicated", "confirmed")) for r in judge)
    m = _metrics(curve, replicated, refuted, adapt_explicit or (refuted + relax),
                 int(truth.sum()), spent)
    m.update(run=path.parent.name, world=world, seed=_get(start, "seed"), budget=budget,
             skipped_experiment_records=bad)
    return m


def _stat(vals):
    v = [x for x in vals if x is not None]
    return None if not v else {"mean": round(float(np.mean(v)), 2), "min": min(v), "max": max(v), "n": len(v)}


def summarise(runs: list[dict]) -> dict:
    keys = ["hits@20", "hits@40", "hits@60", "first_hit_units", "discoveries_replicated",
            "hypotheses_refuted", "adapt_events"]
    return {k: _stat([r.get(k) for r in runs]) for k in keys}


# ---------- selftest ----------
def selftest():
    set_world(2000)
    sp = composition_space()
    hit_i = int(np.flatnonzero(space_arrays()[-1])[0])
    miss_i = int(np.flatnonzero(~space_arrays()[-1])[0])
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ll-w2000"
        p.mkdir()
        L = [{"kind": "ll_start", "world": 2000, "seed": 0, "budget": 60},
             {"kind": "experiment", "composition": sp[miss_i].as_dict(), "result": {"ok": True}, "cost": 1.5},
             {"kind": "experiment", "composition": {k: getattr(sp[hit_i], k) for k in KEY_FIELDS}, "cost": 1.0},
             {"kind": "experiment", "composition": {k: getattr(sp[hit_i], k) for k in KEY_FIELDS}, "cost": 1.0},
             {"kind": "analysis", "updates": [{"id": "H1", "verdict": "refuted"}], "prior_relaxations": ["eg"]},
             {"kind": "judge_verdict", "discoveries": [{"verdict": "replicated"}]}]
        (p / "record.jsonl").write_text("\n".join(json.dumps(x) for x in L))
        m = parse_run(p / "record.jsonl")
    assert m["hits@60"] == 1 and m["first_hit_units"] == 2.5 and m["films"] == 3, m
    assert m["hypotheses_refuted"] == 1 and m["discoveries_replicated"] == 1 and m["adapt_events"] == 2, m
    print("selftest ok:", m)


FIXTURE = ROOT / "scripts" / "ll_fixtures"


def make_fixture():
    """Write a synthetic record.jsonl (rule-based run on world 2000, seed 0, budget 60) in the assumed schema."""
    set_world(2000)
    tr = run_campaign(Config(seed=0, budget=60.0, target_discoveries=99, record_maps=False, label="rule", world=2000))
    L = [{"kind": "ll_start", "world": 2000, "seed": 0, "budget": 60.0, "synthetic": True}]
    seen_h, seen_d = {}, set()
    for rd in tr["rounds"]:
        for e in rd["experiments"]:
            L.append({"kind": "experiment", "composition": {k: e["comp"][k] for k in KEY_FIELDS},
                      "result": {"ok": e["result"]["ok"], "bandgap_ev": e["result"]["bandgap_ev"],
                                 "log_t80": e["result"]["log_t80"]}, "cost": e["result"]["cost"]})
        ups = []  # only verdict CHANGES, as a per-round analysis record would carry
        for h in rd.get("hypotheses", []):
            if h["status"] in ("falsified", "supported", "qualified") and seen_h.get(h["id"]) != h["status"]:
                seen_h[h["id"]] = h["status"]
                ups.append({"id": h["id"], "verdict": h["status"]})
        if ups or any(ev["type"] == "revision" for ev in rd["events"]):
            L.append({"kind": "analysis", "updates": ups,
                      "prior_relaxations": [ev["text"] for ev in rd["events"] if ev["type"] == "revision"]})
        new_d = [d for d in rd.get("discoveries", []) if d["status"] == "confirmed" and d["idx"] not in seen_d]
        seen_d.update(d["idx"] for d in new_d)
        L.append({"kind": "judge_verdict", "discoveries": [{"verdict": "replicated"} for _ in new_d]})
    d = FIXTURE / "ll-w2000"
    d.mkdir(parents=True, exist_ok=True)
    (d / "record.jsonl").write_text("\n".join(json.dumps(x) for x in L) + "\n")
    print("wrote", d / "record.jsonl", len(L), "records")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--runs-dir", default="runs", help="directory holding ll-w2000, ll-w2001, ll-w2002")
    ap.add_argument("--out", default="runs/ll_compare.json")
    ap.add_argument("--fixture", action="store_true")
    ap.add_argument("--make-fixture", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if a.make_fixture:
        make_fixture(); sys.exit(0)
    base = {}
    for w in WORLDS:
        runs = [dict(baseline(w, s, a.budget), seed=s, world=w) for s in range(a.seeds)]
        base[str(w)] = {"runs": runs, "summary": summarise(runs)}
    root = FIXTURE if a.fixture else ROOT / a.runs_dir
    omni, missing = [], []
    for w in WORLDS:
        rec = root / f"ll-w{w}" / "record.jsonl"
        if rec.exists():
            omni.append(parse_run(rec))
        else:
            missing.append(str(rec.relative_to(ROOT)))
    for m in missing:
        print(f"MISSING: {m} not found. Expected from the lead's live Omnigent run on this world; "
              f"skipping (use --fixture to exercise the parser on the synthetic fixture).")
    good = [r for r in omni if "unparsed" not in r]
    out = {"worlds": list(WORLDS), "budget": a.budget, "baseline_seeds": a.seeds,
           "baseline": base, "omnigent_runs": omni, "missing_run_files": missing,
           "source": "synthetic fixture (NOT an Omnigent result)" if a.fixture else "live runs",
           "omnigent_summary": summarise(good) if good else None,
           "note": ("No Omnigent run records available; baseline only." if not good else
                    "Omnigent n is small; no significance claimed."),
           "caveat": "Team-designed simulator; synthetic worlds; rule-based scientist is the baseline."}
    p = ROOT / (a.out if not a.fixture else a.out.replace(".json", "_fixture.json"))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(ROOT)}; run files found: {len(omni)} (parsed {len(good)}), missing: {len(missing)}")
    for w in WORLDS:
        s = base[str(w)]["summary"]
        print(w, {k: (v and v["mean"]) for k, v in s.items()})
    for r in omni:
        print("run:", {k: r.get(k) for k in ("run", "world", "hits@20", "hits@40", "hits@60", "first_hit_units", "discoveries_replicated", "hypotheses_refuted", "adapt_events", "unparsed")})
