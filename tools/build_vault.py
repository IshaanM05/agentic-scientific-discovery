"""One-off generator for the knowledge/ vault (atomic notes + index + Obsidian config).
Edit the dicts below and re-run to regenerate; hand-edited notes are overwritten, so edit notes directly once the project is underway.
"""
import json
from pathlib import Path

K = Path(__file__).resolve().parent.parent / "knowledge"

PAPERS = {
    "co-scientist": (2025, "arxiv.org/abs/2502.18864", """# Google AI Co-Scientist
**One line:** Gemini multi-agent system, generate-debate-evolve with a tournament (Generation, Reflection, Ranking, Evolution, Proximity, Meta-review agents).
**Key result:** quality improves with more test-time compute; validated on AML repurposing, liver-fibrosis targets, bacterial gene transfer.
**Limit:** experts still pick candidates; the wet lab was done by humans.
**Use for us:** [[hypothesis-arena]]. Links: [[robin]], [[loop-structure]]"""),
    "robin": (2025, "arxiv.org/abs/2505.13400", """# Robin (FutureHouse)
**One line:** literature plus data-analysis agents in a lab-in-the-loop cycle; proposed ripasudil for dry AMD, then an RNA-seq follow-up that surfaced ABCA1.
**Limit:** semi-autonomous; humans run the experiments.
**Use for us:** closest full-loop reference for [[loop-structure]]. Links: [[co-scientist]], [[kosmos]]"""),
    "kosmos": (2025, "arxiv.org/abs/2511.02824", """# Kosmos
**One line:** runs up to 12 h; parallel data-analysis and literature agents share a structured world model; every claim cites code or a paper.
**Key result:** 79.4% of report statements judged accurate by independent scientists; 7 discoveries; about 200 rollouts, 42k lines of code, 1,500 papers per run.
**Use for us:** [[belief-state]] design and the citation-for-every-claim rule. Links: [[robin]]"""),
    "ai-scientist": (2024, "arxiv.org/abs/2408.06292", """# The AI Scientist v1/v2 (Sakana)
**One line:** idea, code, experiments, paper, simulated review; v2 (arxiv.org/abs/2504.08066) adds agentic tree search and a manager agent.
**Limit:** ML domain, not physical science.
**Use for us:** experiment-manager pattern; automated review as a judge. Links: [[judge-calibration]]"""),
    "alphaevolve": (2025, "arxiv.org/abs/2506.13131", """# AlphaEvolve (DeepMind)
**One line:** evolutionary coding agent; an LLM proposes edits, automated evaluators score them, the loop evolves.
**Use for us:** propose-evaluate-evolve pattern for the arena. Links: [[hypothesis-arena]]"""),
    "biodiscoveryagent": (2024, "arxiv.org/abs/2405.17631", """# BioDiscoveryAgent
**One line:** an LLM picks which genes to perturb, with no trained model and no acquisition function.
**Key result:** about 21% better than BO baselines across six datasets and 46% better on non-essential genes; includes one unpublished dataset to avoid leakage.
**Use for us:** the pure-LLM baseline and Perturb-seq replay data. Links: [[baselines-and-evaluation]], [[replay-oracle]]"""),
    "lgbo": (2026, "arxiv.org/html/2605.17976v1", """# LGBO (LLM-guided Bayesian optimization)
**One line:** LLM preferences shift the GP surrogate mean at every iteration.
**Key result:** wet-lab Fe-Cr electrolyte task reached 90% of the best value in 6 iterations versus more than 10 for BO and LLM baselines; claimed not much worse than BO in the worst case.
**Use for us:** [[llm-guided-bo]] core method. Links: [[awcd-language-priors]]"""),
    "awcd-language-priors": (2026, "doi:10.1021/acs.jcim.6c00976", """# Language-guided priors and AWCD
**One line:** an LLM turns expert prose into a BO prior mean and constraints; AWCD switches the prior off when data contradict it.
**Use for us:** the trust meter in [[llm-guided-bo]]. Links: [[lgbo]]"""),
    "a-lab": (2023, "chemistryworld.com / cen.acs.org (2026 correction)", """# A-Lab (Berkeley)
**One line:** robotic solid-state synthesis, claimed about 41-43 new materials in 17 days.
**Limit:** disputed by independent analysis; Nature published an Author Correction in Jan 2026.
**Use for us:** state novelty cautiously and add an independent verification step. Links: [[judge-calibration]]"""),
    "chemcrow": (2024, "arxiv.org/abs/2304.05376", """# ChemCrow
**One line:** an LLM plus 18 chemistry tools.
**Key result:** LLM-based grading rated it about equal to GPT-4, while expert chemists rated it far better.
**Use for us:** never let an LLM grade its own work unchecked. Links: [[judge-calibration]]"""),
    "coscientist-boiko": (2023, "nature.com/articles/s41586-023-06792-0", """# Coscientist (Boiko et al.)
**One line:** a GPT-4 agent with search, code execution and robotic lab control.
**Use for us:** tool-use anatomy; the safety result (4 of 11 weapons-agent requests accepted) is from Lilian Weng's post and is unverified here. Links: [[safety-gate]]"""),
    "benchmarks": (2025, "various", """# Benchmarks
ScienceAgentBench (ICLR 2025), MLE-bench, MLAgentBench (37.5% average success, 0% on post-cutoff tasks, so contamination matters), BixBench.
Unverified names: PaperBench, LAB-Bench, DiscoveryBench.
**Use for us:** the held-out data rule in [[baselines-and-evaluation]]."""),
}
UNVERIFIED = {"benchmarks"}  # partly unverified

CONCEPTS = {
    "loop-structure": """# Loop structure
Hypothesize, design, run, analyze, update belief, decide next. Sources: [[robin]], [[co-scientist]], Periodic Labs (unverified, from teammate notes).
**Our choice:** a PI step picks explore / exploit / replicate / stop under a budget. Backlog: T001.""",
    "hypothesis-arena": """# Hypothesis arena
A generator proposes N hypotheses, a critic attacks them, a ranker runs pairwise Elo. Every hypothesis states a testable prediction and a kill condition.
Evidence: [[co-scientist]], [[alphaevolve]]. Backlog: T004.""",
    "llm-guided-bo": """# LLM-guided Bayesian optimization
The LLM proposes and constrains the candidate pool; the acquisition function picks the batch. A trust meter drops the prior when data contradict it.
Evidence: [[lgbo]], [[awcd-language-priors]]. Counterpoint: [[biodiscoveryagent]] (no BO). Backlog: T005.
**Report honestly if it does not beat pure BO.**""",
    "belief-state": """# Belief state / lab notebook
Every hypothesis with status, every experiment, every negative result, with provenance. Every claim cites a log line, code cell or paper.
Evidence: [[kosmos]]. Store in SQLite. Backlog: T001.""",
    "replay-oracle": """# Replay oracle
A dataset-backed lab: run(protocol) returns result, cost and duration. Deterministic with a seed.
Candidates: Materials Project (API key needed), Perturb-seq screens ([[biodiscoveryagent]]). Matbench Discovery and JARVIS are unverified. Backlog: T002.""",
    "judge-calibration": """# Judge and calibration
A rubric-based judge gives each conclusion a confidence label. Calibrate against expert-like labels where possible, and say when we could not.
Evidence: [[chemcrow]] (LLM grader blind spot), [[a-lab]] (overclaiming), [[ai-scientist]] (automated review). Backlog: T006.""",
    "safety-gate": """# Safety gate
Screen protocols for hazardous chemistry or biology; require human sign-off above a risk level; include a test case that must be blocked.
Evidence: [[coscientist-boiko]]. Backlog: T006.""",
    "baselines-and-evaluation": """# Baselines and evaluation
Random, one-factor-at-a-time, pure BO, single-LLM (same model as ours), and the full system. Same budget and seeds, at least 5 seeds. Metric: experiments to first k hits.
Ablate arena, BO, negative memory and judge. Use held-out data ([[benchmarks]]). Report the real speedup even if it is below 10x. Backlog: T003.""",
}

INDEX = """# INDEX (map of content; open only what you need)
## Project
- Brief and rules: [[../docs/HACKATHON_BRIEF]] | Prior-work digest: [[../docs/REFERENCES]]
- Live state: [[../coord/HANDOFF]] | [[../coord/BACKLOG]] | [[../coord/SCOREBOARD]]
## Concepts (our design)
[[loop-structure]] · [[hypothesis-arena]] · [[llm-guided-bo]] · [[belief-state]] · [[replay-oracle]] · [[judge-calibration]] · [[safety-gate]] · [[baselines-and-evaluation]]
## Papers
Full loop: [[co-scientist]] · [[robin]] · [[kosmos]] · [[ai-scientist]] · [[alphaevolve]]
Experiment selection: [[biodiscoveryagent]] · [[lgbo]] · [[awcd-language-priors]]
Labs and cautions: [[a-lab]] · [[chemcrow]] · [[coscientist-boiko]]
Evaluation: [[benchmarks]]
## Decisions
(add ADRs in decisions/ and list them here)
## Gaps we claim
Few systems choose the next experiment under a budget, and same-budget baseline comparisons are rare. See [[baselines-and-evaluation]].
"""

for d in ("papers", "concepts", "decisions", "templates", ".obsidian"):
    (K / d).mkdir(parents=True, exist_ok=True)

for name, (year, url, body) in PAPERS.items():
    status = "partly-unverified" if name in UNVERIFIED or name == "coscientist-boiko" else "verified"
    (K / "papers" / f"{name}.md").write_text(
        f"---\ntype: paper\nstatus: {status}\nyear: {year}\nurl: {url}\n---\n{body}\n", encoding="utf-8")

for name, body in CONCEPTS.items():
    (K / "concepts" / f"{name}.md").write_text(f"---\ntype: concept\n---\n{body}\n", encoding="utf-8")

(K / "00-INDEX.md").write_text(INDEX, encoding="utf-8")
(K / ".obsidian" / "app.json").write_text(json.dumps(
    {"useMarkdownLinks": False, "newLinkFormat": "shortest", "alwaysUpdateLinks": True}), encoding="utf-8")
(K / ".obsidian" / "graph.json").write_text(json.dumps({
    "colorGroups": [
        {"query": "path:papers", "color": {"a": 1, "rgb": 5431378}},
        {"query": "path:concepts", "color": {"a": 1, "rgb": 14701138}},
        {"query": "path:decisions", "color": {"a": 1, "rgb": 14120960}}],
    "showOrphans": True}), encoding="utf-8")
print("papers", len(PAPERS), "concepts", len(CONCEPTS))
