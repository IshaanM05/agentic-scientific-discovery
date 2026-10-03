# LabLoop: an AI scientist that decides the next experiment

Hack-Nation 7th Global AI Hackathon, Challenge 3: Agentic Scientific Discovery.

Most "AI scientist" systems are good at generating hypotheses. LabLoop focuses on
the part that is still done by humans: **deciding which experiment to run next,
under a budget, and learning from the result**, including results that contradict
the textbook.

**Open the demo:** `docs/index.html` (one self-contained file; works offline and on
GitHub Pages via Settings → Pages → branch `labloop-mvp`, folder `/docs`).

## What it does

The lab searches 2,772 halide perovskites (Cs/FA/MA)(Pb/Sn)(I/Br/Cl)₃ for a solar
absorber with a 1.24–1.38 eV bandgap and T80 ≥ 500 h. The textbook prior predicts
**zero** films meet that spec. In the hidden lab, 11 do, because of effects the
agents' literature never mentions (Cs protecting Sn from oxidation, Cl passivating
Sn-Pb films). To find them, the system has to notice that the literature is wrong.

In the demo run it does exactly that, unprompted:

1. Seeds the arena with literature hypotheses, each with a prediction and kill condition.
2. Falsifies Vegard's law (bandgaps bow far below linear mixing).
3. Finds a counterexample to "≥30% Sn always degrades fast", marks it *holds with exceptions*.
4. Turns the counterexample into new hypotheses ("Cs raises T80 in Sn films", a Cl effect), tests and supports them.
5. Relaxes the discredited textbook prior, exploits the new region, replicates every
   hit, and stops early once 4 discoveries are confirmed.

## Architecture

| Agent | Job | Design choice |
|---|---|---|
| PI | goal, budget, stop rule; picks seed / investigate / exploit / stop | goal-relevance gate: never funds tests of regions that can't meet spec |
| Literature | sourced claims (8 real citations; optional Semantic Scholar) | nothing unsourced enters belief state |
| Hypothesis arena | propose, critique, Elo tournament, dedupe | every hypothesis is machine-checkable and has a kill condition |
| Designer + BO | Gaussian processes for bandgap, stability, film success | acquisition = P(film meets full spec); literature prior as GP mean |
| Safety gate | screens each generated protocol | restricted elements and scale-up need human sign-off |
| Lab adapter | `run(protocol) → result, cost, duration` | replay lab today; robot / cloud-lab API tomorrow |
| Analyst | findings, surprise detection, ridge attribution of anomalies | separates co-varying variables (Cs vs FA) |
| Judge | replication, sample size, physical sanity | a discovery needs two passing syntheses |
| Notebook | SQLite, full provenance | failures stored as first-class data |

The LLM proposes and critiques; the acquisition function decides; the Judge decides
what counts as known. With `ANTHROPIC_API_KEY` set, Claude writes new hypotheses (in
the validated DSL) and PI rationales. Without it, a deterministic rule-based scientist
runs, so the demo can never fail on stage.

## Results

Same lab, same 60-unit budget (one film costs 1–1.5 units), medians over 20 seeds.

**On 20 hidden worlds the system was never tuned on** (each draws new physics:
which element protects Sn, bowing strength, penalties, end-member offsets; 6–35 hits each):

| Strategy | First hit | Third hit | Hits by 60 | Share of hits found |
|---|---|---|---|---|
| Random | not reached | not reached | 0.1 | 1% |
| One factor at a time | 6 | not reached | 2.9 | 20% |
| LLM-style, no BO | 6.5 | 34 | 2.9 | 22% |
| Bayesian optimisation only | 30.5 | 37 | 8.2 | 56% |
| **LabLoop** | **6.5** | **24** | **9.9** | **67%** |
| LabLoop − arena | 11.5 | 24 | 9.2 | 58% |
| LabLoop − negative memory | 6.5 | 21 | 9.6 | 65% |
| LabLoop − literature prior | 16.5 | 28.5 | 10.4 | 68% |

On the demo landscape: first hit after 7 units vs 26.5 for BO alone, 56 for
one-factor-at-a-time and ~336 expected for random screening; 91% of hits found.

Honest notes: the unseen-worlds table is the number to quote, because the demo
landscape is the one the system was developed on. Negative-result memory makes no
measurable difference here because failed films are rare near the optimum. The
literature prior roughly halves time to first hit but slightly biases late search,
which is why the PI relaxes it when the lab contradicts it.

## Run it

```bash
pip install -r requirements.txt
python -m labloop                    # watch a campaign in the terminal
python -m labloop --world 42         # an unseen hidden world
python scripts/build_dashboard.py    # rebuild docs/index.html (add --fresh-bench to rerun benchmarks)
pytest -q                            # 7 tests: smoke, determinism, safety, unseen worlds
ANTHROPIC_API_KEY=... python -m labloop   # Claude-written hypotheses and PI rationale
```

## Limits

The lab is a literature-inspired simulator standing in for a self-driving lab, not
a claim about real devices. The Judge is a rubric, not calibrated against expert
labels. Real measurements are noisier and more ambiguous. See `docs/PLAN.md` for the roadmap.
