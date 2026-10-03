# Project: agentic-scientific-discovery (Hack-Nation Challenge 3)

Deadline: Sun Oct 4, 9:00 AM ET. Public repo. No secrets in git. No claim without a measurement.

## Orientation (read in this order, stop as soon as you have what you need)
1. `coord/HANDOFF.md` : current state, next actions, blockers (<= 40 lines)
2. `coord/BACKLOG.md` top 5 items and `coord/SCOREBOARD.md`
3. `knowledge/00-INDEX.md` : map of atomic notes. Open only the notes you need.
Do NOT read `docs/REFERENCES.md`, `docs/HACKATHON_BRIEF.md` or `docs/AGENT_PROMPT.md` in full unless asked. The vault holds the same facts in small notes.

## Token discipline
- Use Grep/Glob and line ranges instead of reading whole files. Logs: read only the last 40 lines (`tail -n 40`).
- Test and eval commands: quiet flags, pipe through `tail -n 30`. Never paste long output into notes.
- Keep messages terse: result, evidence, next step. Do not restate the task or the plan.
- Logs are append-only, dated, one entry <= 8 lines. Notes <= 60 lines. Split instead of growing.
- Cache every LLM and oracle call in eval runs, keyed by (prompt, model, seed).
- Model routing: Sonnet 5.5 builds, Opus 5.5 reviews, Haiku 4.5 summarizes or checks. Never xhigh/max effort.
- Stop and ask at the spend limits in `coord/PROTOCOL.md`.

## Handoff rule (what makes a fresh agent cheap)
Before context passes ~50%, at the end of a cycle, or before stopping: update `coord/HANDOFF.md` using `knowledge/templates/handoff.md`, commit, then end. A new agent starts from HANDOFF.md, not from the transcript.

## Knowledge rule
New durable fact -> one atomic note in `knowledge/` (template in `knowledge/templates/`), linked with [[wikilinks]] and added to the right MOC line in `00-INDEX.md`. Unverified claims carry `status: unverified`. Decisions go in `knowledge/decisions/` (ADR style) and one line in `coord/DECISIONS.md`.

## Git
Feature branches only (`builder/*`, `scout/*`). Integration branch is `dev/agentic-loop`; branch builder/* and scout/* from it and merge back only after Scout approval in `coord/`. Never commit to main.
