# INDEX (map of content; open only what you need)
## Project
- Brief and rules: [[../docs/HACKATHON_BRIEF]] | Prior-work digest: [[../docs/REFERENCES]]
- Live state: [[../coord/HANDOFF]] | [[../coord/BACKLOG]] | [[../coord/SCOREBOARD]]
- OFFICIAL brief (wins over everything): [[../docs/CHALLENGE_BRIEF]] | Mandatory layer: [[omnigent]]
## Concepts (our design)
[[loop-structure]] · [[hypothesis-arena]] · [[llm-guided-bo]] · [[belief-state]] · [[replay-oracle]] · [[judge-calibration]] · [[safety-gate]] · [[baselines-and-evaluation]]
Omnigent (mandatory orchestration): [[omnigent-yaml]] install, tool/sub-agent/policy YAML, auth (T000 recon)
## Papers
Full loop: [[co-scientist]] · [[robin]] · [[kosmos]] · [[ai-scientist]] · [[alphaevolve]]
Experiment selection: [[biodiscoveryagent]] · [[lgbo]] · [[awcd-language-priors]]
Labs and cautions: [[a-lab]] · [[chemcrow]] · [[coscientist-boiko]]
Evaluation: [[benchmarks]]
## Datasets
[[steel-strength]] (primary replay oracle) · [[expt-gap]] (fallback)
## Decisions
[[ADR-001-replay-dataset]] replay oracle = steel_strength, hit yield >= 2000 MPa, B = 60
(add ADRs in decisions/ and list them here)
## Gaps we claim
Few systems choose the next experiment under a budget, and same-budget baseline comparisons are rare. See [[baselines-and-evaluation]].
