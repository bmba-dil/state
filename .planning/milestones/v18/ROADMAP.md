# v18 — Teach Kernel: Kolb + Concepts + Mental-Model

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 167–177 (11 phases)

---

## Phases

#### Phase 167 — Concept-graph schema (CONCEPT-GRAPH.json) + CONCEPT.md frontmatter
**Goal:** Pydantic models: `Concept`, `Edge`, `Prerequisite`; `scaffold_levels`, `teaching_modes`, `observation_rules`.
**Depends on:** 002
**Requirements:** TCH-01
**Parallelizable:** yes

#### Phase 168 — Subject-loading + concept-graph projection
**Goal:** Load `.state/teach/subjects/<id>/*` → build graph; rebuildable from `state.concept.introduced` events.
**Depends on:** 167
**Requirements:** TCH-01
**Parallelizable:** yes

#### Phase 169 — Kolb state machine (CE → RO → AC → AE → MASTERED)
**Goal:** Per ARCHITECTURE §9.2 pseudocode; one machine instance per active concept.
**Depends on:** 167
**Requirements:** TCH-02
**Parallelizable:** yes with P4..P6

#### Phase 170 — Mental-model projection (event-sourced from OBSERVATIONS.jsonl)
**Goal:** `project_mental_model(events)` per ARCHITECTURE §9.4; Bayesian mastery update placeholder (full math in v19).
**Depends on:** 169
**Requirements:** TCH-03
**Parallelizable:** yes with P3, P5, P6

#### Phase 171 — Observation recording (schema-validated, structured-only)
**Goal:** Pydantic `Observation` with `extra = "forbid"`; rejects freeform text; writes to OBSERVATIONS.jsonl + events.
**Depends on:** 167, 118
**Requirements:** TCH-07, MCP-T-05
**Parallelizable:** yes

#### Phase 172 — Rebuild MENTAL-MODEL.json on demand (`state teach mental-model rebuild`)
**Goal:** CLI; reads OBSERVATIONS.jsonl → replays → writes projection.
**Depends on:** 170
**Requirements:** TCH-08
**Parallelizable:** yes

#### Phase 173 — Concept-teacher orchestrator (mode selection + personality + Kolb stage)
**Goal:** `concept_teach` tool dispatches to correct mode (v20) + personality (v21) + current Kolb stage.
**Depends on:** 169
**Requirements:** TCH-04
**Parallelizable:** no

#### Phase 174 — Next-concept selector (`concept_next`)
**Goal:** Given current mastery + prereq graph, pick next concept; surfaces via CLI + MCP.
**Depends on:** 168, 170
**Requirements:** TCH-06
**Parallelizable:** yes

#### Phase 175 — Frustration-signal detection + drop-to-simpler
**Goal:** Pattern-match OBSERVATIONS.jsonl (e.g., 3 errors in 5 min) → emit `state.concept.frustration_detected` → mode-selector drops to simpler.
**Depends on:** 171
**Requirements:** TCH-05
**Parallelizable:** yes

#### Phase 176 — Learner privacy guard (no raw-input leakage verifier)
**Goal:** Regression test: scan OBSERVATIONS.jsonl for prose patterns; fail if found.
**Depends on:** 171
**Requirements:** TCH-07
**Parallelizable:** yes

#### Phase 177 — Teach-kernel integration test (Kolb walkthrough w/ fixture concept)
**Goal:** E2E: introduce concept → Kolb CE→RO (question)→AC→AE (drill stub)→MASTERED.
**Depends on:** 167..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

