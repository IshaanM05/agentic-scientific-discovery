# Judge guide (one page)

Entry: Omnigent-orchestrated agent team, Challenge 3. Two test beds: **steel strength** (real public Matbench steels, 312 candidates, 15 hits, budget 60) and **LabLoop** (team-designed simulated perovskite lab on unseen worlds). Offline check: `pip install -r requirements.txt && python -m pytest -q`. Items marked TO FILL in square brackets need the live Omnigent LabLoop runs, which are not in the repo (`docs/TODO_HUMAN.md`).

## Criterion to evidence
| Criterion (weight) | Evidence in the repo | Look at in the live demo |
|---|---|---|
| **Omnigent orchestration (30%)** | `agents/planner.yaml`: planner plus 8 sub-agents (literature, generator, critic, elo_ranker, insight, analysis, judge, safety), tools declared per sub-agent. Tools: `asd/tools.py`. Policies: `asd/policies.py`. Live run: `runs/e2-live/SUMMARY.md`. LabLoop agents: `agents/labloop_planner.yaml` (W1; live Omnigent run `runs/ll-w2000` (world 2000, partial: 23.5 of 60 units): 6 distinct hits, first at 1.5 units, 5 hits by 20 units vs 4.6 for the rule-based baseline, n = 1; worlds 2001 and 2002 **[TO FILL: not run]**) | Omnigent session tree: planner delegating to live sub-sessions; two analysis sessions sent in one response (`runs/e2-live/SUMMARY.md`, step 4); ADAPT beat from `runs/t011` |
| **Breakthrough potential (25%)** | Question: can an agent team find 2000 MPa+ steels in fewer experiments? README "Result": blind prior+GP 8.75 hits@60 vs BO 6.85, OFAT 6.40 (20 seeds, paired CI vs BO [+0.90, +2.95]). `scripts/t009_blind20.py`, `docs/headline.png`. LabLoop benchmark (60 unseen worlds x 20 seeds, budget 60 units, rule-based LabLoop scientist (not an Omnigent run): 9.86 hits [95% CI 8.88, 10.89] vs pure BO 8.04 [7.43, 8.67], paired gap +1.82 [+1.29, +2.35] (ahead in 46 of 60 worlds); median first hit 7.0 vs 30.0 units; the earlier 20-world rerun gave 9.90 vs 8.25, gap +1.65 [+0.05, +3.20]; `docs/RESULTS_LABLOOP.md`). Omnigent runs: live Omnigent run on world 2000 only: `runs/ll-w2000` (seed 0, budget 60, PARTIAL: stopped at 16 films and 23.5 of 60 units) found 6 distinct true hits (the world holds 16), first hit at 1.5 units, and 5 hits by 20 units vs 4.6 (range 3-6, 5 seeds) for the rule-based baseline; n = 1, no significance claim (`runs/ll_compare.json`); worlds 2001 and 2002 **[TO FILL: Omnigent runs not done; `docs/TODO_HUMAN.md` item 1]** | `docs/headline.png`; replay dashboard `streamlit run dashboard/app.py` |
| **Discovery acceleration and learning (20%)** | Named bottleneck: experiments are the scarce resource. Measured: hits@60 and experiments to 1/3/5 hits (blind 11.1/18.4/27.4 vs OFAT 15.6/27.0/41.1, BO 18.0/25.4/42.2; README E1 table). Next experiment: README "Next experiment". LabLoop benchmark rerun: all 8 rows of the teammate's README table (`docs/LABLOOP_README.md`) reproduce exactly; 60 unseen worlds x 20 seeds, budget 60 units, rule-based LabLoop scientist (not an Omnigent run): 9.86 hits [95% CI 8.88, 10.89] vs pure BO 8.04 [7.43, 8.67], paired gap +1.82 [+1.29, +2.35] (ahead in 46 of 60 worlds); median first hit 7.0 vs 30.0 units; the earlier 20-world rerun gave 9.90 vs 8.25, gap +1.65 [+0.05, +3.20] (`docs/RESULTS_LABLOOP.md` section 2; `docs/RESULTS_LABLOOP_BIG.md`) | Results tab; the ADAPT beat showing a refuted hypothesis changing the next experiment |
| **Scientific rigor (15%)** | Pre-registered counterfactual (commit 92ca1e3, `results/e1_counterfactual.json`, `knowledge/concepts/memorization-control.md`); memorisation probe flag SET, so **no acceleration claim**; judge n=12 (`results/judge_calibration.json`) and arena Spearman 0.56, p=0.21 (`results/arena_calibration.json`) stated as weak; every record has an id (`runs/*/record.jsonl`); hypotheses labelled agent-generated | Open a record id in `record.jsonl`; README "Hard gates vs soft checks" |
| **Creativity and responsibility (10%)** | Policies: budget DENY (`runs/policy_demo`, `scripts/demo_policies.py`), safety DENY (`tests/test_omnigent.py`), approval ASK held 22.2 s (`runs/t011-repl30/APPROVAL_EVIDENCE.md`); README "Responsible use" and "Validation needed before real use" | Policy demo: `python scripts/demo_policies.py` |

## The loop, with one real example of each
| Step | Where to see it |
|---|---|
| Question | README "Question"; `runs/t011/meta.json` (seed 21, budget 60) |
| Evidence | `runs/t011/record.jsonl` rec-0001..0007 (cited searches), handoff rec-0008; `runs/e2-live` rec-0005 |
| Hypothesis | `runs/t011` rec-0010 (H1), rec-0011 (H2); arena of six, `runs/e2-live` rec-0006..0008 |
| Experiment (>= 2 candidate tests, one chosen) | `runs/e2-live` rec-0016: three options scored, 0.475 vs 0.2125 and 0.21; `runs/t011` rec-0013 |
| Result | `runs/t011` rec-0014 (c000), rec-0019 (c299: 1123.1 MPa); `runs/e2-live` rec-0018, rec-0019 |
| Updated decision | `runs/t011` rec-0020 (H2 refuted), rec-0023 (revised H3) |
| Next experiment | `runs/t011` rec-0025 (test choice), rec-0026 (c150; H3 supported, rec-0027) |

The ADAPT example is `runs/t011`. `runs/e2-live` is the full live multi-agent run and has no ADAPT line.

## Limits to keep in mind
- Steel data is public; the memorisation flag is set, so we do not claim LLM knowledge accelerates discovery. The blinded arm is evidence, not an acceleration claim.
- LabLoop is team-designed and synthetic: a benchmark, not evidence about real devices. Its README table was rerun and reproduces exactly (`docs/RESULTS_LABLOOP.md` section 2; `docs/RESULTS_LABLOOP_BIG.md`); the Omnigent runs on it are not committed yet.
- Hard gates: budget, safety keyword list, approval (interactive runs; headless `-p` declines automatically). Advisory only: judge, critic, novelty check, labels.
