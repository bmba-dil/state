# v10 — TUI DAG Viewer

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 089–096 (8 phases)

---

## Phases

#### Phase 089 — Route registration + layout (topological auto-layout)
**Goal:** `route.register({ name: "state.dag" })`; topological layout algorithm.
**Depends on:** 080
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase 090 — Node rendering (color-coded by status)
**Goal:** Status palette: pending/in-progress/done/failed/blocked; colors from opencode theme.
**Depends on:** 089
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes with P3, P4

#### Phase 091 — Click-to-detail pane (STEP.md / SLICE.md / PHASE.md / ARC.md)
**Goal:** Side panel renders markdown content; scroll sync.
**Depends on:** 090
**Requirements:** DAG-VIEW-02
**Parallelizable:** yes with P4

#### Phase 092 — Filter bar (Arc / Phase / Slice / critical-path)
**Goal:** Filter presets; critical-path computed from scheduler data.
**Depends on:** 090
**Requirements:** DAG-VIEW-03
**Parallelizable:** yes with P3

#### Phase 093 — SSE live updates
**Goal:** Subscribe to daemon SSE; diff-patch node status.
**Depends on:** 090, 054
**Requirements:** DAG-VIEW-04
**Parallelizable:** yes

#### Phase 094 — Keyboard navigation + accessibility
**Goal:** Arrow keys move focus; Enter opens detail; `F` focuses filter.
**Depends on:** 091
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase 095 — Large-graph performance (≥500 nodes)
**Goal:** Virtualized rendering; clip off-screen; layout cache.
**Depends on:** 090
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase 096 — Integration smoke test (multi-mode projects)
**Goal:** Verify DAG viewer works in both build and teach (teach shows concept DAG).
**Depends on:** 089..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

