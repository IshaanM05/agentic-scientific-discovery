# Multi-fidelity testing on LabLoop (optional extra, W4)

**Caveat first.** LabLoop is a simulator designed by the team; the screen is a simulated cheap test with noise we chose (below). These results are benchmark evidence about the method on synthetic worlds, not evidence about real perovskite devices. Everything runs offline.

## What was built (all new files)
- `labloop/multifidelity.py`: `MFLab` wraps the same hidden worlds with two tests: **screen** (0.2 units; bandgap estimate with sd 0.06 eV; stability proxy with sd 0.35 dex, binned to 0.25) and **synthesis** (1.0, 1.5 with Sn; sd 0.015 eV and 0.10 dex, film can fail). Each measurement is a pure function of (world, seed, film, test, repeat number), so runs are deterministic. `MFSurrogate` is LabLoop's GP surrogate with a per-observation noise variance, so screens enter with inflated noise. `plan_actions` scores every film for both tests: `score = (EIG + beta * P(hit) [synthesis only]) / cost`, where EIG is the expected entropy reduction (nats, 7-point quadrature, film-wise Gaussian update) of "this film meets spec". `beta = 1` nat per expected hit, because only synthesis can deliver a hit. With `beta = 0` it is pure information gain per cost.
- `asd/labloop_mf_tools.py`: `ll_mf_start`, `ll_mf_plan`, `ll_screen`, `ll_run_mf`. State in `ll_mf_state.json` plus `record.jsonl` per run dir; synthesis is safety-reviewed; over-budget actions are DENIED and not charged. Tools return only noisy measurements and surrogate beliefs.
- `agents/labloop_mf_fragment.yaml`: tool declarations and a prompt addition for the lead to merge into W1's planner (it makes the planner compare a screen option and a synthesis option, as the brief requires).
- `tests/test_labloop_mf.py` (10 tests): determinism, budget accounting, no leakage, fresh-process state.

## Benchmark
`python scripts/ll_mf_benchmark.py` (raw rows in `runs/ll_mf_benchmark.json`). Unseen worlds 1000-1019 x 10 seeds, total budget 60 units for every arm; screens spend from the same budget. A hit is a film synthesised successfully that truly meets spec (distinct films); screens never count. Uncertainty: paired bootstrap over **worlds** (seeds averaged within a world, 20 clusters, 10,000 draws, 95% percentile CI), because seeds within a world are not independent.

Arms: `mf` (screen + synthesis), `sf_eig` (same surrogate and rule, synthesis only; the clean ablation), `sf_greedy` (same surrogate, LabLoop-style exploit/explore, synthesis only), `labloop` (the full LabLoop campaign with arena and replication, reference).

| Arm | hits @15 | @30 | @45 | @60 | units to first hit (censored at 60) |
|---|---|---|---|---|---|
| mf | 1.72 | 4.92 | 9.44 | 13.40 | 12.96 |
| sf_eig | 1.14 | 3.94 | 8.52 | 12.57 | 15.76 |
| sf_greedy | 1.15 | 3.51 | 6.79 | 10.15 | 17.36 |
| labloop (full) | 1.79 | 3.69 | 6.58 | 9.48 | 11.53 |

Paired differences, mf minus arm [95% CI] (worlds where mf is better, of 20; for first hit negative is better):

| vs | @30 | @60 | first hit |
|---|---|---|---|
| sf_eig | +0.98 [0.56, 1.40] (17) | +0.83 [0.32, 1.41] (12) | -2.80 [-4.27, -1.37] (15) |
| sf_greedy | +1.41 [1.05, 1.78] (19) | +3.25 [2.10, 4.53] (17) | -4.39 [-7.40, -1.56] (12) |
| labloop | +1.23 [0.68, 1.80] (16) | +3.92 [2.42, 5.47] (18) | +1.44 [-1.24, 3.81] (6) |

## Reading
- **Multi-fidelity helps against its own single-fidelity ablation**: about +0.8 hits at 60 units (CI excludes 0, but only 12 of 20 worlds improve, so the gain is modest and uneven) and a first hit about 2.8 units earlier. The mf arm used about 34 screens per run (about 7 units, 11% of budget) in place of roughly 5 syntheses.
- **Against the full LabLoop campaign** mf finds more hits at 30 to 60 units (+3.9 at 60), but **not** an earlier first hit (12.96 vs 11.53 units; the CI includes 0) and no difference at 15 units. This comparison is confounded: mf lacks LabLoop's hypothesis arena, replication and prior revision, and uses a different designer. It shows that the simple MF loop is competitive, not that screening alone explains the gap to LabLoop. The clean test of screening is mf vs sf_eig.
- Our LabLoop reference gives 9.48 hits at 60, while its README reports 9.9 on 20 worlds x 20 seeds; ours uses 10 seeds and counts only successfully formed films (stricter), so the two are not identical and we did not reproduce his table.
- The result depends on the screen quality we simulated (sd 0.06 eV, 0.35 dex, no bias, no failure information). A biased or less informative real screen would shrink or remove the gain; we did not test that. `beta = 1` was chosen on tuning worlds 500-507 (4 seeds; mf with beta 0 was worse, 1 to 4 similar); the benchmark worlds were not used for tuning.
- Limits: film-wise information gain ignores correlation between films (conservative); screens are limited to one per film; no replication in the mf loop; failed films are not retried. Validation on a real lab would be needed before any claim beyond the simulator.
