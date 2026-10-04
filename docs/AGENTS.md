## Agent specifications

Every agent owns one scientific decision, has an explicit tool allowlist and exchanges typed payloads
(`plainsboro/schemas.py`). The Omnigent bundle (`omnigent/princeton_plainsboro/`) declares the same agents as
Omnigent sub-agents. The tools available to each agent's directory are its permission boundary.

| Agent | Decision it owns | Tools (Omnigent) | Inputs → Output | Cannot |
|---|---|---|---|---|
| **House** (root) | Bold, non-obvious hypotheses; the final verdict | `open_case`, `propose_hypothesis`, `get_whiteboard`, `issue_verdict`, `propose_followup` | Signal, whiteboard, critiques → `HypothesisProposal[]` (`origin: agent_generated`), `Verdict` | Run tests, read labels, override the posterior, claim "confirmed" |
| **Cuddy** | Which test runs next; when to stop | `plan_next_tests`, `get_whiteboard` | Posterior, registry, budget → `PlannerRationale` (≥ 2 candidates, EIG, cost, score) | Exceed the budget without human approval |
| **Chase** | How to execute an approved test reproducibly | `run_vetting_test`, `rerun_vetting_test` | `TestSpec` → `TestResult` (run_id, metrics, code hash, runtime) | Run tests outside the registry |
| **Foreman** | Is the result trustworthy, and how much should beliefs move | `data_trust_check`, `assess_result`, `get_whiteboard` | `TestResult` → `ResultAssessment` (ok / marginal / unreliable, weight), `CounterExperimentRequest` | Upgrade a marginal result |
| **Cameron** | Which published evidence bears on the differential; source reliability | `literature_search` (OpenAlex), `evidence_for_tests`, `resolve_citation` (arXiv API) | Tests and hypotheses → `Evidence[]` with resolved IDs | Search for the target by name (label leak) |
| **Wilson** | What the lab has learned across targets | `record_lesson` | Closed case → knowledge-graph edges + `LessonLearned` | Change a verdict |
| **Data Gatekeeper** | Who sees labels (infrastructure, non-LLM) | not exposed to agents | Holds dispositions; `score()` for the evaluator only | — |

### Handoff sequence (one round)

1. House → Cuddy: leader + contrarian hypothesis + requested test.
2. Cuddy → Chase: `TestSpec` (chosen by EIG/cost; runner-up logged; parallel batch if two tests score within 15%).
3. Chase → Foreman: `TestResult`.
4. Foreman → Whiteboard: `ResultAssessment`; posterior update. If surprising: `CounterExperimentRequest` → Chase reruns with
   alternate detrending (charged at half the test's cost). If the leader flips, House must say which assumption was wrong (**reopen**).
5. Cameron → Whiteboard: resolved method citations for the tests run.
6. Cuddy decides whether to stop: posterior ≥ threshold and no open critique, budget exhausted, or max EIG < 0.02 bits.
7. House → `Verdict` (policy-checked) → Wilson → `LessonLearned`. A confident planet candidate triggers `propose_followup`
   (ASK → human).

### Bounded boldness

House's contrarian test gets an exploration bonus `β · I_pair(leader, contrarian)` added to its EIG before dividing by cost
(β = 0.25, `configs/experiment.yaml`). This rewards House's challenge, but it cannot override evidence. The verdict label
is always the posterior's top class.
