---
type: concept
status: protocol designed by scout 2026-10-04; not yet run (T009)
tags: [T009, rigor, contamination, steel_strength]
---
# Memorisation control (T009)
**Why.** steel_strength = the 312 rows of Matbench `matbench_steels` ([[steel-strength]]), public since 2018. An LLM-prior gain may be row recall, not reasoning. Benchmark contamination inflates scores and must be measured per benchmark (Sainz et al., "NLP Evaluation in trouble", arXiv 2310.18018, Findings of EMNLP, opened). Recall can be detected by comparing a *guided* prompt (names the dataset) with a *generic* one on the same instances (Golchin & Surdeanu, "Time Travel in LLMs", ICLR 2024, arXiv 2308.08493, opened). Whether any of our models saw this table is [unverified]. The probe measures it.
## Part A: recall probe (offline, about 60 calls, cached by (prompt, model, seed))
- Rows: 20 fixed rows in `data/t009_probe_ids.json` (original row index, not shuffled cXXX ids): all 15 hits + 5 non-hits drawn with `random.Random(0)`. Commit the file before the first call.
- Model: the planner model (Sonnet 5.5), temperature 0, seed 0. Haiku 4.5 is optional.
- Prompts, one row per call, answer as JSON `{"yield_mpa": float}`:
  P1 generic: "A steel with composition (wt%) C=.., Mn=.., ... Estimate its yield strength in MPa."
  P2 guided: same text plus "This row is from the matminer steel_strength / Matbench matbench_steels dataset. Give the recorded value."
  P3 blinded: 13 features renamed f01..f13 (columns permuted, each min-max scaled to [0,1]), "material", "target property". Expect it to fail (a floor check).
- Reference: kNN (k=5, z-scored wt%, Euclidean) with leave-one-out over all 312 rows, scored on the same 20 rows. Also report the train-mean predictor.
- Metrics per arm: MAE, Spearman rho, near-exact count `|pred-true| <= max(10 MPa, 1% of true)`. Write them to `runs/t009/probe.json`.
- **Recall flag** (any one): near-exact(P1 or P2) >= 3/20; MAE(P2) < 0.5 x MAE(kNN); MAE(P2) < 0.8 x MAE(P1) (guided beats generic, the Golchin signal).
## Part B: blinded arm at matched budget
- Same agent/acquisition code, pool (312), budget B=60, initial design, model, prompt template and seeds {0,1,2,3,4} as the named arm. Only the feature view differs.
- Blinded view: drop `formula`; rename columns f01..f13 with a column permutation drawn from `random.Random(1000+seed)`; min-max scale each column (this removes the unit cue, e.g. C ~0.1 wt%); task text says "maximise target y, hit = y >= threshold" with no word steel/yield/MPa/alloy. The literature sub-agent is OFF in both arms (or ON in both with the same queries) so that only the names differ.
- Revealed y values are shown raw in both arms (same information about outcomes).
- Log per run: hits@20/40/60, experiments to first hit (censored at 61), first pick a hit (y/n). Write `runs/t009/{named,blind}/seed{s}/`.
## Decision rule (write the verdict to README, whatever it is)
Let G_named = mean hits@60(named) - mean hits@60(best non-LLM baseline from T003, same seeds), and G_blind the same for the blind arm.
1. No LLM speedup claim at all unless G_named > 0 and named beats that baseline on >= 4/5 paired seeds.
2. Recall flag set -> the claim is INVALID as "acceleration". Report: "advantage consistent with memorisation of a public benchmark".
3. No flag, G_blind >= 0.5 x G_named -> claim allowed as "LLM-guided search beats baseline X by G hits at B=60 (5 seeds)", plus this probe result.
4. No flag, G_blind < 0.5 x G_named -> claim only "named-domain-prior advantage" (legitimate metallurgy such as maraging Ni-Co-Mo-Ti, or recall we could not detect). Not "the agent learns faster".
5. Named first-pick hit rate >> blind (e.g. >= 3/5 vs <= 1/5) is extra evidence for 2/4. Say so.
Five seeds is a small sample. State n=5, show per-seed values, and do not quote p-values below what a 5-seed sign test can give (p = 1/32 one-sided at best).
## Known leak to fix first
`agents/planner.yaml:30` uses `c272` as the example safety candidate_id. At seed 0, c272 is a 2411 MPa hit. The prompt names a hit id, so it must become `c###` before any T003/T009 run.
## E1 counterfactual (pre-registered 2026-10-04, before any call)
- **View.** The NAMED prompt shown to the LLM swaps the labels of two element columns: the true Ni column is printed as "Mn" and the true Mn column as "Ni". True data, pool, oracle and hit threshold are unchanged. Pair Ni<->Mn because they are the discriminating pair for the top steels: maraging grades have Ni ~18 wt% and Mn ~0.1, so the swapped view reads as ~18 wt% Mn / ~0.1 Ni (a Hadfield-like, chemically wrong story). A model applying correct metallurgy is misled; one that recalls the table by composition pattern is less affected.
- **Arms** (seeds 0-19, B=60, same code and initial design as T003): counterfactual-named prior+GP (llm_bo, view `cfnamed`); blind prior+GP (control, existing seeds 0-19); OFAT; BO. Prior model Sonnet 5.5, cached.
- **Decision rule.** "If counterfactual-named prior+GP beats the better of OFAT and BO on mean hits@60 with a paired bootstrap 95% CI excluding 0 over 20 seeds, recall of the true table cannot explain the gain, and we report an acceleration of hits-within-budget versus these baselines on this benchmark. Because the prior was given wrong element identities, this gain is NOT attributed to correct chemical knowledge. If it does not, we report that the named-prior gain depends on correct labels, consistent with recall or with a domain prior, and make no acceleration claim."
- **Trust meter.** Per step, Spearman(prior score, revealed y) over revealed candidates; report whether the counterfactual arm's curve falls below the blind arm's (detects the misleading prior).
- Bootstrap: 10000 resamples of paired differences, seed 0, percentile 95% CI.

**Links:** [[steel-strength]] · [[baselines-and-evaluation]] · [[llm-guided-bo]] · [[awcd-language-priors]]
