# LabLoop: an AI scientist that decides the next experiment

Hack-Nation 7th Global AI Hackathon, Challenge 3: Agentic Scientific Discovery.

LabLoop is a multi-agent research loop: it reads the literature, writes **falsifiable** hypotheses, ranks them in an Elo tournament, designs experiments with a Bayesian-optimisation surrogate, runs them through a safety gate on a pluggable lab, analyses the results, has a judge verify claims, and remembers every failure. Then it decides what to run next, or stops.

The demo campaign searches 2,772 halide perovskite compositions, (Cs/FA/MA)(Pb/Sn)(I/Br/Cl)₃, for a lead-reduced solar absorber with a 1.24–1.38 eV bandgap and T₈₀ ≥ 500 h. Only 11 compositions meet spec. The lab hides physics that the textbook prior gets wrong (Sn–Pb bandgap bowing, and Cs shielding Sn²⁺ from oxidation), so the agents have to discover it from data.

**Open `dashboard/index.html` in a browser.** It is a single self-contained file with three recorded campaigns and the benchmark baked in.

## Results (20 seeds, 60-unit budget, same replay lab)

| Strategy | Hits found at full budget | Budget to first hit | Budget to 3 hits |
|---|---|---|---|
| Random picks | 0.1 of 11 | not within 60 (≈336 expected) | not within 60 (≈1,008 expected) |
| One factor at a time | 1.7 | 56 | not within 60 |
| Bayesian optimisation only | 8.5 | 26.5 | 34.5 |
| Hypotheses, no surrogate ("LLM-style") | 3.45 | 7 | 47 |
| LabLoop without arena | 7.0 | 15.5 | 26 |
| LabLoop without literature prior | 9.85 | 11.5 | 22 |
| LabLoop without failure memory | 10.15 | 7 | 19 |
| **LabLoop, full** | **10.05** | **7** | **19** |

What this supports: **1.8× less budget than BO alone to reach three hits, 3.8× to the first hit, and ≈53× less than random search** (analytic expectation, since random almost never gets there inside the budget). What it does not support: failure memory makes no measurable difference in this lab, because few films fail. We report that rather than hide it.

## Quick start

```bash
pip install -r requirements.txt
python -m labloop                       # watch one campaign in the terminal
python -m labloop --seed 3 --delay 0.3  # slower, for a live stage demo
python scripts/run_benchmark.py         # ~2 min, writes dashboard/data/benchmark.json
python scripts/build_dashboard.py       # re-runs campaigns, rebuilds dashboard/index.html
python -m pytest -q tests
```

Optional: with `ANTHROPIC_API_KEY` set, Claude writes new hypotheses (validated against a strict JSON schema before they touch the belief state) and the PI agent's rationale. `LABLOOP_ONLINE=1` lets the literature agent query Semantic Scholar. Without either, a deterministic rule-based scientist runs, so the demo never breaks on stage.

## The loop

```
PI agent ──► Literature ──► Hypothesis arena ──► Designer + BO
   ▲          (cited claims)  (generator, critic,   (GP surrogate,
   │                           Elo ranker)           P(meets spec))
belief state                        ▲                     │ protocol
   │                    surprises   ┊                     ▼
Notebook ◄── Judge ◄── Analyst ◄────┴──── Lab adapter ◄── Safety gate
(SQLite)   (replication,  (measured vs     (replay lab / simulator /
            sanity)        predicted, z)    robot API)
```

| Agent | File | What makes it more than a prompt |
|---|---|---|
| PI | `campaign.py` `PIAgent` | Owns goal, budget and stopping rule. Each round picks seed / investigate / exploit / stop, reserves slots for replication and surprise re-runs, and explains why. |
| Literature | `literature.py` | Every claim carries a citation; nothing unsourced enters the belief state. Claims become the GP prior mean. |
| Hypothesis arena | `hypotheses.py` | Hypotheses are machine-checkable: region + property + prediction, and the kill condition is derived from the prediction. Critic flags untestable, too-broad or conflicting ones; Elo ranks the rest. |
| Hypothesis generator | `campaign.py` `HypothesisAgent` | Reproduced surprises and counterexamples to "qualified" laws spawn new hypotheses (rule-based, or Claude when a key is set). |
| Designer | `campaign.py` `DesignerAgent`, `surrogate.py` | Two GPs (bandgap, stability) on top of the literature prior, plus a film-formation model learned from failures. Acquisition = P(meets full spec); hypotheses constrain the pool, diversity filter within a batch. |
| Safety gate | `lab.py` `safety_review` | Restricted elements, toxic-metal handling, scale. Level 3 requires human sign-off. |
| Lab adapter | `lab.py` | `run(protocol) -> Result(ok, measurements, cost, duration)`. Swap the replay lab for a simulator or robot API. |
| Analyst | `campaign.py` `AnalystAgent` | Measured vs predicted, surprise z-scores. |
| Judge | `campaign.py` `JudgeAgent` | Discoveries need two spec-meeting measurements; hypotheses get confidence from sample size and pass rate. |
| Notebook | `notebook.py` | Append-only SQLite log of experiments, hypothesis events and decisions. Negative results are first-class rows. |

Belief revision: when a literature hypothesis is falsified or only qualified by our own data, the matching part of the prior is relaxed, so the lab trusts its measurements over the textbook.

## Honest limits

* The lab is a replay with hidden physics, noise, failed films and costs built from published trends. It is a controlled benchmark, not a wet lab.
* The judge is a rubric. In production it would be calibrated against expert verdicts (Periodic Labs' approach).
* Physical-property numbers are approximate literature values; the point is the decision loop, not the materials claims.

See `docs/PLAN.md` for the design rationale and `docs/PITCH.md` for the slide outline and demo script.
