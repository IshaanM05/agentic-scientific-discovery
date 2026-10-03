# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-03 19:07 ET (cycle 3 end) by lead
## State
- Merged on dev/agentic-loop (842aa3d, Scout APPROVE): T000 Omnigent workflow + T002 steel replay oracle. 25 tests pass.
- Live (subscription token in .env, loaded only by scripts/live.ps1): hello agent; planner -> literature/insight/analysis/safety sub-agents (runs/live2: 11 citations, 2 labeled hypotheses, design_tests choice, 5 experiments, reopened assumptions); budget DENY policy (runs/policy_demo).
- Models: Sonnet 5.5 + Haiku 4.5 only, never Opus. Usage limit hit -> stop and report, no retry loops.
- Weak: ASK approval seen only as runner-log event; planner did not adapt next experiment after an analysis.
- Bug F1: ASD_SEED/BUDGET/RUN_DIR do not reach tool processes -> all runs share runs/default. Blocks evals.
- Honesty: c272 hit at experiment 1 is likely memorization (public matbench_steels). NO speedup claim before T003 + T009.
## Plan (ET; freeze 06:00 Oct 4, deadline 09:00)
1. Now-22:00: T010 (F1), T011 (adaptive run + visible ASK), T003 baselines.
2. 22:00-03:00: T009 memorization control, T005 LLM-prior acquisition as tool; >=5 seeds at budget 60.
3. 03:00-06:00: headline curve, measured speedup (whatever it is), next experiment.
4. 06:00-09:00: 2-min demo, README, videos, submission.
## Next 3 actions
1. Builder: T010 then T011 then T003 on builder/t010-run-config (from dev/agentic-loop).
2. Scout: review T010/T011; design T009 probe; audit claims (T012).
3. Lead: get human OK past $10 agent spend before next cycle.
## Gotchas
- Worktrees spawn from main: `git checkout -B <branch> dev/agentic-loop` first.
- Omnigent: PyPI install (git URL fails on Windows); PYTHONUTF8=1; `omnigent server --background`; `--server local`; tools: inherit does not work, declare tools per sub-agent; handoff type unused at runtime; cost_budget needs expensive_models: [].
- Never read/print .env.
## Spend so far
agent ~$6.7 (lead ~1.1, scout ~2.7, builder ~2.9) | model calls on subscription | eval $0. Ask human at $10 agent, $18 total.
