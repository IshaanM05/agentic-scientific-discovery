# LabLoop large-sample results: does the gain over Bayesian optimization hold up?

**Read this first.** The LabLoop simulator was designed by our team and its worlds are synthetic. This is a benchmark of decision strategies inside that simulator, not evidence about real perovskite devices. Offline, deterministic, no model calls. Numbers come from `runs/ll_big_benchmark.json` and `runs/ll_big_misspec.json`; scripts `scripts/ll_big_benchmark.py`, `scripts/ll_big_misspec.py`; plot `docs/ll_big_headline.png`.

## Design
- **60 unseen worlds (ids 3000-3059), 20 seeds each = 1,200 runs per arm**, budget 60 units. Earlier scripts used worlds 1000-1019 (W2) and 2000-2002; none used 3000+. Worlds contain 6-40 true hits (mean 18.0).
- Same 8 arms and ablations as `ll_benchmark.py`. (Difference from W2: there, one seed was paired with each world, so n = 20 world-seed pairs; here every world gets seeds 0-19.)
- **Confidence intervals resample WORLDS** (10,000 draws; a drawn world brings all 20 of its seeds). Seeds in one world share hidden physics and are not independent, so seed-level resampling would be too narrow. Arms are paired by (world, seed). Medians pool the resampled worlds' seeds. Percentiles use actual draws (no interpolation), so "not reached" can be infinite.
- Time to hit: not reached = infinite for medians (">60" = undefined, at least half not reached); coded 61 for paired differences and censored means.
- Reproducibility: each (world, seed) unit is a pure function of its inputs; multiprocessing (4 cores) only changes runtime. A test checks identical output for 1 vs 2 processes.
- Runtime: benchmark 1,660 s; misspec sweep 1,997 s (4 cores). Full size was run; nothing reduced.

## 1. Benchmark (worlds 3000-3059, 20 seeds)
Means/medians over 1,200 runs; 95% CIs over worlds. Share found = hits by 60 / true hits in the world.

| Strategy | Hits by 60, mean [CI] | Hits, median [CI] | Share found [CI] | First hit, median [CI] (reached) | Third hit, median [CI] (reached) |
|---|---|---|---|---|---|
| Random | 0.26 [0.22, 0.29] | 0 [0, 0] | 0.015 [0.014, 0.017] | >60 (277/1200) | >60 (0/1200) |
| One factor at a time | 2.94 [2.51, 3.39] | 3 [2, 3] | 0.205 [0.162, 0.252] | 6.0 [4.0, 44.0] (889) | 58.0 [55.0, >60] (628) |
| LLM-style, no BO | 3.15 [2.54, 3.79] | 3 [2, 4] | 0.220 [0.174, 0.271] | 7.0 [6.0, 7.0] (912) | 44.0 [25.0, >60] (696) |
| Pure BO | 8.04 [7.43, 8.67] | 8 [7, 9] | 0.519 [0.474, 0.565] | 30.0 [29.0, 31.0] (1133) | 38.0 [36.0, 40.0] (1088) |
| **LabLoop (full)** | **9.86 [8.88, 10.89]** | 10 [8, 11] | 0.644 [0.576, 0.711] | **7.0 [6.0, 7.0] (1186)** | **19.0 [15.0, 26.0] (1163)** |
| LabLoop - arena | 8.90 [7.83, 9.98] | 9 [8, 10] | 0.577 [0.504, 0.648] | 8.0 [8.0, 15.0] (1114) | 26.0 [20.0, 29.0] (1081) |
| LabLoop - negative memory | 9.82 [8.82, 10.86] | 10 [8, 11] | 0.641 [0.572, 0.708] | 7.0 [6.0, 7.0] (1182) | 20.0 [15.0, 26.0] (1150) |
| LabLoop - literature prior | 10.42 [9.59, 11.23] | 11 [9, 12] | 0.657 [0.610, 0.703] | 15.0 [15.0, 16.0] (1194) | 26.0 [24.0, 27.0] (1176) |

### Paired: LabLoop (full) minus each arm
Positive hits / negative time favour LabLoop. Last column: worlds (of 60, by per-world mean) where LabLoop had more / equal / fewer hits.

| vs | Hits by 60 [CI] | First hit, mean units [CI] | Third hit, mean units [CI] | Worlds more/equal/fewer |
|---|---|---|---|---|
| Random | +9.61 [+8.64, +10.62] | -42.8 [-46.2, -39.1] | -35.9 [-39.8, -32.0] | 60/0/0 |
| One factor at a time | +6.92 [+6.14, +7.73] | -15.0 [-19.8, -10.4] | -22.6 [-26.7, -18.4] | 60/0/0 |
| LLM-style, no BO | +6.71 [+6.07, +7.35] | -6.6 [-9.5, -3.9] | -13.5 [-16.3, -10.7] | 60/0/0 |
| **Pure BO** | **+1.82 [+1.29, +2.35]** | **-18.2 [-21.0, -15.3]** | **-14.6 [-17.7, -11.4]** | **46/0/14** |
| LabLoop - arena | +0.96 [+0.53, +1.40] | -4.9 [-6.7, -3.2] | -4.1 [-5.3, -2.9] | 42/1/17 |
| LabLoop - negative memory | +0.04 [-0.01, +0.10] | -0.2 [-0.3, -0.1] | -0.3 [-0.4, -0.1] | 30/8/22 |
| LabLoop - literature prior | -0.55 [-1.13, -0.01] | -3.3 [-6.1, -0.2] | -2.3 [-5.3, +0.7] | 35/2/23 |

## 2. Prior misspecification (worlds 3000-3059, 20 seeds)
Method as in `ll_misspec.py`: prior = (1-f)*truth + f*textbook; "revision off" disables `Surrogate.relax_prior`; `labloop/` unedited. Check: f = 100%, revision on gives 9.86 hits, identical to the benchmark LabLoop (full) arm, so the patch is neutral.

| Prior wrong | Revision | Hits by 60 [CI] | First hit, mean censored at 61 [CI] (reached) |
|---|---|---|---|
| 0% | on | 13.15 [12.09, 14.20] | 2.1 [2.0, 2.2] (1200) |
| 0% | off | 15.75 [14.21, 17.27] | 2.1 [2.0, 2.2] (1200) |
| 50% | on | 12.15 [11.13, 13.17] | 6.1 [4.4, 7.9] (1200) |
| 50% | off | 13.22 [12.09, 14.35] | 5.9 [4.3, 7.5] (1200) |
| 100% | on | 9.86 [8.88, 10.89] | 13.2 [9.7, 17.1] (1186) |
| 100% | off | 8.55 [7.52, 9.63] | 14.5 [10.5, 18.9] (1139) |
| no prior | n/a | 10.42 [9.59, 11.23] | 16.5 [15.5, 17.6] (1194) |

Paired gain of belief revision (on minus off):

| Prior wrong | Hits by 60 [CI] | First hit, mean units [CI] | Worlds better/equal/worse |
|---|---|---|---|
| 0% | -2.60 [-3.12, -2.08] | +0.0 [+0.0, +0.0] | 1/4/55 |
| 50% | -1.07 [-1.28, -0.86] | +0.2 [+0.1, +0.4] | 2/3/55 |
| 100% | **+1.31 [+0.97, +1.66]** | -1.3 [-2.1, -0.6] | 47/1/12 |

## 3. Plain-language reading
- **The hits gap over pure BO is real and now clearly excludes zero in this simulator: +1.82 hits by 60, 95% CI [+1.29, +2.35], with LabLoop ahead in 46 of 60 worlds.** The 20-world estimate was +1.65 [+0.05, +3.20]; the larger sample gives nearly the same point estimate, with an interval about a third as wide. Effect size is moderate: roughly 9.9 vs 8.0 hits, 0.64 vs 0.52 of the available hits. BO still wins in 14 of 60 worlds.
- **The timing gain is larger and clear**: first hit about 18 units earlier on average (median 7 vs 30 units), third hit about 15 units earlier (19 vs 38).
- Against one-factor-at-a-time, LLM-style without BO and random the margins are large and consistent in every world.
- **Ablations:** the arena adds about 1 hit and about 5 units to the first hit (clear). Negative memory has no practical effect on hits (+0.04; the earlier +0.30 is not seen here). Removing the literature prior does not cost hits (it gains 0.55, interval touching zero) but delays the first hit by about 3 units on average (median 7 vs 15): the prior buys speed early, not more hits by 60.
- **Belief revision:** with a fully wrong prior it helps (+1.31 hits [+0.97, +1.66], better in 47 of 60 worlds, a bit larger and tighter than the 20-world +1.15 [+0.15, +2.40]). With a right or half-right prior it costs hits (-2.60 and -1.07; the 50% estimate is smaller than the earlier -1.35). Wrong priors slow the first hit (2.1 to 6.1 to 13.2 units) and cost hits (13.2 to 12.2 to 9.9). A fully wrong prior with revision (9.86 hits) is no better than no prior (10.42).

## 4. Limitations
Still one team-built simulator and one generator for worlds (6-40 hit filter); 60 worlds is more worlds, not a different simulator, so shared simulator assumptions are untested. One budget (60) and one configuration. Intervals cover world sampling and seed noise only, not model-form uncertainty. The "x% wrong" blend is our definition. Pooled medians of time to hit are bounded by the 61 censoring. Everything here is a mechanism test; real-lab validation is still needed.
