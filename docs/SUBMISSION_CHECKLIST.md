# Submission checklist

Maps every requirement in `docs/CHALLENGE_BRIEF.md` (authoritative) and `docs/HACKATHON_BRIEF.md` to the file that satisfies it, or marks it HUMAN with the reason. Status as of branch `final/submission`. Owners and commands for HUMAN items: `docs/TODO_HUMAN.md`.

## Challenge brief: what to build
| Requirement | Status | Where |
|---|---|---|
| Omnigent orchestrates the live workflow (mandatory) | DONE for steel; LabLoop: one partial live run (world 2000), worlds 2001 and 2002 HUMAN | `agents/planner.yaml`, `agents/labloop_planner.yaml`; live record `runs/e2-live/SUMMARY.md`; session tree demo `runs/t011`; LabLoop live `runs/ll-smoke2000` (budget 8, complete) and `runs/ll-w2000` (partial, 23.5 of 60 units) |
| Specialist agents with owned decisions, declared tools, structured handoffs | DONE | `agents/planner.yaml` (8 sub-agents, tools declared per sub-agent), `asd/schemas.py`, `record_step` in `asd/tools.py` |
| Oracle and selector as Python function tools | DONE | `asd/tools.py`, `asd/labloop_tools.py` |
| Budget and safety as Omnigent policies | DONE | `asd/policies.py` (`experiment_budget` DENY, `safety_gate` DENY, `human_approval` ASK), README "Hard gates vs soft checks" |
| One specific question, testable in 24 h | DONE | README "Test bed 1" Question |
| Full loop question -> evidence -> hypothesis -> experiment -> result -> updated decision | DONE | `runs/t011` (ADAPT), `runs/e2-live` (all sub-agents live), `docs/DEMO_SCRIPT.md` |
| At least two candidate tests, chosen by expected learning, feasibility, cost | DONE | `design_tests` in `asd/tools.py`; `runs/e2-live` rec-0013..0016 (0.475 vs 0.2125 and 0.21) |
| Result changes the next step; surprises reopen assumptions | DONE (steel); LabLoop live HUMAN | `runs/t011` rec-0020..0025 (H2 refuted, H3, next experiment changed); LabLoop: `runs/ll-w2000` has refutations and prior relaxations followed by changed decisions (`docs/RESULTS_LABLOOP.md` section 5; replay tab labels ADAPT as inferred) |
| Baseline vs proposed method under matched conditions | DONE | README Result and E1; `scripts/run_baselines.py`, `scripts/t009_blind20.py`, `docs/headline.png`; LabLoop `scripts/ll_benchmark.py`, `docs/ll_headline.png` |
| Safety agent routing to human approval via tool permissions and policies | DONE | `asd/policies.py`; `runs/t011-repl30/APPROVAL_EVIDENCE.md` (22.2 s hold, interactive); headless `-p` declines (fail-closed) |
| Shared research record, every decision reconstructible | DONE | `runs/<run>/record.jsonl`, `ledger.jsonl`; knowledge graph `docs/kg.html`, `runs/kg_*.json` |

## Rigor and responsibility
| Requirement | Status | Where |
|---|---|---|
| Citations for factual claims | DONE | README "References" (DOIs where verified; incomplete ones are marked incomplete); `knowledge/papers/` |
| Run records attached | DONE | `runs/` (steel); `runs/ll_*.json` (LabLoop offline results) |
| Agent-generated hypotheses labelled | DONE | README "Responsible use"; labels in every record |
| Uncertainty preserved | DONE | intervals on every headline number, README "Limitations", `docs/RESULTS_LABLOOP.md` section 6 |
| Controls | DONE | memorisation probe, blinded arm, pre-registered counterfactual (README E1), random/OFAT/BO baselines, ablations |
| Human-approval gates documented | DONE | README "Human approval (policy ASK)" |
| Validation needed before real use | DONE | README "Validation needed before real use" |
| Claims match committed sources | DONE | `python scripts/check_claims.py --strict`, `docs/CLAIMS_AUDIT.md` |

## Submission contents
| Item | Status | Where |
|---|---|---|
| Repository | DONE | this repo, branch `final/submission` (merge to `main` is HUMAN, item 11) |
| Agent specifications and policies | DONE | `agents/*.yaml`, `asd/policies.py` |
| Two-minute demo (script) | DONE | `docs/DEMO_SCRIPT.md`; recording is HUMAN |
| Cited evidence | DONE | README "References", `docs/REFERENCES.md`, `knowledge/` |
| Experiment code and results | DONE | `scripts/`, `asd/`, `labloop/`, `results/`, `runs/`, `docs/RESULTS_LABLOOP.md`, `docs/RESULTS_MULTIFIDELITY.md` |
| Measured improvement | DONE with limits | steel: 8.75 vs 6.85 (BO) and 6.40 (OFAT) hits@60, 20 seeds, no acceleration claim (memorisation flag set); LabLoop (60 worlds, rule-based scientist): 9.86 [8.88, 10.89] vs 8.04 [7.43, 8.67] hits, first hit median 7.0 vs 30.0 units (`docs/RESULTS_LABLOOP_BIG.md`); Omnigent run n = 1, partial |
| Next experiment | DONE | README "Next experiment" |
| 1-2 slide pitch for finalists | DONE (text) | `docs/PITCH.md` (slides themselves HUMAN) |

## Hack-Nation checklist (HACKATHON_BRIEF.md)
| Item | Status | Where / reason |
|---|---|---|
| Demo video | HUMAN | needs a screen recording and voice; script `docs/DEMO_SCRIPT.md`, `docs/VIDEO_SCRIPTS.md`; TODO item 5 |
| Tech video | HUMAN | same; TODO item 5 |
| Team video | HUMAN | needs the people on camera; TODO items 5 and 6 |
| GitHub repo, public link | HUMAN | visibility is a GitHub setting; TODO item 10 |
| Live demo (Vercel, Replit or Lovable) | HUMAN | deploy needs an account; `vercel.json`, `docs/DEPLOY.md` ready; TODO items 3 and 4 |
| Every member has an account on app.hack-nation.ai and is under "team & submission" | HUMAN | personal logins; TODO item 7 |
| Upload videos, repo link and live link to app.hack-nation.ai AND the Google form | HUMAN | needs the links above; TODO item 8 |
| Tell organizers in Discord which challenge we chose | HUMAN | Discord account; TODO item 9 |
| Omnigent live LabLoop runs on worlds 2001 and 2002 (and a full-budget world 2000) | HUMAN | needs the model login not available in the cloud; exact commands in TODO item 1 |
| Token rotation | HUMAN | account action; TODO item 2 |
