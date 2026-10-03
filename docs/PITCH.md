# Pitch: 12 slides, 3-minute demo

1. **Hook.** Discovery is bottlenecked by choosing experiments, not by having ideas.
2. **Problem.** Real labs are slow (days per film), costly and noisy. You cannot brute-force 2,772 compositions to find 11.
3. **State of the art.** Co-Scientist (Elo tournament of hypotheses), Robin (literature-to-candidate), Periodic (harness beats raw model 3.8× on XRD). Humans still pick and run experiments.
4. **Insight.** The LLM proposes and explains; a Gaussian-process surrogate decides; the notebook remembers failures; a judge verifies before anything is called a discovery.
5. **Architecture.** The loop diagram (dashboard, "How the loop is built").
6. **Hypotheses you can kill.** Every hypothesis states a prediction and the result that falsifies it.
7. **Choosing the next film.** P(meets spec) from two GPs over a literature prior; hypotheses narrow the pool.
8. **Demo** (below).
9. **Results.** Curves and table: 1.8× vs BO, ≈53× vs random, ablations.
10. **Safety and humans.** Safety gate before hardware; level-3 sign-off; judge calibration plan.
11. **Generality.** Same harness, different lab adapter: robot API, simulator, CRISPR screen.
12. **Roadmap.** Real lab adapter, calibrated judge, traces as training data.

## Demo script (dashboard, seed 7)

* **Round 1.** "No data yet, so the PI spends the batch testing the top literature hypotheses." Point at the map: dark cells are where the model thinks a hit is.
* **Round 2.** A half-tin film came back with a lower bandgap than the textbook predicts. The PI re-runs it before believing it; it reproduces. H1 (Vegard's law) is falsified, H3 ("Sn always degrades") holds only with exceptions, and the counterexample spawns a new hypothesis about Cs. Notebook shows the belief revision.
* **Round 3–4.** By round 4 H3 is fully falsified once the evidence has doubled, and a replicate that missed spec is logged as "not reproduced". Switch rows to "A-site cations": hits cluster in Cs-rich Sn–Pb films, which is exactly the hidden physics. Tick "Show hidden ground truth" to reveal the true targets.
* **Stop.** The PI stops with budget left once the goal is met, and every discovery is replicated.
* Scroll to "Lab time is the scarce resource": agents keep working while films anneal.
* Scroll to the benchmark.

## Q&A prep

* *Is the lab real?* No, a replay with hidden physics. That is what makes the comparison fair; the adapter interface is where a robot plugs in.
* *Where is the LLM?* Hypothesis generation and rationale (with a key). The decision maths is deliberately not an LLM: LLMs are poor at sample-efficient search.
* *Why should I trust "discovery"?* Two independent spec-meeting measurements, sanity checks, and the replicate can fail (it does: "not reproduced").
