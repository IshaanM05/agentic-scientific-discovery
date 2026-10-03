# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-03 14:40 ET (cycle 2 start, re-plan) by lead
## State
- PLAN CHANGED: docs/CHALLENGE_BRIEF.md is authoritative. Omnigent orchestration is mandatory (30% of score).
- Merged on dev/agentic-loop: T001 toy loop (asd/, 4 tests pass), ADR-001 dataset notes. main untouched.
- Test bed accepted: steel_strength (MIT), hit = yield >= 2000 MPa (15/312), budget 60.
- Not exercised: real LLM path (no API key). Omnigent not installed yet.
## Plan (ET; freeze 06:00 Oct 4, deadline 09:00)
1. To 16:30: T002 replay oracle = the meaningful test; Scout verifies Omnigent install/YAML/auth.
2. 16:30-03:00: T000 Omnigent workflow: planner + literature, insight, analysis, safety sub-agents; asd/ functions + oracle/selector as tools; budget + approval policies; >=2 candidate tests chosen by learning/feasibility/cost; surprise reopens an assumption. Then baselines (T003) and LLM-prior acquisition (T005) as tools.
3. 03:00-06:00: >=5-seed baseline vs proposed under matched conditions; report the real speedup.
4. 06:00-09:00: two-minute demo, README with Omnigent specs/policies, 3 videos, submission.
## Next 3 actions
1. Scout (scout/t000-omnigent-recon): Omnigent install on Windows, YAML shape for sub-agents / Python tools / policies, model+auth with Anthropic key -> SCOUT_NOTES + knowledge note; then dataset facts; review Builder.
2. Builder (builder/t000-omnigent): hello-agent YAML calling one asd/ function as a tool, then T000 full, then T002 + Scout's six carry-overs.
3. Lead: relay blockers to human, merge after Scout APPROVE, status every 3h.
## Gotchas
- Agent worktrees spawn from main: `git checkout -B <branch> dev/agentic-loop` first.
- Builder sandbox may block the main checkout's coord/: commit coord edits on the feature branch.
- analyze() uses a fixed 0.9 cutoff; not a real falsification test.
## Blockers needing the human
- ANTHROPIC_API_KEY (or other model auth) for Omnigent agents, in .env, never committed.
## Spend so far
agent ~$2.4 | eval $0. Ask human at $10 agent, $18 total.
