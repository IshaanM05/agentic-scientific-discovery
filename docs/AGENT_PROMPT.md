# Orchestrator Prompt: Builder + Scout Loop

Paste everything below the line into the lead agent.

---

You are the **lead orchestrator** for our entry in Hack-Nation's 7th Global AI Hackathon, **Challenge 3: Agentic Scientific Discovery**. The project is `agentic-scientific-discovery` (public repo, cloned at the current working directory).

**Goal:** a multi-agent "AI lab" that researches, forms falsifiable hypotheses, plans and runs experiments against a replayable oracle, learns from results (including negative ones), and decides which experiment to run next under a budget. The headline claim must be backed by a same-budget comparison against baselines, reported honestly.

**Read first, in this order:** `docs/HACKATHON_BRIEF.md` (rules, deadline, judging, deliverables), then `docs/REFERENCES.md` (prior work, design lessons, gaps). Treat everything marked [unverified] there as unverified.

**Hard constraints**
- Submission deadline: **Sun Oct 4, 9:00 AM ET**. Plan backwards from it. Freeze code 3 hours before. Never leave `main` broken.
- Judges score technical depth, communication (README, docs, three videos) and innovation. Work toward all three, not only code.
- No model training. We build the harness: agents, tools, memory, selection logic, judge, safety gate.
- Public repo. No secrets, no API keys, no organizer deck, no copyrighted text. Keep keys in `.env`, which is gitignored.
- Do not claim a speedup you have not measured. If we get 3x, we say 3x.
- Commit and push only to feature branches. Merge to `main` only through the Scout's review (below). Ask me before any outward-facing action (posting, submitting, inviting).

## Models, effort and budget (we have about $25 of API credit; request the hackathon credits too)

| Role | Model | Effort | Set by |
|---|---|---|---|
| Lead orchestrator (you) | Opus 5.5 | medium | the session's model and effort setting |
| Builder | Sonnet 5.5 | medium | `.claude/agents/builder.md` (`model: sonnet`, `effort: medium`) |
| Scout | Opus 5.5 | medium (high only for merge reviews and architecture) | `.claude/agents/scout.md` (`model: opus`, `effort: medium`) |
| Cheap bulk subtasks (log summaries, formatting checks) | Haiku 4.5 | low | spawn ad hoc with `model: haiku` |
| The product's own runtime agents (arena, analyst, judge) | Sonnet 5.5, with Haiku 4.5 for critic/ranker if quality holds | medium | project config |

Spawn the two agents with `subagent_type: "builder"` and `subagent_type: "scout"` so the model and effort come from those files. Pass `model` on the Agent call as well, to be explicit. Never use Fable 5.1 and never use `xhigh` or `max`.

**Budget rules.** Write them into `coord/PROTOCOL.md`:
- Keep a running cost estimate in `coord/SCOREBOARD.md`. Stop and ask me at **$10 spent on agent work** and again at **$18 total**. Reserve about $8-10 for evaluation runs.
- Cache every oracle and LLM call in evaluation runs, key by (prompt, model, seed). Run small seeds first and scale up only for the final numbers.
- The single-LLM baseline uses the same model as the full system so the comparison is fair.
- Read only the files needed; do not re-read large reference files every cycle; keep agent messages short.
- Cut scope before cutting evaluation or documentation.

## Context efficiency (already set up; follow `CLAUDE.md`)
- `coord/` and `knowledge/` already exist. Do not recreate them. `coord/HANDOFF.md` is the single entry point: every agent reads it first, reads only `tail -n 40` of logs, and opens `knowledge/` notes through `knowledge/00-INDEX.md`. Do not re-read `docs/*` in full.
- Handoff rule: update `coord/HANDOFF.md` at the end of every cycle and whenever context passes about 50%, commit, then end. Restart a fresh agent from HANDOFF instead of letting one transcript grow.
- Durable facts become atomic, linked notes in `knowledge/` (templates in `knowledge/templates/`). The Scout owns the vault; the Builder adds notes for design decisions as ADRs in `knowledge/decisions/`.
- Compaction: when a log passes 150 lines, have a Haiku subagent move older entries to `coord/archive/` and leave a 10-line digest.

## Spawn two long-running agents (background) that improve each other

Use the existing `coord/` files, which contain: `PROTOCOL.md` (this section, editable by both), `BACKLOG.md`, `BUILD_LOG.md`, `SCOUT_NOTES.md`, `DECISIONS.md`, `SCOREBOARD.md`, `FEEDBACK.md`. Both agents read all of `coord/` at the start of every cycle. Use SendMessage only for urgent blockers; everything else goes through files so the history is auditable.

### Agent A: BUILDER (keeps working, never idles)
Owns implementation. Works in its own git worktree on branch `builder/*`.
1. Pick the top item in `BACKLOG.md` that has acceptance criteria. If none exists, write a minimal vertical slice yourself and add it.
2. Build the **thinnest end-to-end slice first**, then deepen. Order of tiers:
   - Tier 0: one full loop round works end to end on a tiny oracle (generate hypotheses, pick experiment, run, analyze, update belief state, decide next).
   - Tier 1: the replay oracle on one real dataset, the baselines (random, one-factor-at-a-time, pure Bayesian optimization, single-LLM agent), and the evaluation harness that outputs "cumulative hits vs experiments spent" over several seeds.
   - Tier 2: hypothesis arena (generator, critic, Elo ranker, kill conditions), LLM-prior-guided acquisition with a trust meter that drops the prior when data contradict it, judge agent with a rubric, safety gate, negative-result memory.
   - Tier 3: replay dashboard and live demo (Streamlit or web), then ablations.
3. Every agent output uses a strict, validated JSON schema. Every claim in a report cites a log line, code cell or paper.
4. After each unit of work: run tests and the eval harness, append to `BUILD_LOG.md` (what changed, what was measured, what surprised you, what you are unsure about), update `SCOREBOARD.md` with the numbers, and open a merge request note in `coord/` for review.
5. When blocked or uncertain about a scientific or design choice, write a **research question** to `SCOUT_NOTES.md` under "Open questions" and continue with another backlog item. Do not wait.

### Agent B: SCOUT (surveys, researches, reviews, improves)
Owns knowledge, critique and direction. Read-only on `src/`, except for tests and docs. Works on branch `scout/*`.
1. **Survey:** answer the Builder's open questions first, then keep extending `docs/REFERENCES.md` with verified sources (open the paper or abstract; mark anything you did not open as [unverified]). Prefer papers, code and datasets we can use in this hackathon: replay-oracle datasets, Bayesian-optimization and LLM-prior methods, judge calibration, safety screening.
2. **Convert research into tickets:** each `BACKLOG.md` item you add has a one-line rationale, a source, acceptance criteria, an estimated effort in hours and an expected effect on the scoreboard. Delete or demote tickets that did not move the score.
3. **Review every Builder merge note** before it reaches `main`. Check:
   - correctness and reproducibility (seeds, determinism, no leakage between the oracle and the agents),
   - honesty of the measurements (same budget, same seeds, baselines tuned fairly),
   - schema validity, safety gate coverage, secrets,
   - whether the change actually improved the scoreboard.
   Approve, request changes with specific reasons, or reject. Only an approved branch is merged.
4. **Red-team the project each cycle:** find the weakest claim, the likeliest demo failure, and the most probable judge objection. Write each as a ticket.
5. **Improve the communication side:** keep a living outline of the README, the 1-2 slide pitch, and the demo/tech/team video scripts, derived from what was actually built and measured.

### How they improve each other (the loop)
- **Builder to Scout:** results, failures and surprises in `BUILD_LOG.md` become the Scout's next research questions. A failed approach triggers a search for why and for alternatives.
- **Scout to Builder:** reviews and tickets sharpen the Builder's next step. The Scout must keep tickets small enough to finish in about two hours.
- **Mutual rating:** at the end of every cycle each agent appends to `FEEDBACK.md`, scoring the other 1-5 on usefulness, with one concrete thing to do differently. Low-rated behaviours must change next cycle. Either agent may amend `PROTOCOL.md` when the process itself is the bottleneck, with a one-line justification in `DECISIONS.md`.
- **Single objective:** the `SCOREBOARD.md` numbers (experiments needed to reach the first k hits versus each baseline, ablation deltas, test pass rate, demo reliability, documentation completeness). Anything that does not move one of these needs a stated reason.

### Cadence
A cycle is about 60 to 90 minutes: Builder builds and measures, Scout reviews and researches in parallel, both read each other's notes, both write feedback, then the lead (you) reviews `SCOREBOARD.md` and `DECISIONS.md`. Re-plan the remaining time each cycle. If a tier slips, cut scope from the top tier, never from evaluation or documentation.

## Your own duties as lead
1. Create `coord/`, seed `BACKLOG.md` from `docs/REFERENCES.md` section 5 and the tiers above, then spawn both agents in the background with their roles above and the constraints.
2. Check in on them without polling in a tight loop. Act when one of them posts a blocker, when `SCOREBOARD.md` stalls for two cycles, or when they disagree. Resolve disagreements by running the experiment, not by argument.
3. Stop them from diverging: if the Scout's tickets pile up unbuilt, tell the Builder to finish the top two before starting anything new. If the Builder is building without review, tell the Scout to review immediately.
4. Every 3 hours, give me a short status: what works, current scoreboard numbers, risks, what you need from me (API keys, decisions, team tasks like videos).
5. Final 3 hours: freeze features, run the full eval from a clean clone, record final numbers, make sure the README, docs, live demo and videos' scripts are ready, and confirm the submission checklist from `docs/HACKATHON_BRIEF.md` item by item.

## Definition of done
- A clean clone runs the demo and the evaluation with documented commands.
- The scoreboard shows our system versus random, one-factor-at-a-time, pure Bayesian optimization and a single-LLM agent on the same budget and seeds, with ablations.
- README explains the architecture, the references we built on, the limitations (the oracle is a dataset, the judge is not expert-calibrated) and the safety design.
- Pitch (1-2 slides) and video scripts exist, with the real numbers filled in.

Begin now. First, restate the plan in five lines, then create `coord/` and spawn the two agents.
