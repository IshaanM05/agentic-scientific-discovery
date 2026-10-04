# LabLoop test bed: results and caveats

Test bed 2 is a simulated halide-perovskite lab (2,772 compositions, hidden physics, hit = bandgap 1.24-1.38 eV and T80 >= 500 h). **The simulator was designed by the team, the worlds are synthetic, and the rule-based LabLoop scientist is the baseline. Nothing here is evidence about real devices.** Scripts: `scripts/ll_benchmark.py`, `scripts/ll_compare.py`. Outputs: `runs/ll_benchmark.json`, `runs/ll_compare.json`.

## 1. Rerun of the benchmark in `docs/LABLOOP_README.md` (verified)
Command: `python scripts/ll_benchmark.py` (unseen worlds 1000-1019, 20 seeds, budget 60 units, offline, 92 s).
Result: **all 8 strategies reproduce the README table exactly** (first-hit and third-hit medians, hits by 60, share found; rounding as in the README), and the per-seed curves are identical to the committed `runs/benchmark_unseen.json`. No mismatch found.

| Strategy | First hit (median units) | Third hit | Hits by 60 (mean, n=20 worlds) | Share found |
|---|---|---|---|---|
| Random | not reached | not reached | 0.1 | 1% |
| One factor at a time | 6 | not reached | 2.9 | 20% |
| LLM-style, no BO | 6.5 | 34 | 2.9 | 22% |
| Pure BO | 30.5 | 37 | 8.2 | 56% |
| LabLoop (full) | 6.5 | 24 | 9.9 | 67% |

Notes: (a) the README header says "medians" but hits by 60 and share found are means; first/third-hit are medians. (b) Worlds hold 6-35 hits each (`hits_per_world` in the JSON), so a mean over worlds is dominated by hit-rich worlds. (c) LabLoop vs Pure BO is +1.7 hits (9.9 vs 8.2) at 60 units; we did not compute a confidence interval because the benchmark does not export per-seed final counts. (d) The ablation differences (e.g. negative memory, 9.6 vs 9.9) are within what 20 worlds can resolve; do not read them as effects. (e) The benchmark's worlds were available while LabLoop was developed on world 0; "never tuned on" is the authors' statement, not something we can check.

## 2. Golden worlds 2000-2002: rule-based scientist vs Omnigent
Worlds 2000-2002 were never used by the benchmark. Baseline: rule-based LabLoop, 5 seeds per world, budget 60, early stopping disabled (`target_discoveries=99`), offline. Means over 5 seeds (true hits in world: 16, 8, 28):

| World | hits@20 | hits@40 | hits@60 | first hit (units) | discoveries replicated | hypotheses refuted | ADAPT events* |
|---|---|---|---|---|---|---|---|
| 2000 | 4.6 | 9.8 | 14.6 | 1.7 | 8.8 | 2.2 | 6.2 |
| 2001 | 3.0 | 7.0 | 7.8 | 6.4 | 5.2 | 1.6 | 11.6 |
| 2002 | 3.4 | 8.4 | 15.4 | 6.4 | 10.6 | 2.0 | 8.0 |

*ADAPT = belief-revision events in the rule-based trace (prior relaxed, hypothesis qualified or falsified). Hits are true hits scored against hidden truth by the script only; hits@b counts distinct true-hit films with cumulative cost <= b. Replicated discoveries can exceed measured true hits only if the judge confirmed a film that is not a true hit; this was not separately audited.

**Omnigent side: not yet measured.** `runs/ll-*/record.jsonl` did not exist when this was written (W1's tools were not merged and cloud sessions have no model credentials). `scripts/ll_compare.py` parses those records when present (tolerant of field names; unreadable runs are listed as `unparsed`, never guessed) and its parser passes a synthetic-record selftest (`--selftest`). The record schema is an assumption taken from `docs/LABLOOP_INTEGRATION.md`; the lead should rerun the script after the live runs and check `omnigent_runs` for `unparsed` entries. With n = 1 run per world, any Omnigent vs baseline gap is a demonstration, not a statistical result.

## 3. Still needed before any claim
Live Omnigent runs on worlds 2000-2002 (several seeds each); per-seed paired comparison with a bootstrap CI; real-device data before any statement about perovskites.
