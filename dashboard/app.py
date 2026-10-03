"""Offline replay dashboard. Read-only; no LLM or network calls.
Run: streamlit run dashboard/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import streamlit as st  # noqa: E402
import data as D  # noqa: E402

st.set_page_config(page_title="Agentic discovery replay", layout="wide")
st.title("Agentic scientific discovery: offline replay")
st.caption("Read-only replay of committed runs/* and results/*. Content marked AGENT-GENERATED was "
           "produced by LLM agents and is not verified science.")
tabs = st.tabs(["Run timeline", "Policies", "Hypothesis arena", "Judge", "Results"])
AG = "AGENT-GENERATED"

with tabs[0]:
    runs = D.list_runs()
    run = st.selectbox("Run", runs, index=runs.index("t011") if "t011" in runs else 0)
    rec = D.annotate_adapt(D.load_record(run))
    st.write(f"{len(rec)} record entries, in written order.")
    for e in rec:
        k = e.get("kind")
        head = f"{e.get('record_id')} | {k}"
        if k == "handoff":
            head += f" | {e.get('agent')} -> planner ({e.get('handoff_kind')})"
        if k == "test_choice" and e.get("adapt"):
            head += " | ADAPT (inferred: follows a surprising/reopened analysis)"
        with st.expander(head):
            if k == "literature":
                st.caption("Retrieved from OpenAlex (external); query written by an agent")
                st.write(e.get("query"))
                for c in e.get("citations", []):
                    st.markdown(f"- {c.get('title')} ({c.get('year')}) {c.get('doi') or c.get('id')}")
            elif k == "hypothesis":
                st.caption(AG)
                st.write(e.get("text"))
                st.write({x: e.get(x) for x in ("predicted_value", "assumption", "candidate_ids") if x in e})
            elif k == "test_choice":
                st.table([{"option": o.get("name"), "learning": o.get("expected_learning"),
                           "feasibility": o.get("feasibility"), "cost": o.get("cost"),
                           "score": o.get("score")} for o in e.get("options", [])])
                st.write("Chosen: " + str(e.get("chosen")))
                st.write(e.get("reasons"))
            elif k == "analysis":
                st.caption(AG)
                st.write({x: e.get(x) for x in ("hypothesis_id", "value", "predicted", "rel_error",
                                                "supported", "surprising")})
                st.write("Reopened assumptions:", e.get("reopened_assumptions"))
            else:
                if k in ("safety", "handoff"):
                    st.caption(AG)
                st.json(e)

with tabs[1]:
    P = D.load_policies()
    st.subheader("1. Budget DENY (runs/policy_demo)")
    st.table(P["policy_demo_ledger"])
    for d in P["deny"]:
        st.code(d)
    st.subheader("2. Approval hold (runs/t011-repl30, interactive)")
    st.write("The call was held 22.2 s, with no automatic resolve, until the human clicked Approve.")
    st.markdown(P["approval_evidence"])
    st.subheader("3. Non-interactive -p, fail-closed (runs/t011-ask)")
    st.write(P["ask_meta"])
    st.write("Non-interactive -p runs decline automatically (fail-closed).")
    st.json(P["ask_calls"][-2:] if P["ask_calls"] else [])
    st.caption("README, verbatim:")
    st.info(D.readme_section("Human approval (policy ASK)"))

with tabs[2]:
    A = D.load_arena()
    elo = {r["id"]: r["elo"] for r in A["elo"] if "elo" in r}
    cal = {i["id"]: i for i in A["calibration"].get("items", [])}
    st.caption(AG + " hypotheses and critiques. Elo from pairwise agent matches.")
    st.table(sorted([{"id": k, "elo": v} for k, v in elo.items()], key=lambda r: -r["elo"]))
    for h in A["hypotheses"]:
        c = A["critiques"].get(h["id"], {})
        with st.expander(f"{h['id']} (Elo {elo.get(h['id'])}): {h['hypothesis'][:90]}"):
            st.write(h["hypothesis"])
            st.write("Prediction:", h.get("quantitative_prediction"))
            st.write("Kill condition:", h.get("kill_condition"))
            st.write("Novelty verdict:", h.get("novelty"))
            st.write("Critic attack:", c.get("attack"))
            st.write("Refuting test (not executed):", c.get("refuting_test"))
            st.write("Calibration vs pool:", cal.get(h["id"]))
    st.caption("README, verbatim:")
    st.info(D.readme_section("Hypothesis arena"))

with tabs[3]:
    st.caption("Verdicts come from a Haiku 4.5 judge (AGENT-GENERATED).")
    st.warning("Caveat: the judge is shown the ledger value, so the outcome check is close to "
               "arithmetic and says little about scientific judgement. n=12; no low-confidence verdicts.")
    for r in D.judge_runs():
        st.subheader(r)
        st.table([{"conclusion": v.get("conclusion_id"), **v.get("checks", {}),
                   "confidence": v.get("confidence"), "reason": v.get("reason")} for v in D.load_judge(r)])
    st.json(D.jf(D.RESULTS / "judge_calibration.json"))
    st.caption("README, verbatim:")
    st.info(D.readme_section("Judge"))

with tabs[4]:
    R = D.load_results()
    if R["headline"].exists():
        st.image(str(R["headline"]), caption="docs/headline.png")
    b = R["blind20"]
    st.subheader("20-seed blind run (hits@60)")
    rows = [{"arm": "blind llm_bo", "mean": b.get("mean")}]
    for k in ("ofat", "bo"):
        if k in b:
            v = b[k]
            rows.append({"arm": k, "mean": v.get("mean"),
                         "wins/ties/losses": f"{v.get('wins')}/{v.get('ties')}/{v.get('losses')}",
                         "mean diff": round(v.get("mean_diff", 0), 2),
                         "boot95": str(v.get("boot95")), "sign p": v.get("sign_p")})
    st.table(rows)
    st.subheader("5-seed arms (summary.json)")
    st.table([{"arm": k, "hits60_mean": v.get("hits60_mean"), "hits60": str(v.get("hits60"))}
              for k, v in R["summary"].items() if isinstance(v, dict) and "hits60_mean" in v])
    st.error("Memorisation flag SET: no acceleration claim. Guided prompt MAE 189 vs generic 255 MPa; "
             "3/20 near-exact; the advantage is consistent with memorisation of a public benchmark "
             "or a named-domain prior.")
    st.caption("README, verbatim:")
    st.info(D.readme_section("Result"))
    st.info(D.readme_section("Limitations"))
