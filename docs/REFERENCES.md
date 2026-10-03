# Research References & Inspirations: Agentic Scientific Discovery

Hack-Nation Challenge 3: "Use multiple AI agents to research, form hypotheses, plan and run experiments, learn from the results, and decide what experiment should happen next."

See also [HACKATHON_BRIEF.md](HACKATHON_BRIEF.md) for the organizers' rules, timeline, judging criteria and submission checklist.

Notes on reliability: items marked **[verified]** were checked against the paper abstract or publisher page. Items marked **[from Shibam's notes]** come from the teammate chat and the Periodic / Lilian Weng posts; I have not re-checked them. Items marked **[unverified]** are known names I did not open this session, so check them before putting numbers on a slide.

---

## 1. Direct competitors / state of the art (name-drop these)

| System | What it does | Why it matters for us | Source |
|---|---|---|---|
| **Google AI Co-Scientist** (Gottweis et al., 2025; Nature 2026) | Gemini multi-agent system. Agents: Generation, Reflection, Ranking, Evolution, Proximity, Meta-review. A "generate, debate, evolve" loop with a tournament. Validated on AML drug repurposing, liver-fibrosis targets, and bacterial gene-transfer mechanism. **[verified]** | Template for our **hypothesis arena** (Elo tournament). Its test-time-compute scaling shows quality improves with more debate. | arxiv.org/abs/2502.18864 |
| **Robin** (FutureHouse, 2025; Nature 2026) | Literature agents plus data-analysis agents in a lab-in-the-loop cycle. Proposed ripasudil for dry AMD, then proposed a follow-up RNA-seq that surfaced ABCA1. All steps logged. **[verified]** | The closest "full-loop" reference. Honest limitation: it is semi-autonomous, with humans doing the wet lab. | arxiv.org/abs/2505.13400 |
| **Kosmos** (Edison/FutureHouse, Nov 2025) | Runs up to 12 h; parallel data-analysis and literature agents share a **structured world model**; 200+ rollouts, ~42k lines of code and ~1,500 papers per run. 79.4% of report statements judged accurate by scientists; 7 discoveries. Every claim cites code or literature. **[verified from abstract]** | Our **belief-state / lab-notebook** design should copy the "world model + citation for every claim" idea. Also a useful honest-accuracy number (79.4%). | arxiv.org/abs/2511.02824 |
| **The AI Scientist v1 / v2** (Sakana, 2024/2025) | Idea, then code, then experiments, then paper, then simulated peer review. v2 adds **agentic tree search** and a manager agent; produced a workshop paper that passed peer review. **[verified]** | Reference for the tree-search experiment manager and for automated review as a judge. Domain is ML, not physical science. | arxiv.org/abs/2408.06292, arxiv.org/abs/2504.08066 |
| **AlphaEvolve** (DeepMind, 2025) | Evolutionary coding agent: an LLM proposes code edits, evaluators score them, and the loop evolves programs. Found new algorithms and data-centre scheduling gains. **[verified]** | Evidence for "LLM proposes, an automated evaluator selects, and evolution iterates". Fits the arena and the replay oracle. | arxiv.org/abs/2506.13131 |
| **InternAgent-1.5** (2026) | Generation, verification and evolution subsystems; computational plus lab experiments. **[title/abstract only]** | Recent long-horizon framework to compare against. | alphaxiv.org/abs/2602.08990 |
| **Deep Research / "Rethinking the AI Scientist"** (Jan 2026) | Interactive multi-agent workflow with persistent world state, semi-autonomous mode with human checkpoints, minutes-per-cycle. 48.8% open / 64.4% MC on BixBench. **[verified]** | Supports our human-checkpoint design and "fast cycle" pitch. | arxiv.org/abs/2601.12542 |
| **SciAgents** (MIT, Buehler, 2024) | Ontological knowledge graph, multi-agent reasoning and in-situ learning for bio-inspired materials. **[verified]** | Idea: use a knowledge graph to seed hypotheses (relevant to the materials domain). | arxiv.org/abs/2409.05556 |

## 2. Agents that actually run experiments (chemistry / bio)

- **Coscientist** (Boiko et al., Nature 2023): GPT-4 agent with web/doc search, code execution and robotic lab control. Planned and ran chemistry experiments. Its safety test is in Weng's post. **[verified]** nature.com/articles/s41586-023-06792-0
- **ChemCrow** (Bran et al., Nat. Mach. Intell. 2024): LLM plus 18 expert tools. Experts rated it better than GPT-4 alone, while LLM-based evaluation rated them roughly equal. Use this as the argument for a **calibrated judge**. **[verified]** arxiv.org/abs/2304.05376
- **BioDiscoveryAgent** (Roohani et al., 2024): LLM chooses which genes to perturb with no trained model and no acquisition function. About 21% better than Bayesian-optimization baselines across six datasets, and 46% better on the non-essential-gene task. Includes one unpublished dataset to avoid training-data leakage. **[verified]** arxiv.org/abs/2405.17631
  - **This is our best evidence for the pure-LLM baseline**, and a ready-made replay dataset family (Perturb-seq).
- **ChemAgents** (JACS 2025): hierarchical multi-agent robotic chemist (Task Manager plus Literature Reader, Experiment Designer and others) on an on-board Llama-3.1-70B. **[search summary]** pubs.acs.org/doi/10.1021/jacs.4c17738
- **SciToolAgent** (Nat. Comput. Sci. 2025): knowledge-graph-driven selection among hundreds of science tools. **[search summary]** nature.com/articles/s43588-025-00849-y
- **A-Lab** (Berkeley, Nature 2023): robotic solid-state synthesis, with a claim of about 41 to 43 new materials in 17 days. The claim was **disputed** (an independent analysis concluded no new materials were made; the paper received an Author Correction in Jan 2026, and C&EN reports some questions remain). **[verified via news pages]**
  - Takeaway for us: state novelty claims cautiously and have an independent verification step. Sources: chemistryworld.com/news/new-analysis-raises-doubts-over-autonomous-labs-materials-discoveries/4018791.article and cen.acs.org/research-integrity/Nature-robot-chemist-paper-corrected/104/web/2026/01
- **Periodic Labs** [from Shibam's notes]: the posts at periodic.com/news. Key points: a hypothesize, synthesize, characterize loop; the harness matters (about 3.8x higher XRD analysis success than a generic Claude Code harness); an LLM judge calibrated against experts; don't leave compute idle while the lab runs.
- **Lilian Weng, "LLM Powered Autonomous Agents"** [from Shibam's notes]: planning, memory and tool-use anatomy, plus the ChemCrow evaluation caveat and the Boiko safety result (4 of 11 weapons-agent synthesis requests accepted).

## 3. "LLM proposes, Bayesian optimization decides" (our technical differentiator)

- **LGBO, LLM-Guided Bayesian Optimization** (May 2026): LLM preferences shift the GP surrogate mean in every iteration. It claims never much worse than standard BO in the worst case. On a wet-lab Fe-Cr electrolyte task it reached 90% of the best value in 6 iterations, versus more than 10 for BO and other LLM-augmented methods. **[verified from abstract]** arxiv.org/html/2605.17976v1
- **Language-guided priors for chemical experiments** (J. Chem. Inf. Model. 2026): an LLM parses expert prose into a BO prior mean and constraints. It includes **AWCD**, a credibility detector that switches the prior off when the data contradict it. **[verified from abstract]**
  - Directly reusable: put an "LLM-prior trust meter" in our design. The agent loses faith in its own hypothesis when the data disagree, which is also a good demo moment.
- **AutoLead** (bioRxiv 2025): LLM-guided BO for multi-objective lead optimisation. **[title only]**
- **LLMs as uncertainty-calibrated optimizers** (Nat. Mach. Intell. 2026). **[title only]** nature.com/articles/s42256-026-01283-z
- **FunSearch** (DeepMind 2023, Nature 2023/24). **[unverified, from memory]** Same "LLM generates, evaluator scores, evolve" pattern as AlphaEvolve.

## 4. Benchmarks and evaluation designs we can borrow

- **ScienceAgentBench** (ICLR 2025, OSU NLP): rigorous evaluation of agents on data-driven discovery tasks. github.com/OSU-NLP-Group/ScienceAgentBench **[verified exists]**
- **MLE-bench** (OpenAI) and **MLAgentBench** (Stanford): evaluation of ML-experimentation agents. MLAgentBench found a 37.5% average success rate, ranging from 100% on old datasets to 0% on new ones. **[verified]** The lesson is **contamination**, so use held-out or unpublished data as BioDiscoveryAgent did. A follow-up shows search policy and operator design matter most: Greedy, MCTS and Evolutionary search lifted the MLE-bench lite medal rate from 39.6% to 47.7%. **[verified]** arxiv.org/abs/2507.02554
- **BixBench** (computational biology), used by Deep Research above. **[verified as a benchmark name]**
- Other names to check: PaperBench, LAB-Bench, DiscoveryBench. **[unverified]**
- **Survey / reading lists:** "A Survey of LLM-based Scientific Agents" (arxiv.org/pdf/2503.24047) and github.com/tsinghua-fib-lab/Awesome-AI-Scientists. **[verified exists]**

## 5. Cross-cutting design lessons

1. **Loop structure.** Hypothesize, design, run, analyze, update belief, decide next (Robin, Co-Scientist, Periodic).
2. **Shared structured world model** with a citation for every claim (Kosmos). It is cheap to build and makes outputs traceable.
3. **Tournament / debate for hypothesis quality** (Co-Scientist). Quality grows with test-time compute.
4. **LLM prior plus a statistical selector** (LGBO, AWCD, BioDiscoveryAgent as the pure-LLM counterpoint). The experiment-selection step is where we differentiate.
5. **Calibrated, rubric-based judge** (ChemCrow caveat, Periodic). Never let the LLM grade itself unchecked.
6. **Honest evaluation:**
   - Compare against random, pure BO, single-LLM and full-system baselines, on the same budget.
   - Use held-out data to avoid contamination.
   - Report modest speedups truthfully (A-Lab, Kosmos coverage show what overclaiming costs).
7. **Safety gate and human checkpoints** (Boiko 4 of 11, Deep Research semi-autonomous mode).
8. **Replayable "lab" oracle** built from existing data, so the loop runs in minutes (Periodic, BioDiscoveryAgent).

## 6. Suggested replay-oracle datasets (to check before committing)

- Materials Project (mp-api / pymatgen). Needs a free API key. **[from Shibam's notes]**
- Published Perturb-seq / CRISPR screens (as used by BioDiscoveryAgent). **[verified as used in the paper]**
- Matbench Discovery / JARVIS. **[unverified]**

## 7. Gaps we can claim

- Most systems generate hypotheses well, but few **choose the next experiment under an explicit budget** and learn from negative results.
- None of the verified systems ran without skilled human supervision. Robin's unsupervised bioinformatics performance was about 15% **[from Shibam's notes]**.
- Controlled, same-budget comparisons against BO and single-LLM baselines are rare in the published system papers I reviewed, so a clean "experiments to first k hits" curve would be a real contribution.
