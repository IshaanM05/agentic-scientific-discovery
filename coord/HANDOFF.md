# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-03 15:25 ET (cycle 4 end) by lead. NOTE: the earlier "19:07 ET" stamp was wrong (that was UTC). Get ET via python with UTC-4; git-bash TZ= does not work.
## State
- dev/agentic-loop 83d5271: T000 Omnigent workflow, T002 replay oracle, T010 run-config fix (LC_ASD_* env), c272 prompt-leak fix, T003 baselines. 29 tests pass. Scout APPROVE on all except T011.
- T003 (20 seeds, budget 60, matched pool/initial design): exp-to-k mean k=1/3/5: random 12.4/41.5/55.8, OFAT 15.6/26.9/41.0, BO 17.9/25.4/42.1. Random row lucky; plot random from >=200 seeds or analytic.
- Single-LLM n=1: 14/15 hits -> likely recall. NOT a result until T009.
- T011: adaptation proven (runs/t011: H1,H2 refuted -> ADAPT -> H3 -> c150). ASK: human ran policy_demo (runs/t011-ask, session 8e65f71d...): first ASK auto-rejected instantly; human typed "approve" in chat; second call ran (rec-0003) in same second as the approval event. Open question to human: card click or chat only? CanUseToolShadowedWarning in runner log -> policy ASK may not be a hard human gate on Windows claude-sdk.
## Plan (ET; freeze 06:00 Oct 4, deadline 09:00)
1. Next: T011 fix (commit t011-ask record + exported transcript, explicit approval entry, honest note on ASK behavior); no-id test covers all agents/*.yaml.
2. T009 probe + named vs blinded LLM arm, seeds 0-4, budget 60 (protocol: knowledge/concepts/memorization-control.md).
3. T005 LLM-prior acquisition vs BO under matched conditions; headline curve; report what we measure.
4. 03:00-06:00 strengthen + analysis; 06:00-09:00 demo, README, videos.
## Gotchas
- Worktrees spawn from main: `git checkout -B <branch> dev/agentic-loop` first.
- Omnigent: PyPI install; PYTHONUTF8=1; `omnigent server --background`; `--server local`; declare tools per sub-agent; env reaches tools only via LC_ASD_*; session export needs `--server http://127.0.0.1:6767`.
- Human runs scripts with `powershell -ExecutionPolicy Bypass -File scripts/live.ps1 ...`.
- Agent sandboxes cannot write main checkout coord/; they commit coord on their branch, lead merges.
- Never read/print .env.
## Spend so far
agent ~$11.3 (lead ~1.5, scout ~3.9, builder ~5.9) | model calls on subscription | eval $0. Ask human at $16 agent, $18 total.
