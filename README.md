# agentic-scientific-discovery
Hack-Nation 7th Global AI Hackathon - Challenge 3: Agentic Scientific Discovery (multi-agent AI lab)

Omnigent orchestrates the live workflow: `agents/planner.yaml` is a PI/planner supervising literature, insight, analysis and
safety sub-agents. The oracle, selector, hypothesis registry and research record are Python function tools (`asd/tools.py`);
the experiment budget and human approval are Omnigent policies (`asd/policies.py`, plus built-in `cost_budget`).
Test bed: `steel_strength` (312 steels, MIT, figshare 10.6084/m9.figshare.7250453; hit = yield strength >= 2000 MPa, 15 hits).

## Windows install (verified, omnigent 0.16.0)
```
uv tool install --python 3.12 omnigent --with jsonschema --with pyyaml    # PyPI; the git+https form fails on Windows (MAX_PATH)
pip install -r requirements.txt                                            # tests: Python >= 3.12
```
Add any other non-stdlib import used by a tool with another `--with`. Run `omnigent` from the repo root (the CWD is put on sys.path).
Windows is "degraded mode": SDK harnesses (`claude-sdk`) work; tmux wrappers and bwrap do not.
**Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`** (otherwise the host tunnel dies on a charmap error and `omnigent run` times out).
Auto-spawn of the local server can time out; `scripts/live.ps1` starts it with `omnigent server --background` and runs with `--server local`.

## Auth
`claude-sdk` reads `CLAUDE_CODE_OAUTH_TOKEN` (or `ANTHROPIC_API_KEY`) from the environment; never put it in YAML. Put it in a gitignored
`.env`; `scripts/live.ps1` loads it into the process only. Models are pinned in every executor (Sonnet 5.5 planner/insight/analysis,
Haiku 4.5 literature/safety). `agents/hello.yaml` pins Haiku too.

## Run
```
python -m pytest -q                         # 25 tests, no model needed
python scripts/demo_policies.py             # model-free: budget DENY + approval ASK
powershell -File scripts/live.ps1 agents/hello.yaml "go"                 # one real model call + one asd tool
powershell -File scripts/live.ps1 agents/planner.yaml "Run one loop ..." # full workflow (live; spends tokens)
powershell -File scripts/live.ps1 agents/policy_demo.yaml "go"           # live DENY + ASK
```
Run records: `runs/<name>/record.jsonl` (shared research record, one `rec-NNNN` id per decision), `ledger.jsonl` (experiment ledger),
`session.jsonl` (Omnigent session export), `transcript.txt`. Tool state is rebuilt from these files on every call because Omnigent
may run each agent session's tools in a different process. Output location is `runs/default` (ASD_* env vars do not reach tool processes).

## Omnigent notes (0.16.0)
- Single-file YAML: no `spec_version`, executor is flat (`executor: {harness, model}`).
- `tools: {x: inherit}` does NOT give sub-agents the parent's function tools in a live run: declare tools explicitly inside each sub-agent.
- cost_budget hard stop needs `expensive_models: []`.
- A policy ASK in a headless `-p` run parks the call and the run exits (an `approval` event is posted); approve in the web UI session.
