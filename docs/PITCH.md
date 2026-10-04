# Pitch (finalists: 3 minutes, 2 slides plus demo)

**One-sentence claim:** An Omnigent-orchestrated team of specialist agents runs the full loop from question to updated decision under enforced budget and approval policies; on a public steel benchmark with all element names hidden it found more ultra-strong steels per 60 experiments than Bayesian optimisation, and we state plainly that this is not proof that LLM knowledge accelerates discovery.

**Three numbers to show**
1. **8.75 vs 6.85 hits@60**, blind prior+GP vs Bayesian optimisation, 20 seeds, paired 95% CI [+0.90, +2.95] (README "Result"; OFAT 6.40).
2. **22.2 s**: a policy-held human approval until a person clicked Approve (`runs/t011-repl30`).
3. **LabLoop, unseen worlds 2000-2002:** benchmark on 60 unseen worlds x 20 seeds: LabLoop 9.86 hits [8.88, 10.89] vs pure BO 8.04 [7.43, 8.67] at 60 units (paired +1.82 [+1.29, +2.35]), median first hit 7.0 vs 30.0 units (`docs/RESULTS_LABLOOP_BIG.md`); rule-based baseline on golden worlds 2000-2002 (5 seeds each, n=5 per world): mean hits@60 14.6, 7.8 and 15.4; mean units to first hit 1.7, 6.4 and 6.4; Omnigent team vs baseline on 2000-2002: **[TO FILL: no `runs/ll-w2000..2002` committed; see `docs/TODO_HUMAN.md` item 1]**.

## Slide 1: Result and limits (speak 0:00-1:00)
**Title:** An agent team that designs, runs and revises its own experiments, measured against baselines and honestly bounded
- Left: bar chart from `docs/headline.png`: blind prior+GP 8.75, BO 6.85, OFAT 6.40 hits in 60 experiments (20 seeds, CI shown).
- Right: "Loop, run live by Omnigent: question, evidence, hypothesis, experiment, result, updated decision, next experiment."
- **Limits box (on the slide):** memorisation flag SET: no claim that LLM knowledge accelerates discovery. Public benchmark, 312 rows, replayed oracle. Judge and arena checks weak (n=12; p=0.21). Simulator for LabLoop is team-designed.

**Speaker notes:** 0:00-0:15 question: finding 2000 MPa+ steels (15 of 312) when each experiment is expensive. 0:15-0:40 headline number and what "blind" means (names hidden, features permuted and scaled). 0:40-1:00 read the limits box aloud: we kept the claim to what the control allows.

## Demo (1:00-2:10, live or video; follows `docs/DEMO_SCRIPT.md`)
1:00-1:20 Omnigent session tree. 1:20-1:40 arena and test choice (`runs/e2-live` rec-0016). 1:40-1:55 ADAPT: H2 refuted, H3 written, next experiment changed (`runs/t011`). 1:55-2:10 policy DENY and approval hold; LabLoop panel (benchmark numbers above, `docs/RESULTS_LABLOOP_BIG.md`; Omnigent run stats **[TO FILL: no `runs/ll-w2000..2002` committed; see `docs/TODO_HUMAN.md` item 1]**).

## Slide 2: Why it counts and what is next (speak 2:10-3:00)
**Title:** Controls, gates, and the next experiment
- Orchestration: planner plus 8 sub-agents, Python tools, policies (budget DENY, safety DENY, approval ASK).
- Rigor: pre-registered counterfactual, memorisation probe, run records with ids, agent-generated labels.
- Second test bed: LabLoop, unseen synthetic worlds no LLM has memorised (benchmark, 60 worlds: first hit at a median 7.0 vs 30.0 units for pure BO; hits +1.82 [+1.29, +2.35]; team-designed simulator, not real devices).
- Next: rerun on a post-cutoff or private dataset; real validation needs a real or higher-fidelity oracle and expert review.

**Speaker notes:** 2:10-2:30 enforced vs advisory checks. 2:30-2:45 unseen-worlds test bed and why it addresses memorisation. 2:45-3:00 the next experiment and the single claim again.
