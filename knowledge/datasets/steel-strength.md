---
type: dataset
status: verified (license, hash, counts, units checked 2026-10-03 by scout); upstream Citrine license unverified
tags: [replay-oracle, T002]
---
# Dataset: steel_strength (primary replay oracle)
**What.** 312 steels, 13 composition columns (c, mn, si, cr, ni, mo, v, n, nb, co, w, al, ti) + yield strength, tensile strength, elongation. No missing values, no duplicate compositions (checked).
**Source.** figshare article 7250453, DOI 10.6084/m9.figshare.7250453.v1, file 13354691 `steel_strength.json.gz` (14,945 B, pandas split-JSON, gzip). Also file 13354694 `steel_strength.csv`. Same file as matminer `steel_strength`.
**sha256** `e36501d7057cd833223bb8ed9948668b5ac90fd585d29a749f45af51c1d7f6ad` (matches matminer metadata hash).
**License.** MIT, per figshare API `license.name` for article 7250453 (checked). Upstream: Citrine "Mechanical properties of some steels", citrination.com/datasets/153092 (matminer bibtex). Citrination is shut down and the 2024 Wayback snapshot is a JS stub, so the upstream license is [unverified]. Our redistribution basis is the figshare MIT grant. Cite figshare DOI + Citrine in README.
**Fetch.** `https://ndownloader.figshare.com/files/13354691`, no API key. 15 KB, so bundle it under `data/` and verify sha256 on load.
**Units (verified, matminer dataset_metadata.json `steel_strength.columns`).** Composition columns are weight percent. Yield and tensile strength are in MPa. Elongation is in %. The file also has a `formula` column derived from the composition (not leakage).
## Hit definition
- Target: `yield strength`. Hit = yield strength >= 2000 MPa (true recorded value).
- Count: 15 / 312 = 4.81% hits. Top value 2510.3. Median 1344.2.
- Sensitivity (counts >= t): 1800:29 (9.3%) | 1900:16 | 2000:15 (4.8%) | 2100:13 (4.2%) | 2200:12 (3.8%).
## LLM memorisation risk (assessed, not measured)
- HIGH exposure: this is the same 312 rows as Matbench `matbench_steels` (a public benchmark since 2018; matminer metadata), so it is common in tutorials and papers.
- Domain priors are legitimate: maraging-type compositions (high Ni, Co, Mo, Ti; low C) are textbook high-strength steels. Row-level recall of yield values is possible [unverified].
- Controls: (1) a probe: ask the LLM for the yield strength of 20 rows from composition alone and compare its MAE with a composition-only kNN; near-exact values flag recall. (2) An anonymised arm (element names hidden, columns permuted) with a matched budget. Report both.
## Budget accounting (see [[ADR-001-replay-dataset]])
- 1 experiment = reveal one candidate's measured yield strength. Cost 1 unit. Pool-based: candidates are the 312 rows.
- Default budget B = 60 experiments (19% of pool). Random expects ~2.9 hits in 60; expected experiments to k-th hit = k*313/16 (19.6, 58.7, 97.8 for k=1,3,5), so k=5 is usually censored for random.
- Initial design counts against the budget. Re-querying a revealed row is free and returns the cached value (never double-counted, never a new hit).
- LLM calls cost 0 experiments but are logged separately (tokens, $).
**Links:** [[replay-oracle]] · [[baselines-and-evaluation]] · fallbacks: [[expt-gap]]
