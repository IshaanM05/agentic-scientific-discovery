<!-- asd-report: {"kind": "labloop", "run_dir": "runs/ll-offline-w3100"} -->
# Research report: LabLoop simulated perovskite lab (ll-offline-w3100)

> Auto-generated from the run notebook and records by a template; no model wrote this text [src: file:scripts/make_report.py]
> LabLoop is a team-built simulator with synthetic hidden physics: a benchmark, not evidence about real devices [src: file:docs/LABLOOP_INTEGRATION.md]

## 1. Question and run type

- Which halide-perovskite compositions have a bandgap of 1.24 to 1.38 eV and a T80 of at least 500 h in a simulated lab, when the textbook prior says none qualify [src: calc:target_eg_min, calc:target_eg_max, calc:target_t80_h, file:docs/CLOUD_WORKER_CONTEXT.md]
- The run used world 3100, seed 0 and a budget of 60.0 units [src: state:run, rec-0001]
- This is an offline rule-based run: no Omnigent planner and no model took part, so it shows the LabLoop baseline loop, not the Omnigent system [src: rec-0004]
- The recorded planner text reads “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” [src: rec-0004]
- The notebook holds 40 films across 9 rounds and 59.0 units were spent [src: calc:n_films, calc:n_rounds, state:run]

## 2. Evidence: sourced literature claims the agents started from


| id | claim | citation | source |
|---|---|---|---|
| L1 | “Single-junction efficiency peaks for absorbers near 1.34 eV (detailed-balance limit ≈33.7%).” | “Shockley & Queisser, J. Appl. Phys. 32, 510 (1961)” | [src: lit:L1] |
| L2 | “Mixed Sn-Pb iodide perovskites show anomalous bandgap bowing: mixed films absorb further into the IR than either end mem…” | “Hao et al., J. Am. Chem. Soc. 136, 8094 (2014)” | [src: lit:L2] |
| L3 | “FA/Cs Sn-Pb (≈50% Sn) films reach ≈1.2-1.25 eV and serve as low-gap tandem subcells.” | “Eperon et al., Science 354, 861 (2016)” | [src: lit:L3] |
| L4 | “Sn(II) readily oxidises to Sn(IV), creating p-doping and fast degradation; stability drops with Sn content.” | “Noel et al., Energy Environ. Sci. 7, 3061 (2014)” | [src: lit:L4] |
| L5 | “Mixed I/Br films phase-segregate under illumination (Hoke effect) when Br ≳ 20%.” | “Hoke et al., Chem. Sci. 6, 613 (2015)” | [src: lit:L5] |
| L6 | “Adding a small fraction of Cs to FA/MA perovskites improves phase stability and reproducibility.” | “Saliba et al., Energy Environ. Sci. 9, 1989 (2016)” | [src: lit:L6] |
| L7 | “MA-based perovskites are intrinsically thermally unstable at 85 °C.” | “Conings et al., Adv. Energy Mater. 5, 1500477 (2015)” | [src: lit:L7] |
| L8 | “3D perovskite formability is predicted by the Goldschmidt tolerance factor, roughly 0.8 < t < 1.0.” | “Kieslich et al., Chem. Sci. 5, 4712 (2014)” | [src: lit:L8] |


## 3. Hypotheses (all produced by agents; none validated)

- The arena holds 11 hypotheses, each labelled with its origin: literature-seeded by a rule-based agent, rule-based from an anomaly, or model-written [src: calc:n_hyps, calc:n_literature, calc:n_rule_based, calc:n_agent_generated]

| id | label | prediction | kill condition | final status | evidence | source |
|---|---|---|---|---|---|---|
| H1 | agent-generated (rule-based, from cited literature) | “bandgap (eV) between 1.40 eV and 1.56 eV for Br = 0, Cl = 0, Sn 0.4–0.6” | “False if ≥⅔ of ≥3 films in the region fall outside 1.40 eV–1.56 eV.” | falsified | n=4, pass rate 0.0 | [src: state:H1] |
| H10 | agent-generated (rule-based, no model) | “log10 T80 (h) > 500 h for Br ≤ 0.1, Cl ≤ 0.25, FA ≥ 0.6, Sn 0.1–0.5” | “False if ≥⅔ of ≥3 films in the region measure <= 500 h.” | qualified | n=30, pass rate 0.5 | [src: state:H10] |
| H11 | agent-generated (rule-based, no model) | “log10 T80 (h) is higher by >0.25 in [Br ≤ 0.1, Cl ≥ 0.05, FA ≥ 0.6, Sn 0.1–0.5] than in [Br ≤ 0.1, Cl = 0, Sn…” | “False if, after ≥2 films per arm, the difference is below a third of the predicted effect.” | supported | n=33, pass rate 0.58 | [src: state:H11] |
| H14 | agent-generated (rule-based, no model) | “log10 T80 (h) < 334 h for Br ≤ 0.1, FA 0.7–0.95, Sn ≤ 0.4” | “False if ≥⅔ of ≥3 films in the region measure >= 334 h.” | qualified | n=26, pass rate 0.35 | [src: state:H14] |
| H15 | agent-generated (rule-based, no model) | “log10 T80 (h) is higher by >0.25 in [Br ≤ 0.1, FA ≥ 0.7, Sn ≤ 0.4] than in [Br ≤ 0.1, FA ≤ 0.6, Sn ≤ 0.4]” | “False if, after ≥2 films per arm, the difference is below a third of the predicted effect.” | falsified | n=31, pass rate 0.06 | [src: state:H15] |
| H2 | agent-generated (rule-based, from cited literature) | “bandgap (eV) < 1.36 eV for Br = 0, FA ≥ 0.6, Sn 0.3–0.7” | “False if ≥⅔ of ≥3 films in the region measure >= 1.36 eV.” | qualified | n=20, pass rate 0.45 | [src: state:H2] |
| H3 | agent-generated (rule-based, from cited literature) | “log10 T80 (h) < 400 h for Sn ≥ 0.3” | “False if ≥⅔ of ≥3 films in the region measure >= 400 h.” | qualified | n=23, pass rate 0.43 | [src: state:H3] |
| H4 | agent-generated (rule-based, from cited literature) | “log10 T80 (h) < 250 h for Br 0.3–0.6, Cs ≤ 0.05” | “False if ≥⅔ of ≥3 films in the region measure >= 250 h.” | proposed | n=0 | [src: state:H4] |
| H5 | agent-generated (rule-based, from cited literature) | “log10 T80 (h) > 600 h for Br ≤ 0.1, Cs 0.1–0.3, FA ≥ 0.6, Sn = 0” | “False if ≥⅔ of ≥3 films in the region measure <= 600 h.” | testing | n=2, pass rate 0.5 | [src: state:H5] |
| H6 | agent-generated (rule-based, from cited literature) | “log10 T80 (h) < 250 h for MA ≥ 0.5” | “False if ≥⅔ of ≥3 films in the region measure >= 250 h.” | proposed | n=0 | [src: state:H6] |
| H7 | agent-generated (rule-based, no model) | “bandgap (eV) < 1.40 eV for Br ≤ 0.1, FA ≥ 0.6, Sn 0.2–0.6” | “False if ≥⅔ of ≥3 films in the region measure >= 1.40 eV.” | qualified | n=27, pass rate 0.74 | [src: state:H7] |

- Round 1: hypothesis H2 was recorded as supported (n=3, pass=1.0) [src: nb:hyp-1]
- Round 1: hypothesis H3 was recorded as supported (n=3, pass=1.0) [src: nb:hyp-2]
- Round 3: hypothesis H7 was recorded as supported (n=8, pass=0.88) [src: nb:hyp-4]
- Round 5: hypothesis H1 was recorded as falsified (n=4, pass=0.0) [src: nb:hyp-5]
- Round 6: hypothesis H2 was recorded as qualified (n=11, pass=0.73) [src: nb:hyp-6]
- Round 6: hypothesis H3 was recorded as qualified (n=13, pass=0.69) [src: nb:hyp-7]
- Round 6: hypothesis H7 was recorded as qualified (n=17, pass=0.76) [src: nb:hyp-8]
- Round 7: hypothesis H10 was recorded as qualified (n=26, pass=0.46) [src: nb:hyp-11]
- Round 7: hypothesis H11 was recorded as supported (n=29, pass=0.53) [src: nb:hyp-12]
- Round 8: hypothesis H14 was recorded as qualified (n=26, pass=0.35) [src: nb:hyp-15]
- Round 8: hypothesis H15 was recorded as falsified (n=31, pass=0.06) [src: nb:hyp-16]

## 4. Experiments and measured values

- Each row is one simulated film: the notebook id, the measured bandgap and log10 T80, and the surrogate's bandgap prediction made before the run [src: nb:E001]

| id | round | composition | bandgap (eV) | log10 T80 | predicted bandgap (eV) | outcome | cost | source |
|---|---|---|---|---|---|---|---|---|
| E001 | 1 | `Cs0.1FA0.9Pb0.6Sn0.4I3` | 1.304 | 2.168 | 1.479 | misses spec | 1.5 | [src: nb:E001, rec-0006] |
| E002 | 1 | `Cs0.1FA0.9Pb0.7Sn0.3I3` | 1.346 | 2.49 | 1.492 | misses spec | 1.5 | [src: nb:E002, rec-0007] |
| E003 | 1 | `Cs0.1FA0.9PbI3` | 1.491 | 3.004 | 1.532 | misses spec | 1.0 | [src: nb:E003, rec-0008] |
| E004 | 1 | `FA0.5MA0.5Pb0.9Sn0.1I3` | n/a | n/a | 1.535 | failed film | 1.5 | [src: nb:E004, rec-0009] |
| E005 | 1 | `Cs0.2FA0.8Pb0.7Sn0.3I3` | 1.33 | 2.451 | 1.504 | misses spec | 1.5 | [src: nb:E005, rec-0010] |
| E006 | 2 | `Cs0.1FA0.9Pb0.6Sn0.4I3` | 1.293 | 2.294 | 1.307 | misses spec | 1.5 | [src: nb:E006, rec-0016] |
| E007 | 2 | `Cs0.15FA0.6MA0.25PbI3` | 1.547 | 2.759 | 1.504 | misses spec | 1.0 | [src: nb:E007, rec-0017] |
| E008 | 2 | `Cs0.3FA0.7Pb0.9Sn0.1I3` | 1.46 | 2.876 | 1.445 | misses spec | 1.5 | [src: nb:E008, rec-0018] |
| E009 | 2 | `Cs0.5FA0.5Pb0.9Sn0.1I3` | 1.502 | 2.883 | 1.468 | misses spec | 1.5 | [src: nb:E009, rec-0019] |
| E010 | 2 | `Cs0.2FA0.8Pb0.8Sn0.2I3` | 1.377 | 2.663 | 1.382 | misses spec | 1.5 | [src: nb:E010, rec-0020] |
| E011 | 3 | `Cs0.2FA0.8Pb0.7Sn0.3I3` | 1.32 | 2.634 | 1.333 | misses spec | 1.5 | [src: nb:E011, rec-0026] |
| E012 | 3 | `Cs0.1FA0.9Pb0.8Sn0.2I3` | 1.375 | 2.59 | 1.379 | misses spec | 1.5 | [src: nb:E012, rec-0027] |
| E013 | 3 | `Cs0.3FA0.7Pb0.8Sn0.2I3` | 1.429 | 2.807 | 1.393 | misses spec | 1.5 | [src: nb:E013, rec-0028] |
| E014 | 3 | `Cs0.5FA0.5Pb0.8Sn0.2I3` | 1.433 | 2.684 | 1.427 | misses spec | 1.5 | [src: nb:E014, rec-0029] |
| E015 | 3 | `Cs0.1FA0.9Pb0.9Sn0.1I3` | 1.436 | 2.899 | 1.431 | misses spec | 1.5 | [src: nb:E015, rec-0030] |
| E016 | 4 | `Cs0.3FA0.7Pb0.7Sn0.3I3` | 1.344 | 2.365 | 1.347 | misses spec | 1.5 | [src: nb:E016, rec-0036] |
| E017 | 4 | `Cs0.5FA0.5Pb0.7Sn0.3I3` | 1.38 | 2.365 | 1.374 | misses spec | 1.5 | [src: nb:E017, rec-0037] |
| E018 | 4 | `Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3` | 1.381 | 2.224 | 1.393 | misses spec | 1.5 | [src: nb:E018, rec-0038] |
| E019 | 4 | `Cs0.05FA0.8MA0.15Pb0.9Sn0.1I3` | 1.446 | 2.606 | 1.446 | misses spec | 1.5 | [src: nb:E019, rec-0039] |
| E020 | 4 | `Cs0.2FA0.8Pb0.9Sn0.1I3` | 1.475 | 2.722 | 1.447 | misses spec | 1.5 | [src: nb:E020, rec-0040] |
| E021 | 5 | `Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3` | 1.372 | 2.644 | 1.388 | misses spec | 1.5 | [src: nb:E021, rec-0046] |
| E022 | 5 | `CsPb0.4Sn0.6I3` | 1.284 | 0.557 | 1.355 | misses spec | 1.5 | [src: nb:E022, rec-0047] |
| E023 | 5 | `Cs0.1FA0.75MA0.15Pb0.7Sn0.3I3` | 1.34 | 2.375 | 1.344 | misses spec | 1.5 | [src: nb:E023, rec-0048] |
| E024 | 5 | `Cs0.2FA0.8Pb0.6Sn0.4I3` | 1.299 | 2.436 | 1.297 | misses spec | 1.5 | [src: nb:E024, rec-0049] |
| E025 | 5 | `Cs0.15FA0.6MA0.25Pb0.8Sn0.2I3` | 1.395 | 2.501 | 1.411 | misses spec | 1.5 | [src: nb:E025, rec-0050] |
| E026 | 6 | `Cs0.1FA0.9Pb0.7Sn0.3I2.7Cl0.3` | 1.404 | 2.967 | 1.383 | misses spec | 1.5 | [src: nb:E026, rec-0056] |
| E027 | 6 | `Cs0.2FA0.8Pb0.7Sn0.3I2.7Cl0.3` | 1.432 | 3.026 | 1.389 | misses spec | 1.5 | [src: nb:E027, rec-0057] |
| E028 | 6 | `Cs0.3FA0.7Pb0.7Sn0.3I2.7Cl0.3` | 1.434 | 3.196 | 1.399 | misses spec | 1.5 | [src: nb:E028, rec-0058] |
| E029 | 6 | `Cs0.1FA0.75MA0.15Pb0.8Sn0.2I3` | n/a | n/a | 1.388 | failed film | 1.5 | [src: nb:E029, rec-0059] |
| E030 | 6 | `Cs0.2FA0.8Pb0.6Sn0.4I2.7Cl0.3` | n/a | n/a | 1.35 | failed film | 1.5 | [src: nb:E030, rec-0060] |
| E031 | 7 | `Cs0.1FA0.9Pb0.7Sn0.3I2.7Cl0.3` | 1.435 | 3.031 | 1.407 | misses spec | 1.5 | [src: nb:E031, rec-0066] |
| E032 | 7 | `Cs0.1FA0.9Pb0.6Sn0.4I2.7Cl0.3` | 1.405 | 3.206 | 1.371 | misses spec | 1.5 | [src: nb:E032, rec-0067] |
| E033 | 7 | `Cs0.2FA0.8Pb0.5Sn0.5I2.7Cl0.3` | 1.38 | 2.97 | 1.348 | meets spec | 1.5 | [src: nb:E033, rec-0068] |
| E034 | 7 | `Cs0.3FA0.7Pb0.5Sn0.5I2.7Cl0.3` | 1.362 | 3.139 | 1.353 | meets spec | 1.5 | [src: nb:E034, rec-0069] |
| E035 | 7 | `Cs0.3FA0.7Pb0.6Sn0.4I2.7Cl0.3` | 1.392 | 3.153 | 1.385 | misses spec | 1.5 | [src: nb:E035, rec-0070] |
| E036 | 8 | `Cs0.2FA0.8Pb0.5Sn0.5I2.7Cl0.3` | 1.379 | 3.217 | 1.368 | meets spec | 1.5 | [src: nb:E036, rec-0076] |
| E037 | 8 | `Cs0.3FA0.7Pb0.5Sn0.5I2.7Cl0.3` | 1.348 | 3.236 | 1.367 | meets spec | 1.5 | [src: nb:E037, rec-0077] |
| E038 | 8 | `Cs0.2FA0.8Pb0.7Sn0.3I2.7Cl0.3` | 1.44 | 3.172 | 1.427 | misses spec | 1.5 | [src: nb:E038, rec-0078] |
| E039 | 8 | `Cs0.3FA0.7Pb0.6Sn0.4I2.7Br0.3` | 1.323 | 2.109 | 1.332 | misses spec | 1.5 | [src: nb:E039, rec-0079] |
| E040 | 8 | `Cs0.3FA0.7Pb0.4Sn0.6I2.7Cl0.3` | 1.367 | 3.108 | 1.351 | meets spec | 1.5 | [src: nb:E040, rec-0080] |

- 5 of 40 films met the spec (1.24 to 1.38 eV and T80 of at least 500 h) [src: calc:n_spec_films, calc:n_films, calc:target_eg_min, calc:target_eg_max, calc:target_t80_h]
- These 5 films cover 3 distinct compositions, so repeats are not new discoveries [src: calc:n_spec_films, nb:E033, nb:E034, nb:E036, nb:E037, nb:E040]
- The first spec-meeting film was E033 after 48.5 units [src: nb:E033, calc:first_hit_units]

## 5. Discovery verdicts (replication rubric)


| composition | status | confidence | films | bandgap (eV) | T80 (h) | reason | source |
|---|---|---|---|---|---|---|---|
| `Cs0.2FA0.8Pb0.5Sn0.5I2.7Cl0.3` | confirmed | High | 2 | 1.379 | 1241 | “replicated 2×, Eg spread 1 meV” | [src: rec-0088] |
| `Cs0.3FA0.7Pb0.5Sn0.5I2.7Cl0.3` | confirmed | High | 2 | 1.355 | 1539 | “replicated 2×, Eg spread 14 meV” | [src: rec-0088] |
| `Cs0.3FA0.7Pb0.4Sn0.6I2.7Cl0.3` | candidate | Low | 1 | 1.367 | 1281 | “single measurement, replication queued” | [src: rec-0088] |

- 2 of 3 discovery candidates were replicated at the final judge call [src: rec-0088, calc:n_discoveries, calc:n_replicated]

## 6. Negative results (kept, not hidden)

- 3 films failed to form a usable phase [src: calc:n_failed]
- Film E004 (`FA0.5MA0.5Pb0.9Sn0.1I3`) failed with phase “pinholes, incomplete coverage” [src: nb:E004]
- Film E029 (`Cs0.1FA0.75MA0.15Pb0.8Sn0.2I3`) failed with phase “pinholes, incomplete coverage” [src: nb:E029]
- Film E030 (`Cs0.2FA0.8Pb0.6Sn0.4I2.7Cl0.3`) failed with phase “pinholes, incomplete coverage” [src: nb:E030]
- 32 measured films missed the spec [src: calc:n_miss]
- Hypothesis H1 was falsified after 4 films: “bandgap (eV) between 1.40 eV and 1.56 eV for Br = 0, Cl = 0, Sn 0.4–0.6” [src: state:H1]
- Hypothesis H15 was falsified after 31 films: “log10 T80 (h) is higher by >0.25 in [Br ≤ 0.1, FA ≥ 0.7, Sn ≤ 0.4] than in [Br ≤ 0.1, FA ≤ 0.6, Sn ≤…” [src: state:H15]
- Hypothesis H10 holds only with exceptions after 30 films [src: state:H10]
- Hypothesis H14 holds only with exceptions after 26 films [src: state:H14]
- Hypothesis H2 holds only with exceptions after 20 films [src: state:H2]
- Hypothesis H3 holds only with exceptions after 23 films [src: state:H3]
- Hypothesis H7 holds only with exceptions after 27 films [src: state:H7]

## 7. What changed the planner's decisions


| round | mode | LabLoop rationale | planner rationale | source |
|---|---|---|---|---|
| 1 | seed | “No data yet, so slots test the goal-relevant literature hypotheses (H1, H2, H5, H6, H3); H4 parked because their regions cannot me…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-1] |
| 2 | investigate | “Re-run the surprising Cs0.1FA0.9Pb0.6Sn0.4I3 result (z = -2.1) to rule out noise; best P(hit) is only 6%; testing H5 to sharpen th…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-2] |
| 3 | investigate | “Re-run the surprising Cs0.2FA0.8Pb0.7Sn0.3I3 result (z = -2.1) to rule out noise; best P(hit) is only 8%; testing H7 to sharpen th…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-3] |
| 4 | investigate | “No open hypotheses worth a film; exploring where a hit is still plausible.” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-4] |
| 5 | investigate | “Re-run the surprising Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3 result (z = -2.2) to rule out noise; best P(hit) is only 0%; testing H1 to sha…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-5] |
| 6 | investigate | “No open hypotheses worth a film; exploring where a hit is still plausible.” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-6] |
| 7 | exploit | “Re-run the surprising Cs0.1FA0.9Pb0.7Sn0.3I2.7Cl0.3 result (z = 2.2) to rule out noise; model now gives P(hit) up to 38%, so most…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-7] |
| 8 | exploit | “Replicate 2 spec-meeting film(s) before claiming a discovery; re-run the surprising Cs0.2FA0.8Pb0.7Sn0.3I2.7Cl0.3 result (z = 2.5)…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-8] |
| 9 | exploit | “Replicate 1 spec-meeting film(s) before claiming a discovery; re-run the surprising Cs0.3FA0.7Pb0.7Sn0.3I2.7Cl0.3 result (z = 3.5)…” | “offline rule-based run: no planner model; the LabLoop PI rules choose the mode” | [src: nb:decision-9] |

- The PI mode changed from seed in round 1 to investigate in round 2 [src: nb:decision-1, nb:decision-2]
- The PI mode changed from investigate in round 6 to exploit in round 7 [src: nb:decision-6, nb:decision-7]
- Round 1 analysis reported a surprise event: “Cs0.1FA0.9Pb0.6Sn0.4I3: surprise in bandgap (z = -2.1); queued for replication” [src: rec-0011]
- Round 1 analysis reported a surprise event: “Cs0.2FA0.8Pb0.7Sn0.3I3: surprise in bandgap (z = -2.1); queued for replication” [src: rec-0011]
- Round 4 analysis reported a surprise event: “Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3: surprise in stability (z = -2.2); queued for replication” [src: rec-0041]
- Round 5 analysis reported a falsified event: “H1 falsified (n = 4)” [src: rec-0051]
- Round 5 analysis reported a revision event: “Literature bandgap prior relaxed after H1 was falsified” [src: rec-0051]
- Round 6 analysis reported a surprise event: “Cs0.1FA0.9Pb0.7Sn0.3I2.7Cl0.3: surprise in stability (z = +2.2); queued for replication” [src: rec-0061]
- Round 6 analysis reported a surprise event: “Cs0.2FA0.8Pb0.7Sn0.3I2.7Cl0.3: surprise in stability (z = +2.5); queued for replication” [src: rec-0061]
- Round 6 analysis reported a surprise event: “Cs0.3FA0.7Pb0.7Sn0.3I2.7Cl0.3: surprise in stability (z = +3.5); queued for replication” [src: rec-0061]
- Round 6 analysis reported a qualified event: “H2 holds with exceptions; strongest counterexample Cs0.1FA0.9Pb0.7Sn0.3I2.7Cl0.3 (Eg 1.40 eV vs prior Eg 1.64 eV)” [src: rec-0061]
- Round 7 analysis reported a surprise event: “Cs0.1FA0.9Pb0.6Sn0.4I2.7Cl0.3: surprise in stability (z = +2.4); queued for replication” [src: rec-0071]
- Round 7 analysis reported a qualified event: “H10 holds with exceptions; strongest counterexample Cs0.05FA0.8MA0.15Pb0.8Sn0.2I3 (T80 167 h vs prior T80 309 h)” [src: rec-0071]
- Round 7 analysis reported a qualified event: “H10 qualified (n = 26)” [src: rec-0071]
- Round 8 analysis reported a qualified event: “H14 holds with exceptions; strongest counterexample Cs0.1FA0.9Pb0.6Sn0.4I2.7Cl0.3 (T80 1606 h vs prior T80 222 h)” [src: rec-0081]
- Round 8 analysis reported a qualified event: “H14 qualified (n = 26)” [src: rec-0081]
- Round 8 analysis reported a falsified event: “H15 falsified (n = 31)” [src: rec-0081]
- ADAPT: the bandgap prior was relaxed after hypothesis H1 was falsified [src: rec-0051]
- ADAPT: the stability prior was relaxed after hypothesis H3 was qualified [src: rec-0061]
- Across 9 arena rounds 0 model proposals were admitted and 5 rule-based anomaly hypotheses were added [src: calc:n_arena_rounds, calc:n_admitted, calc:n_fallback]

## 8. Safety, controls and human approval

- 0 designed protocols were marked not runnable by the safety review [src: calc:n_design_blocked]
- The budget gate recorded 1 denial record(s) when a film would exceed the unit budget [src: calc:n_denials]
- Denied slot `r9s1`: “DENY: budget 60 units would be exceeded (used 59, film costs 1.5)” [src: rec-0086]
- Denied slot `r9s2`: “DENY: budget 60 units would be exceeded (used 59, film costs 1.5)” [src: rec-0086]
- Restricted elements and scale-up need human approval before a run, and runs past the unit budget are denied [src: file:docs/LABLOOP_INTEGRATION.md, file:asd/labloop_tools.py]

## 9. Uncertainty and limits

- This is one run on one world with one seed (40 films), so it supports no rate or improvement claim [src: calc:n_films, state:run]
- The simulator was designed by the team, so a measured value is a property of the model world, not of a real device [src: file:docs/LABLOOP_INTEGRATION.md]
- Benchmark numbers from the LabLoop README stay unverified until rerun [src: file:docs/CLOUD_WORKER_CONTEXT.md]
- Hypothesis verdicts rest on few films: 5 of 11 hypotheses are only qualified [src: calc:n_qualified, calc:n_hyps]
- 3 hypotheses never reached a verdict [src: calc:n_open]
- No Omnigent planner or generator agent was involved, so nothing here measures agent collaboration [src: rec-0004]

## 10. Recommended next experiment and validation needed

- Next experiment: replicate `Cs0.3FA0.7Pb0.4Sn0.6I2.7Cl0.3`, which has 1 film so far and status candidate [src: rec-0088]
- Before any real use a confirmed composition must be made and measured in a physical lab, with human sign-off [src: file:docs/CHALLENGE_BRIEF.md]
- The simulator's physics would have to be checked against real device data before any conclusion transfers [src: file:docs/LABLOOP_INTEGRATION.md]
