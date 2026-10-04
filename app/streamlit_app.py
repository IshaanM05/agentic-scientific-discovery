"""Princeton-Plainsboro live demo.

    streamlit run app/streamlit_app.py

Step through one discovery loop: the scientist sets the objective and budget,
the House team builds a differential, Cuddy picks tests by EIG/cost, Chase runs
them live on the light curve, Foreman challenges results, the posterior updates,
and consequential actions stop at a human approval gate.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plainsboro import llm  # noqa: E402
from plainsboro.config import HYP_IDS, HYP_LABELS, RESULTS, experiment  # noqa: E402
from plainsboro.data.gatekeeper import load_set  # noqa: E402
from plainsboro.lab import Lab  # noqa: E402
from plainsboro.planner.likelihood import load_tables  # noqa: E402
from plainsboro.record.ledger import Ledger  # noqa: E402
from plainsboro.vetting.common import detrend, epoch_index, phase_fold  # noqa: E402
from plainsboro.vetting.registry import REGISTRY  # noqa: E402

st.set_page_config(page_title="Princeton-Plainsboro Lab", layout="wide")

HCOL = {"H1": "#2a78d6", "H2": "#eb6834", "H3": "#1baf7a", "H4": "#eda100", "H5": "#e87ba4"}
AGENTS = {
    "house": ("House", "Lead diagnostician", "🩺"), "cuddy": ("Cuddy", "Test planner / budget", "📋"),
    "chase": ("Chase", "Experiment runner", "🧪"), "foreman": ("Foreman", "Analysis / skeptic", "🔍"),
    "cameron": ("Cameron", "Literature / evidence", "📚"), "wilson": ("Wilson", "Knowledge graph", "🧠"),
    "gatekeeper": ("Gatekeeper", "Data access (holds labels)", "🔒"), "whiteboard": ("Whiteboard", "Shared record", "🗒️"),
    "safety": ("Safety", "Policy engine", "🛡️"), "human": ("Scientist", "Human approval", "👩‍🔬"),
}


# --------------------------------------------------------------------------- resources
@st.cache_resource
def resources():
    tabs = load_tables()
    sets = {"Synthetic blind set": load_set("blind")}
    try:
        sets["Real Kepler KOIs (transfer test)"] = load_set("real")
    except FileNotFoundError:
        pass
    return tabs, sets


@st.cache_data
def curated_cases():
    """Demo cases picked by rule from blind-set benchmark records (not tuned on)."""
    path = RESULTS / "benchmark" / "records.jsonl"
    if not path.exists():
        return {}
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    P = [r for r in rows if r["condition"] == "P-house-team" and r["threshold"] == 0.9]
    out = {}

    def flips(r):
        ls = [t["leader"] for t in r["trajectory"]]
        return sum(a != b for a, b in zip(ls, ls[1:]))

    sure = [r for r in P if r["correct"] and r["top"] >= 0.9]
    c = [r for r in sure if r["truth"] != "H1" and flips(r) >= 1]
    if c:
        out["Leader flips mid-investigation"] = min(c, key=lambda r: (-flips(r), r["cost"]))["target_id"]
    c = [r for r in sure if r["truth"] == "H1" and r["top"] > 0.95]
    if c:
        out["Clean planet candidate"] = min(c, key=lambda r: r["cost"])["target_id"]
    c = [r for r in sure if any("@rerun" in t for t in r["tests_run"])]
    if c:
        out["Foreman's counter-experiment"] = c[0]["target_id"]
    c = [r for r in sure if r["truth"] == "H3"]
    if c:
        out["Tricky false positive (blend)"] = c[0]["target_id"]
    c = [r for r in P if not r["correct"] and r["needs_human"]]
    if c:
        out["Honest failure -> escalated to human"] = c[0]["target_id"]
    return out


# --------------------------------------------------------------------------- plots
def lc_figure(target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s, lc = target.signal, target.lc
    P, t0, dur = s["period_d"], s["epoch"], s["duration_h"] / 24
    fig, axes = plt.subplots(1, 3, figsize=(12, 2.8), gridspec_kw={"width_ratios": [2.2, 1, 1]})
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)
    ax = axes[0]
    ax.plot(lc.time, (lc.flux - 1) * 1e3, ".", ms=1.2, color="#8a8984")
    q = lc.quality
    ax.plot(lc.time[q], (lc.flux[q] - 1) * 1e3, "|", ms=8, color="#e34948", label="flagged cadences")
    n = epoch_index(lc.time, P, t0)
    for k in np.unique(n):
        tc = t0 + k * P
        if lc.time[0] <= tc <= lc.time[-1]:
            ax.axvline(tc, color=HCOL["H1"], lw=0.5, alpha=0.4)
    ax.set_title("Raw light curve (ppt); blue = predicted transits, red = flagged", fontsize=9, loc="left")
    f = detrend(lc, P, t0, dur)
    ph = phase_fold(lc.time, P, t0)
    for ax, center, title in ((axes[1], 0.0, "Folded at transit (odd vs even)"),
                              (axes[2], 0.5 * P, "Folded at phase 0.5 (secondary?)")):
        d = phase_fold(lc.time, P, t0 + center)
        m = np.abs(d) < 3 * dur
        odd = (n % 2 == 1) & m
        even = (n % 2 == 0) & m
        ax.plot(d[odd] * 24, (f[odd] - 1) * 1e3, ".", ms=2, color=HCOL["H1"], label="odd")
        ax.plot(d[even] * 24, (f[even] - 1) * 1e3, ".", ms=2, color=HCOL["H2"], label="even")
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_xlabel("hours from center", fontsize=8)
    axes[1].legend(fontsize=7, frameon=False, markerscale=4)
    fig.tight_layout()
    return fig


def trajectory_figure(events):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pts = [e for e in events if e["kind"] == "posterior"]
    if not pts:
        return None
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ax.spines[["top", "right"]].set_visible(False)
    xs = range(len(pts))
    for h in HYP_IDS:
        ys = [p["posterior"][h] for p in pts]
        ax.plot(xs, ys, "-o", color=HCOL[h], lw=2, ms=5, mec="white", mew=1)
        ax.annotate(h, (len(pts) - 1, ys[-1]), xytext=(5, 0), textcoords="offset points", fontsize=8, va="center")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(["prior"] + [(p.get("after") or "")[2:] for p in pts[1:]], rotation=30, fontsize=7, ha="right")
    ax.set_ylim(0, 1.02)
    ax.axhline(experiment()["stopping"]["posterior_threshold"], color="#b5b4ad", ls="--", lw=1)
    ax.set_ylabel("posterior", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.set_title("Belief over the differential after each experiment", fontsize=9, loc="left")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- loop control
def start(target, cfg, opts):
    tabs, _ = resources()
    narrator = None
    if opts["narrate"] and llm.available():
        narrator = llm.Narrator()
    lab = Lab(tabs, cfg, name="P-live", benchmark_mode=opts["benchmark_mode"], live_literature=opts["live_lit"],
              ledger=Ledger(ROOT / "runs" / "demo_ledger.jsonl"), approver=lambda e: "deny", n_interval_draws=300,
              narrator=narrator, threshold=cfg["stopping"]["posterior_threshold"])
    st.session_state.update(lab=lab, gen=lab.investigate(target), events=[], pending=None, record=None,
                            primed=False, answer=None, target_id=target.target_id)


def pump(mode: str):
    ss = st.session_state
    gen = ss.get("gen")
    if gen is None or ss.get("record") is not None:
        return
    steps = 0
    while True:
        try:
            if not ss.primed:
                ev = next(gen)
                ss.primed = True
            else:
                ans, ss.answer = ss.answer, None
                ev = gen.send(ans)
        except StopIteration as stop:
            ss.record = stop.value
            ss.pending = None
            return
        ss.events.append(ev)
        steps += 1
        if ev["kind"] == "approval":
            ss.pending = ev
            return
        if mode == "one":
            return
        if mode == "decision" and ev["kind"] in ("plan", "reopen", "verdict") and steps > 1:
            return
        if steps > 400:
            return


def render_event(ev):
    name, role, icon = AGENTS.get(ev["agent"], (ev["agent"], "", "•"))
    with st.chat_message(ev["agent"], avatar=icon):
        st.markdown(f"**{name}** · <span style='color:#8a8984'>{role} · {ev['kind']}</span>", unsafe_allow_html=True)
        k = ev["kind"]
        if k == "plan" and ev.get("plan") and ev["plan"]["candidates"]:
            st.write(ev["text"])
            df = pd.DataFrame(ev["plan"]["candidates"]).sort_values("score", ascending=False)
            df["chosen"] = df.test_id.isin(ev["plan"]["chosen"])
            st.dataframe(df, hide_index=True, width="stretch")
        elif k == "hypotheses":
            st.write("Differential = default H1-H5 plus House's **agent-generated** hypotheses:")
            for p in ev.get("proposals", []):
                st.markdown(f"- `{p['id']}` → {p['parent']} · *{p['name']}* "
                            f"<span style='background:#fdf0d5;padding:1px 6px;border-radius:6px;font-size:0.8em'>"
                            f"agent_generated</span> — {p['mechanism']}", unsafe_allow_html=True)
        elif k == "evidence":
            st.write(ev["text"].split(":")[0] + ":")
            for e in ev.get("evidence", []):
                ok = {True: "resolved ✔", False: "UNRESOLVED", None: "cached"}[e.get("resolved")]
                st.markdown(f"- [{e['source_id']}]({e['url']}) *{e['title'][:90]}* — {e['claim']} ({ok})")
            for h in ev.get("openalex", []) or []:
                st.markdown(f"- OpenAlex {h['openalex_id']}: *{h['title']}* ({h['year']}, cited {h['cited_by']})")
        elif k == "verdict":
            st.success(ev["text"])
        elif k in ("approval",):
            st.warning(ev["text"])
        elif k == "policy":
            (st.error if "DENIED" in ev["text"] else st.info)(ev["text"])
        elif k == "reopen":
            st.warning(ev["text"])
        else:
            st.write(ev["text"])


# --------------------------------------------------------------------------- UI
tabs, sets = resources()
cfg0 = experiment()

st.title("Princeton-Plainsboro · agentic exoplanet diagnosis lab")
st.caption("Every transit-like dip is a patient. Question → Evidence → Hypothesis → Experiment → Result → Updated "
           "decision. Orchestration and policies mirror the Omnigent bundle in `omnigent/princeton_plainsboro`.")

with st.sidebar:
    st.header("1 · Scientist sets the objective")
    set_name = st.selectbox("Case set", list(sets))
    gk = sets[set_name]
    cur = curated_cases() if set_name.startswith("Synthetic") else {}
    options = [f"★ {k}: {v}" for k, v in cur.items()] + gk.target_ids()
    pick = st.selectbox("Target (anonymized)", options)
    target_id = pick.split(": ")[-1] if pick.startswith("★") else pick
    thr = st.slider("Stopping threshold (posterior)", 0.6, 0.99, float(cfg0["stopping"]["posterior_threshold"]), 0.01)
    max_tests = st.slider("Budget: max tests", 2, 8, int(cfg0["budget"]["max_tests"]))
    max_cost = st.slider("Budget: max cost units", 3.0, 16.0, float(cfg0["budget"]["cost_units_max"]), 0.5)
    st.header("2 · Options")
    live_lit = st.checkbox("Live literature (OpenAlex + arXiv resolver)", value=True)
    bench_mode = st.checkbox("Benchmark mode (block target-specific lookups)", value=True)
    narrate = st.checkbox("LLM voices for agents (needs OPENAI_API_KEY with credit)", value=False,
                          disabled=not llm.available())
    if st.button("▶ Start investigation", type="primary", width="stretch"):
        cfg = copy.deepcopy(cfg0)
        cfg["stopping"]["posterior_threshold"] = thr
        cfg["budget"].update(max_tests=max_tests, cost_units_max=max_cost)
        start(gk.get_target(target_id), cfg, dict(live_lit=live_lit, benchmark_mode=bench_mode, narrate=narrate))
        st.session_state.set_name = set_name
        pump("decision")
        st.rerun()
    st.caption("Labels are held by the Data Gatekeeper and revealed only after the verdict.")

tab_inv, tab_bench, tab_ledger, tab_agents = st.tabs(["Live investigation", "Benchmark: measured speedup",
                                                      "Run ledger & policies", "Agents & Omnigent"])

with tab_inv:
    ss = st.session_state
    if "gen" not in ss:
        st.info("Pick a target in the sidebar (★ = curated demo cases) and press **Start investigation**.")
    else:
        gk = sets[ss.get("set_name", set_name)]          # the set this investigation was started from
        target = gk.get_target(ss.target_id)
        c1, c2, c3, c4 = st.columns(4)
        done = ss.record is not None
        if c1.button("Next step", disabled=done or ss.pending is not None, width="stretch"):
            pump("one"); st.rerun()
        if c2.button("Run to next decision", disabled=done or ss.pending is not None, width="stretch"):
            pump("decision"); st.rerun()
        if c3.button("Run to verdict", disabled=done or ss.pending is not None, width="stretch"):
            pump("end"); st.rerun()
        if c4.button("Reset", width="stretch"):
            for k in ("gen", "events", "record", "pending", "lab"):
                ss.pop(k, None)
            st.rerun()

        if ss.pending is not None:
            st.warning(f"🛡️ **Human approval required** · {ss.pending['text']}")
            a1, a2 = st.columns(2)
            if a1.button("Approve", type="primary", width="stretch"):
                ss.answer = "approve"; ss.pending = None; pump("decision"); st.rerun()
            if a2.button("Deny", width="stretch"):
                ss.answer = "deny"; ss.pending = None; pump("decision"); st.rerun()

        if target is not None:
            st.pyplot(lc_figure(target), width="stretch")
        left, right = st.columns([1.25, 1])
        with left:
            st.subheader("Agent handoffs")
            for ev in ss.events:
                if ev["kind"] == "posterior" and ev["agent"] == "whiteboard" and ev.get("after") is None:
                    continue
                render_event(ev)
        with right:
            post = next((e["posterior"] for e in reversed(ss.events) if e["kind"] == "posterior"), None)
            if post:
                st.subheader("Differential whiteboard")
                dfp = pd.DataFrame({"hypothesis": [f"{h} {HYP_LABELS[h]}" for h in HYP_IDS],
                                    "posterior": [post[h] for h in HYP_IDS]})
                st.bar_chart(dfp, x="hypothesis", y="posterior", horizontal=True, height=230)
                fig = trajectory_figure(ss.events)
                if fig:
                    st.pyplot(fig, width="stretch")
            lab = ss.get("lab")
            if lab is not None and target is not None:
                st.caption(f"Policy session state: {lab.policy.session_state}")
            if ss.record is not None:
                v = ss.record["verdict"]
                st.subheader("Verdict")
                st.metric("Diagnosis", v["label_text"].split(" (")[0], f"P = {v['top_posterior']:.3f}")
                st.write(f"90% credible interval **{v['interval'][0]:.2f}–{v['interval'][1]:.2f}** · "
                         f"{v['tests_used']} tests · {v['cost_used']} cost units · needs human: **{v['needs_human']}**")
                if v["dissent"]:
                    st.markdown("**Dissent**\n" + "\n".join(f"- {d['agent']}: {d['objection']}" for d in v["dissent"]))
                st.markdown("**Required follow-up**\n" + "\n".join(f"- {f}" for f in v["required_followup"]))
                st.markdown("**Provenance**: run IDs " + ", ".join(f"`{r}`" for r in v["run_ids"]) +
                            "; evidence " + ", ".join(f"`{e}`" for e in v["evidence_ids"]))
                truth_ok = gk.score(ss.target_id, v["label"], caller="evaluator")
                with st.expander("Reveal ground truth (Data Gatekeeper, evaluator only)"):
                    lab_true = gk._label(ss.target_id, "evaluator")
                    st.write(f"Truth: **{lab_true}** ({' / '.join(HYP_LABELS[h] for h in lab_true.split('|'))}) → "
                             f"verdict {'CORRECT' if truth_ok else 'WRONG'}.")

with tab_bench:
    rep = RESULTS / "REPORT.md"
    figs = RESULTS / "figures"
    if rep.exists():
        cols = st.columns(2)
        for i, name in enumerate(["accuracy_vs_cost.png", "accuracy_at_k.png"]):
            if (figs / name).exists():
                cols[i].image(str(figs / name), width="stretch")
        st.markdown(rep.read_text(encoding="utf-8"))
        real = RESULTS / "REAL_REPORT.md"
        if real.exists():
            st.markdown(real.read_text(encoding="utf-8"))
    else:
        st.info("Run `python -m plainsboro.eval.run_benchmark` then `python -m plainsboro.eval.analyze`.")

with tab_ledger:
    lab = st.session_state.get("lab")
    if lab is None:
        st.info("Start an investigation to see its ledger.")
    else:
        evs = lab.ledger.events
        df = pd.DataFrame([{k: e.get(k) for k in ("ts", "agent", "action", "target_id", "inputs_hash", "outputs_hash",
                                                   "cost_units")} | {"policy": (e.get("policy") or {}).get("result"),
                                                                    "reasons": " ".join((e.get("policy") or {}).get("reasons", []))}
                           for e in evs])
        st.write(f"{len(df)} ledger events (append-only, also written to `runs/demo_ledger.jsonl`).")
        st.dataframe(df, width="stretch", hide_index=True)
        pol = df[df.policy.notna()]
        st.subheader("Policy decisions")
        st.dataframe(pol[["agent", "action", "policy", "reasons"]], width="stretch", hide_index=True)
    st.subheader("Policy self-check")
    if st.button("Try forbidden actions (label read, external write, target lookup, unregistered test)"):
        from plainsboro.policies import PolicyEngine, default_policies
        eng = PolicyEngine(default_policies(cfg0, benchmark_mode=True))
        trials = [("house", "gatekeeper_read_label", {"target_id": "T-0001"}),
                  ("house", "send_email", {"to": "press@example.org"}),
                  ("cameron", "literature_search", {"query": "KOI-7016 disposition", "target_id": "T-0001"}),
                  ("chase", "run_vetting_test", {"target_id": "T-0001", "test_id": "T-made-up"}),
                  ("house", "run_vetting_test", {"target_id": "T-0001", "test_id": "T-odd-even"}),
                  ("house", "issue_verdict", {"label_text": "confirmed planet", "run_ids": ["x"], "top_posterior": 0.99}),
                  ("house", "propose_followup", {"kind": "RV"})]
        st.table(pd.DataFrame([{"actor": a, "tool": t, **{k: v for k, v in eng.evaluate(a, t, g).items()
                                                            if k in ("result", "reasons")}} for a, t, g in trials]))

with tab_agents:
    st.markdown((ROOT / "docs" / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "docs" / "AGENTS.md").exists()
                else "See `omnigent/princeton_plainsboro/`.")
    st.subheader("Test registry")
    st.dataframe(pd.DataFrame([{"test_id": t, "name": d.name, "cost": d.cost, "separates": ", ".join(d.separates),
                                "outcome bins": " | ".join(d.bin_labels), "method refs": ", ".join(d.method_refs)}
                               for t, d in REGISTRY.items()]), hide_index=True, width="stretch")
    st.subheader("Calibrated likelihood tables P(outcome | H) (calibration set only)")
    for t in REGISTRY:
        st.markdown(f"**{t}** — temper τ = {tabs.temper}")
        st.dataframe(pd.DataFrame(tabs.table(t), index=[f"{h} {HYP_LABELS[h]}" for h in HYP_IDS],
                                  columns=REGISTRY[t].bin_labels).round(3), width="stretch")
