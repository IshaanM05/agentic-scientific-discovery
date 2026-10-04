# Cloud worker context (read this first, in full)

You are a parallel worker on our entry to the Hack-Nation 7th Global AI Hackathon, **Challenge 3: Agentic Scientific Discovery** (Databricks x Hack-Nation). You have no memory of earlier work; this file is your briefing. Then read `docs/LABLOOP_INTEGRATION.md` (the contract: file ownership, tool interfaces) and your own task prompt. The repo's `CLAUDE.md` describes the lead's local workflow; where it conflicts with this file or your prompt, **this file and your prompt win** (for example: you branch from `integration/labloop`, not `dev/agentic-loop`).

**Deadline:** code freeze Sun Oct 4 15:30 IST (06:00 ET); submission 18:30 IST (09:00 ET). Your time-box is in your prompt. Push early and often; unfinished-but-working beats perfect-but-missing.

## What the organizers require (docs/CHALLENGE_BRIEF.md is the authoritative brief)
- **Omnigent (Databricks' open-source meta-harness, github.com/omnigent-ai/omnigent) must orchestrate the live discovery workflow**: specialist agents exchanging structured outputs, using tools, adapting their plan after a result. Agents are YAML files; tools are Python functions; guardrails are policies. This is 30% of the score.
- Scoring: Omnigent orchestration 30%, breakthrough potential 25%, discovery acceleration and learning 20%, scientific rigor 15%, creativity and responsibility 10%.
- The loop to demonstrate: question, evidence, hypothesis, experiment (planner designs at least two candidate tests and picks one by expected learning, feasibility and cost), result, updated decision, next experiment.
- Required rigor: citations for factual claims; run records; agent-generated hypotheses labeled as such; uncertainty preserved; controls and human-approval gates documented; validation still needed before real use stated. Report the improvement you actually observe (1.5x is fine); evidence strength matters more than the multiplier.

## What exists (all on `integration/labloop`)
Two test beds, both driven by the same Omnigent workflow idea:
1. **Steel strength (ours, `asd/`, `agents/planner.yaml`):** real public Matbench steels data (312 candidates, hit = yield >= 2000 MPa, 15 hits, budget 60). A live Omnigent planner with sub-agents (literature, hypotheses/arena, analysis, judge, safety), tools backed by a replay oracle, 4 policies (experiment budget, cost budget, human-approval ASK, safety DENY). Honest result: the LLM may have memorized this public dataset (memorization probe flag is SET), so **we make no LLM-knowledge acceleration claim**. A blinded arm (unnamed, permuted, scaled features) still beat one-factor-at-a-time on 20 seeds (about 8.75 vs 6.40 mean hits at 60 experiments, paired CI [1.75, 3.00]); this is reported as evidence, not as an acceleration claim. Judge calibration (n=12) was near-arithmetic and the arena check (n=5, Spearman 0.56, p=0.21) was at chance; both are stated as weak.
2. **LabLoop (a teammate's branch `labloop-v2`, now `labloop/`):** a simulated halide-perovskite lab with hidden physics (2,772 compositions, target bandgap 1.24-1.38 eV and T80 >= 500 h). The textbook prior says zero films qualify; the hidden lab has some. Rule-based agents (PI, literature, hypothesis arena with Elo, Gaussian-process designer, safety gate, analyst, judge, SQLite notebook). Its README reports, on 20 unseen random worlds, 9.9 vs 8.25 hits at 60 units against Bayesian optimization alone and a first hit at 6.5 vs 30.5 units. **Those numbers are unverified until we rerun them.** The simulator was designed by the team, so it is a benchmark, not evidence about real devices; say so everywhere.
The integration goal: Omnigent orchestrates LabLoop as test bed 2, so the agents run on worlds no LLM can have memorized.

## Repo map
`asd/` our tools, policies, baselines, schemas; `agents/` Omnigent YAML; `labloop/` teammate's simulator and agents (read-only unless your prompt says otherwise); `scripts/` runners; `runs/` committed run records; `dashboard/`, `docs/index.html` demos; `docs/` briefs, results, demo script; `knowledge/` Obsidian-style vault (index at `knowledge/00-INDEX.md`); `coord/` lead's handoff and logs (do not edit).

## Hard rules
- Start from branch `integration/labloop`; create the branch named in your prompt; push it; **do not open a pull request; do not merge; never touch `main`, `dev/agentic-loop` or other workers' branches**.
- Edit only the files your prompt lists as owned by you. If you need a change elsewhere, write it in your final report instead of making it.
- **Never add co-author trailers or mention any AI assistant or tool in commit messages or in files you create.** Commit as the repository's configured user.
- No secrets. No `.env`. No API keys. Cloud sessions have no model credentials for our live Omnigent runs, so everything you build must run **offline** (stubbed model where needed). The lead runs the live tests locally.
- **Never expose hidden ground truth to agents or tools** (true bandgaps, true T80, world parameters, true hit lists, untested measurements). Add a test where your task touches tools.
- No claim without a measurement. If a result is negative or weak, report it plainly. Report counts, confidence intervals and caveats; never a bare number.
- Keep the 7 existing LabLoop tests and the 40 existing asd tests passing: run `python -m pytest -q` before every push. Install with `pip install -r requirements.txt`.
- Token discipline: grep and line ranges instead of whole-file reads; short messages.

## Definition of done and reporting
Push your branch, add a short dated note to `coord/BUILD_LOG.md` **on your branch only if your prompt allows** (otherwise put it in your final message), and finish with a report of at most 15 lines: branch name and head commit, files added or changed, tests run and result, numbers produced (with caveats), what is incomplete or risky, and anything the lead must decide.
