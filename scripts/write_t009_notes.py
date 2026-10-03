"""Append the T009/T005 verdict to README.md and coord/BUILD_LOG.md (numbers from runs/t009/summary.json, probe.json)."""
README = '''
## T009 memorisation control + T005 LLM-prior acquisition (steel_strength, B=60, seeds 0-4, n=5)
Probe (runs/t009/probe.json, 20 fixed rows, Sonnet 5.5 via cached CLI calls, default sampling): MAE MPa P1 generic 254.9 (near-exact 2/20),
P2 guided 188.7 (near-exact 3/20), P3 blinded 1573 (0/20), LOO kNN-5 104.3 (near-exact 6/20), train mean 719. Spearman P1 0.73, P2 0.71, kNN 0.73.
**Recall flag: SET** (near-exact(P2) 3 >= 3, and MAE(P2) 188.7 < 0.8 x MAE(P1) 254.9 = 203.9; MAE(P2) is NOT < 0.5 x kNN).
Arms (same pool, seeds, init design, budget as T003; LLM = static per-candidate prior from Sonnet 5.5, 5 revealed init rows in context; see asd/llm_prior.py):
hits@60 per seed 0-4: random(500-seed mean) 2.95 | OFAT [6,7,7,7,6] 6.6 | BO [8,3,5,8,5] 5.8 | named llm_bo [8,10,7,9,7] 8.2 | blind llm_bo [8,10,8,6,10] 8.4 |
named llm_greedy [15,13,11,14,13] 13.2 | blind llm_greedy [0,15,6,14,6] 8.2. Mean experiments to 1/3/5 hits: random500 18.2/46.8/59.0, OFAT 18.0/29.2/40.6,
BO 27.6/35.6/55.2, named llm_bo 6.0/9.6/30.6, blind llm_bo 15.4/21.6/28.8. G_named = 1.6 (4/5 paired wins vs best baseline OFAT, 1 tie), G_blind = 1.8 (4/5 wins).
**Verdict by the pre-registered rule: recall flag set => NO acceleration claim.** The measured advantage is "consistent with memorisation of a public benchmark
or named-domain prior". Caveat for the reader: the blinded arm (no names, permuted, scaled features) kept the llm_bo advantage (G_blind >= 0.5 G_named) but its
greedy variant is erratic (0 hits in one seed), so we cannot separate recall from legitimate metallurgy priors with n=5. Not shown: that the agent "learns faster".
'''
LOG = '''2026-10-04 builder/t011-t009-t005: T009 + T005 results (runs/t009, scripts/t009_probe.py, scripts/t009_t005_run.py, asd/llm_prior.py, asd/cli_llm.py).
LLM path: logged-in `claude -p` (no API key read), temp cwd, no tools, cached by (prompt, model, seed) in runs/t009/cache; CLI cannot set temperature. 120 real calls, CLI-reported cost ~$1.3, 0 throttling events.
Probe (20 rows): MAE P1 254.9 / P2 188.7 / P3 1573 / kNN5 104.3; near-exact 2/3/0/6 of 20 => RECALL FLAG SET (near-exact(P2)=3>=3; P2<0.8*P1). Rule outcome: claim INVALID as acceleration.
hits@60 seeds0-4: OFAT 6.6, BO 5.8, random500 2.95, named llm_bo 8.2 [8,10,7,9,7], blind llm_bo 8.4 [8,10,8,6,10], named greedy 13.2, blind greedy 8.2 [0,15,6,14,6]. G_named 1.6 (4 wins/1 tie of 5), G_blind 1.8.
Deviation from protocol: LLM prior is static (sees only the 5 init rows' y), not re-asked after each reveal; literature agent not used in either arm; first-pick-hit named 5/5 vs blind 2/5 (llm_bo).
Merge note: tests `python -m pytest -q` 30 passed. Spend ~$1.3 builder this cycle (CLI-reported).
'''
open("README.md", "a", encoding="utf8").write(README)
open("coord/BUILD_LOG.md", "a", encoding="utf8").write(LOG)
