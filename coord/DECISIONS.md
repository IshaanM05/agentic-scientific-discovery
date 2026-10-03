# DECISIONS (append-only, newest at bottom, entries <= 8 lines)
2026-10-03 scout: ADR-001 (proposed) replay oracle = figshare steel_strength (MIT, 312 rows), hit = yield >= 2000 MPa (15 hits, 4.8%), 1 experiment = 1 reveal, B = 60 incl. initial design; fallback expt_gap (MIT, gap >= 4 eV, 4.15%). Note: knowledge/decisions/ADR-001-replay-dataset.md on scout/t002-dataset.
- 2026-10-03: Re-plan per docs/CHALLENGE_BRIEF.md: Omnigent orchestration mandatory; T000 added above T002; time split compressed to fit 06:00 freeze.
- 2026-10-03: Human raised the agent spend limit from $10 to $16 for cycle 4 (T010, T011, T003, T009). $18 total cap unchanged.
- 2026-10-03: Human approval on Windows + claude-sdk: no Approve/Deny card appeared; the human typed "approve" in chat. Document approval as recorded, NOT enforced as a hard block. Never claim a hard gate. Max 20 min to find why; else move on.
- 2026-10-03: Cycle 5 order: T011 -> T009 (mandatory) -> T005. Builder cap $3.5; stop at $16 agent spend. Real constraint is the Pro usage limit: throttled -> stop and report.
- 2026-10-03: SciAgents addendum applies to B/C only. Positioning line scoped to SciAgents (Coscientist and A-Lab do run experiments, so no general claim).
