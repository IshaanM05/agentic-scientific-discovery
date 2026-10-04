> Moved from the `labloop-v2` branch README during integration. Paths below are relative to the repo root. LabLoop is the second test bed; see the main README.

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

Same lab, same 60-unit budget (one film costs 1–1.5 units), over 20 seeds. First-hit and third-hit columns are medians; "Hits by 60" and "Share of hits found" are means (correction made during integration).

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
landscape is the one the system was developed on. Negative-result memory gives a small measured gain on the unseen worlds: +0.30 hits by 60 units, paired 95% CI [+0.10, +0.55] (re-measured during integration, `runs/ll_benchmark.json`; an earlier version of this README said it made no measurable difference). The
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

## Integration summary (kept in sync with the main README)
Two test beds, deliberately different. **Steel strength** (below) uses real public data, but the data has been public since 2018, so an LLM may recall it (memorisation flag set; no LLM-knowledge acceleration claim). **LabLoop** (`labloop/`, a teammate's work; `docs/LABLOOP_README.md`, contract in `docs/LABLOOP_INTEGRATION.md`) is a simulated halide-perovskite lab: 2,772 compositions, hidden physics redrawn per world id, target bandgap 1.24-1.38 eV with T80 >= 500 h, and a textbook prior under which no film qualifies. On unseen worlds recall is impossible. **The simulator was designed by our team and the worlds are synthetic: it is a benchmark, not evidence about real devices.** Omnigent orchestrates LabLoop through `agents/labloop_planner.yaml` and `asd/labloop_tools.py` (contract in `docs/LABLOOP_INTEGRATION.md`); live Omnigent runs on it are not yet committed (`docs/TODO_HUMAN.md`).

### LabLoop results (offline)
All offline, deterministic, no model calls (`scripts/ll_benchmark.py`, `ll_calibrate.py`, `ll_misspec.py`, `ll_compare.py`; outputs `runs/ll_*.json`). Full tables and caveats: `docs/RESULTS_LABLOOP.md`.

![LabLoop headline](docs/ll_headline.png)

- **Benchmark rerun** (worlds 1000-1019, 20 seeds, 60 units): LabLoop 9.90 hits [95% CI 8.25, 11.70] vs pure BO 8.25 [6.65, 9.75]; paired gap +1.65 [+0.05, +3.20] (marginal). Median first hit 6.5 vs 30.5 units, 20/20 vs 19/20 runs reaching it. All 8 rows of the teammate's README table reproduce exactly.
- **Judge vs hidden truth:** 119 confirmations, precision 0.96 [0.91, 0.98], recall 0.58 [0.51, 0.64] (conservative; misses true hits it never replicated).
- **Arena vs hidden truth:** Spearman(Elo, true share of region meeting spec) per-run mean 0.39 [0.28, 0.50]; random ordering about 0 (218 hypotheses, 20 runs; Elo is a proxy for relevance, not truth).
- **Prior misspecification:** belief revision adds +1.15 hits [+0.15, +2.40] when the prior is fully wrong, but costs hits when the prior is right (-2.60 [-3.55, -1.65]).
- **Golden worlds 2000-2002:** rule-based baseline recorded; the Omnigent comparison awaits live runs (the script reports missing records and is tested on a synthetic fixture).

Related work, each read by abstract only: Olympus (2021, benchmarking framework for noisy optimization and experiment planning), Atlas (Digital Discovery 2025, Bayesian optimization for self-driving labs), Rainbow (Nature Communications 2025, perovskite nanocrystal self-driving lab).

Full tables, calibration and caveats: `docs/RESULTS_LABLOOP.md`; multi-fidelity extension: `docs/RESULTS_MULTIFIDELITY.md`; Omnigent agents: `agents/labloop_planner.yaml`; tools: `asd/labloop_tools.py`.
