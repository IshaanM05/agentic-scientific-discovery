# Official Challenge 3 Brief (Databricks x Hack-Nation) - AUTHORITATIVE
Source: the organizers' problem statement PDF (`file.pdf`, 4 pages). Where this conflicts with earlier notes (`HACKATHON_BRIEF.md`, `REFERENCES.md`, teammate chat), this file wins.

## The big change: Omnigent is mandatory
- **"Mandatory for every submission: build with Omnigent."** Omnigent must **orchestrate the live discovery workflow**: multiple specialist agents exchanging outputs, using tools, and **adapting their plan after an experimental result**.
- Omnigent is Databricks' open-source meta-harness (Apache 2.0, alpha): github.com/omnigent-ai/omnigent, docs at omnigent.ai, PyPI `omnigent` (Python >= 3.12). Agents are **YAML files** (prompt, executor = harness + model + auth, tools = Python functions / MCP servers / sub-agents / handoffs, **policies** = guardrails such as cost budgets and permissions). Run with `omnigent run path/to/agent.yaml`.
- Install (from the README): `uv tool install -q --python 3.12 git+https://github.com/omnigent-ai/omnigent.git` (add the `databricks` extra only if using a Databricks workspace for models). Windows-native install has its own section in the README. Managed option: Databricks workspace -> `<workspace-url>/omnigent` -> New session -> Sandbox.
- Our hand-written Python loop is NOT enough. It must be re-expressed as Omnigent agents, or wrapped so Omnigent runs it: each specialist is an Omnigent agent/sub-agent, the oracle and Bayesian-optimization selector are Python function tools, and budget/safety are Omnigent **policies**.

## Scoring (weights)
| 30% | Omnigent orchestration (purposeful specialist collaboration, handoffs, tools, policies, adapting after a result) |
| 25% | Breakthrough potential (ambitious question, meaningful reproducible result) |
| 20% | Discovery acceleration and learning (a named bottleneck, a measured improvement, a justified next experiment) |
| 15% | Scientific rigor (citations, run records, labeled agent-generated hypotheses, uncertainty, controls) |
| 10% | Creativity and responsibility (human approval gates, safety agent, validation still needed) |

## What to build
- Free choice of domain. Pick **one specific scientific question** testable in 24 h with existing datasets, literature, APIs, simulations or generated data. Wet lab is not expected.
- One complete loop: **Question -> Evidence -> Hypothesis -> Experiment -> Result -> Updated decision.**
- Design **at least two possible tests**, choose one by expected learning, feasibility and cost (planner has a budget), run it, interpret it, and let the result change the next step. Parallel searches/experiments; surprising results reopen earlier assumptions.
- Suggested roles (adapt freely): Literature, Insight (hypotheses), Experiment planner, Experiment runner, Analysis, Knowledge graph, plus a **Safety agent** that flags risk and routes decisions for **human approval**, enforced via tool permissions and Omnigent policies.
- Structured handoffs: each agent owns a decision, has declared tools, inputs and output. Pass structured evidence, candidate IDs, experiment specs and results. Keep a **shared research record** so every decision is reconstructible.
- What counts as an experiment: simulation, computational screening, benchmark evaluation, model comparison, analysis of an existing dataset, sensitivity or counterfactual analysis, experiment on data you generate. A **baseline vs proposed method under matched conditions** is the model pattern shown in the brief.
- Suggested sources: OpenAlex, Europe PMC, PubChem, Materials Project, NIST JARVIS, arXiv, OpenML. Check keys, licenses and compute early.

## "10x faster" is not required
Identify **one bottleneck**, define what "faster" means (more candidates screened in the same budget, fewer downstream tests, shorter literature-to-hypothesis path, hypotheses evaluated in parallel, less human effort, faster evidence-to-decision), and **report the improvement you actually observe** (1.5x, 3x, 5x or 10x). Evidence strength matters more than the multiplier. Explain what would be needed to approach 10x at scale.

## Required rigor and responsibility
Citations for factual claims; attach source evidence or run records; label agent-generated hypotheses; preserve uncertainty; document controls and human approval gates; state the validation still needed before real-world use.

## Suggested time split (24 h)
First 4 h: domain, question, measurable outcome, data and tools, run a meaningful test and use it to change the next decision. Next 14 h: build the Omnigent workflow, generate hypotheses/candidates, select experiments, get one full loop running with a result that changes the next decision. Final 6 h: strengthen the experiment, analyze, prepare a **two-minute demo**.

## Submission contents
Repository; **agent specifications and policies**; **two-minute demo**; cited evidence; experiment code and results; measured improvement; the next experiment. (Plus the earlier checklist in HACKATHON_BRIEF.md: three videos, public repo, live demo, upload to app.hack-nation.ai and the Google form.)

## Time check
At 18:31 GMT on Oct 3 (14:31 ET), about 18.5 hours remained to the Sun Oct 4 9:00 AM ET deadline.
