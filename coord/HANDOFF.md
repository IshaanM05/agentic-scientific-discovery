# HANDOFF (overwrite each cycle; keep <= 40 lines)
updated: 2026-10-04 ~11:40 IST by lead (stopped early: Pro quota). Freeze 15:30 IST, deadline 18:30 IST.
## Branches
- integration/labloop (pushed): dev/agentic-loop + labloop-v2 + merged, re-authored to IshaanM05: W1 tools/planner, W3 demo/hosting, W2 results, W4 multifidelity (code only), W6 pitch, W7 claims audit, W8 knowledge graph; Scout notes merged. Fixes: safety prompt (Pb/Sn level 2 approved), cost cap 20 USD (ask 15), parsers match live schema, W6/W8 Scout fixes, Olympus/Atlas/Rainbow refs, LabLoop README memory + medians/means.
- dev/agentic-loop (658d5aa) and main (214aac5) untouched. Remote w1..w8 branches still exist (author "Claude"); do not delete without the human's OK.
## Tests (Python 3.12 venv with omnigent 0.16.0)
- 92 pass, 1 fails: tests/test_check_claims.py::test_real_claims_match_committed_results (demo-script claim texts changed). Fix by re-running scripts/check_claims.py after the final README/demo edits; if still red at 15:15 IST, delete that single test.
## Live runs
- runs/ll-smoke2000 (world 2000, budget 8): complete. 6 sub-agents live, >=2 designs per decision, ADAPT 1, 5 films, 2 unique true hits (first at 1.5 units), no policy fired (nothing hazardous).
- runs/ll-w2000 (world 2000, budget 60): PARTIAL, stopped by the lead at quota: 16 films, 23.5/60 units, 40 records. Label it partial; not a finished 60-unit run.
- Leak check (eg_true|lt_true|true_hit) on both: clean.
## NOT done
- Worlds 2001 and 2002 (and a full 60-unit world 2000): to be run by a teammate with the RUNBOOK in docs/LABLOOP_INTEGRATION.md (fresh dirs runs/ll-w2001 etc.; never reuse a dir). Omnigent tool venv needs: uv tool install --force --python 3.12 omnigent==0.16.0 --with jsonschema --with pyyaml --with numpy --with scipy --with scikit-learn.
- Cloud worker: ll_compare, dashboard rebuild (scripts/build_dashboard.py), make_kg, [TO FILL] markers, README test count, claims checker last.
- W4 bonus mf run: skipped. W5/W9/W10: not merged.
- Team names/roles: placeholders for the humans.
- Human: live demo deploy (vercel.json / docs/DEPLOY.md), 3 videos, submission form, Discord, OK to merge into main.
## Gotchas
- Never read/print .env; live.ps1 loads it. Headless (-p) runs decline ASKs; -Interactive holds them.
