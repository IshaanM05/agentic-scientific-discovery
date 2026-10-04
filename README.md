# Princeton-Plainsboro: a House M.D. agentic lab for exoplanet candidate diagnosis

**Hack-Nation × Databricks, Challenge 03: Agentic Scientific Discovery (built with Omnigent)**

Space telescopes produce thousands of transit-like signals, and most are not planets. The bottleneck is not
*running* vetting tests. It is **deciding which test to run next, and when to stop**. This lab treats every dip as a
patient. A team of adversarial specialist agents builds a differential diagnosis, chooses the most informative test
under a budget, has a skeptic challenge every result, re-plans after each experiment, and issues a cited verdict
with calibrated uncertainty. Every verdict passes through human-approval gates.

```
Question → Evidence → Hypothesis → Experiment → Result → Updated decision   (repeated until the stopping rule fires)
```

## Headline results (measured, not projected)

Matched conditions: 240 blind synthetic targets. All conditions replay identical test outcomes and share the same
5-test / 10-cost-unit budget. 90% bootstrap CIs. Full tables are in [results/REPORT.md](results/REPORT.md).

| | Accuracy @ threshold 0.9 | Mean cost | Brier ↓ | Escalated to human |
|---|---|---|---|---|
| B1 fixed checklist (Robovetter-like order) | 0.846 [0.81, 0.88] | 6.62 | 0.243 | 42% |
| B2 random order | 0.871 [0.83, 0.90] | 7.51 | 0.190 | 43% |
| B3 EIG planner only (no debate agents) | 0.883 [0.85, 0.92] | 5.56 | 0.159 | 24% |
| **P House team (full lab)** | **0.917 [0.89, 0.94]** | 6.62 | **0.133** | 26% |
| Oracle (hindsight-optimal test subset) | 0.975 | 4.04 | — | — |

**Speedup at matched accuracy.** Each condition's accuracy-vs-cost curve comes from a stopping-threshold sweep.

| vs. | Matched accuracy | Speedup (cost ratio) | 90% CI | Accuracy ceiling within budget |
|---|---|---|---|---|
| Fixed checklist | 0.846 | **1.90×** | [1.47, 2.39] | 0.846 → 0.917 (+3 to +11 pts) |
| Random order | 0.896 | 1.85× | [1.19, 2.08] | 0.896 → 0.917 |
| EIG planner alone | 0.892 | 1.51× | [0.86, 1.64] (includes 1×) | 0.892 → 0.917 (+0 to +5 pts) |

What we can honestly claim:

* **vs. the standard fixed checklist:** about **1.9× less diagnostic cost** for the same accuracy, a 7-point higher
  accuracy ceiling, and **1.6× fewer human escalations** (42% → 26%).
* **vs. EIG planning alone:** most of the cost saving comes from information-gain planning (Cuddy). The adversarial
  team (House + Foreman) adds accuracy and calibration: 0.917 vs 0.883, Brier 0.133 vs 0.159. Below 0.88 accuracy,
  the team costs about 8% *more* than the planner alone. The 1.51× speedup is only at the planner's own ceiling, and its
  CI includes 1×.
* **Ablations** ([results/REPORT.md](results/REPORT.md)): removing Foreman drops accuracy to 0.896, and removing
  House's contrarian slot drops it to 0.900. Removing Cameron changes nothing, because literature is context and
  provenance only and never moves the posterior. Parallel dispatch *costs* a little (0.925 without it), since it
  commits a second test before seeing the first result. We report P exactly as pre-specified rather than retuning it
  on the blind set.
* **Real Kepler data (transfer test), a negative result we report as-is**
  ([results/REAL_REPORT.md](results/REAL_REPORT.md)). On 48 real KOIs, with tables calibrated on synthetic data, every
  condition is weak (0.38–0.54 accuracy) and the lab is overconfident: 11 confident-and-wrong verdicts. After
  Wilson's leave-one-out recalibration on the other real KOIs, confident-and-wrong drops from **11 to 2**. However,
  96% of cases are then escalated to a human, and accuracy is flat (0.48). **The synthetic speedup does not yet
  transfer to real data.** Closing that gap is the next experiment.

## The lab

| Agent | Owns the decision | Key behaviour |
|---|---|---|
| **House** (insight + verdict) | Non-obvious hypotheses; final verdict | "Everybody lies." Reads the raw signal for clues (e.g. *period = 2× momentum-dump spacing → artifact*), always names a contrarian, requests the test that would settle it. Hypotheses are tagged `agent_generated`. Cannot override the posterior. |
| **Cuddy** (planner + budget) | Which test next; when to stop | Scores every untested test by expected information gain per cost, plus House's bounded bonus. Always compares ≥ 2 tests and logs the runner-up. |
| **Chase** (experiment runner) | Executing approved tests | 8 real computational tests on the light curve: odd/even, secondary eclipse, trapezoid shape, stellar density (Seager & Mallén-Ornelas), centroid shift, Lomb-Scargle rotation, systematics coincidence, depth consistency. |
| **Foreman** (analysis + skeptic) | Is the result trustworthy | Data-trust checks; grades results ok/marginal/unreliable (flattens weak evidence). On a **surprise** it requests a counter-experiment (re-detrending) and blocks stopping until an independent test corroborates. |
| **Cameron** (literature + safety) | Which evidence applies | Method citations **resolved live against the arXiv API** (unresolvable → dropped) and OpenAlex search. Target-specific lookups are blocked (label leak). |
| **Wilson** (knowledge graph) | What the lab learned | Knowledge-graph edges, a `LessonLearned` per case (most decisive test, low-quality results), and adaptive table recalibration. |
| **Data Gatekeeper** | Who sees labels | Only component holding dispositions; agents get anonymized IDs. Audited: 0 label reads by agents. |

Full specs, handoff sequence and bounded-boldness rule: [docs/AGENTS.md](docs/AGENTS.md). Typed handoff payloads:
[plainsboro/schemas.py](plainsboro/schemas.py).

### Omnigent orchestration

[omnigent/princeton_plainsboro/](omnigent/princeton_plainsboro/) is an **Omnigent agent bundle**. The root agent is
`house`, with sub-agents `cuddy`, `chase`, `foreman`, `cameron` and `wilson`. Each has its own prompt, executor,
tool directory (`tools/python/*.py`, `@tool` functions) and guardrails. It passes Omnigent 0.16's own
`spec.parser` + `spec.validator`, and all 8 policies resolve and fire through Omnigent's `resolve_function_policy`
(`make omnigent-validate`; `tests/test_lab.py::test_omnigent_bundle_validates`).

* **Permissions by construction.** Only Chase's directory contains test-execution tools. House has no tool that runs
  tests or reads labels.
* **Policies as code** ([plainsboro/policies.py](plainsboro/policies.py),
  [configs/policies/policies.yaml](configs/policies/policies.yaml)) follow Omnigent's handler contract
  (`event → ALLOW | DENY | ASK`, `state_updates`):
  `budget_cap` (ASK a human to extend), `test_allowlist`, `no_label_access`, `no_target_specific_lookup`,
  `no_external_writes`, `human_approval_required` (follow-ups → ASK; "confirmed planet" → DENY),
  `provenance_required`, `low_confidence_needs_human`.
* **Shared research record.** A Differential Whiteboard per target plus an append-only JSONL ledger with
  input/output hashes, policy decisions, code hashes and cost. Every decision can be replayed.

The same agent classes and the *same policy functions* also run in a local runtime
([plainsboro/lab.py](plainsboro/lab.py)), with a policy engine that applies Omnigent semantics. The benchmark uses
the local runtime because it is deterministic, free and reproducible (7,000+ investigations). The Omnigent bundle adds
LLM reasoning, live collaboration and approvals on top of the identical tools.

### Live Omnigent run (verified)

The bundle was run end to end with `omnigent run`, using all six agents on **Claude Sonnet 5.5** via the
`claude-sdk` harness, on the curated case T-0167. The transcript, ledger, whiteboard and knowledge graph are in
[results/omnigent_run/](results/omnigent_run/).

* **The loop ran entirely through Omnigent.** House opened the case. Foreman checked data trust, and Cameron
  verified 9 arXiv sources and ran OpenAlex searches. Then came 5 rounds of Cuddy plan → Chase test → Foreman
  assessment, with Foreman's counter-experiments (odd/even and density re-detrending) dispatched to Chase. Cuddy
  stopped the loop, House issued the verdict and Wilson recorded the lesson: 32 ledger events in all.
* **The verdict was correct:** *likely false positive: stellar variability*, P(H4) = 0.942, 90% CI 0.86–0.98, using 5
  tests and 8.0 cost units. House set `needs_human = true` itself, because it judged the final periodogram evidence
  weak and wanted the 4-unit centroid test that the budget no longer allowed.
* **The LLM House found three real tool defects, which are now fixed:**
  * `issue_verdict` dropped its dissent; it now has a `dissent` argument that forces `needs_human`.
  * `record_lesson` could not store notes; it now takes `notes`.
  * Re-running a test that doesn't depend on detrending replicated identical output, so `rerun_vetting_test` now
    refuses those.
* **One of House's objections was wrong.** It claimed the periodogram doesn't mask transits, but `t_periodogram`
  excludes in-transit points.

```bash
# Omnigent route (open source), from the repo root, in the same environment as omnigent
pip install -e ".[omnigent,real]"
python scripts/patch_omnigent_windows.py   # Windows only, see below
set ANTHROPIC_API_KEY=...                  # or `omnigent setup` for Databricks or another provider
omnigent run omnigent/princeton_plainsboro -p "Diagnose target T-0167 using the full discovery loop."
```

**Windows notes (Omnigent 0.16).**
* Local Python `@tool` functions fail with `pass_fds not supported on Windows`.
  `scripts/patch_omnigent_windows.py` switches them to Omnigent's own stdout protocol. It is idempotent and
  reverts with `--revert`.
* The `claude-sdk` harness needs `claude.exe`. The Windows x64 wheel `claude-agent-sdk==0.2.159` bundles it, but
  0.2.163 has no Windows wheel.
* Set `PYTHONUTF8=1` so the host tunnel doesn't crash on non-ASCII console output.

Managed route: open `<workspace-url>/omnigent` → New session → Sandbox, upload the repo and run `pip install -e .`,
then run the bundle. Every agent pins `model: claude-sonnet-5-5` in its `executor`; change it to a model your
provider serves.

## Quick start

```bash
python -m venv .venv && .venv/Scripts/activate        # (Linux/macOS: source .venv/bin/activate)
pip install -e ".[demo,dev,real,omnigent]"

python -m plainsboro.eval.calibrate                    # likelihood tables from the CALIBRATION split only (~1.5 min)
python -m streamlit run app/streamlit_app.py           # live demo UI
python -m plainsboro.cli investigate T-0167            # same loop in the terminal
python -m pytest -q                                    # 13 tests: physics, planner math, policies, leak canary, Omnigent bundle

python -m plainsboro.eval.run_benchmark                # full matched-condition benchmark (~4 min)
python -m plainsboro.eval.analyze                      # -> results/REPORT.md, results/summary.json, results/figures/
python -m plainsboro.data.kepler --per-class 12        # optional: 48 real KOIs from NASA Exoplanet Archive + MAST
python -m plainsboro.eval.run_real                     # -> results/REAL_REPORT.md
```

`make benchmark`, `make demo`, `make test` and `make real` wrap the same commands. Seeds, budgets and thresholds live
in [configs/experiment.yaml](configs/experiment.yaml).

### Live AI research (Gemini or Claude)

Cameron can research each question on the spot. At intake, and again every time the leading hypothesis flips, she
searches arXiv and OpenAlex live for papers on *leader vs. contrarian* and hands the titles and abstracts to an LLM,
which writes a 2–4 point brief ([plainsboro/research.py](plainsboro/research.py)). Guardrails: the query must pass
`no_target_specific_lookup` first; the model replies in JSON and may cite only IDs that were actually retrieved
(anything else is stripped and shown as removed); the brief is context only and never moves the posterior.

```bash
cp .env.example .env          # then put ONE key in it: GEMINI_API_KEY=... or ANTHROPIC_API_KEY=...
```

Alternatively, paste a key into **3 · AI research → Set API key** in the app's sidebar. Provider order is Anthropic
(`claude-sonnet-5-5`), then Gemini (`gemini-flash-latest`, falling back to `gemini-3.5-flash` and the lite models
when a free-tier quota runs out), then OpenAI. `PP_LLM_PROVIDER` and `PP_LLM_MODEL` override. On a shared deployment
set `PP_ALLOW_KEY_ENTRY=0` and supply the key through the host's secrets. Without a key, the lab still runs and
lists the retrieved papers unread. On the free Gemini tier, a brief takes 20–40 s.

### Demo UI ([app/streamlit_app.py](app/streamlit_app.py))

The scientist sets the objective in the sidebar (case set, target, stopping threshold, budget), then steps through the
loop: **Next step / Run to next decision / Run to verdict**. Chase runs the tests live on the light curve. The panel
shows the raw and folded light curve (odd vs even, phase 0.5), every agent handoff, Cuddy's scored test table each
round, the posterior trajectory, approval gates with **Approve / Deny**, and the verdict card (credible interval,
dissent, follow-ups, provenance). Ground truth is revealed by the Gatekeeper only after the verdict. Other tabs show
the benchmark report, the run ledger with policy decisions, a "try forbidden actions" policy self-check, the agent
specs and the calibrated likelihood tables.

★ Curated demo cases are chosen by rule from blind-set results (not tuned on):

* **T-0167, leader flips 3×.** Planet (36%) → odd/even 6.1σ, the detrending control holds → EB (66%) → transit-derived
  stellar density far too low → blend (65%) → rotation periodogram matches the period → spots (90%). Foreman blocks
  stopping until depth consistency corroborates → **stellar variability, P = 0.96 (90% CI 0.91–0.99)**. Correct.
* A clean planet candidate, which triggers the human-gated follow-up proposal; a blended EB; and an honest failure
  that was escalated to a human.

### Two-minute demo script

| Time | Show |
|---|---|
| 0:00–0:15 | The bottleneck: thousands of dips, most are not planets; which test next, and when to stop? |
| 0:15–0:40 | T-0167: House's differential with agent-generated hypotheses; Cuddy's table comparing EIG/cost of 8 tests |
| 0:40–1:10 | Chase runs odd/even; Foreman flags SURPRISE and runs the detrending counter-experiment; posterior flips; House says REOPEN |
| 1:10–1:30 | Two more flips; Foreman blocks stopping until corroboration; verdict with CI, dissent, citations (resolved arXiv IDs) |
| 1:30–1:50 | Benchmark tab: accuracy-vs-cost frontier; 1.9× vs checklist, team vs planner ablation |
| 1:50–2:00 | Real-Kepler transfer gap: what the lab learned, and the next experiment |

## Scientific rigor and responsibility

* **Leakage controls.** Labels are held only by the Data Gatekeeper (audit: 8,160 evaluator reads, 240
  adaptive-mode reads, **0 agent reads**). Targets are anonymized (`T-####`, `K-####`). Archive false-positive flag
  columns are treated as labels and stripped. A label-leak canary test checks that queries naming
  KOI/Kepler/KIC/TOI/the target ID are DENIED.
* **Splits.** The calibration split (600 synthetic cases) is the only data used for likelihood tables and the temper
  τ, chosen by 2-fold CV log-loss. The blind split (240 cases) is used for every reported number. Splits are fixed by
  seed before any agent runs.
* **Matched conditions.** Outcomes are precomputed once per target, so all conditions see identical evidence; only
  the orchestration differs. Paired Wilcoxon tests and bootstrap CIs are reported.
* **Uncertainty.** Credible intervals come from Dirichlet resampling of the likelihood tables. Dissent is recorded.
  Verdicts below the threshold, or with open critiques, are `needs_human`.
* **Citations.** All 8 method references resolve against the arXiv API (titles checked). Cameron drops unresolvable
  sources rather than citing them.
* **Claims.** The system outputs *vetting recommendations* ("planet candidate", "likely false positive: …"). Policy
  forbids "confirmed/validated planet". Follow-up observations (imaging, RV) are proposals that need human approval;
  the lab never writes to external services.

### Known limitations (validation still needed before real-world use)

1. **Headline numbers are synthetic.** The injected mechanisms are simplified: a uniform-disk-overlap transit model
   with limb-darkened intensity, Gaussian spot dips, momentum-dump box dips and point-source centroid shifts. Real
   data are harder, as the transfer test shows.
2. **Conditional independence.** Tests share data (shape and density share one fit), so posteriors can be
   overconfident. Tempering is fitted (τ = 1.0 was CV-optimal on synthetic data), but on real data this
   overconfidence is visible.
3. **Coarse real labels.** "Not transit-like" KOIs merge H4 and H5. One Kepler quarter per target; one-quarter
   centroids are much weaker than DR25 difference imaging.
4. **B0 (single LLM agent) was run on only 40 targets.** Claude Sonnet 5.5 used the same tools, budget and cached
   outcomes on the first 40 blind targets ([results/benchmark/b0_llm.jsonl](results/benchmark/b0_llm.jsonl)). On
   those same 40 targets, B0 reached accuracy 0.85 at mean cost 7.83 with Brier 0.281. The House team reached 0.95
   at cost 6.30, the planner alone 0.90 at 5.42, and the checklist 0.90 at 6.70. B0 used 216k input and 32k output
   tokens. With n = 40 the CIs are wide, so treat this as indicative.
5. **Only one live Omnigent case has been run.** It was T-0167, run once. Benchmark numbers come from the
   deterministic local runtime, which uses the same agents, tools and policies. LLM-driven Omnigent runs will vary
   from run to run, and their accuracy across many targets has not been measured.
6. Wall-clock: the team's deliberation adds ~70 ms per target over the bare planner in the local runtime; with
   LLM-driven Omnigent agents, per-target latency is dominated by model calls.

## What the lab learned, and the next experiment

* **Learned (synthetic).** Information-gain planning is where most of the cost saving comes from. The adversarial
  layer buys accuracy and calibration, and it catches detrending-sensitive and uncorroborated surprises. Wilson's lessons (most decisive test per case, 240 blind cases) are: systematics in 113 cases, odd/even in 46,
  shape in 29, density in 20, secondary in 18, periodogram in 13, centroid in 1. Cuddy ran the 4-unit pixel-level
  centroid test in only 20% of cases, so cheap tests do most of the work.
* **Learned (real).** Likelihood tables do not transfer from synthetic to Kepler. Real-data recalibration fixes
  overconfidence first (11 → 2 confident errors) but needs far more labelled KOIs to recover accuracy.
* **Next experiment (computational).** Calibrate on ~2,000 DR25 KOIs using all quarters, with a held-out real blind
  split. Replace the independence assumption with a learned joint likelihood. Then re-measure the speedup on real
  data, and on TESS TOIs to test cross-mission transfer.
* **Path to 10× at scale (argued, not claimed).** Combine (a) the 1.9× cost reduction, (b) auto-resolving the
  confident ~74% while escalating only the ambiguous cases (human effort currently 1.6× lower than the checklist), and
  (c) parallel dispatch across thousands of targets. Those multiply, but only once (d) the real-data calibration gap
  is closed. The oracle (4.04 cost units at 0.975 accuracy) shows the planning headroom that remains.
* **Physical (human-gated).** For confident, low-dissent planet candidates, prioritized high-resolution imaging and
  RV proposals. These are queued for a scientist, never executed.

## Repository map

```
configs/experiment.yaml           budgets, thresholds, seeds, data sizes
configs/policies/policies.yaml    policy catalogue (paths, arguments, rules)
omnigent/princeton_plainsboro/    Omnigent bundle: house (root) + agents/{cuddy,chase,foreman,cameron,wilson}
plainsboro/
  data/synth.py                   synthetic injection set (5 mechanisms, real-noise-like LCs, momentum dumps, centroids)
  data/kepler.py                  real KOIs: NASA Exoplanet Archive TAP + MAST (lightkurve), anonymized
  data/gatekeeper.py              Data Gatekeeper (labels, audit log)
  vetting/registry.py             8 vetting tests with costs, outcome bins, method references
  planner/                        likelihood tables, posterior update, EIG, cached outcomes
  agents/                         house, cuddy, chase, foreman, cameron, wilson
  lab.py                          discovery-loop orchestrator (generator of events, approval gates)
  policies.py                     Omnigent-contract policies + PolicyEngine
  record/                         whiteboard + append-only ledger
  omnigent_tools.py               file-backed tool layer used by the Omnigent bundle
  literature.py                   arXiv resolver + search, OpenAlex search, curated method references
  research.py                     Cameron's live research: search now, LLM brief with citation allow-list
  llm.py                          LLM providers (Anthropic, Gemini, OpenAI), narrator, single-agent baseline B0
  eval/                           calibrate, run_benchmark, analyze, run_real
app/streamlit_app.py              live demo
results/                          REPORT.md, REAL_REPORT.md, summary.json, figures/, benchmark ledgers & records
tests/test_lab.py                 13 tests
submission/                       hackathon summary, video scripts, one-pager (make_onepager.py), dataset card
.env.example                      where the LLM API key goes (.env is git-ignored)
```

### Design-document mapping

| Design section | Implementation |
|---|---|
| 3.2 hypothesis space H1–H5 | `config.HYPOTHESES`; synthetic mechanisms in `data/synth.py` |
| 3.4 leakage controls | `data/gatekeeper.py`, `policies.no_label_access`, `no_target_specific_lookup`, anonymized IDs |
| 5 agents / 7 schemas | `agents/*`, `schemas.py`, `omnigent/princeton_plainsboro/**/config.yaml` |
| 6 whiteboard + ledger | `record/whiteboard.py`, `record/ledger.py` |
| 8 policies | `policies.py`, attached as Omnigent guardrails |
| 9.1 test registry | `vetting/registry.py` (all 8 tests incl. density + centroid) |
| 9.2–9.3 likelihood tables, EIG/cost | `planner/likelihood.py`, `planner/posterior.py`, `agents/cuddy.py` |
| 9.4–9.6 debate, reopen, stopping | `agents/house.py`, `agents/foreman.py`, `lab.py` |
| 12 baselines, ablations, oracle, statistics | `eval/run_benchmark.py`, `eval/analyze.py` |
| 12.6 controls | label-leak canary test, detrending-sensitivity reruns, fixed splits |

## Team

Built for the Hack-Nation 7th Global AI Hackathon by [FAZ610](https://github.com/FAZ610), [IshaanM05](https://github.com/IshaanM05) and [SSM11011](https://github.com/SSM11011).
