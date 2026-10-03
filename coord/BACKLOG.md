# BACKLOG (top = next). Scout curates, Builder pulls.
- [ ] T001 Toy-oracle vertical slice: generate -> pick -> run -> analyze -> update belief -> decide | [[loop-structure]] | accept: one round runs, JSON-schema validated | 3h | proves the loop
- [ ] T002 Replay oracle on one real dataset + budget accounting | [[replay-oracle]] | accept: deterministic with seed, hit definition documented | 3h | enables all comparisons
- [ ] T003 Baselines: random, one-factor-at-a-time, pure BO, single-LLM | [[baselines-and-evaluation]] | accept: curves of hits vs experiments over >=5 seeds | 3h | the headline plot
- [ ] T004 Hypothesis arena (generator, critic, Elo ranker, kill conditions) | [[hypothesis-arena]] | accept: ranked list with falsifiable predictions | 4h | innovation
- [ ] T005 LLM-prior-guided acquisition + trust meter | [[llm-guided-bo]] | accept: beats pure BO or we report that it does not | 4h | core claim
- [ ] T006 Judge agent with rubric + safety gate | [[judge-calibration]], [[safety-gate]] | accept: schema-valid verdicts, blocks a hazardous test case | 3h | credibility
- [ ] T007 Replay dashboard (Streamlit) + live-demo URL | | accept: runs from clean clone | 4h | demo
- [ ] T008 README, pitch (1-2 slides), 3 video scripts with real numbers | | accept: matches HACKATHON checklist | 3h | communication score
