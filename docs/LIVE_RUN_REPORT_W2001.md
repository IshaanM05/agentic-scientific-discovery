# Live Omnigent run, LabLoop world 2001 (seed 0, budget 60)

Caveat: LabLoop is a team-built simulator with synthetic hidden physics (a benchmark, not real devices). This is one live run, a single sample; it supports no claim about real materials or about any average performance.

## Result
- Run directories: `runs/ll-smoke2001` (budget 8 smoke) and `runs/ll-w2001` (budget 60). Records were not edited.
- Status of the full run: the planner ended the run itself. It was NOT stopped by the budget and LabLoop never returned mode `stop`. 46.0 of 60 units used, 14.0 left. The planner stated the remaining slots had predicted p_hit 0.03-0.23 in directions already missed, and chose not to spend them. Round 11 was designed but nothing was run. Treat it as complete by the planner's decision, not as budget-exhausted.
- Films: 31 (28 ok, 3 failed QC as pinholes). Films meeting spec: 9, over 6 distinct compositions (single noisy measurements). First spec-meeting film: film 2 (2.5 units cumulative).
- Judge status at the last verdict (replicated = confirmed): 3 compositions confirmed (Cs0.2FA0.8Pb0.6Sn0.4I3, Cs0.3FA0.7Pb0.6Sn0.4I3, Cs0.3FA0.7Pb0.5Sn0.5I3, each n=2 films); 3 hit compositions "not reproduced" (Cs0.1FA0.9Pb0.7Sn0.3I3, Cs0.3FA0.7Pb0.7Sn0.3I3, Cs0.3FA0.7Pb0.5Sn0.5I2.7Br0.3).
- Duration: about 15 minutes of wall clock from launch to the last record (launch about 06:21 UTC, last record 06:35 UTC), measured from file timestamps; model cost was not reported by the records and was not measured here (the 20 USD guard was never approached by any figure I could see).
- Sub-agents that ran (named in the planner's output and visible in the tool records): ll_literature_agent, ll_generator, ll_critic, ll_analyst, ll_judge, ll_safety. The planner called ll_start, ll_arena_round, ll_pi_decide, ll_design, ll_run, ll_status itself.
- Rounds: 11 PI decisions (modes: seed 1, investigate 5, exploit 5). Records: 31 experiment, 12 design, 11 pi_decision, 9 analysis, 9 judge_verdict, 6 arena_round, 1 literature, 1 ll_start.
- Candidate designs per decision: 5 protocols in 9 of 12 design calls, 2, 3 and 4 in the others (at least 2 each time).
- Hypotheses: 9 generator proposals admitted (labelled agent-generated), 8 rejected, all by the validator: 6 region too small ("region contains only 2 compositions (need >= 3)", plus 1 "region_b contains fewer than 3 compositions" counted among them), 2 "near-duplicate of an existing hypothesis". The planner reported widening regions and re-proposing.
- Analysis events: hypotheses falsified H1, H2, H3; qualified (holds with exceptions) H2, H8, H10, H12; literature bandgap prior relaxed after H2 and stability prior relaxed after H3; one reproduced surprise (Cs0.2FA0.8Pb0.5Sn0.5I2.7Cl0.3). `adapt_triggers` true in 3 analysis records.
- ADAPT lines in the planner's output (verbatim fragments, from the console log, not a record file): "the MA-containing films all missed spec, which supports moving away from MA"; "E028 (Br 0.3) is a marginal single-film hit (+21 h T80 margin), so the next round replicates it before any claim"; "Br 0.3 is not reproduced, so I'm moving away from it"; the MA line was repeated once later. Four ADAPT lines in total. The planner did not write an ADAPT line for every analysis that refuted a hypothesis, so the prompt rule ("log it whenever an analysis refutes a hypothesis or relaxes a prior") was not followed on every round.
- Policies: no human-approval ASK and no safety DENY fired in the full run. All reviewed protocols were safety level 2, approved with standard handling. In the smoke run one ll_run film was denied by the budget check (record `budget_or_safety_denial`: "DENY: budget 8 units would be exceeded (used 7, film costs 1.5)"). The planner said it skipped analyse and judge for round 9 (QC failures only), a deviation from its own loop.
- Smoke run (budget 8): handoff to all sub-agents worked; 5 films, 4 ok, 1 spec-meeting film (Cs0.2FA0.8Pb0.7Sn0.3I3, n=1, status "candidate"); 7.0 units used; 2 proposals rejected for regions of 1 composition.

## Environment and handling
- Python 3.12 venv (`uv venv --python 3.12 .venv-live`, omnigent 0.16.0, not committed). Model calls via the session's existing logged-in claude CLI; no credential was read, printed or stored.
- The server and tool env were set with a bash port of scripts/live.ps1 (not committed): PYTHONPATH=repo root, PYTHONUTF8=1, ASD_* and LC_ASD_* mirrors, `omnigent server --background`.
- Errors: none needing a fix. No agents/ or asd/ file was changed. Smoke and full run each ran once; no retries.
- Leak check: grep for eg_true, lt_true, true_hit, world_params in both run directories returned 0 matches.

## Limits
- n = 1 world, 1 seed, one live sample; hits are noisy single or paired films; "confirmed" means two films agree in the LabLoop judge rubric, not independent replication.
- No comparison against the rule-based baseline on this world is made here; that is scripts/ll_compare.py's job.
