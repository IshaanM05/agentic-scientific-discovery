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
may run each agent session's tools in a different process. Run config (ASD_SEED, ASD_BUDGET, ASD_RUN_DIR, ASD_RUN_ID) reaches tool processes via LC_ASD_* (the host daemon strips other env names; LC_ is allow-listed). Each run dir is bound to its run id by `meta.json`; a tool refuses a foreign ledger and refuses to start without ASD_RUN_DIR.

## Omnigent notes (0.16.0)
- Single-file YAML: no `spec_version`, executor is flat (`executor: {harness, model}`).
- `tools: {x: inherit}` does NOT give sub-agents the parent's function tools in a live run: declare tools explicitly inside each sub-agent.
- cost_budget hard stop needs `expensive_models: []`.
- A policy ASK in a headless `-p` run parks the call and the run exits (an `approval` event is posted); approve in the web UI session.

## Human approval (policy ASK)
In an interactive run the approval policy held the tool call until a human answered (runs/t011-repl, about 1.6 s); non-interactive -p runs decline automatically (fail-closed).
Evidence: `runs/t011-repl/APPROVAL_EVIDENCE.md` (interactive REPL run; the browser's resolve arrived first, so a hold lasting until a human answers is not yet proven) and `runs/t011-ask` (non-interactive `-p` run: the first ASK was declined automatically, Omnigent server log line 170; the second call was resolved by the web-UI connection 1 ms after the approval event with no visible card, after the human typed "approve" in chat; human decision recorded as `rec-0004`).
The budget DENY policy is the enforced one.

## T009 memorisation control + T005 LLM-prior acquisition (steel_strength, B=60, seeds 0-4, n=5)
Probe (runs/t009/probe.json, 20 fixed rows, Sonnet 5.5 via cached CLI calls, default sampling): MAE MPa P1 generic 254.9 (near-exact 2/20),
P2 guided 188.7 (near-exact 3/20), P3 blinded 1573 (0/20), LOO kNN-5 104.3 (near-exact 6/20), train mean 719. Spearman P1 0.73, P2 0.71, kNN 0.73.
**Recall flag: SET** (near-exact(P2) 3 >= 3, and MAE(P2) 188.7 < 0.8 x MAE(P1) 254.9 = 203.9; MAE(P2) is NOT < 0.5 x kNN).
Arms (same pool, seeds, init design, budget as T003; LLM = static per-candidate prior from Sonnet 5.5, 5 revealed init rows in context; see asd/llm_prior.py):
hits@60 per seed 0-4: random(500-seed mean) 2.95 | OFAT [6,7,7,7,6] 6.6 | BO [8,3,5,8,5] 5.8 | named llm_bo [8,10,7,9,7] 8.2 | blind llm_bo [8,10,8,6,10] 8.4 |
named llm_greedy [15,13,11,14,13] 13.2 | blind llm_greedy [0,15,6,14,6] 8.2. Mean experiments to 1/3/5 hits: random500 18.2/46.8/59.0, OFAT 18.0/29.2/40.6,
BO 27.6/35.6/55.2, named llm_bo 6.0/9.6/30.6, blind llm_bo 15.4/21.6/28.8. G_named = 1.6 (4/5 paired wins vs best baseline OFAT, 1 tie), G_blind = 1.8 (4/5 wins).
**Verdict by the pre-registered rule: recall flag set => NO acceleration claim.** The measured advantage is "consistent with memorisation of a public benchmark
or named-domain prior". Caveat for the reader: the blinded arm (no names, permuted, scaled features) kept the llm_bo advantage (G_blind >= 0.5 G_named) but its
greedy variant is erratic (0 hits in one seed), so we cannot separate recall from legitimate metallurgy priors with n=5. Not shown: that the agent "learns faster".
