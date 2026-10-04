# Results: two test beds, and what the LabLoop numbers do and do not show

**Read this first.** The LabLoop simulator was designed by our team and its worlds are synthetic. Everything below is a benchmark of decision strategies inside that simulator. It is not evidence about real perovskite devices, and the rule-based LabLoop scientist is the baseline we compare Omnigent runs against. All scripts are offline and deterministic (no model calls); numbers come from `runs/ll_*.json`.

## 1. Why two test beds
| | Steel strength (`asd/`) | LabLoop (`labloop/`) |
|---|---|---|
| Data | Real public Matbench steels table, 312 candidates, 15 hits (yield >= 2000 MPa) | Simulated halide-perovskite lab, 2,772 compositions, hidden physics redrawn per world id |
| Strength | Real measurements | Worlds cannot have been memorised by any model |
| Weakness | Public since 2018, so an LLM may recall it; our memorisation probe flag is SET and we make no LLM-knowledge acceleration claim | Team-designed physics; not real devices |
| Evidence we report | Blinded arm (unnamed, permuted, scaled features): 8.75 vs 6.40 hits (OFAT) on 20 seeds, paired CI [1.75, 3.00] (from the main README; not rerun here) | This document |

The point of the second test bed is the weakness of the first: on LabLoop worlds recall is impossible, so any gain from the loop has to come from the decision strategy.

## 2. Benchmark rerun (`python scripts/ll_benchmark.py`; `runs/ll_benchmark.json`, `docs/ll_headline.png`)
Unseen worlds 1000-1019, 20 seeds (one per world), budget 60 units. 95% bootstrap CIs (10,000 resamples of the 20 world-seed pairs; arms are paired because they share worlds). Time to first or third hit is a median in units; "reached" is how many of 20 runs got there; ">60" means the median is undefined because at least half the runs did not reach it.

| Strategy | Hits by 60, mean [95% CI] | First hit, median [CI] (reached) | Third hit, median [CI] (reached) |
|---|---|---|---|
| Random | 0.15 [0.00, 0.30] | >60 (3/20) | >60 (0/20) |
| One factor at a time | 2.85 [1.85, 3.90] | 6.0 [4.0, 56.5] (15/20) | >60 (10/20) |
| LLM-style, no BO | 2.90 [2.00, 3.80] | 6.5 [3.5, 10.0] (16/20) | 34.0 [21.0, >60] (11/20) |
| Pure BO | 8.25 [6.65, 9.75] | 30.5 [22.5, 34.0] (19/20) | 37.0 [35.5, 42.0] (19/20) |
| **LabLoop (full)** | **9.90 [8.25, 11.70]** | **6.5 [3.5, 9.5] (20/20)** | **24.0 [15.0, 33.5] (20/20)** |
| LabLoop - arena | 9.15 [7.15, 11.15] | 11.5 [7.0, 17.0] (19/20) | 24.0 [18.0, 33.0] (18/20) |
| LabLoop - negative memory | 9.60 [7.95, 11.40] | 6.5 [3.5, 9.5] (20/20) | 21.0 [15.0, 30.0] (20/20) |
| LabLoop - literature prior | 10.45 [8.80, 12.10] | 16.5 [9.5, 20.5] (20/20) | 28.5 [25.0, 33.0] (20/20) |

Paired differences, LabLoop (full) minus the other arm (positive hits / negative time favour LabLoop; not-reached coded as 61 for time):
- vs pure BO: **+1.65 hits [+0.05, +3.20]** (more hits in 12 worlds, equal in 5, fewer in 3); first hit 23 units earlier [-24.0, -13.5]; third hit 14.5 earlier [-21.5, -8.5]. The hits gap barely excludes zero; the timing gap is clear.
- vs OFAT: +7.05 hits [+5.40, +8.80], better in 20/20 worlds.
- Ablations: removing the arena costs +0.75 hits [-0.75, +2.15] (not resolved) but delays the first hit by 5 units [-9, -3]. Removing negative memory changes hits by +0.30 [+0.10, +0.55] (5 worlds better, 15 equal, none worse): a real but tiny effect, contrary to the README's "no measurable difference". Removing the literature prior gives -0.55 hits [-2.00, +0.70] (it does not reduce hits) but delays the first hit by 9 units [-15.0, -1.5].

**Verification of the table in `docs/LABLOOP_README.md`: all 8 rows (first-hit and third-hit medians, hits by 60, share of hits found) reproduce exactly; no number differs.** Comments on that table: (i) "medians over 20 seeds" is accurate for time-to-hit, but hits by 60 and share found are means; (ii) the README gives no intervals, and the headline gap over pure BO (9.9 vs 8.25) is marginal at 20 worlds (CI above); the large, solid gain is time to first/third hit; (iii) the claim "never tuned on" for worlds 1000-1019 is the authors' statement and cannot be checked from the repo.

## 3. Calibration against hidden truth (`python scripts/ll_calibrate.py`; `runs/ll_calibrate.json`)
Same 20 runs of LabLoop (full). Truth is used only to score.
**Judge ("discovery confirmed").** Over 579 distinct measured films (198 true hits): confirmed 119, TP 114, FP 5, FN 84, TN 376. Precision 0.958 (Wilson 95% [0.905, 0.982]); recall 0.576 [0.506, 0.643]; accuracy 0.846 [0.815, 0.873]. By judge confidence: High 110/115 true (0.957 [0.902, 0.981]); Medium 4/4 (Wilson [0.51, 1.0]; too few to say). Reading: confirmations are rarely wrong, but the judge misses many true hits, mostly films it never saw replicated within the budget (FN includes true hits that were measured only once or failed). It is conservative by construction (a discovery needs two passing syntheses); recall is low because of the 60-unit budget, not necessarily because of the rubric.
**Arena.** 218 hypotheses over 20 runs. Spearman between final Elo and the true share of each hypothesis region that meets spec: pooled rho = 0.34 (p = 2.6e-7, treat as optimistic because hypotheses repeat across runs); per-run mean rho = 0.39 with bootstrap 95% CI [0.28, 0.50] over the 20 runs. A random ordering of the same hypotheses gives rho = -0.01 (95% range [-0.14, +0.13]; permutation p < 0.0005 with 2,000 permutations). 33% of regions have true share zero (ties). So Elo rank is positively related to goal-relevant regions in this simulator, unlike the n=5, rho 0.56, p=0.21 arena check on steels, which was at chance. Caveat: Elo rewards relevance and informativeness, not whether the hypothesis is true, so this is a proxy.

## 4. Prior misspecification (`python scripts/ll_misspec.py`; `runs/ll_misspec.json`)
No edits to `labloop/*`: inside the script, `space_arrays` as seen by the surrogate and campaign is wrapped so the textbook prior is `(1-f)*truth + f*textbook`, with f = 0, 0.5, 1 ("0%, 50%, 100% wrong"; our definition of "x% wrong"). The hard-coded literature hypotheses are unchanged. "Revision off" makes `Surrogate.relax_prior` a no-op. f = 1, revision on reproduces the benchmark LabLoop row exactly (9.90 hits), which checks the patch is neutral. Worlds 1000-1019.

| Prior wrong | Revision | Hits by 60 [CI] | First hit mean, censored at 61 [CI] (reached) |
|---|---|---|---|
| 0% | on | 12.95 [10.80, 14.95] | 2.1 [2.0, 2.5] (20/20) |
| 0% | off | 15.55 [12.60, 18.40] | 2.1 [2.0, 2.5] (20/20) |
| 50% | on | 12.10 [10.10, 14.10] | 4.0 [2.7, 5.8] (20/20) |
| 50% | off | 13.45 [11.10, 15.80] | 4.0 [2.7, 5.8] (20/20) |
| 100% | on | 9.90 [8.25, 11.70] | 10.9 [6.3, 16.2] (20/20) |
| 100% | off | 8.75 [6.70, 10.85] | 13.3 [6.9, 21.4] (19/20) |
| no prior | n/a | 10.45 [8.80, 12.10] | 16.1 [11.8, 20.9] (20/20) |

Paired, revision on minus off: hits **+1.15 [+0.15, +2.40]** when the prior is fully wrong (better in 10 worlds, equal 6, worse 4); **-1.35 [-2.05, -0.70]** at 50%; **-2.60 [-3.55, -1.65]** at 0%. First hit when fully wrong: -2.5 units [-6.4, 0.0]. Reading: belief revision pays off only when the prior is badly wrong, and it costs hits when the prior is right. Wrong priors slow the first hit (2.1 -> 4.0 -> 10.9 units) and cost hits (12.95 -> 12.10 -> 9.90). Even a fully wrong prior still beats no prior on first-hit time (10.9 vs 16.1, intervals overlap) but not on hits (9.90 vs 10.45). These are mechanism tests inside one simulator.

## 5. Golden worlds 2000-2002 and Omnigent (`python scripts/ll_compare.py`)
Rule-based baseline, 5 seeds per world, budget 60, early stopping off (means; true hits in world 16, 8, 28):

| World | hits@20 | hits@40 | hits@60 | first hit (units) | replicated | refuted | ADAPT events |
|---|---|---|---|---|---|---|---|
| 2000 | 4.6 | 9.8 | 14.6 | 1.7 | 8.8 | 2.2 | 6.2 |
| 2001 | 3.0 | 7.0 | 7.8 | 6.4 | 5.2 | 1.6 | 11.6 |
| 2002 | 3.4 | 8.4 | 15.4 | 6.4 | 10.6 | 2.0 | 8.0 |

**The Omnigent side is one partial run.** `runs/ll-w2000` (live Omnigent, world 2000, seed 0, budget 60) was stopped at 16 films and 23.5 of 60 units: 6 distinct true hits (the world holds 16), first hit at 1.5 units, 4 replicated discoveries, 3 refutations, 5 ADAPT events by this script's count; 5 hits by 20 units vs a baseline mean of 4.6 (range 3-6, 5 seeds). Its hits@40 and hits@60 columns repeat 6 only because the run ended early: they are not measurements at those budgets. `runs/ll-smoke2000` is an 8-unit smoke run (5 films, 2 distinct hits). `runs/ll-w2001` and `runs/ll-w2002` do not exist (not run); the script says so per missing file. The parser is tested on a committed synthetic fixture (`scripts/ll_fixtures/ll-w2000/record.jsonl`, a rule-based run rewritten in the assumed record schema: NOT an Omnigent result). The schema is an assumption taken from `docs/LABLOOP_INTEGRATION.md`; the first live run parsed with no `unparsed` entries. With n = 1 run per world, any gap to the baseline is a demonstration, not a statistical result.

## 6. Limitations
Team-designed simulator and hidden physics; 20 worlds drawn by the same generator; world draws are filtered to 6-40 hits; bootstrap over only 20 pairs; one budget (60) and one configuration; the Judge is a rubric that was never calibrated against experts (section 3 calibrates it only against the simulator's own truth); LLM components of LabLoop are not exercised here (offline rule-based path). Validation needed before real use: real-device or real-lab data, noisier measurements, an independent simulator, Omnigent live runs on worlds 2000-2002 with several seeds each, and expert review.

## 7. Related work (each read by abstract only; details to verify before citing formally)
- Olympus (2021): benchmarking framework for noisy optimization and experiment planning. Relevant as the established way to compare planners on surfaces with noise; our benchmark is much smaller and not compatible with it.
- Atlas (Digital Discovery, 2025): Bayesian optimization for self-driving labs. Relevant to the BO baseline and to how a real lab would host the designer.
- Rainbow (Nature Communications, 2025): perovskite nanocrystal self-driving lab. A real-lab counterpart to our simulated one; it shows what real noise and hardware constraints look like, which our simulator does not capture.
