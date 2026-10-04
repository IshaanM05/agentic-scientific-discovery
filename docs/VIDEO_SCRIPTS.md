# Video scripts

Facts come from README.md and committed run records. TO FILL in square brackets marks a number that needs live Omnigent runs not yet in the repo (`docs/TODO_HUMAN.md`). Do not say "faster"/"acceleration" for the steel result, and say "hard gate" for approval only with "in interactive runs" (see `docs/DEMO_SCRIPT.md` "Must not say").

## 1. Demo video (2:00)
Follows `docs/DEMO_SCRIPT.md` (v4). Record at 1080p; terminal font large.

| Time | On-screen action | Say |
|---|---|---|
| 0:00-0:12 | README top, steel table | Question: find ultra-strong steels (yield >= 2000 MPa, 15 of 312) under an experiment budget. |
| 0:12-0:24 | Omnigent web UI, session tree of `runs/e2-live` | One Omnigent planner delegates to eight live sub-agent sessions; handoffs are schema-checked and logged. |
| 0:24-0:38 | `python scripts/show_record.py` or open `runs/e2-live/record.jsonl` at rec-0005..0008 | Cited literature, six falsifiable hypotheses, critic attacks, Elo ranking; all labelled agent-generated. |
| 0:38-0:50 | rec-0011, rec-0013..0016 | Novelty check says "partly reported"; planner scores three candidate tests and picks the best by expected learning and cost (0.475 vs 0.2125, 0.21). |
| 0:50-1:12 | rec-0018..0028 | Two experiments miss predictions; parallel analysis; judge disagrees on c068 so it stays advisory. 0 hits in 4; no ADAPT line in this run, and we say so. |
| 1:12-1:24 | `runs/t011` rec-0020, 0023, 0025, 0027 | ADAPT, from a different run: H2 refuted, H3 written, next experiment changed. |
| 1:24-1:34 | `python scripts/demo_policies.py`; `runs/t011-repl30/APPROVAL_EVIDENCE.md` | Budget DENY, safety DENY; approval held 22.2 s until a human clicked Approve; headless runs decline. |
| 1:34-1:48 | `docs/headline.png` | Blind arm: 8.75 vs 6.85 (BO) hits in 60 experiments, paired CI [+0.90, +2.95]. Memorisation flag set, so no claim that LLM knowledge accelerates discovery. |
| 1:48-1:56 | LabLoop panel in the live demo / dashboard benchmark, 60 unseen worlds: median first hit 7.0 vs 30.0 units for pure BO; hits at 60 units 9.86 [8.88, 10.89] vs 8.04 [7.43, 8.67]; Omnigent run stats **[TO FILL: no `runs/ll-w2000..2002` committed; see `docs/TODO_HUMAN.md` item 1]** | Second test bed: unseen synthetic worlds; result with its n and caveat. |
| 1:56-2:00 | README "Hard gates vs soft checks" | Budget, safety, approval enforced; judge, critic, novelty advisory. Next: a post-cutoff dataset. |

## 2. Tech video (3:00)
| Time | Screen | Say |
|---|---|---|
| 0:00-0:30 | README mermaid architecture | Planner supervises literature, generator, critic, Elo ranker, insight, analysis, judge, safety. Specs are YAML (`agents/planner.yaml`); Sonnet 5.5 for planner, insight, analysis, generator; Haiku 4.5 for the rest. |
| 0:30-1:00 | `asd/tools.py` | Tools are Python functions: literature search, design_tests, select_next, replay oracle, jsonschema-validated record_step, research record. Tools are declared per sub-agent because `inherit` does not pass them to sub-agents in a live run. |
| 1:00-1:30 | `asd/policies.py`, `tests/test_omnigent.py` | Policies: experiment_budget DENY, safety_gate DENY (a keyword list, not a hazard analysis), human_approval ASK, built-in cost_budget. Approval is hard in interactive runs; `-p` declines automatically. |
| 1:30-2:00 | `docs/headline.png`, `knowledge/concepts/memorization-control.md` | Memorisation control: probe flag SET (MAE 189 vs 255 MPa; 3/20 near-exact), blinded arm (names hidden, permuted, scaled), pre-registered Ni/Mn label swap, rule met but a weak manipulation. Result: 8.75 vs 6.85, no acceleration claim. |
| 2:00-2:30 | `labloop/`, `agents/labloop_planner.yaml` | Unseen-worlds test bed: LabLoop, a team-designed simulated perovskite lab with hidden physics (2,772 compositions); Omnigent runs on worlds 2000-2002 that no LLM can have seen; hidden truth is never returned by tools (test-enforced) Result (rule-based scientist, 60 worlds x 20 seeds): 9.86 hits [8.88, 10.89] vs 8.04 [7.43, 8.67] for pure BO at 60 units, first hit at a median 7.0 vs 30.0 units; Omnigent runs **[TO FILL: no `runs/ll-w2000..2002` committed; see `docs/TODO_HUMAN.md` item 1]**. |
| 2:30-3:00 | README "Limitations" | Honest limits: public benchmark, replayed oracle, single live runs are demos, judge n=12 near-arithmetic, arena p=0.21, default sampling, simulator is ours. Next experiment and validation needed. |

## 3. Team video (0:60) template
Fill placeholders; keep it to one take per person.

| Time | Who | Say |
|---|---|---|
| 0:00-0:08 | All | "We are [TEAM NAME], working on Challenge 3: Agentic Scientific Discovery." |
| 0:08-0:20 | [NAME 1] (GitHub: IshaanM05), [ROLE] | "I am [NAME 1]. I built [PART: e.g. the Omnigent loop, baselines, controls]." |
| 0:20-0:32 | [NAME 2] (GitHub: SSM11011), [ROLE] | "I am [NAME 2]. I built [PART]." |
| 0:32-0:44 | [NAME 3] (GitHub: FAZ610), [ROLE] | "I am [NAME 3]. I built [PART]." |
| 0:44-0:54 | Anyone | "What we are proudest of: [ONE THING, e.g. we kept the claim to what our memorisation control allows]." |
| 0:54-1:00 | All | "Repo and demo links are in the submission. Thank you." |

Check before recording: which handle belongs to which person is not recorded in the repo; confirm. Add a `[NAME 4]` row if needed.
