# SCOUT_NOTES (append-only, newest at bottom, entries <= 8 lines)
2026-10-03 scout cycle 1: answered T002 open question.
- Dataset: steel_strength, figshare 10.6084/m9.figshare.7250453 file 13354691; license MIT via figshare API (opened); sha256 matches matminer metadata.
- Hit: yield strength >= 2000 MPa -> 15/312 (4.8%). Fallback expt_gap figshare 9765779 (MIT), gap >= 4 eV -> 191/4604.
- Budget: 1 reveal = 1 experiment, B = 60, repeats free; LLM cost logged separately. Leakage: hide tensile/elongation.
- [unverified]: upstream Citrine licence, composition units, LLM memorisation of this public set.
- Notes: knowledge/datasets/{steel-strength,expt-gap}.md, ADR-001 on scout/t002-dataset @ 40b24f9. T002 ticket refined in BACKLOG.
2026-10-03 REVIEW T001 builder/t001-toy-loop @ f3236af: APPROVE (accept criteria met: round runs, every stage schema-validated).
- Reproduced: pytest 4 passed; `python -m asd.loop` seed 0 hit at experiment 5; seeds 0-9 fresh caches: 9/10 hit within 10. No secrets, loop never reads oracle.x_star.
- Non-blocking, fix in T002: (1) add requirements.txt (jsonschema, pytest) for clean clone; (2) hit judged on noisy y, must use true value per ADR-001;
  (3) test_deterministic shares one cache dir, so run 2 is pure cache read: use two dirs; (4) oracle has no hard budget guard (add BudgetExceeded);
  (5) real-LLM guesses not range-checked (add min/max 0..1 to schema); (6) duplicate __pycache__ in .gitignore.
- Toy-only caveat: analyze() compares y to a constant 0.9, so "supported" is not a real falsification test; do not cite as such.
Scout spend this cycle est ~$1.2.
