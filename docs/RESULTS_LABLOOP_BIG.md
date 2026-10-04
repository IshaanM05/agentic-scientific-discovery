# Results: large-sample LabLoop benchmark (worlds 3000-3059)

**Read this first.** LabLoop is a simulator designed by our team; the worlds are synthetic. These numbers compare decision strategies inside that simulator (the rule-based LabLoop scientist, not an Omnigent run). They are a benchmark, not evidence about real devices. Source: `runs/ll_big_benchmark.json` (script `scripts/ll_big_benchmark.py`, offline, deterministic, no model calls; 1660 s on the run that produced the file). This supersedes the 20-world intervals in `docs/RESULTS_LABLOOP.md` section 2, which stay valid but are wider.

## Design
60 worlds (3000-3059, never used for development) x 20 seeds = 1200 runs per arm, budget 60 units. Seeds within a world share the same hidden physics and are not independent, so the 95% bootstrap CIs resample WORLDS (10,000 draws, all seeds of a drawn world pooled); arms are paired by (world, seed). Time to first hit: runs that never hit count as 61 in means and paired differences; medians are undefined when fewer than half the runs reach a hit.

## Arms (hits by 60 units, mean [95% CI]; first-hit median [CI]; runs reaching a first hit)
| Strategy | Hits by 60 | First hit, median units | Reached |
|---|---|---|---|
| Random | 0.26 [0.22, 0.29] | not defined (fewer than half reached) | 277/1200 |
| Grad-student OFAT | 2.94 [2.51, 3.39] | 6 [4, 44] | 889/1200 |
| LLM-style (no BO) | 3.15 [2.54, 3.79] | 7 [6, 7] | 912/1200 |
| Pure BO (no literature) | 8.04 [7.43, 8.67] | 30 [29, 31] | 1133/1200 |
| LabLoop − arena | 8.90 [7.83, 9.98] | 8 [8, 15] | 1114/1200 |
| LabLoop − negative memory | 9.82 [8.82, 10.86] | 7 [6, 7] | 1182/1200 |
| LabLoop − literature prior | 10.42 [9.59, 11.23] | 15 [15, 16] | 1194/1200 |
| LabLoop (full) | 9.86 [8.88, 10.89] | 7 [6, 7] | 1186/1200 |

## Paired differences, LabLoop (full) minus the other arm
Positive hits / negative time favour LabLoop. Last column: worlds where LabLoop had more / equal / fewer hits.

| Other arm | Hits by 60 | First hit, mean units (censored at 61) | Worlds more/equal/fewer |
|---|---|---|---|
| Random | +9.61 [+8.64, +10.62] | -42.76 [-46.20, -39.07] | 60/0/0 |
| Grad-student OFAT | +6.92 [+6.14, +7.73] | -14.97 [-19.81, -10.38] | 60/0/0 |
| LLM-style (no BO) | +6.71 [+6.07, +7.35] | -6.60 [-9.52, -3.94] | 60/0/0 |
| Pure BO (no literature) | +1.82 [+1.29, +2.35] | -18.21 [-21.00, -15.26] | 46/0/14 |
| LabLoop − arena | +0.96 [+0.53, +1.40] | -4.92 [-6.69, -3.23] | 42/1/17 |
| LabLoop − negative memory | +0.04 [-0.01, +0.10] | -0.18 [-0.34, -0.05] | 30/8/22 |
| LabLoop − literature prior | -0.55 [-1.13, -0.01] | -3.27 [-6.14, -0.16] | 35/2/23 |

## Reading
- Against pure BO, LabLoop's advantage in hits is about 1.82 per 60 units with an interval that excludes zero ([+1.29, +2.35]); it is ahead in 46 of 60 worlds and behind in 14. The earlier 20-world estimate (+1.65, [+0.05, +3.20]) is consistent with this and was marginal.
- The clearest gain is time to first hit: median 7 units vs 30 for pure BO.
- Ablations: removing the arena costs 0.96 hits [+0.53, +1.40]; removing negative memory changes hits by +0.04 [-0.01, +0.10] (no resolvable effect on hits); removing the literature prior changes hits by +0.55 (it slightly raises hits) but delays the first hit (paired mean -3.27 units [-6.14, -0.16] in LabLoop's favour).
- Not shown here: any Omnigent-run result, any real-device result.

## Limits
Team-designed simulator and hidden physics; one budget (60) and one configuration; worlds from one generator and filtered to 6-40 hits (6-40 hits per world here); the rule-based scientist is the only LabLoop implementation measured; bootstrap treats the 60 worlds as exchangeable.
