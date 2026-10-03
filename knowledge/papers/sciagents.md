---
type: paper
status: verified-first-third-only
year: 2024
url: arxiv.org/abs/2409.05556
---
# SciAgents (Ghafarollahi and Buehler, MIT)
**One line:** multi-agent system that samples paths from an ontological knowledge graph (about 1,000 papers, bio-inspired materials) and has agents turn each path into a structured research hypothesis.
**Agents:** Ontologist (defines concepts and relations on the path), Scientist 1 (drafts the hypothesis), Scientist 2 (expands it with quantities, simulation and experiment plans), Critic (reviews and amends), plus in the autonomous variant a Planner and an Assistant that checks novelty with the Semantic Scholar API. Two modes: a fixed pipeline, and a self-organizing group with human-in-the-loop.
**Key ideas:** random path sampling (more concepts, more novelty) instead of the shortest path; a seven-key JSON hypothesis (hypothesis, outcome, mechanisms, design principles, unexpected properties, comparison, novelty); hierarchical expansion then critique.
**Limit (as read):** it generates and critiques hypotheses; it runs no experiment, and its numbers (for example a predicted 1.5 GPa) are model-generated, not measured. I read only the first third of the paper, so its evaluation and limitations sections are unread.
**Use for us:** a hypothesis schema with a quantitative prediction ([[hypothesis-arena]]); a novelty-check tool in the literature agent; an adversarial critic. Contrast: we close the loop with measured results. Links: [[co-scientist]], [[kosmos]]
