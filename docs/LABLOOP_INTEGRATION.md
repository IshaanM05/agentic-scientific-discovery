# LabLoop integration contract (parallel work W1, W2, W3)

Base branch: `integration/labloop` (dev/agentic-loop + labloop-v2 merged, 47 tests pass).
Goal: Omnigent orchestrates LabLoop's simulated perovskite lab as a second test bed, so our agent team runs on unseen worlds that no LLM can have memorised.
Freeze 06:00 ET (15:30 IST) Oct 4. Rules: Sonnet 5.5 / Haiku 4.5 only, cache every LLM call, no AI-tool mention in commits, never touch main, never read .env.

## Branches and file ownership (edit only your files; anything else -> ask the lead)
| Worker | Branch (from integration/labloop) | Owns |
|---|---|---|
| W1 tools + agents | `w1/labloop-tools` | `asd/labloop_tools.py`, `agents/labloop_*.yaml`, `tests/test_labloop_tools.py` |
| W2 results | `w2/labloop-results` | `scripts/ll_*`, `docs/RESULTS_*.md`, README sections "LabLoop test bed" and "LabLoop results" (add only; do not edit other sections) |
| W3 demo + hosting | `w3/labloop-demo` | `dashboard/*`, `docs/index.html`, `dashboard/template.html`, hosting files (`vercel.json`, etc.) |
Shared, read-only for all workers: `labloop/*` (bug fixes only via the lead), `asd/schemas.py`, `asd/policies.py`, `asd/tools.py`.
Each worker: small commits, a BUILD_LOG note on their branch, `python -m pytest -q` green, push the branch, report to the lead. The lead merges after a brief Scout review.

## W1: `asd/labloop_tools.py` (Omnigent function tools)
Omnigent may run each tool call in a fresh process, so ALL state is persisted per run directory.
- Run dir from env, as in `asd/tools.py`: `ASD_RUN_DIR` or `LC_ASD_RUN_DIR` (required), `ASD_RUN_ID`/`LC_ASD_RUN_ID`.
- `notebook.sqlite`: LabLoop `Notebook` (experiments, hypothesis events, decisions).
- `ll_state.json`: `{world, seed, budget, units_used, round, tested_idx[], observations[], measurements{}, discoveries{}, hyps{}, pending_surprises[], rng_state}`. It must be enough to rebuild Surrogate, Arena and agents deterministically in a new process.
- Every call first does `chemistry.set_world(state.world)`; that is global per-process state.
- Every tool appends one entry to `record.jsonl` via the same record writer as `asd/tools.py` (kinds below) and returns JSON-serialisable dicts only.
- NEVER return or log hidden truth: no `eg_true`, `lt_true`, `true_hits`, world parameters or untested measurements. Add a test asserting no tool output contains them.

| Tool | Args | Returns | Record kind |
|---|---|---|---|
| `ll_start` | `world:int, seed:int, budget:float=60` | `{run_id, world, budget, n_candidates, spec}` | `ll_start` |
| `ll_literature` | none | sourced claims plus literature hypotheses (id, region, prediction, kill_condition, citation) | `literature` |
| `ll_arena_round` | `proposals: list[dict]` (from the Omnigent generator sub-agent; may be empty) | validated hypotheses admitted or rejected (reason), critiques, Elo table | `arena_round` |
| `ll_pi_decide` | `rationale: str` (from the Omnigent planner) | `{mode: seed/investigate/exploit/stop, slots:[...], budget_left}`; the mode comes from LabLoop's PIAgent rules, and the planner's text is recorded | `pi_decision` |
| `ll_design` | `slots: list[dict]` | protocols with `slot_id`, composition, purpose, `safety_review` result | `design` |
| `ll_run` | `slot_ids: list[str]` | measured results for those slots only, units charged, `budget_left` | `experiment` (one per film) |
| `ll_analyse` | none | findings, surprises, hypothesis verdict updates (supported / refuted / holds-with-exceptions), prior relaxations | `analysis` |
| `ll_judge` | none | discovery verdicts (replicated?), hypothesis verdicts | `judge_verdict` |
| `ll_status` | none | round, `units_used`, `budget_left`, n_tested, hits found so far, discoveries, open hypotheses | none (read-only) |

Proposer rule: LabLoop's `HypothesisAgent` calls Anthropic directly via urllib (`labloop/llm.py`). In the Omnigent path that call is NOT used. New hypotheses come from an Omnigent sub-agent (`ll_generator`, Sonnet 5.5) whose JSON proposals in LabLoop's region DSL are passed to `ll_arena_round`, which validates them (`_admit`, `region_mask`) and rejects bad ones with a reason. Rule-based fallback hypotheses are allowed only when proposals are empty, and are labelled `source: rule_based`. Every model-written hypothesis is labelled `agent-generated`.

Policies (reuse `asd/policies.py`; add LabLoop-specific ones only inside `asd/labloop_tools.py` if needed):
- the budget is counted in LabLoop units (one film costs 1-1.5): `ll_run` DENY past budget;
- `safety_gate` and LabLoop's `safety_review` both apply before `ll_run`; restricted elements or scale-up give ASK (human approval).

Agents (`agents/labloop_planner.yaml`): a planner (Sonnet 5.5) supervising `ll_literature_agent` (Haiku), `ll_generator` (Sonnet), `ll_critic` (Haiku), `ll_analyst` (Sonnet), `ll_judge` (Haiku) and `ll_safety` (Haiku). Tools are declared explicitly per sub-agent, with no candidate ids or world parameters in prompts. Loop: literature -> arena -> pi_decide -> design (>= 2 candidate slots with reasons) -> safety -> run -> analyse -> judge -> ADAPT (log it when an analysis refutes a hypothesis or relaxes a prior) -> repeat until stop or budget.
Tests (offline, no model): a fresh-process round trip (state saved, reloaded and identical); `ll_*` over one full round with a stub proposer; a no-leak test; budget DENY; determinism per (world, seed).

## W2: results (offline first; no live model needed)
- `scripts/ll_benchmark.py`: rerun his benchmark (`labloop.benchmark.run_benchmark`, unseen worlds 1000-1019, 20 seeds, budget 60) and verify the README table in `docs/LABLOOP_README.md`. Report any mismatch; do not copy his numbers without rerunning.
- `scripts/ll_compare.py`: on golden worlds 2000, 2001 and 2002 (never used in his benchmark), compare the rule-based LabLoop scientist with the Omnigent run records (read `runs/ll-*/record.jsonl` produced by the lead's live runs). Metrics: hits by budget, units to first hit, discoveries replicated, hypotheses refuted, and ADAPT events.
- `docs/RESULTS_LABLOOP.md` plus README sections with honest caveats: the simulator was designed by the team; worlds are synthetic; the rule-based scientist is the baseline; n is small for the Omnigent runs.

## W3: demo + hosting
- Keep `streamlit run dashboard/app.py` working. Add a LabLoop tab that reads `runs/ll-*` (offline replay).
- `docs/index.html` (his static demo): add our headline and a LabLoop Omnigent-run panel from committed JSON. It must stay self-contained and offline.
- Hosting: `vercel.json` serving `docs/` as static (no build), so the live demo URL is `docs/index.html`. Document the steps in README "Live demo". The human performs the deploy.

## Lead (step 3)
After each branch is pushed: Scout review (Sonnet, brief) -> merge into `integration/labloop` -> tests -> local live Omnigent tests with the subscription token -> golden end-to-end runs on worlds 2000-2002 (`runs/ll-w2000` etc.) -> W2's compare script -> README and demo script update.

## RUNBOOK (W1): live Omnigent test of LabLoop, run locally by the lead
Not run in the cloud (no model credentials). Offline check first: `python -m pytest tests/test_labloop_tools.py -q` (needs Python 3.12 + `pip install -r requirements.txt` for the omnigent loader test).
1. `scripts/live.ps1` already sets PYTHONPATH (needed so `asd` and `labloop` import in tool processes), the env passthrough, the LC_ASD_* mirror and a fresh local server. Set only the run dir and id: `$env:ASD_RUN_DIR="runs/ll-w2000"; $env:ASD_RUN_ID="ll-w2000"` (ASD_SEED/ASD_BUDGET are ignored here; `ll_start` takes world, seed, budget).
2. Run: `powershell -File scripts/live.ps1 agents/labloop_planner.yaml "Call ll_start(world=2000, seed=0, budget=60) and run the full LabLoop loop to stop or budget. Follow your prompt."` (add `-Interactive` to answer policy ASKs y/n).
3. Do not run from a shell where ASD_RUN_DIR points at an existing steel run: the steel tools and LabLoop tools use different files, but keep dirs separate (`runs/ll-*`).
4. Watch `runs/ll-w2000/record.jsonl` (kinds: ll_start, literature, arena_round, pi_decision, design, experiment, analysis, judge_verdict). Look for "ADAPT:" lines, rejected proposals with reasons, and `human-approval ASK` prompts (approve or deny in the Omnigent UI).
5. Repeat with a fresh dir for worlds 2001 and 2002 (never reuse a run dir; `ll_start` refuses a different world or seed in an existing dir).
6. If a sub-agent says it lacks a tool, tools are declared per sub-agent in the YAML (inherit does not work); fix the YAML, not the prompt.
7. Check no leaks: `grep -E "eg_true|lt_true|true_hit" runs/ll-w2000/*` must print nothing.
8. Cost caps: policy `cost_budget` (USD 8 hard, ask at 5), `ll_budget` (60 units), `call_cap` (500 calls). Raise only with the lead's approval.
9. Records are the evidence: do not edit them; W2's `scripts/ll_compare.py` reads `runs/ll-*/record.jsonl`.
10. Caveat to repeat in every write-up: LabLoop is a team-built simulator with synthetic hidden physics (benchmark, not real devices); n of live runs is small.
