# Research knowledge graph

One graph per run connecting **question, hypotheses, experiments, citations, findings and decisions**, so a reader can follow how a result changed the next decision. It is the Knowledge graph role from the challenge brief. Open `docs/kg.html` (works offline, phone width) and click a node for its evidence and source id; clicking a finding highlights the chain from the experiment that produced it to the decision it changed.

## What the edges mean
| type | from -> to | |
|---|---|---|
| tests | experiment -> hypothesis | the experiment was run or analysed against it |
| supports / refutes | finding -> hypothesis (supports also -> question) | verdict from the analysis or evaluator |
| cites | hypothesis -> citation | citation ids listed on the hypothesis |
| caused_decision | finding (or hypothesis) -> decision | evidence available before that decision |
| reopens | finding -> hypothesis | an assumption or prior was put back in play |
| yields, led_to, addresses | structural | experiment -> finding, decision -> experiment it scheduled, hypothesis -> question |

**Inferred links.** Every edge has `inferred` and `basis`. `inferred: false` means a structured field of the run record states it (for example an experiment record naming its hypothesis). `inferred: true` (dashed in the viewer) means we reconstructed it from order or text: a finding recorded between two decisions is linked to the later one, an analysis is matched to the experiment with the same measured value, or a region test places a film inside a hypothesis region. Most `caused_decision` links are of this kind, because the records do not log which finding a decision used. Treat them as "was available to", not "was the reason".

## Inputs
- **Steel** (`asd/kg.py: build_steel`): `record.jsonl`, `ledger.jsonl`, `meta.json` of a run directory. Default `runs/t011`.
- **LabLoop**: `build_run` reads `notebook.sqlite` and `record.jsonl` (kinds from `docs/LABLOOP_INTEGRATION.md`) when an Omnigent run directory exists. `build_labloop_record` follows that contract but was written before any Omnigent LabLoop record existed, so it is untested on real output. Otherwise `make_kg.py` runs the **offline rule-based campaign** (fixed world 2000, seed 7, budget 60) and labels the graph as such. That graph shows the baseline scientist, not the Omnigent agents.
- Missing files give a graph with warnings, not an error.

## Rigor notes
- Hypotheses are labeled agent-generated and unvalidated. Citations come from the run's literature calls; a cited id the run never retrieved is marked.
- Hidden ground truth is never read: only measured values of experiments that were run, and no world parameters, true hit lists or untested measurements. `check_clean` rejects those keys and a test scans the output.
- LabLoop is a team-built simulator and the steel data are a public dataset behind a replay oracle. Neither graph is evidence about real materials.

## Regenerate
```
python scripts/make_kg.py                                  # writes runs/kg_steel.json, runs/kg_labloop.json, embeds both in docs/kg.html
python scripts/make_kg.py --steel-run runs/e2-live         # another steel run
python scripts/make_kg.py --labloop-run runs/ll-w2000      # use Omnigent records when that directory exists
python -m pytest tests/test_kg.py -q
```

## Agent tools (`asd/kg_tools.py`)
`kg_update(node_type, node_id, label, evidence, source, links)` adds a node and/or typed links; `kg_query(query, node_id, node_type, limit)` answers `summary | list | node | chain | why | open`. Stateless per call: the base graph is rebuilt from the run directory (`ASD_RUN_DIR` or `LC_ASD_RUN_DIR`), and additions go to `kg.jsonl` there plus one `kg_update` entry in `record.jsonl` when the directory already has an owner. A link is `inferred` unless its `basis` is a record id that exists. Not yet wired into any agent YAML.
