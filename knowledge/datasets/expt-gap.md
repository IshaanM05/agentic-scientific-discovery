---
type: dataset
status: verified (license, hash, counts checked 2026-10-03 by scout); featurization unverified
tags: [replay-oracle, T002, fallback]
---
# Dataset: expt_gap / matbench v0.1 (fallback 1)
**What.** 4,604 compositions with experimental band gap (eV), deduplicated (Zhuo et al. 2018 SI via Matbench v0.1). Columns: `composition` (string), `gap expt`.
**Source.** figshare article 9765779, DOI 10.6084/m9.figshare.9765779.v1, file 17494814 `expt_gap.json.gz` (37,193 B). URL `https://ndownloader.figshare.com/files/17494814`, no key.
**sha256** `1e6816fb8e7132535b76cdac458c4d53944eca97e1ecb68e6a8fd853c9cedc3a`.
**License.** MIT per figshare API for article 9765779 (checked). Upstream Zhuo et al. SI license [unverified].
**Hit.** gap >= 4.0 eV: 191 / 4604 = 4.15%. (>=5.0 eV: 80, 1.74%.) 2450 rows are exactly 0 eV (metals).
**Cost.** Needs a composition parser + features (element fractions). Avoid pymatgen if possible; a regex parser for nested formulas like `Ag(AuS)2` is needed [unverified effort]. Budget B = 150.
**Fallback 2.** matbench_steels (same 312 steels, composition string only) from `ml.materialsproject.org/projects/matbench_steels.json.gz`, sha256 prefix 473bc4957b2ea5e6. License of that host [unverified], so prefer figshare steel_strength.
**Links:** [[steel-strength]] · [[replay-oracle]]
