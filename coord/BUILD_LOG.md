# BUILD_LOG (append-only, newest at bottom, entries <= 8 lines)

## 2026-10-03 T001 MERGE REQUEST
branch builder/t001-toy-loop (base 06e1216). Added asd/{schemas,cache,oracle,llm,belief,loop}.py + tests/test_loop.py.
Loop: generate (stub LLM, cached by prompt/model/seed) -> pick -> toy oracle -> analyze -> SQLite belief -> decide. Every stage output jsonschema-validated.
Run: `python -m asd.loop`; tests: `python -m pytest -q` -> 4 passed (e2e round, determinism+cache, budget stop, schema rejection).
Demo seed 0: hit after 5 experiments (stub LLM, no API key). Real LLM path untested (use_real=True + ANTHROPIC_API_KEY).
Spend est: ~$0.4.
2026-10-03 builder/t000-omnigent (base b3b0892): T002 done + T000 offline-verified, live run BLOCKED on model auth.
Added asd/replay.py (sha-verified steel_strength, 312/15 hits, BudgetExceeded, ledger, metric), asd/tools.py (10 function tools + shared research record), asd/policies.py (experiment_budget DENY, human_approval ASK), agents/{hello,planner}.yaml (planner + literature/insight/analysis/safety sub-agents, cost_budget+call_cap built-ins), requirements.txt; T001 carry-overs 1,4,5,6 + fresh-cache determinism test.
Measured: `python -m pytest -q` 21 passed (random-policy mean within 10% of k*313/16; spec loads via omnigent.spec.load; policies DENY/ASK via omnigent shim).
NOT measured: any `omnigent run` with a model (no ANTHROPIC_API_KEY/CLAUDE_CODE_OAUTH_TOKEN). Omnigent server starts fine (/health ok). Sub-agent `tools: inherit` shows empty local_tools at spec level: unverified until a live run. Carry-over 2 (hit on true value): oracle.is_true_hit added, loop.decide still uses noisy y (toy only).
Run (needs key): `omnigent run agents/planner.yaml -p "Run the loop" ` from repo root. Spend ~ $0.5.
