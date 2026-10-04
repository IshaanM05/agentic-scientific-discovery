<!-- asd-report: {"kind": "steel", "run_dir": "runs/t011"} -->
# Research report: steel yield strength (t011)

> Auto-generated from committed run records by a template; no model wrote this text [src: file:scripts/make_report.py]
> Every line carries a source id that the checker resolves against the run directory [src: file:scripts/make_report.py]

## 1. Question

- Which steel compositions in a 312-candidate public dataset reach a yield strength of 2000 MPa or more, and can an agent team find them within a small experiment budget [src: file:docs/CLOUD_WORKER_CONTEXT.md, file:asd/replay.py]
- This run used seed 21 and a budget of 60 experiments [src: meta]
- The run record holds 34 entries and the ledger 4 revealed measurements [src: calc:n_records, calc:n_ledger]

## 2. Evidence from literature (retrieved by the literature agent)

- The literature agent ran 7 searches [src: rec-0001, rec-0002, rec-0003, rec-0004, rec-0005, rec-0006, rec-0007]

| search query | papers returned | source |
|---|---|---|
| “maraging steel yield strength 2000 MPa” | 20 | [src: rec-0001, calc:ncit_rec-0001] |
| “precipitation hardened steel ultra-high strength cobalt nickel” | 20 | [src: rec-0002, calc:ncit_rec-0002] |
| “high strength steel composition yield stress 2000 MPa alloy design” | 20 | [src: rec-0003, calc:ncit_rec-0003] |
| “machine learning materials discovery steel strength prediction” | 20 | [src: rec-0004, calc:ncit_rec-0004] |
| “alloy composition optimization screening experiments design of experiments” | 15 | [src: rec-0005, calc:ncit_rec-0005] |
| “high-strength steel composition design nickel cobalt molybdenum vanadium” | 15 | [src: rec-0006, calc:ncit_rec-0006] |
| “materials informatics accelerated discovery metallic alloys yield strength” | 15 | [src: rec-0007, calc:ncit_rec-0007] |

- Each row is a retrieved paper with the literature agent's one-line summary of it [src: https://openalex.org/W2092782143]
- The summary is the agent's own reading and was not verified against the full text [src: rec-0008]

| id | title | agent summary | source |
|---|---|---|---|
| W2092782143 | “Microstructure and mechanical properties of a 2000 MPa Co-free maraging steel after aging…” (2004) | “Co-free maraging steel achieves 2000 MPa yield strength.” | [src: https://openalex.org/W2092782143, rec-0008] |
| W2561149941 | “Development of thermo-mechanical treatments of a maraging steel for yield strengths above…” (1987) | “Thermo-mechanical treatments of maraging steel achieve yield strengths >3 GPa.” | [src: https://openalex.org/W2561149941, rec-0008] |
| W2996591776 | “High Strength X3NiCoMoTi 18-9-5 Maraging Steel Prepared by Selective Laser Melting from At…” (2019) | “X3NiCoMoTi 18-9-5 maraging steel reaches ultra-high strength via laser powder.” | [src: https://openalex.org/W2996591776, rec-0008] |
| W2792578012 | “A novel ultra-high strength maraging steel with balanced ductility and creep resistance ac…” (2018) | “β-NiAl and Laves phase precipitates enable ultra-high strength with ductility.” | [src: https://openalex.org/W2792578012, rec-0008] |
| W4311975210 | “Austenite Formation in the Oxidized Layer of Ultra-High-Strength 13Ni15Co10Mo Maraging Ste…” (2022) | “13Ni15Co10Mo composition achieves ultra-high strength in maraging steels.” | [src: https://openalex.org/W4311975210, rec-0008] |
| W7116631459 | “Design of a Cobalt‐Free Maraging Steel with Ultra‐High Strength of 2.3 GPa Through Additiv…” (2025) | “Co-free maraging steel achieves 2.3 GPa yield strength via additive manufacturing.” | [src: https://openalex.org/W7116631459, rec-0008] |
| W4225013525 | “A sustainable ultra-high strength Fe18Mn3Ti maraging steel through controlled solute segre…” (2022) | “Fe18Mn3Ti maraging steel achieves ultra-high strength via α-Mn nanoprecipitation.” | [src: https://openalex.org/W4225013525, rec-0008] |
| W3137870691 | “Discovery of marageing steels: machine learning vs. physical metallurgical modelling” (2021) | “Machine learning outperforms physical models for discovering maraging steel compositions.” | [src: https://openalex.org/W3137870691, rec-0008] |
| W2903802132 | “Property prediction and properties-to-microstructure inverse analysis of steels by a machi…” (2018) | “ML models predict yield strength from composition and processing parameters.” | [src: https://openalex.org/W2903802132, rec-0008] |
| W2969389191 | “Physical metallurgy-guided machine learning and artificial intelligent design of ultrahigh…” (2019) | “Physical metallurgy-guided ML accelerates ultrahigh-strength (>2000 MPa) steel design.” | [src: https://openalex.org/W2969389191, rec-0008] |
| W3175424420 | “Machine learning assisted composition effective design for precipitation strengthened copp…” (2021) | “ML-assisted design screens precipitation-hardened alloys within reduced experiments.” | [src: https://openalex.org/W3175424420, rec-0008] |
| W3210035924 | “A machine learning-based alloy design system to facilitate the rational design of high ent…” (2021) | “ML alloy design system screens HEA composition space for enhanced strength.” | [src: https://openalex.org/W3210035924, rec-0008] |
| W2950904464 | “Materials informatics for the screening of multi-principal elements and high-entropy alloy…” (2019) | “Materials informatics efficiently screens alloys against yield strength targets.” | [src: https://openalex.org/W2950904464, rec-0008] |
| W4402173094 | “Accelerated discovery of eutectic compositionally complex alloys by generative machine lea…” (2024) | “Generative ML accelerates discovery within large composition spaces.” | [src: https://openalex.org/W4402173094, rec-0008] |
| W4417513448 | “Machine learning driven insights into yield strength of multi-principal element alloys” (2025) | “ML-driven yield strength prediction identifies composition-strength relationships.” | [src: https://openalex.org/W4417513448, rec-0008] |


## 3. Hypotheses (all agent-generated, unvalidated)

- **H1** carries the label “agent-generated hypothesis (unvalidated)”: “c000 (Ni 18.5, Co 8.8, Mo 4.7, Ti 0.71, Al 1.02) is a classic maraging composition and reaches about 2000 MPa yield after aging through Ni3(Ti,Mo) and Fe2Mo precipitation. c101 (Cr 17, Ni 7, Al 1.2, no Co/Mo/Ti) is a precipitation…” [src: rec-0010]
- H1 predicts a yield strength of 2000 MPa for candidates c000, c101 [src: rec-0010]
- H1 rests on the assumption “Both alloys are solution-treated and peak-aged, with no retained austenite or overaging. The rec-0008 claim (>=2000 MPa) applies directly only to c000. c101 lac…” [src: rec-0010]
- Kill condition for H1: a measured value more than 25% away from the prediction counts as unsupported and reopens the assumption [src: file:asd/tools.py]
- Final status of H1: refuted by every test (0 of 1 analysed tests supported) [src: rec-0015, calc:H1_tests]
- **H2** carries the label “agent-generated hypothesis (unvalidated)”: “c299 (Co 19.5, Cr 13.4, Mo 3.0, W 2.35), c008 (Mo 9.67, Co 4.9, C 0.38) and c049 (W 9.18, Co 5.0, C 0.36) are high-Co/Mo/W compositions with no Ni. Co lowers Mo/W solubility and promotes fine carbide or intermetallic precipitation…” [src: rec-0011]
- H2 predicts a yield strength of 2300 MPa for candidates c299, c008, c049 [src: rec-0011]
- H2 rests on the assumption “Strength rises with Co, Mo and W through secondary-hardening precipitation, with no embrittlement from coarse carbides or intermetallics. These are Cr/C seconda…” [src: rec-0011]
- Kill condition for H2: a measured value more than 25% away from the prediction counts as unsupported and reopens the assumption [src: file:asd/tools.py]
- Final status of H2: refuted by every test (0 of 1 analysed tests supported) [src: rec-0020, calc:H2_tests]
- **H3** carries the label “agent-generated hypothesis (unvalidated)”: “Revised after H1 and H2 were refuted (c000 maraging measured 1309 MPa vs 2000 predicted; c299 tool steel measured 1123 MPa vs 2300 predicted). c154 (Cr 12.3, Co 14.8, W 8.0), c173 (Cr 17.5, Co 11.8, Si 2.0, Ni 2.1) and c150 (Cr 17…” [src: rec-0023]
- H3 predicts a yield strength of 1200 MPa for candidates c154, c173, c150 [src: rec-0023]
- H3 rests on the assumption “Real yield in this dataset sits well below the literature peak-aged claims. The two measurements (1309 and 1123 MPa) are taken as the anchor, and the prediction…” [src: rec-0023]
- Kill condition for H3: a measured value more than 25% away from the prediction counts as unsupported and reopens the assumption [src: file:asd/tools.py]
- Final status of H3: supported by every test (2 of 2 analysed tests supported) [src: rec-0027, rec-0031, calc:H3_tests]

## 4. Experiments and measured values


| ledger id | candidate | yield strength (MPa) | meets 2000 MPa | hypothesis | source |
|---|---|---|---|---|---|
| ledger-0001 | c000 | 1309.1 | no | H1 | [src: ledger-0001, rec-0014] |
| ledger-0002 | c299 | 1123.1 | no | H2 | [src: ledger-0002, rec-0019] |
| ledger-0003 | c150 | 1236.6 | no | H3 | [src: ledger-0003, rec-0026] |
| ledger-0004 | c094 | 1463.0 | no |  | [src: ledger-0004, rec-0030] |

- 0 of 4 measured candidates reached 2000 MPa [src: calc:hits, calc:n_measured, file:asd/replay.py]

## 5. Experiment choices (two or more candidate tests compared)

- Record rec-0013 compared 2 candidate tests and chose “run c000 (true maraging, tests H1)” [src: rec-0013]

| option | expected learning | feasibility | cost | score | source |
|---|---|---|---|---|---|
| “run c000 (true maraging, tests H1)” | 0.8 | 0.95 | 1 | 0.76 | [src: rec-0013] |
| “run c299 (tool steel, tests H2)” | 0.6 | 0.9 | 1 | 0.54 | [src: rec-0013] |

- Record rec-0018 compared 2 candidate tests and chose “run c299 (tool steel, tests H2, top surrogate)” [src: rec-0018]

| option | expected learning | feasibility | cost | score | source |
|---|---|---|---|---|---|
| “run c299 (tool steel, tests H2, top surrogate)” | 0.8 | 0.9 | 1 | 0.72 | [src: rec-0018] |
| “run c154 (surrogate runner-up)” | 0.6 | 0.9 | 1 | 0.54 | [src: rec-0018] |

- Record rec-0025 compared 2 candidate tests and chose “run c150 (H3, in both surrogate lists)” [src: rec-0025]

| option | expected learning | feasibility | cost | score | source |
|---|---|---|---|---|---|
| “run c150 (H3, in both surrogate lists)” | 0.8 | 0.9 | 1 | 0.72 | [src: rec-0025] |
| “run c094 (new family, exploration)” | 0.6 | 0.9 | 1 | 0.54 | [src: rec-0025] |

- Record rec-0029 compared 2 candidate tests and chose “run c094 (new family, exploration of high tail)” [src: rec-0029]

| option | expected learning | feasibility | cost | score | source |
|---|---|---|---|---|---|
| “run c094 (new family, exploration of high tail)” | 0.8 | 0.9 | 1 | 0.72 | [src: rec-0029] |
| “run c154 (H3 family, Cr/Co/W)” | 0.5 | 0.9 | 1 | 0.45 | [src: rec-0029] |


## 6. Negative results (kept, not hidden)

- Candidate c000 measured 1309.1 MPa, below the 2000 MPa target [src: ledger-0001, file:asd/replay.py]
- Candidate c299 measured 1123.1 MPa, below the 2000 MPa target [src: ledger-0002, file:asd/replay.py]
- Candidate c150 measured 1236.6 MPa, below the 2000 MPa target [src: ledger-0003, file:asd/replay.py]
- Candidate c094 measured 1463.0 MPa, below the 2000 MPa target [src: ledger-0004, file:asd/replay.py]
- Hypothesis H1 was unsupported: predicted 2000 MPa, measured 1309.1 MPa (relative error 0.345) [src: rec-0015]
- Hypothesis H2 was unsupported: predicted 2300 MPa, measured 1123.1 MPa (relative error 0.512) [src: rec-0020]

## 7. What changed the planner's decisions

- Analysis rec-0015 reopened an assumption: “Both alloys are solution-treated and peak-aged, with no retained austenite or overaging. The rec-0008 claim (>=2000 MPa) applies directly only to c000. c101 lacks Co, Mo…” [src: rec-0015]
- The next hypothesis registered after the first reopened assumption was H3 [src: rec-0023, rec-0015]
- Analysis rec-0020 reopened an assumption: “Strength rises with Co, Mo and W through secondary-hardening precipitation, with no embrittlement from coarse carbides or intermetallics. These are Cr/C secondary-hardeni…” [src: rec-0020]
- Hypothesis H3 states it was revised after earlier hypotheses failed: “H1 and H2 were refuted (c000 maraging measured 1309 MPa vs 2000 predicted; c299 tool steel measured 1123 MPa vs 2300 predicted). c154 (Cr 12.3, Co 14.…” [src: rec-0023]
- The surrogate selector was consulted 3 times [src: rec-0009, rec-0017, rec-0022]

## 8. Independent checks, safety and human approval

- Judge verdict judge-rec-0015 on rec-0015: confidence medium, ledger-supported true, citations present true [src: judge-rec-0015, rec-0015]
- Judge verdict judge-rec-0020 on rec-0020: confidence high, ledger-supported true, citations present true [src: judge-rec-0020, rec-0020]
- Judge verdict judge-rec-0027 on rec-0027: confidence high, ledger-supported true, citations present true [src: judge-rec-0027, rec-0027]
- Judge verdict judge-rec-0031 on rec-0031: confidence high, ledger-supported true, citations present true [src: judge-rec-0031, rec-0031]
- Safety agent flagged candidate c094 at level low: “Measured 1463.0 MPa (rec-0030), 27% below 2000 MPa target. In-silico hypothesis-grade; no physical synthesis yet. Underperformance poses no…” [src: rec-0033]
- Recommending a candidate for real-world validation is gated by a human-approval ask policy [src: file:asd/tools.py]

## 9. Uncertainty and limits

- This run measured 4 candidates under a single seed, so no rate or improvement is claimed from it [src: calc:n_measured, file:asd/replay.py]
- The steel data is public, a memorization probe flag is set, and no acceleration claim is made from LLM knowledge [src: file:docs/CLOUD_WORKER_CONTEXT.md]
- Judge calibration (n=12) was near-arithmetic and the arena check (n=5, Spearman 0.56, p=0.21) was at chance, so both are weak evidence [src: file:docs/CLOUD_WORKER_CONTEXT.md]
- Predictions are the agents' own estimates and the oracle replays a fixed dataset, so a measured value is a lookup, not a new experiment [src: file:docs/CLOUD_WORKER_CONTEXT.md, file:asd/replay.py]

## 10. Recommended next experiment and validation needed

- Next experiment: run candidate c101, the highest surrogate pick not yet measured (score 2281.07) [src: rec-0022]
- Before real use a hit must be replicated and then synthesised and tested in a physical lab, with human sign-off [src: file:docs/CHALLENGE_BRIEF.md]
- The recorded hypotheses and agent summaries must be checked against the cited papers before anyone relies on them [src: file:docs/CHALLENGE_BRIEF.md]
