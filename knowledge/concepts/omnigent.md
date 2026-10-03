---
type: concept
status: verified-from-readme
---
# Omnigent (MANDATORY orchestration layer, 30% of score)
Open-source meta-harness by Databricks (github.com/omnigent-ai/omnigent, Apache 2.0, alpha). Agents are YAML: prompt, executor (harness + model + auth), tools (Python functions, MCP servers, sub-agents, handoffs), policies (guardrails, cost budgets, permissions). `omnigent run agent.yaml`.
**Our mapping:** PI/planner agent supervises sub-agents literature, insight (hypotheses), analysis, safety; oracle and BO selector are Python function tools; budget and safety approval are policies.
Full official requirements: docs/CHALLENGE_BRIEF.md. Related: [[loop-structure]], [[safety-gate]], [[hypothesis-arena]], [[llm-guided-bo]].
