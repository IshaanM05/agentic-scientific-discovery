## Transfer test: real Kepler KOIs

n = 48 anonymized KOIs (one quarter each), dispositions from the NASA Exoplanet Archive cumulative table used as hidden labels. Likelihood tables are the synthetic-calibrated ones (no real-data tuning). 'H4|H5' = archive 'not transit-like' false positives; either verdict counts as correct.

| Condition | Accuracy [90% CI] | Mean cost | needs_human | confident & wrong | H1 | H2 | H3 | H4|H5 |
|---|---|---|---|---|---|---|---|---|
| B1-checklist | 0.54 [0.42, 0.67] | 6.83 | 0.69 | 8 | 0.67 | 0.50 | 0.67 | 0.33 |
| B2-random | 0.38 [0.27, 0.48] | 7.83 | 0.52 | 14 | 0.58 | 0.17 | 0.42 | 0.33 |
| B3-planner | 0.54 [0.42, 0.67] | 5.79 | 0.44 | 15 | 0.83 | 0.25 | 0.75 | 0.33 |
| P-house-team | 0.42 [0.29, 0.54] | 6.91 | 0.60 | 11 | 0.83 | 0.08 | 0.50 | 0.25 |
| B3-planner+real-LOO | 0.46 [0.35, 0.56] | 6.92 | 0.96 | 2 | 0.67 | 0.67 | 0.25 | 0.25 |
| P-house-team+real-LOO | 0.48 [0.35, 0.60] | 7.00 | 0.96 | 2 | 0.67 | 0.58 | 0.33 | 0.33 |

Class key: H1 = Transiting planet (candidate); H2 = Eclipsing binary on target; H3 = Blended background EB; H4|H5 = not transit-like.

`+real-LOO` rows: Wilson's recalibration. Each target is scored with tables built from the synthetic tables (8 pseudo-counts per class) plus the outcomes of the *other* 47 real KOIs (leave-one-out, so no target ever sees its own label). The class prior becomes the real set's stratified base rate.
