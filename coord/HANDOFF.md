# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-03 16:00 ET (cycle 6, A done) by lead. Get ET via python with UTC-4; git-bash TZ= does not work.
## State
- dev/agentic-loop 8aa58ab: T000, T002, T003, T009, T005, T010 merged (Scout APPROVE). 30 tests pass. T011 merged with 3 small fixes owed.
- T005/T009 result (seeds 0-4, B=60, mean hits@60): OFAT 6.6, BO 5.8, named prior+GP 8.2, blind prior+GP 8.4, named prior-only 13.2, blind prior-only 8.2.
- T009 recall flag SET -> NO acceleration claim. Use Scout's verbatim README paragraph (coord/SCOUT_NOTES.md, cycle 5 review). Probe ran at default sampling via claude CLI (temperature 0 not settable): state it.
- Approval: -p runs decline ASK automatically (fail-closed, runs/t011-ask). Interactive REPL run (runs/t011-repl) held the call ~1.6 s until a client answered; the browser's resolve won, so the hold-until-human is NOT proven. Approved wording: "In an interactive run the approval policy held the tool call until a human answered (runs/t011-repl, about 1.6 s); non-interactive -p runs decline automatically (fail-closed)."
## Cycle 6
- A DONE, merged at fb903a7 (30 tests). 20-seed blind llm_bo 8.75 hits@60 vs OFAT 6.40 (19/0/1, +2.35, CI [1.75,3.00]) vs BO 6.85 (15/3/2, +1.90); flag set -> no acceleration claim. docs/headline.png, README, docs/DEMO_SCRIPT.md v2. Approval: 22.2 s human hold (runs/t011-repl30).
- B DONE, merged 4f019c3 (33 tests): judge n=12, acc 1.00, Brier 0.060, bins 0/2/10; near-arithmetic (judge sees ledger value), do not cite as skill.
- C DONE (36 tests): arena 5 hyps, 4/5 within 25%, Spearman 0.56 p=0.21 (chance); wide ranges score free, not skill.
- D DONE (37 tests): offline Streamlit replay, `streamlit run dashboard/app.py`; ADAPT labelled inferred. All A-D merged at 816dee4.
- Clean-clone check PASSED after deps fix (fresh venv: 37 tests, plot ok, dashboard 200).
- Next: optional T013 ablation only if human wants; then human records demo/videos and submits. main untouched until human OK.
## Plan (ET; freeze 06:00 Oct 4, deadline 09:00)
- Remaining features: demo polish only. Then 2-min demo, README, 3 videos, submission checklist (docs/HACKATHON_BRIEF.md + CHALLENGE_BRIEF.md). Merge to main only when the human says so.
## Gotchas
- Worktrees spawn from main: `git checkout -B <branch> dev/agentic-loop` first.
- Omnigent: PyPI install; PYTHONUTF8=1; `omnigent server --background`; `--server local`; tools declared per sub-agent; env to tools only via LC_ASD_*; session export needs `--server http://127.0.0.1:6767`.
- Human scripts: `powershell -ExecutionPolicy Bypass -File ...`.
- Agent sandboxes cannot write the main checkout's coord/; they commit coord on their branch.
- Builder used the logged-in claude CLI (same Pro subscription) for T009/T005 calls.
- Never read/print .env.
## Spend so far
agent ~$15 of $16 limit (lead ~2, scout ~5, builder ~8, rough self-reports) | model calls on Pro subscription, no throttling so far.
- Cycle 7 (E plan): E1 counterfactual + E2 live end-to-end (incl. E3 safety block) in parallel; then E4 packaging; E5 optional. dev pushed at 5ea28db; main untouched.
- THROTTLED (Pro session limit, resets 04:50 IST): E2 live run not done. builder/e2-live 4b9f5be has rewired planner (judge+arena live order, parallel analysis, safety_gate DENY, 39 tests) unreviewed. E1 status pending. Resume E2 run after reset: ASD_SEED=7 ASD_RUN_DIR=runs/e2-live ASD_RUN_ID=e2-live ASD_BUDGET=8.
- E1 partial on builder/e1-counterfactual: pre-reg 92ca1e3 (before any call), code+test 1c98c61; 4/20 cfnamed seeds done; resume: python scripts/e1_counterfactual.py (cached), then plot + README; needs Scout review.
