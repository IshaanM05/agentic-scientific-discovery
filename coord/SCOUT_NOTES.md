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
