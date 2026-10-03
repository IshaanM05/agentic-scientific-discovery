# runs/e2-live: one live Omnigent run (seed 7, budget 8, headless -p)
Session dbd0cbb6b1ee4846b009e9f97a50be09; transcript.jsonl (runner_token ids redacted); record.jsonl; ledger.jsonl (4 reveals).
Prompt asked for at most 4 experiments. All sub-agents ran as live Omnigent sessions (sys_session_send): literature, generator, critic, elo_ranker, insight, analysis (4 sessions), judge (4), safety.

| Step | Record ids | What happened |
|---|---|---|
| 1 literature | rec-0001..0004 (searches), rec-0005 (handoff) | cited papers on strong steels (OpenAlex) |
| 2a arena generator | rec-0006 | 6 hypotheses H1..H6 (arena ids), predictions 500..2300 MPa (first submit rejected by schema, resubmitted) |
| 2b critic | rec-0007 | attack + refuting test for each of 6 |
| 2c elo_ranker | rec-0008 | Elo H2 1059.7, H1 1029.9, H4 986.2, H5 984.8, H3 972.1, H6 967.4 |
| 2d novelty (shallow keyword check) | rec-0009, rec-0010 (searches), rec-0011 | top 2 (arena H2, H1): both "partly reported" |
| 2e insight registers | rec-0013 (H1, predicts 2300), rec-0014 (H2, predicts 2175), rec-0015 | numbering differs from the arena ids; labelled agent-generated |
| 3 design_tests | rec-0016 | 3 options; two are critic refuting tests (Mo-Ti synergy, Aging temperature robustness); chosen "Surrogate-top single pick" (0.475 vs 0.2125, 0.21). The critic test was NOT executed |
| 4 parallel step | rec-0018 c000 = 1382.2 MPa, rec-0019 c068 = 1661.2 MPa; analyses rec-0020/0021 (c000), rec-0023 (c068); handoffs rec-0024, rec-0025 | two run_experiment calls in one response, then analysis-A and analysis-B sent in one response (same response id; sent 3 s apart) |
| 6 judge | rec-0027 (c000: supported_by_ledger true, high), rec-0028 (c068: supported_by_ledger false, medium) | the judge disagreed with the analysis on c068 (analysis said unsupported, rec-0023); advisory only |
| experiment 3 | rec-0030 c174 = 1144.8 (H2); analysis rec-0031; handoff rec-0033 (reopens 3 assumptions); judge rec-0034 | not a hit |
| experiment 4 | rec-0036 c014 = 1199.0 (H2); analysis rec-0037; handoff rec-0038; judge rec-0042 | not a hit |
| 8 safety | rec-0040, rec-0041 | c068 flagged medium |

Not as specified (honest):
- No "ADAPT:" line appears in the transcript; experiments 3 and 4 followed select_next picks without a stated adaptation, and design_tests ran once, not before each experiment.
- Hits found: 0 of 4. All analyses unsupported (1145 to 1661 vs predicted 2175 to 2300).
- The planner's last message says it is calling recommend_for_validation and propose_processing_route but it made neither call (session idle, no record entry). So the approval ASK, the -p auto-decline and the safety_gate DENY were NOT exercised in this live run. They are shown separately (runs/t011-repl30, tests/test_omnigent.py, scripts/demo_policies.py).
- Parallelism: observed as same-response dispatch of two sessions; execution overlap was not timed beyond the 3 s send gap.
