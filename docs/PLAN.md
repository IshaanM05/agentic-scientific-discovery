# LabLoop: the definitive plan

## 1. Thesis

Most AI-scientist systems (Google Co-Scientist, FutureHouse Robin) are strong at generating hypotheses, and still rely on humans to choose and run experiments. In a physical lab the bottleneck is not ideas; it is that each experiment costs days and money, and results are noisy. LabLoop's job is the step the challenge calls out: **decide which experiment should happen next, under a budget, and learn from the result.**

Design principle borrowed from Periodic Labs: the harness matters as much as the model. We train nothing. We build tools, memory, decision logic and verification around a model.

## 2. Problem-statement mapping

| Challenge asks for | LabLoop component |
|---|---|
| Research | Literature agent: cited claims become the surrogate's prior mean |
| Hypothesize | Arena: falsifiable hypotheses with a derived kill condition, critic, Elo ranking |
| Plan and run experiments | Designer (GP + P(meets spec) acquisition) → safety gate → lab adapter |
| Learn | Analyst surprise z-scores, GP refit, belief revision of discredited priors, failure model |
| Decide what's next | PI agent: seed / investigate / exploit / replicate / stop, with written rationale |
| Multi-agent lab | 8 roles with typed JSON hand-offs and a shared SQLite notebook |

## 3. Why a perovskite replay lab

* Mirrors the materials-discovery framing judges will know (propose → synthesise → characterise).
* A hidden ground truth lets us run fair, repeatable comparisons: the only honest way to defend a speed-up claim.
* The hidden physics differs from the textbook (Sn–Pb bowing, Cs-shielded Sn oxidation), so there is something to discover, and the notebook shows the moment the agents discover it (H1 falsified, H3 qualified, H7/H8 proposed from counterexamples).
* Rare targets (11 / 2,772) make random search hopeless and decision quality visible.

## 4. Evaluation design

Same lab, same 60-unit budget, 20 seeds:
random, one-factor-at-a-time (a grad student's sweep), pure BO, hypotheses without a surrogate, full LabLoop, and three ablations (no arena, no literature prior, no failure memory). Metrics: distinct spec-meeting films vs budget, budget to first and third hit, fraction of runs reaching three hits. Random's expectation is computed analytically.

Headline: 1.8× faster than BO alone to three hits, 3.8× to the first hit, ≈53× faster than random. We state the null result (failure memory) openly.

## 5. Demo tiers

* Tier 0: slides (docs/PITCH.md).
* Tier 1 (shipped): `dashboard/index.html`, a replay of real recorded campaigns. Cannot break on stage, works offline.
* Tier 2 (shipped): `python -m labloop --delay 0.3`, a live run in the terminal; with an API key, Claude writes hypotheses and rationale.

## 6. Roadmap after the hackathon

1. Real lab adapters: a self-driving-lab or robot API behind the same `run(protocol)` interface.
2. Judge calibration against expert labels, measuring agreement the way Periodic did for XRD.
3. Async multi-station scheduling with real queue times.
4. Second domain adapter (CRISPR screen replay) to prove the harness is domain-agnostic.
5. Notebook traces as training data for a future scientific model (the data flywheel).
