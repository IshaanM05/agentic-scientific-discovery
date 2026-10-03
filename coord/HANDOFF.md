# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-03 (cycle 0 start) by lead
## State
- Phase/tier: 0 (nothing built yet). Scaffold committed locally on main (not pushed).
- Working: coord/, knowledge/ vault, agent definitions
- Broken: nothing
- Oracle: no .env / no MP key -> use bundled offline materials sample (MP API optional later)
## Plan (lead)
1. Tier 0: toy-oracle loop end to end (T001), then replay oracle on offline materials sample (T002).
2. Tier 1: baselines random/OFAT/pure BO/single-LLM (Sonnet 5.5) + eval harness, >=5 seeds -> "experiments to first k hits" curve (T003).
3. Tier 2: arena + LLM-prior acquisition w/ trust meter + judge/safety + negative memory (T004-T006), with ablations.
4. Tier 3: Streamlit replay dashboard (T007); docs/pitch/video scripts with real numbers (T008).
5. Freeze 06:00 ET Oct 4; clean-clone run + HACKATHON_BRIEF checklist. Report real speedup.
## Stack
Python, SQLite belief state, Streamlit dashboard, no training. Product agents + single-LLM baseline: Sonnet 5.5. Cache all LLM+oracle calls keyed (prompt, model, seed).
## Next 3 actions
1. Builder: T001 on branch builder/t001-toy-loop (worktree)
2. Scout: pick offline materials sample + hit definition (answer for T002); review T001 merge note
3. Lead: check SCOREBOARD/DECISIONS each cycle; status to human every 3h
## Open questions for the other agent
- Scout: which small offline materials dataset (license OK for public repo) + hit threshold?
## Blockers needing the human
- Optional: Materials Project API key in .env; hackathon credits request
## Spend so far
agent ~$0.5 (lead setup) | eval $0. Ask human at $10 agent, $18 total.
