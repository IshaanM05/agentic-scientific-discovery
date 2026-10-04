# Tech video script (60 seconds max)

Mix of the architecture diagram (from the one-pager), short code shots and the app. About 150 words.

| Time | On screen | Voiceover |
|---|---|---|
| 0:00–0:12 | Architecture diagram | "Stack: Python, NumPy and SciPy for eight light-curve tests; Streamlit for the UI; Omnigent for agent orchestration and guardrails; Gemini or Claude for live literature reading; arXiv and OpenAlex APIs; and NASA's Exoplanet Archive plus MAST for real Kepler data." |
| 0:12–0:30 | `planner/posterior.py` (expected information gain), then Cuddy's scored table in the app | "The core is Bayesian. Each test has calibrated likelihood tables. Cuddy scores every test by expected information gain per unit of cost. Foreman down-weights unreliable results and forces control experiments. Policies are code: no label access, no target-specific lookups, and human approval for anything consequential." |
| 0:30–0:48 | `research.py` citation filter, then a stripped-citation caption in the app; REAL_REPORT table | "Hard parts: LLMs invent citations, so every cited ID is checked against what we actually retrieved, and anything else is stripped. Our biggest limitation: likelihood tables learned on synthetic data don't transfer to real Kepler data. Recalibrating cut confident errors from 11 to 2, but accuracy didn't recover." |
| 0:48–0:60 | Ledger tab | "Takeaway: most of the speedup comes from information-gain planning, and the adversarial agents buy accuracy and calibration. Next, we'll calibrate on two thousand real candidates." |
