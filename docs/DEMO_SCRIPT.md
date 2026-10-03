# Two-minute demo script (v2; update after each merged item)
Screen: Omnigent web UI + terminal + docs/headline.png. Narration ~270 words. All numbers come from committed run records.

| Time | Screen | Narration |
|---|---|---|
| 0:00-0:15 | README title, steel_strength table | **Question.** Among 312 published steel compositions, can an agent team find ultra-high-strength steels (yield >= 2000 MPa, 15 of 312) in fewer experiments than standard search? Bottleneck: each experiment is expensive; we give the team a budget of 60. |
| 0:15-0:30 | agents/planner.yaml; Omnigent session list | **Orchestration.** Omnigent runs a planner that delegates to literature, insight, analysis and safety sub-agents. Our Python oracle and selector are function tools; budget and human approval are Omnigent policies. |
| 0:30-0:45 | runs/t011 record: rec-0001..0013 | **Evidence and hypothesis.** Literature returns cited papers (OpenAlex). Insight writes H1, labelled "agent-generated hypothesis": a maraging composition should reach about 2000 MPa. |
| 0:45-1:00 | rec-0013 test_choice | **Experiment.** The planner designs two candidate tests, c000 for H1 and c299 for H2, scores them by expected learning, feasibility and cost (0.76 vs 0.54), and runs c000. |
| 1:00-1:15 | rec-0014/0015, then rec-0019/0020 | **Result.** c000 measures 1309 MPa, not 2000. Analysis flags it surprising and reopens an assumption (peak-aged, no retained austenite). H2 fails too: 1123 vs 2300. |
| 1:15-1:30 | rec-0023, rec-0025..0027 | **Updated decision (ADAPT).** The planner asks insight for H3, a revised family predicted near 1200 MPa, scores c150 against an exploration pick c094 (0.72 vs 0.54) and runs c150 (rec-0025). Measured 1237 MPa: H3 supported (rec-0026/0027). |
| 1:30-1:40 | runs/policy_demo; approval card (runs/t011-repl30) | **Policies.** The budget policy denies the experiment past its limit. Recommending real-world validation triggers an approval request; interactive runs hold it until a human answers (22.2 s until the human clicked Approve, runs/t011-repl30), and -p runs decline automatically. |
| 1:40-1:52 | docs/headline.png | **Measured result.** Over 5 seeds, an LLM prior raised mean hits in 60 experiments from 6.6 (best baseline) to 8.2. But our pre-registered memorisation probe flagged recall of this public benchmark, so we do NOT claim acceleration. With blinded, unnamed features over 20 seeds the prior still averaged 8.75 hits vs 6.40 for OFAT (19 of 20 seeds), but the flag still blocks an acceleration claim. |
| 1:52-1:55 | README positioning line | **Positioning.** SciAgents, as described in its method, generates and critiques hypotheses without running experiments; ours runs the experiment, records the result and lets it change the next decision. |
| 1:55-2:00 | README "Next experiment" | **Next experiment.** Repeat on a dataset newer than the model's training data, with a blinded prior and a live interactive approval gate. |

## Must not say
- "prior systems run no experiments" in general (Coscientist and A-Lab do); name SciAgents only.
- "faster" / "acceleration" (the rule is not met); "hard gate" for approval; anything from runs/live2's first pick (tainted by a prompt example).
## Pending inserts
- Judge (B), arena (C), dashboard (D) only if merged.
