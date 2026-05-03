# v20 — Teach Four Modes + Selector

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 187–197 (11 phases)

---

## Phases

#### Phase 187 — Shared plumbing implementation (SUMMARY Q2 resolution — hosted in v18 kernel)
**Goal:** Implement shared plumbing (selector + drop-to-simpler + Kolb + observation emission) hosted in v18 kernel; four modes (P2–P5) consume. SUMMARY Q2 decision already resolved in STATE.md line 92 — this phase is scaffolding, not discussion.
**Depends on:** 177
**Requirements:** (infrastructure)
**Parallelizable:** no

#### Phase 188 — PRIMM mode state machine (predict / run / investigate / modify / make)
**Goal:** 5-stage FSM per concept; system-prompt injection per stage.
**Depends on:** 187
**Requirements:** MODE-P-01
**Parallelizable:** yes with P3..P5

#### Phase 189 — Scaffolded mode (graduated hints, prereq reinforcement, worked examples)
**Goal:** Reads `scaffold_levels` from CONCEPT.md; progression logic.
**Depends on:** 187
**Requirements:** MODE-S-01
**Parallelizable:** yes with P2, P4, P5

#### Phase 190 — Socratic mode (question-led discovery, no direct answers)
**Goal:** System-prompt guard: never provide answers; question-generation heuristic.
**Depends on:** 187
**Requirements:** MODE-SO-01
**Parallelizable:** yes with P2, P3, P5

#### Phase 191 — Constructivist mode (build-your-own, minimal scaffolding)
**Goal:** Minimal system prompts; learner drives; observer-only teacher.
**Depends on:** 187
**Requirements:** MODE-C-01
**Parallelizable:** yes with P2, P3, P4

#### Phase 192 — Mastery-based mode selector (PRIMM <30% → Scaffolded → Socratic → Constructivist)
**Goal:** Reads `mastery_probability`; picks mode with threshold crossings.
**Depends on:** 188, 189, 190, 191
**Requirements:** MODE-SEL-01
**Parallelizable:** no

#### Phase 193 — Manual override (learner picks mode)
**Goal:** CLI + MCP: set active mode; selector respects override until cleared.
**Depends on:** 192
**Requirements:** MODE-SEL-02
**Parallelizable:** yes

#### Phase 194 — Drop-to-simpler on frustration signal
**Goal:** Subscribe to `state.concept.frustration_detected`; decrement mode; emit `state.mode.activated`.
**Depends on:** 192, 175
**Requirements:** MODE-SEL-03
**Parallelizable:** yes

#### Phase 195 — Mode-specific `chat.params` injection (temperature per mode)
**Goal:** Low-temp Socratic (0.3), mid Scaffolded (0.5), higher PRIMM/Constructivist (0.7+).
**Depends on:** 076, 188..P5
**Requirements:** (wiring; supports MODE-*)
**Parallelizable:** yes

#### Phase 196 — Per-mode system-prompt templates
**Goal:** Mode-specific preambles injected via `experimental.chat.system.transform`.
**Depends on:** 074, 188..P5
**Requirements:** (wiring)
**Parallelizable:** yes

#### Phase 197 — Four-mode golden-fixture test
**Goal:** Teach same concept in all 4 modes; assert distinct behaviors via event patterns.
**Depends on:** 187..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

