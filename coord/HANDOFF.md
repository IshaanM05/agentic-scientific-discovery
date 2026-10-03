# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-04 (cycle 1 end) by lead
## State
- Phase/tier: 0. T001 toy loop merged into dev/agentic-loop (Scout approved); 4 tests pass. main untouched, nothing pushed.
- Working: asd/ loop (generate->pick->run->analyze->update->decide), JSON schemas, SQLite belief, cached stub LLM
- Not exercised: real LLM path (no API key)
- Dataset decided (ADR-001): steel_strength (figshare 7250453, MIT, sha256 in knowledge/datasets/steel-strength.md); hit = yield >= 2000 MPa (15/312); budget 60
## Plan (lead)
1. Tier 0: T002 replay oracle on steel_strength (ticket refined with acceptance a-g in BACKLOG).
2. Tier 1: baselines + eval harness, >=5 seeds -> experiments-to-first-k-hits (T003).
3. Tier 2: arena, LLM-prior acquisition + trust meter, judge/safety, negative memory (T004-T006) + ablations.
4. Tier 3: Streamlit replay dashboard (T007); docs/pitch/video (T008).
5. Freeze 06:00 ET Oct 4; clean-clone run + HACKATHON_BRIEF checklist.
## Next 3 actions
1. Builder: T002 on builder/t002-replay-oracle, plus Scout's T001 carry-overs (requirements.txt, hit on true value, determinism test with fresh caches, hard budget guard, LLM range check, .gitignore dup)
2. Scout: verify unverified dataset facts (units, Citrine source license, LLM memorization check); review T002
3. Lead: merge after Scout approval; status to human every 3h
## Gotchas
- Agent worktrees spawn from main (214aac5): agents must `git checkout -B <branch> dev/agentic-loop` first.
- Builder sandbox cannot write the main checkout's coord/: commit coord edits on the feature branch.
- analyze() uses a fixed 0.9 cutoff; do not present "supported" as a real falsification test.
## Blockers needing the human
- Optional: Materials Project API key / ANTHROPIC_API_KEY in .env (real LLM path untested)
## Spend so far
agent ~$2.3 (lead ~0.7, scout ~1.2, builder ~0.4) | eval $0. Ask human at $10 agent, $18 total.
