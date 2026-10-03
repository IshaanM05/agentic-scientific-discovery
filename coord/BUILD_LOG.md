# BUILD_LOG (append-only, newest at bottom, entries <= 8 lines)

## 2026-10-03 T001 MERGE REQUEST
branch builder/t001-toy-loop (base 06e1216). Added asd/{schemas,cache,oracle,llm,belief,loop}.py + tests/test_loop.py.
Loop: generate (stub LLM, cached by prompt/model/seed) -> pick -> toy oracle -> analyze -> SQLite belief -> decide. Every stage output jsonschema-validated.
Run: `python -m asd.loop`; tests: `python -m pytest -q` -> 4 passed (e2e round, determinism+cache, budget stop, schema rejection).
Demo seed 0: hit after 5 experiments (stub LLM, no API key). Real LLM path untested (use_real=True + ANTHROPIC_API_KEY).
Spend est: ~$0.4.
