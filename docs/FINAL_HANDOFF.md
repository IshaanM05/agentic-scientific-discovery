# Final handoff (branch `final/submission`)

Written by the finisher worker. Offline only: no model credentials, no deploy, no recording. Human work: `docs/TODO_HUMAN.md`. Requirement map: `docs/SUBMISSION_CHECKLIST.md`.

## What is in the repo
- **Test bed 1, steel strength** (`asd/`, `agents/planner.yaml`, `runs/t0*`, `runs/e2-live`, `results/`): Omnigent planner plus 8 sub-agents, Python tools, policies (budget DENY, safety DENY, approval ASK), baselines, memorisation probe, blinded arm, pre-registered counterfactual.
- **Test bed 2, LabLoop** (`labloop/`, `asd/labloop_tools.py`, `agents/labloop_planner.yaml`, `scripts/ll_*.py`, `runs/ll_*.json`): simulated perovskite lab; offline benchmarks; live Omnigent runs `runs/ll-smoke2000` and `runs/ll-w2000` (partial).
- **Extras**: multi-fidelity extension (`labloop/multifidelity.py`, `docs/RESULTS_MULTIFIDELITY.md`), knowledge graph (`asd/kg.py`, `docs/kg.html`, linked from `docs/index.html`), traceable reports (`docs/REPORT_STEEL.md`, `docs/REPORT_LABLOOP.md`, from `scripts/make_report.py`), claims audit (`docs/claims.yaml`, `scripts/check_claims.py`, `docs/CLAIMS_AUDIT.md`), pitch, video scripts, Q&A, judge guide, demo page (`docs/index.html`, `vercel.json`), dashboard (`dashboard/`).
- `README.md` is one document (what it is, headline results with intervals, architecture, two test beds, reproduce, agents and policies, responsible use, limitations, references, live demo placeholder, team placeholders). Long LabLoop detail: `docs/LABLOOP_README.md`.

## Branches merged into `final/submission`
| Branch | Head | Note |
|---|---|---|
| integration/labloop | 198c2bd | includes `runs/ll-smoke2000`, `runs/ll-w2000` |
| w1/labloop-tools | a1c4a4f | content already in integration |
| w2/labloop-results | 6d56adb | already in integration |
| w3/labloop-demo | 9c4fa62 | already in integration |
| w4/labloop-multifidelity | 778f498 | already in integration |
| w5/labloop-report | 0ad95b7 | new here (reports, `runs/ll-offline-w3100`); `claude/w5-labloop-report-t1kxni` is the same commit |
| w6/pitch-materials | 8f8082c | already in integration |
| w7/claims-audit | f13fcdc | already in integration |
| w8/knowledge-graph | 7b2d7bf | already in integration |
| w10/stat-tightening | 07408ec | new here (60-world results and misspecification; its `docs/RESULTS_LABLOOP_BIG.md` replaced my earlier draft) |
| w12/ll-w2000 | e485b85 | `runs/ll-w2000-full`, report; its `runs/ll-smoke2000` conflicted with the lead's, the lead's kept |
| w12/ll-w2001 | fd2816e | `runs/ll-w2001`, `runs/ll-smoke2001`, report |
| w12/ll-w2002 | 19afa50 | `runs/ll-w2002`, `runs/ll-smoke2002`, report |
Not touched: `main`, `dev/agentic-loop`. No pull request opened.

## Tests (`python -m pytest -q`, Python 3.11 sandbox, no `omnigent` package)
117 collected: **110 pass, 6 skipped, 1 fails** (`tests/test_omnigent.py::test_every_yaml_callable_resolves_and_is_callable`, `ModuleNotFoundError: omnigent`, the accepted failure). The 6 skips and that failure are the tests that need `omnigent` (Python 3.12). Not verified here: they passing with omnigent installed (the lead reported 92 pass on a 3.12 venv earlier, before W5 and W10). `python scripts/check_claims.py --strict` exits 0.

## Final numbers (all from committed files; intervals are 95%)
| Result | Value | Source |
|---|---|---|
| Steel, blind prior+GP hits@60 vs OFAT / BO | 8.75 vs 6.40 / 6.85, paired CI [+1.75, +3.00] / [+0.90, +2.95], 20 seeds | `runs/t009/blind20_summary.json` |
| Steel acceleration claim | none (memorisation flag set; label-swap met its rule but is a weak manipulation) | README |
| Steel judge n=12 / arena n=5 | near-arithmetic / chance (p=0.21) | `results/*.json` |
| Human-approval hold | 22.2 s in one interactive run | `runs/t011-repl30/APPROVAL_EVIDENCE.md` |
| LabLoop, 60 worlds x 20 seeds, rule-based scientist: hits@60 full vs pure BO | 9.86 [8.88, 10.89] vs 8.04 [7.43, 8.67]; paired +1.82 [+1.29, +2.35]; ahead in 46 of 60 worlds | `runs/ll_big_benchmark.json`, `docs/RESULTS_LABLOOP_BIG.md` |
| Same, median units to first hit | 7.0 vs 30.0 (reached 1186 vs 1133 of 1200 runs) | same |
| LabLoop, 20 worlds (earlier rerun) | 9.90 vs 8.25, paired +1.65 [+0.05, +3.20] | `runs/ll_benchmark.json` |
| LabLoop live Omnigent, world 2000, `ll-w2000-full` (complete by stop rule, 15 films, 22.0 of 60 units, n = 1) | 6 of 16 true hits, first 2.5 units, 6 hits by 20 units vs baseline 4.6 (range 3-6, 5 seeds) | `runs/ll_compare_w2000_full.json` |
| Same world, earlier `ll-w2000` (PARTIAL, 23.5 units) | 6 of 16, first 1.5, 5 by 20 units | `runs/ll_compare.json` |
| World 2001, `ll-w2001` (planner ended it, 31 films, 46.0 units) | 8 of 8 true hits, first 10.0 units (baseline 6.4), 2 by 20 units (baseline 3.0) | `runs/ll_compare.json` |
| World 2002, `ll-w2002` (stop rule, 18 films, 26.5 units) | 8 of 28, first 4.0 units (baseline 6.4), 5 by 20 units (baseline 3.4); baseline 15.4 at 60 units, so not comparable at 60 | `runs/ll_compare.json` |

## Fixes made in this pass (and why)
- `9.9 vs 8.2` now reads `9.9 vs 8.25` (docs, claims). `docs/LABLOOP_README.md` still prints 8.2 in the teammate's table; it is his table and the audit notes it as a rounding.
- Test count in README was 40; the real count is 117 collected (110 pass here).
- `docs/claims.yaml`: demo-script claim texts were stale after the script was rewritten, so (a) six `demo.e2.*` claims whose numbers the current script no longer states were deleted (the same facts stay claimed in README and QA), (b) `demo.approval_hold_s`, `demo.steel.hits`, `demo.e2.hits` were re-pointed at the current wording. The documents were right and the claim texts were stale. New claims cover every number added in this pass.
- `dashboard/data.py` `readme_section` made heading-level aware (README restructure moved sections).
- `dashboard/ll_summary.py`: counts distinct hit compositions (it counted repeated films, showing 10 hits where the scorer finds 6), and does not list `ll-offline-*` simulations as Omnigent runs.
- `asd/kg.py`: reads the live record schema (ids instead of objects, list-valued hypothesis updates, `exp_id`), which crashed `make_kg.py` once `runs/ll-w2000` arrived; duplicate experiment nodes removed.

## Safety sweep (2026-10-04)
- Hidden-truth names (re-run on `ll-w2000-full`, `ll-w2001`, `ll-w2002` and the smoke runs, files and notebooks: 0 matches; the three `docs/LIVE_RUN_REPORT_W200*.md` match only because they quote the grep pattern): no `eg_true`, `lt_true`, `world_params` anywhere in agent-visible run records, notebooks (`ll-w2000`, `ll-smoke2000`, `ll-offline-w3100`, steel runs) or reports. The key `true_hits` appears only in offline benchmark outputs (`runs/benchmark*.json`, `runs/trace_seed1.json`, `runs/ll_calibrate.json`, `runs/ll_compare*.json`) and the demo page (`docs/index.html`, `dashboard/template.html`), which agents never read, and in guard lists (`asd/kg.py`, `asd/kg_tools.py`) that forbid them.
- Secrets: no key, token value or `.env` tracked; only env-var names in docs (`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`). The earlier-exposed subscription token still has to be rotated (TODO item 2); git history was not scanned for it.
- AI-tool names: commit messages on the branch have none beyond the `CLAUDE.md` pointer commit. **28 commits from worker branches carry the author identity "Claude <noreply@anthropic.com>"** (not fixable without rewriting shared history; TODO item 11 gives a squash-merge command). Files: the remaining mentions are functional identifiers or honest method disclosure, kept on purpose: harness name `claude-sdk` and model ids in `agents/*.yaml` and tests, env-var names, the `claude` CLI used for LLM calls (README "Deviation: temperature"), `coord/*` notes (lead's files, untouched), `docs/AGENT_PROMPT.md`, `knowledge/` notes, `labloop/` (read-only). Prose mentions in `docs/LABLOOP_README.md`, `docs/PLAN.md`, `docs/LABLOOP_INTEGRATION.md` were reworded.

## Known issues and honest limits
- Omnigent evidence on LabLoop is three single samples (one per world, seed 0). All ended before 60 units (stop rule or planner decision), so hits@40 and hits@60 columns in `ll_compare.json` repeat the final count and are not measurements at those budgets; only hits by 20 units compares like with like. On world 2002 the baseline finds more hits at 60 units (15.4 vs 8 at 26.5 units), and on world 2001 the Omnigent first hit was later than the baseline's. ADAPT is counted differently by `ll_compare` (2, 3, 4 for 2000-full, 2001, 2002) and the dashboard (inferred); the planners wrote 0, 4 and 0 literal "ADAPT:" lines. Run-report notes the planner skipped a loop step in 2001 (round 9) and a judge sub-agent looped in 2000-full; the judge's "confirmed" counts (5, 3, 4) are two-film agreement and differ from `ll_compare`'s replicated counts.
- LabLoop gains are for the rule-based scientist inside a team-designed simulator; the benefit of the Omnigent team over the rule-based one is not measured.
- Steel: public benchmark, memorisation flag set, so no acceleration claim; probe n=20 at default sampling; approval hold shown once interactively; headless runs decline.
- `docs/LABLOOP_README.md` is the teammate's text; it was not independently proofread beyond the table rerun.
- No `w5` live outputs beyond the offline report run; no videos, no live URL, no team names (all HUMAN).

## How to reproduce
`bash scripts/reproduce.sh` or `powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1` (offline). Large LabLoop benchmark: `python scripts/ll_big_benchmark.py` (about 28 minutes at the recorded runtime, 1660 s on its machine). Regenerate outputs: `python scripts/ll_compare.py; python scripts/make_kg.py; python scripts/build_dashboard.py; python scripts/make_report.py all; python scripts/check_claims.py --md docs/CLAIMS_AUDIT.md; python scripts/check_claims.py --strict`.

## Independent audit against the five scoring criteria
Weakest points
1. **Omnigent orchestration on the unseen-worlds test bed is evidenced by single samples (30% criterion).** One live run per world, each ended early, with mixed results against the rule-based baseline (better at 20 units on 2000 and 2002, worse first hit on 2001, fewer total hits on 2002). Support: `docs/RESULTS_LABLOOP.md` section 5, `runs/ll_compare.json`, `docs/LIVE_RUN_REPORT_W200*.md`.
2. **No measured acceleration from LLM knowledge (20% criterion).** Memorisation flag set, label-swap manipulation weak, judge near-arithmetic, arena at chance; the steel gain is evidence against baselines, not a learning claim. Support: README "Test bed 1" and E1, `results/judge_calibration.json`, `results/arena_calibration.json`.
3. **Breakthrough potential rests on a simulator the team designed (25% criterion), and the deliverables that judges see first are missing:** no live URL, videos or team names yet. Support: `docs/RESULTS_LABLOOP_BIG.md` (limits), `docs/TODO_HUMAN.md`, `docs/SUBMISSION_CHECKLIST.md`.

Strongest points
1. **Rigor and honesty (15%).** Every published number is tied to a committed file by a strict audit that exits 0; a pre-registered counterfactual; limits stated next to each claim. Support: `docs/CLAIMS_AUDIT.md`, `scripts/check_claims.py`, README "Counterfactual test (E1)".
2. **Enforced guardrails with evidence (30% and 10%).** Budget and safety DENY policies tested through the Omnigent shim, an approval ASK held 22.2 s in an interactive run, hidden truth kept out of tool outputs by test, a refutation changing the next experiment in a live run, and three live LabLoop runs whose records contain no hidden-truth names. Support: `asd/policies.py`, `tests/test_labloop_tools.py`, `runs/t011-repl30/APPROVAL_EVIDENCE.md`, `runs/t011`.
3. **A second test bed that removes the memorisation objection, measured at scale with correct statistics (25% and 20%).** 60 worlds x 20 seeds, bootstrap over worlds, intervals that exclude zero against Bayesian optimisation, ablations, calibration against hidden truth. Support: `docs/RESULTS_LABLOOP_BIG.md`, `scripts/ll_big_benchmark.py`, `docs/RESULTS_LABLOOP.md`.
