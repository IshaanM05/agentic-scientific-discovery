# Plan, pitch and roadmap

## Pitch (about 12 slides)

1. **Hook.** Discovery is bottlenecked by choosing experiments, not running them.
2. **Problem.** Real labs are slow, costly and ambiguous, so brute force is out.
3. **State of the art.** Co-Scientist and Robin generate strong hypotheses, but humans still pick experiments; Periodic shows the harness matters as much as the model.
4. **Insight.** The LLM proposes, Bayesian optimisation decides, the notebook remembers, the Judge verifies.
5. **Architecture** (dashboard "How it works" tab).
6. **The task.** 2,772 films; the textbook says zero meet spec; nature says 11 do.
7. **Live replay.** Rounds 1–3: Vegard falsified, counterexample, new Cs hypothesis.
8. **Hypothesis arena.** Falsifiable by construction; Elo; parked irrelevant hypotheses.
9. **Belief revision.** The PI relaxes the textbook prior once the lab contradicts it.
10. **Results on unseen worlds.** Curves and ablations; quote the honest numbers.
11. **Safety and generality.** Protocol gate, human sign-off, swappable lab adapter.
12. **Roadmap.**

Demo script: open the dashboard, press Play, pause on round 2 to show the
counterexample spawning a hypothesis, open one film's protocol, toggle "Reveal hidden
truth" at the end, then switch to the Benchmark tab.

## Done

- Hidden-physics replay lab with noise, failed films, cost and time; randomisable worlds.
- Nine agents, falsifiable hypothesis DSL, Elo arena, GP acquisition, Judge, notebook.
- Belief revision, goal-relevance gate, ridge anomaly attribution, replication rule.
- Benchmark with 4 baselines and 3 ablations on the demo world and 20 unseen worlds.
- Self-contained dashboard, terminal runner, 7 tests, CI.

## Next (in priority order)

1. **Human steering in the dashboard.** Veto or inject a hypothesis mid-run; the PI re-plans live.
2. **Live Claude panel.** Stream hypothesis generation and critique, with offline replay as fallback.
3. **Multi-fidelity.** A cheap noisy simulation vs expensive synthesis; the agent chooses which to spend on.
4. **Multi-objective.** Efficiency, stability and lead content as a Pareto front.
5. **Second lab adapter.** A published CRISPR screen as a replay biology lab, same harness.
6. **Auto-written report.** Every claim linked to notebook entries.
7. **Production path.** Robot or cloud-lab adapter, Judge calibrated against expert labels,
   notebook traces as training data.
