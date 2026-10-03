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
2026-10-03 15:30 scout cycle 2: T000 Omnigent recon (details: knowledge/concepts/omnigent-yaml.md on scout/t000-omnigent-recon).
- INSTALL OK: `uv tool install --python 3.12 omnigent` -> 0.16.0, `omnigent --help` works. git+https install FAILS on Windows (Filename too long); use PyPI.
- Tool: `{type: function, callable: asd.x.fn}`, run from repo root (CWD on sys.path). Import failure -> callable silently None: assert tools execute. Add non-stdlib deps via `--with`.
- Sub-agent: `{type: agent, prompt, executor, tools: {t: inherit}}`. `type: handoff` parsed but no runtime consumer found [unverified]; use sub-agents + a jsonschema-validating `record_step` tool for structured exchange.
- Policy fn: event -> {result: ALLOW|DENY|ASK, reason}; ASK parks for human approval. cost_budget hard cap only DENYs "expensive" models (default opus/gpt-5): pass expensive_models: [] for a true hard stop (source cost.py block_all; POLICIES.md says the opposite).
- Auth: claude-sdk needs ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN or logged-in claude CLI. No model run done (lead hold pending credential choice).
- Verified offline: a scratch YAML with function tool + sub-agent + cost_budget + custom policy loads via omnigent.spec.load.
2026-10-03 15:50 scout: steel_strength facts (knowledge/datasets/steel-strength.md on scout branch).
- Units VERIFIED (matminer dataset_metadata.json): composition wt%, yield/tensile MPa, elongation %. Extra `formula` column = derived from composition, not leakage.
- Upstream Citrine 153092 license still [unverified]: Citrination is gone and the Wayback snapshot is a JS stub. Rely on the figshare MIT grant + cite Citrine.
- Memorisation risk HIGH: the same 312 rows as Matbench matbench_steels. New ticket T009 (recall probe + anonymised-feature arm).
2026-10-03 16:05 PRE-REVIEW builder/t000-omnigent @ 7c3fdfa (no merge note yet, so no verdict). T002 part looks sound.
- Reproduced: pytest 21 passed on a clean export. asd.hello_tool + asd.replay import and run inside the omnigent uv-tool venv from repo root (jsonschema present).
- OK: sha256 check, features() hides targets, ids shuffled per seed, repeat reveal free, ledger, censoring at B+1, ToyOracle true-hit + budget guard, schema range.
- For T000 verdict I will require: (1) budget gate as an Omnigent policy (custom tool_call DENY past 60 reveals; demo shows a DENY), not only BudgetExceeded in Python;
  (2) safety ASK policy that actually fires in a logged run; (3) sub-agent outputs pass a jsonschema-validating tool (HYP_REC/TESTS/ANALYSIS_R) with a failing-payload test;
  (4) a test asserting every YAML callable resolves (loader silently nulls failed imports); (5) no tool exposes ReplayOracle._rows or the yield of unrevealed ids.
- Nits: LIT_OUT.citations lacks minItems 1; numpy in requirements is unused so far; hello.yaml has no model and relies on the configured default (state that in the README).
2026-10-04 REVIEW builder/t000-omnigent @ 0b125ac: APPROVE merge into dev/agentic-loop. T000 is NOT done until F1-F3 are fixed.
- Reproduced: pytest 25 passed (clean export). runs/live2 is real delegation: sys_session_send to literature/insight/analysis/safety, inbox results, 4 record_step handoffs, 2 labeled+cited hypotheses, design_tests chose by score, 2 assumptions reopened. policy_demo: c002 "Denied by policy: experiment budget 2 exhausted" and ledger stops at 2. Real. Secret scan of runs/ scripts/ agents/ asd/: clean. live.ps1 reads .env into the process only and prints nothing. .env is gitignored.
- Conditions: (1) DENY met. (3) record_step met. (4) callable test met. (5) leak test met. (2) ASK only minimally met: one runner-log approval event, no visible approval or outcome.
- F1 (MUST, before any eval or multi-seed run): ASD_* never reach the tool processes, so every live run uses seed 0 and runs/default, and _sync replays any old ledger there, which carries spent budget across runs. Fix: in live.ps1 set OMNIGENT_RUNNER_ENV_PASSTHROUGH=ASD_SEED,ASD_BUDGET,ASD_RUN_DIR (host/connect.py:768) [untested], and add a run_id guard. A tool must refuse a run_dir whose ledger belongs to another run. Prove it with 2 live runs on different seeds and dirs.
- F2 (MUST, before demo): one live planner run that (a) changes its next experiment after an analysis result (live2 ran all 5 experiments before any analysis, so nothing adapted) and (b) shows the ASK approval card plus the human's decision in the transcript or record.
- F3 (honesty): c272 hit at experiment 1 is not evidence of acceleration. The cold-start farthest-point selector proposed it and the LLM picked it, and it is a textbook maraging composition. No speedup claim until T003 baselines plus T009 memorisation control at matched budget 60 over >=5 seeds. README and BUILD_LOG currently make no such claim: keep it so.
- Nits: policy counts attempts, not reveals (repeat reveals use up the policy budget). n-based record ids can collide if sub-agents write concurrently (add a file lock or uuid). Scout review spend ~$0.5.
2026-10-04 19:20 ET scout cycle 4: T009 designed, T012 audited (scout/t009-memorization). See knowledge/concepts/memorization-control.md.
- T009: 20-row recall probe (15 hits + 5), P1 generic / P2 guided / P3 blinded vs LOO kNN. Recall flag = near-exact >= 3/20, or P2 < 0.5x kNN MAE, or P2 < 0.8x P1 MAE (Golchin & Surdeanu, arXiv 2308.08493, opened). Blind arm: f01..f13, permuted, min-max scaled, same B=60, seeds 0-4. A claim needs >= 4/5 paired seeds, no flag and G_blind >= 0.5 G_named.
- T012 AUDIT: grep of README.md, coord/BUILD_LOG.md, agents/, scripts/, asd/ and runs/live2 finds NO speedup/acceleration/outperform claim. BUILD_LOG states the c272 memorisation caveat. PASS. No demo text exists yet, so re-audit at freeze.
- LEAK (MUST before T003/T009 runs): agents/planner.yaml:30 uses example `"candidate_id": "c272"`. At seed 0, c272 is the 2411.5 MPa hit (live2). The prompt names a hit id, and live2's first pick may be prompt-primed (fc32368 added the example and the artifacts in one commit, so the order is unknown). Replace it with "c###" and treat live2's experiment-1 hit as tainted.
- builder/t010-run-config: no commits or merge note yet. No verdict. Review conditions: two runs with distinct ASD_SEED+run dir and differing ledgers/id maps; run-id guard test; T011 record shows analysis -> changed next pick + ASK card + human decision; T003 same B, seeds, pool and init for all arms.
- PRE-REVIEW builder/t010-run-config @ f46ab36 (code only, no merge note, no live runs, so no verdict): the guard design is sound. meta.json binds (run_id, seed, budget), an unowned ledger is refused, ASD_RUN_DIR is required (no runs/default fallback), and live.ps1 sets PASSTHROUGH before the server restarts. Still owed: the 2 live runs (seeds differ, dirs differ, meta.json differs, ledger ids differ) and proof that the passthrough reaches the tool processes (tool-side echo of ASD_SEED in record).
- coord/ edits are committed on this branch (sandbox blocks main-checkout writes). The lead should port them. Spend ~$0.6.
