---
type: dataset
status: verified (license, hash, counts checked 2026-10-03 by scout); provenance of upstream Citrine data unverified
tags: [replay-oracle, T002]
---
# Dataset: steel_strength (primary replay oracle)
**What.** 312 steels, 13 composition columns (c, mn, si, cr, ni, mo, v, n, nb, co, w, al, ti) + yield strength, tensile strength, elongation. No missing values, no duplicate compositions (checked).
**Source.** figshare article 7250453, DOI 10.6084/m9.figshare.7250453.v1, file 13354691 `steel_strength.json.gz` (14,945 B, pandas split-JSON, gzip). Also file 13354694 `steel_strength.csv`. Same file as matminer `steel_strength`.
**sha256** `e36501d7057cd833223bb8ed9948668b5ac90fd585d29a749f45af51c1d7f6ad` (matches matminer metadata hash).
**License.** MIT, per figshare API `license.name` for article 7250453 (checked). Upstream origin: Citrine dataset 153092 [unverified license]. Cite figshare DOI + Citrine in README.
**Fetch.** `https://ndownloader.figshare.com/files/13354691`, no API key. 15 KB, so bundle it under `data/` and verify sha256 on load.
**Units.** Composition units (wt% vs fraction) [unverified]. Yield strength assumed MPa [unverified, consistent with value range 1000-2510].
## Hit definition
- Target: `yield strength`. Hit = yield strength >= 2000 MPa (true recorded value).
- Count: 15 / 312 = 4.81% hits. Top value 2510.3. Median 1344.2.
- Sensitivity (counts >= t): 1800:29 (9.3%) | 1900:16 | 2000:15 (4.8%) | 2100:13 (4.2%) | 2200:12 (3.8%).
## Budget accounting (see [[ADR-001-replay-dataset]])
- 1 experiment = reveal one candidate's measured yield strength. Cost 1 unit. Pool-based: candidates are the 312 rows.
- Default budget B = 60 experiments (19% of pool). Random expects ~2.9 hits in 60; expected experiments to k-th hit = k*313/16 (19.6, 58.7, 97.8 for k=1,3,5), so k=5 is usually censored for random.
- Initial design counts against the budget. Re-querying a revealed row is free and returns the cached value (never double-counted, never a new hit).
- LLM calls cost 0 experiments but are logged separately (tokens, $).
**Links:** [[replay-oracle]] · [[baselines-and-evaluation]] · fallbacks: [[expt-gap]]
