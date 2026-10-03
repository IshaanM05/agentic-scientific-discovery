# agentic-scientific-discovery
Hack-Nation 7th Global AI Hackathon - Challenge 3: Agentic Scientific Discovery (multi-agent AI lab)

## Question
Can an agent team choose which experiments to run next so that it finds high-value candidates in fewer experiments than standard baselines, under a hard experiment budget and human approval for risky actions?
Test bed: `steel_strength` (312 steels, MIT, figshare 10.6084/m9.figshare.7250453; hit = yield strength >= 2000 MPa, 15 hits), replayed as an oracle that reveals one yield value per experiment.

## Bottleneck
Experiments (here: oracle reveals) are the scarce resource. The measured quantity is hits within a budget B=60 and experiments to the k-th hit (k=1,3,5), against random, one-factor-at-a-time (OFAT) and Gaussian-process Bayesian optimisation (BO) at matched budget, pool, seeds and initial design (5 fixed rows).

## Result
On steel_strength (Matbench steels, public since 2018), B=60, seeds 0-4, a static Sonnet 5.5 prior over all candidates raised mean hits@60 from 6.6 (OFAT, best non-LLM baseline) to 8.2 (prior + GP) and 13.2 (prior-only ranking) with named features. By our pre-registered rule this is NOT an acceleration claim: the memorisation probe's flag is set (guided prompt MAE 189 vs generic 255 MPa; 3/20 near-exact), so the advantage is consistent with memorisation of a public benchmark or a named-domain prior. The probe is weak evidence either way (n=20, default sampling, 15/20 probe rows cluster near 2400 MPa), so we cannot rule out or confirm recall. A blinded view (permuted, scaled, unnamed features) kept the prior+GP gain (8.4) but not the prior-only gain (8.2, one seed with 0 hits), and named first picks hit 5/5 vs blind 2/5. n=5 seeds; no significance claimed; the agent is not shown to learn faster.

Extended blind run (seeds 0-19, `scripts/t009_blind20.py`): blind llm_bo mean hits@60 is 8.75 vs OFAT 6.40 (19 wins/0 ties/1 loss, mean paired difference +2.35, bootstrap 95% CI [+1.75, +3.00], sign test p<0.001) and vs BO 6.85 (15/3/2, +1.90, CI [+0.90, +2.95], p=0.002); the memorisation flag remains set, so this is not an acceleration claim.

![headline](docs/headline.png)
`docs/headline.png`: hits vs experiments used and experiments to the k-th hit (k=1,3,5), with IQR bands. random n=500 seeds, OFAT/BO/blind llm_bo n=20 seeds; the named-feature arm is n=5 with the memorisation flag set.

**Deviation: temperature.** The protocol specified temperature 0. The LLM calls went through the logged-in `claude` CLI, which cannot set temperature, so all probe and prior calls use default sampling with one cached sample per (prompt, model, seed). This adds sampling noise to the probe (P1 vs P2) and to every LLM arm. Other disclosed deviations: static per-candidate prior (not re-queried), no literature arm in the evaluation.

## Agents, specs and policies
Omnigent orchestrates the live workflow. `agents/planner.yaml` is a PI/planner supervising literature, insight, analysis and safety sub-agents (Sonnet 5.5 planner/insight/analysis, Haiku 4.5 literature/safety; models pinned in each executor). Other specs: `agents/hello.yaml` (smoke test), `agents/policy_demo.yaml` (live budget DENY + approval ASK), `agents/single_llm.yaml` (single-agent comparison, n=1, not a result).
The oracle, selector, hypothesis registry and research record are Python function tools (`asd/tools.py`); sub-agent outputs pass a jsonschema-validating `record_step` tool. Policies in `asd/policies.py`: `experiment_budget(limit=60)` DENYs reveals past the budget (attempts counted), and `human_approval(ask_after=30)` ASKs before validation recommendations; plus built-in `cost_budget` (hard stop needs `expensive_models: []`).

## Human approval (policy ASK)
In an interactive run the approval policy holds the tool call until a human answers: in runs/t011-repl30 the call was held 22.2 s, with no automatic resolve, until the human clicked Approve. Non-interactive -p runs decline automatically (fail-closed).
Earlier evidence: `runs/t011-repl/APPROVAL_EVIDENCE.md` (the browser's resolve arrived first, 1.6 s) and `runs/t011-ask` (non-interactive `-p` run: the first ASK was declined automatically, Omnigent server log line 170; human decision recorded as `rec-0004`).
The budget DENY policy is the enforced one.

## How to run from a clean clone (Windows, omnigent 0.16.0)
```
uv tool install --python 3.12 omnigent --with jsonschema --with pyyaml    # PyPI; the git+https form fails on Windows (MAX_PATH)
pip install -r requirements.txt                                            # Python >= 3.12; add matplotlib for the plot
python -m pytest -q                                                        # offline tests, no model needed
python scripts/demo_policies.py                                            # model-free: budget DENY + approval ASK
python scripts/run_baselines.py 20                                         # random/OFAT/BO, seeds 0-19 -> runs/t003 (offline)
python scripts/plot_headline.py                                            # -> docs/headline.png (needs cached runs/t009)
python scripts/t009_blind20.py                                             # blind llm_bo 0-19 + paired stats (cached; new calls spend tokens)
```
Live runs (spend model tokens; auth below):
```
powershell -ExecutionPolicy Bypass -File scripts/live.ps1 agents/hello.yaml "go"
powershell -ExecutionPolicy Bypass -File scripts/live.ps1 agents/planner.yaml "Run one loop ..."
powershell -ExecutionPolicy Bypass -File scripts/live.ps1 agents/policy_demo.yaml "go" -Interactive
```
`-Interactive` omits `-p` and starts the REPL so a policy ASK waits for a human `y/n` (do not attach a `-p` client and a browser at once: the `-p` client auto-declines).
Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` (live.ps1 does). Auto-spawn of the local server can time out on Windows; live.ps1 starts it with `omnigent server --background` and uses `--server local`.
Auth: `claude-sdk` reads `CLAUDE_CODE_OAUTH_TOKEN` (or `ANTHROPIC_API_KEY`) from a gitignored `.env`, loaded into the process only; never put it in YAML or git.
Run records: `runs/<name>/record.jsonl`, `ledger.jsonl`, `meta.json` (binds run id, seed, budget), `session.jsonl`, `transcript.txt`. Run config (ASD_SEED, ASD_BUDGET, ASD_RUN_DIR, ASD_RUN_ID) reaches tool processes via LC_ASD_*; a tool refuses a foreign ledger.
Omnigent notes: single-file YAML, flat `executor: {harness, model}`; `tools: {x: inherit}` does NOT give sub-agents the parent's function tools in a live run, so declare tools explicitly inside each sub-agent.

## Limitations
- steel_strength is a public benchmark (same 312 rows as Matbench steels): LLM arms may recall values; the memorisation flag is set, so no acceleration claim.
- Replay oracle over a fixed 312-row pool with 15 hits; not a real lab. Prior is static and the literature arm is not evaluated.
- Default sampling (no temperature 0); the 20-row probe is weak evidence. Named arms n=5; blind arm n=20; random n=500.
- Single live planner runs (seed 0 etc.) are demonstrations, not evidence of speedup; the single-LLM run is n=1.
- Human approval proven in one interactive run; headless runs decline ASKs.

## Validation needed before real use
Re-run on a dataset the model cannot have seen (post-cutoff or private); temperature-0 or multi-sample probes; larger probe set; more seeds for named arms; a real or higher-fidelity oracle; domain-expert review of recommendations and safety constraints; independent replication of the approval-hold test.
