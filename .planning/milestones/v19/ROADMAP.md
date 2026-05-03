# v19 — Teach Drill Engine

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 178–186 (9 phases)

---

## Phases

#### Phase 178 — AOL drill-verify internals deep-dive research (MEDIUM → HIGH)
**Goal:** Read `~/.claude/agent-of-learning/` drill code; document exact Bayesian update formula; golden fixture.
**Depends on:** 170
**Requirements:** DRL-05 (prep)
**Parallelizable:** yes
**Note:** Flagged as research gap in SUMMARY §10.

#### Phase 179 — `drill_prepare` tool (generate drill per concept + Kolb stage)
**Goal:** Tool impl; reads CONCEPT.md `scaffold_levels`; ≤3000 tokens.
**Depends on:** 117, 178, 173
**Requirements:** DRL-01, DRL-04
**Parallelizable:** yes with P3

#### Phase 180 — Drill prompt token cap enforcement (Hypothesis property test)
**Goal:** Any generated drill ≤3000 tokens across 1000 property-test iterations.
**Depends on:** 179
**Requirements:** DRL-04
**Parallelizable:** yes

#### Phase 181 — opencode `question` tool binding (route drill prompts through question.ask)
**Goal:** `client.question.ask(sessionID, questions)` → typed answers.
**Depends on:** 117
**Requirements:** DRL-03
**Parallelizable:** yes

#### Phase 182 — `drill_verify` tool (grade + update mental-model event)
**Goal:** Grader; emits `state.drill.graded` with score; triggers mastery update.
**Depends on:** 179, 181
**Requirements:** DRL-02
**Parallelizable:** no

#### Phase 183 — Bayesian mastery update (formula from 178)
**Goal:** Implement prior → posterior; verified against AOL golden fixture.
**Depends on:** 178, 182
**Requirements:** DRL-05
**Parallelizable:** no

#### Phase 184 — `drill_stats` tool (mastery projection)
**Goal:** Aggregates mental-model data → projection for next review time.
**Depends on:** 183
**Requirements:** DRL-02 (surface)
**Parallelizable:** yes

#### Phase 185 — `state teach drill` CLI fallback (plain stdin)
**Goal:** For non-opencode hosts; same grader path; stdin I/O.
**Depends on:** 182
**Requirements:** DRL-06
**Parallelizable:** yes

#### Phase 186 — End-to-end drill test (concept → prepare → question → verify → mental-model update)
**Goal:** E2E with real opencode + fixture concept.
**Depends on:** 178..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

