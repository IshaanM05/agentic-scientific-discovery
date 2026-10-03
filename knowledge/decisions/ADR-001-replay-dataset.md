---
type: decision
date: 2026-10-03
status: proposed
---
# ADR-001: Replay oracle dataset = steel_strength, hit = yield strength >= 2000 MPa
**Context.** No Materials Project key; repo is public. T002 needs a small, license-clean, key-free dataset with a hit rate of about 1-5% so "experiments to first k hits" is meaningful.
**Options.**
- steel_strength (312 rows, 13 numeric composition knobs, MIT on figshare): tiny, bundleable, no featurizer; small pool limits statistics.
- expt_gap (4604 rows, MIT on figshare): larger pool; needs formula parsing + featurization.
- Materials Project API: needs key, rate limits, licence CC BY 4.0 terms [unverified]; rejected for the core path.
**Decision.** Primary [[steel-strength]]: hit = `yield strength` >= 2000 MPa (15/312 = 4.8%). Pool-based replay; 1 experiment = 1 reveal, cost 1; budget B = 60 incl. initial design; repeats free and cached; LLM spend logged separately, never converted to experiments. Fallback [[expt-gap]] (gap >= 4.0 eV, 4.15%, B = 150).
**Fair comparison rules.** Same B, same seeds (>= 5; recommend 20, runs are cheap), same initial-design rule, same candidate pool for every method. Report median and IQR of experiments to first k hits for k = 1, 3, 5; methods that miss k within B are censored at B+1 and reported as such.
**Leakage guard.** Agents/LLM prompts see only composition columns and revealed results. Tensile strength and elongation are hidden (correlated with target). Row order shuffled per seed; no row index semantics in prompts.
**Consequences / how we would know it was wrong.** Random reference (analytic, sampling without replacement): expected experiments to k-th hit = k*313/16, i.e. 19.6 / 58.7 / 97.8 for k = 1/3/5. If pure BO reaches k = 5 in < 15 experiments on median, the task is too easy: raise threshold to 2200 MPa (12 hits) or switch to expt_gap. With 312 rows, LLM memorization of this public set is possible; check by asking the model to predict held-out values without context and report it.
