---
type: concept
status: install verified on Windows 2026-10-03 (omnigent 0.16.0); YAML load verified offline; runtime behaviour unverified (no model run yet)
tags: [omnigent, T000]
---
# Omnigent: install, agent YAML, policies, auth (recon for T000)
Source: github.com/omnigent-ai/omnigent @ 25b9583 (README, docs/AGENT_YAML_SPEC.md, docs/POLICIES.md, source). Parent: [[omnigent]].
## Install (Windows native, verified)
- `uv tool install --python 3.12 omnigent` gives 0.16.0. `omnigent --help` and `omnigent run --help` work. `omni` is an alias.
- The git form `uv tool install ... git+https://github.com/omnigent-ai/omnigent.git` FAILS on Windows: "Filename too long" on test snapshots. Use PyPI, or `git config --global core.longpaths true`.
- Windows is "degraded mode": `omnigent run <yaml>` works with SDK harnesses (claude-sdk, codex, cursor). Not available: tmux wrappers (`omnigent claude`) and bwrap sandboxing (README "Windows (native)").
- The tool venv holds only omnigent's own dependencies (numpy is missing). Add yours with `uv tool install --python 3.12 omnigent --with <pkg>`.
## Python function tool (README "Write your own agent"; spec lines 598-613)
`tools: {score: {type: function, description: ..., callable: asd.tools.score}}`. The schema is built automatically from the signature, or you can give `parameters:` (JSON Schema).
- Callables import from the CWD (cli.py puts the CWD at sys.path[0]), so run from the repo root.
- GOTCHA: an import failure sets callable=None SILENTLY (inner/loader.py `_resolve_callable`). Test that each tool really runs.
## Sub-agents (spec lines 664-696)
`analyst: {type: agent, description, prompt, executor: {harness, model}, tools: {score: inherit}, pass_history: false, max_sessions: 2}`.
Each sub-agent can have its own harness and model.
- Handoff `{type: handoff, target_agent, pass_history, bidirectional}` is parsed (inner/loader.py:565). I found no runtime consumer [unverified; prefer type: agent].
- Sub-agent replies are text. To get structured exchange, have each sub-agent return JSON and pass it through a function tool (e.g. `record_step`) that validates it with jsonschema (asd/schemas.py) and appends it to the research record.
## Policies (docs/POLICIES.md)
- Function interface: `fn(event) -> {"result": "ALLOW"|"DENY"|"ASK", "reason": str, "state_updates": [...]} | None`. `None` means abstain.
- `event` has `type` (request/response/tool_call/tool_result), `target`, `data.name`, `data.arguments`, `context.usage.total_cost_usd`, `session_state`.
- Factory form: use `factory_params:` in the YAML.
- On ASK, the action is parked for user approval and the reason is shown to the user. `ask_timeout` (seconds) is a top-level YAML key. How the REPL shows the approval prompt is [unverified].
- Builtins: `omnigent.policies.builtins.cost.cost_budget` {max_cost_usd, ask_thresholds_usd, expensive_models}, `...safety.max_tool_calls_per_session` {limit}, `...safety.ask_on_os_tools`.
- GOTCHA: at the hard limit, cost_budget DENYs only while the session is on an "expensive" model (by default Opus/GPT-5/Fable). For a true hard stop, pass `expensive_models: []`: in the source (builtins/cost.py ~l.329) that means block_all. Note that docs/POLICIES.md wrongly says [] disables the cap. `["claude"]` also works.
- Custom handlers (e.g. `asd.policies.experiment_budget`) are allowed in local single-user mode. Uploaded bundles must be in `policy_modules`. Policies run in the server process [import path at runtime unverified].
## Auth / model
- harness `claude-sdk` drives the Claude Code CLI. Credentials: `ANTHROPIC_API_KEY`, or `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`), or a logged-in `claude` CLI (auto-detected).
- Explicit form: `auth: {type: api_key, api_key: ${ANTHROPIC_API_KEY}}`. Model ids are plain Anthropic ids (e.g. claude-sonnet-4-6). Databricks ids look like `databricks-claude-sonnet-4-6` with `auth: {type: databricks, profile: ...}`.
- Even a hello-agent needs some model credential.
## Our mapping
Planner (claude-sdk) with sub-agents literature, insight, analysis, safety. Function tools: asd oracle, selector, `record_step`. Policies: cost_budget, a custom experiment-budget gate (oracle reveals <= 60) and a safety ASK on flagged actions. Links: [[safety-gate]] · [[loop-structure]] · [[replay-oracle]]
