# Live Omnigent run report: LabLoop world 2000 (seed 0, budget 60)

Caveat: LabLoop is a team-built simulator with synthetic hidden physics (a benchmark, not real devices). This is one live run, a single sample; nothing here is a real-device claim.

## Setup
- Executed inside a cloud session (Linux, Python 3.12 venv via uv, omnigent 0.16.0), planner `agents/labloop_planner.yaml` unmodified (planner Sonnet 5.5; sub-agents as declared). Model calls worked through the session's already provided claude CLI login.
- Smoke run: `runs/ll-smoke2000` (budget 8): completed, 5 films, planner handed off to sub-agents (records: literature, arena_round, pi_decision, design, experiment, analysis, judge_verdict).
- Full run: `runs/ll-w2000-full` (budget 60). Prompt: "Call ll_start(world=2000, seed=0, budget=60) and run the full LabLoop loop to stop or budget. Follow your prompt."

## Result
- Status: COMPLETED by LabLoop's own rule, not PARTIAL. In round 5 `ll_pi_decide` returned mode `stop` ("5 confirmed discoveries meet the goal; stopping to save 38.0 units of budget"). 22.0 of 60 units used, 38.0 unspent.
- Films: 15 (4 rounds; 11 of the 15 recorded `meets_spec: true`, one of those replicate attempts failed QC with pinholes).
- Confirmed (two films in spec, judged replicated): Cs0.1FA0.9Pb0.8Sn0.2I3, Cs0.1FA0.9Pb0.7Sn0.3I3, Cs0.1FA0.9Pb0.6Sn0.4I3, Cs0.2FA0.8Pb0.8Sn0.2I3, Cs0.2FA0.8Pb0.7Sn0.3I3. One further single-film candidate (Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3, 521 h). Misses: three films under 500 h (MA 471 h, Cs0.3 495 h, Pb-only baseline outside the Eg window).
- Duration: about 523 s (8.7 min) wall time, from the exported session's created/updated timestamps.
- Cost: the exported session metadata lists a few cost_usd figures (about 0.26, 1.25, 1.51 USD); these are not summed here and the total is clearly far below the 20 USD guard.

## Orchestration
- Sub-agents: literature, generator, critic, analyst, judge and safety were invoked through `sys_session_send` (22 mentions in the exported transcript). Record kinds present from tools: ll_start 1, literature 1, arena_round 3, pi_decision 5, design 4, experiment 15, analysis 4, judge_verdict 3 (36 records).
- Candidate designs per decision: each of the 4 `design` records holds 5 protocols, each with a reason field and safety_review (level 2 for all).
- ADAPT lines: 0 literal "ADAPT:" lines appear in the run's stdout or in the exported transcript (the planner prompt asks for them; it did not emit that exact string). Adaptation is visible in prose and records instead: H3 ("Sn >= 0.3 gives T80 < 400 h") falsified, relaxing the literature stability prior; the planner changed the round-2 MA contrast proposal after a critic attack (400 h gap to log10 0.2); round-2 onward switched from tests to replication of candidates.
- Policy events: none observed (no human-approval ASK, no safety or budget DENY; all slots level 2, "approved with SOP"). No restricted element or dopant was requested.
- Rejected proposals (arena, all for the same reason): round 2 "FA-rich (0.85-0.95) low-Cs ... T80 > 1000 h" and round 3 "Cs 0.05-0.12 vs 0.18-0.25 ... T80" were rejected with "region contains only 2 compositions (need >= 3)". In the smoke run, 3 proposals were rejected for the same reason in round 2, then a second proposal was dropped.

## Errors and handling
- Round-4 judge sub-agent session looped without calling `ll_judge` (restated data, asked how to call it); the planner did not count it as a verdict and relied on `ll_status` for discovery status.
- H11 was marked falsified by LabLoop because the encoded contrast direction opposed the stated claim; the planner flagged it as an artefact of its own proposal. The analysis `surprises` list stayed empty despite high surprise scores.
- No environment errors; no retries; no agents/ or asd/ files edited. The bash launcher was for local use only and is not committed.

## Checks
- `grep -rE "eg_true|lt_true|true_hit|world_params" runs/ll-smoke2000 runs/ll-w2000-full` printed nothing. Records were not edited.
- Blocker text: none; the run was possible.
