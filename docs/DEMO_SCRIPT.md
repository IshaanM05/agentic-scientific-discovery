# Two-minute demo script (draft v1; update numbers after A2 and each merged item)
Screen: Omnigent web UI + terminal + docs/headline.png. Narration ~270 words. All numbers come from committed run records.

| Time | Screen | Narration |
|---|---|---|
| 0:00-0:15 | README title, steel_strength table | **Question.** Among 312 published steel compositions, can an agent team find ultra-high-strength steels (yield >= 2000 MPa, 15 of 312) in fewer experiments than standard search? Bottleneck: each experiment is expensive; we give the team a budget of 60. |
| 0:15-0:30 | agents/planner.yaml; Omnigent session list | **Orchestration.** Omnigent runs a planner that delegates to literature, insight, analysis and safety sub-agents. Our Python oracle and selector are function tools; budget and human approval are Omnigent policies. |
| 0:30-0:45 | runs/t011 record: rec-0001..0013 | **Evidence and hypothesis.** Literature returns cited papers (OpenAlex). Insight writes H1, labelled "agent-generated hypothesis": a maraging composition should reach about 2000 MPa. |
| 0:45-1:00 | rec-0013 test_choice | **Experiment.** The planner designs two candidate tests, c000 for H1 and c299 for H2, scores them by expected learning, feasibility and cost (0.76 vs 0.54), and runs c000. |
| 1:00-1:15 | rec-0014/0015, then rec-0019/0020 | **Result.** c000 measures 1309 MPa, not 2000. Analysis flags it surprising and reopens an assumption (peak-aged, no retained austenite). H2 fails too: 1123 vs 2300. |
| 1:15-1:30 | rec-0023, rec-0025 | **Updated decision (ADAPT).** The planner asks insight for H3, a revised family predicted near 1200 MPa, and picks c150 over the surrogate's top choice. Measured 1237 MPa: H3 supported. |
| 1:30-1:40 | runs/policy_demo; REPL approval prompt (runs/t011-repl) | **Policies.** The budget policy denies the experiment past its limit. Recommending real-world validation triggers an approval request; interactive runs hold it until a human answers, and -p runs decline automatically. |
| 1:40-1:52 | docs/headline.png | **Measured result.** Over 5 seeds, an LLM prior raised mean hits in 60 experiments from 6.6 (best baseline) to 8.2. But our pre-registered memorisation probe flagged recall of this public benchmark, so we do NOT claim acceleration. Blinded, unnamed features over 20 seeds: [A2 NUMBER] vs OFAT [A2 NUMBER]. |
| 1:52-1:55 | README positioning line | **Positioning.** SciAgents generates and critiques hypotheses without running experiments; ours runs the experiment, records the result and lets it change the next decision. |
| 1:55-2:00 | README "Next experiment" | **Next experiment.** Repeat on a dataset newer than the model's training data, with a blinded prior and a live interactive approval gate. |

## Must not say
- "prior systems run no experiments" in general (Coscientist and A-Lab do); name SciAgents only.
- "faster" / "acceleration" (the rule is not met); "hard gate" for approval; anything from runs/live2's first pick (tainted by a prompt example).
## Pending inserts
- A2 numbers; judge (B), arena (C), dashboard (D) only if merged.
