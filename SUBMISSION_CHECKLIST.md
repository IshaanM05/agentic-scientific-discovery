# Submission checklist

Sources: `docs/CHALLENGE_BRIEF.md` (authoritative) and `docs/HACKATHON_BRIEF.md` (checklist). Deadline Sun Oct 4, 9:00 AM ET. Upload to app.hack-nation.ai AND the Google form.

| # | Requirement | Satisfied by | Status |
|---|---|---|---|
| 1 | Build with Omnigent; Omnigent orchestrates the live workflow | `agents/planner.yaml`, `runs/e2-live/SUMMARY.md`, `runs/t011` | done |
| 2 | Specialist agents exchange structured outputs, declared tools | `agents/planner.yaml` (literature, insight, analysis, safety, judge, generator, critic, elo_ranker); `record_step` schema validation in `asd/tools.py` | done |
| 3 | Oracle and selector as Python function tools | `asd/tools.py` (run_experiment, select_next, design_tests, literature_search, research_record) | done |
| 4 | Budget and safety as Omnigent policies | `asd/policies.py` (experiment_budget DENY, safety_gate DENY, human_approval ASK, cost_budget); `runs/policy_demo`, `tests/test_omnigent.py` | done |
| 5 | One loop: question, evidence, hypothesis, experiment, result, updated decision | `runs/t011` (H1, H2 refuted, H3, next experiment changed); `runs/e2-live` (loop without ADAPT) | done |
| 6 | At least two candidate tests, chosen by expected learning, cost, feasibility | `design_tests` tool; `runs/arena` | done |
| 7 | Adapt plan after a surprising result | `runs/t011` ADAPT beat | done (one example) |
| 8 | Parallel searches or experiments | `runs/e2-live/SUMMARY.md` (two analysis sessions in one response; speedup not benchmarked) | done (not benchmarked) |
| 9 | Safety agent routes risky decisions to human approval, enforced | `safety_gate`, `human_approval`; `runs/t011-repl30/APPROVAL_EVIDENCE.md` (22.2 s hold) | done (one interactive run) |
| 10 | Shared research record, every decision reconstructible | `runs/<run>/record.jsonl`, `ledger.jsonl`, `meta.json`; `scripts/show_record.py` | done |
| 11 | Named bottleneck and defined "faster" | README "Bottleneck" (hits within B=60, experiments to k-th hit) | done |
| 12 | Measured improvement vs baselines, matched conditions | README "Result", `docs/headline.png`, `results/e1_counterfactual.json`, `runs/t003`, `runs/t009` | done (no acceleration claim; memorisation flag set) |
| 13 | What would approach 10x at scale; next experiment | README "Next experiment" | done (10x discussion is brief) |
| 14 | Citations for factual claims | README "References", `knowledge/papers/` | done (some citations marked incomplete) |
| 15 | Label agent-generated hypotheses, preserve uncertainty | README "Responsible use", "Limitations"; judge and arena calibration (`results/`) | done |
| 16 | Controls and human approval gates documented | README "Counterfactual test (E1)", "Hard gates vs soft checks", "Human approval (policy ASK)" | done |
| 17 | Validation needed before real-world use | README "Validation needed before real use" (under Responsible use) | done |
| 18 | Repository public, code and docs | repo, `LICENSE` (MIT), `README.md` | pending-human (confirm repo is public, merge to main after Scout approval) |
| 19 | Agent specifications and policies in submission | `agents/*.yaml`, `asd/policies.py` | done |
| 20 | Experiment code and results | `scripts/`, `results/`, `runs/`; one-command offline repro `scripts/reproduce.ps1` / `.sh` | done |
| 21 | Two-minute demo (video) | script in `docs/DEMO_SCRIPT.md` | pending-human (record and upload) |
| 22 | Tech video (explains the build) | architecture diagram in README | pending-human |
| 23 | Team video | n/a | pending-human |
| 24 | Live demo (Vercel, Replit or Lovable) | offline replay dashboard `dashboard/app.py` runs locally with Streamlit | pending-human (no hosted URL yet) |
| 25 | Upload to app.hack-nation.ai and Google form; every member added under "team & submission" | n/a | pending-human |
| 26 | Tell organizers in Discord which challenge (Challenge 3) | n/a | pending-human |
| 27 | 1-2 slide pitch (finalists, Oct 10) | n/a | pending-human |
