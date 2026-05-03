# v17 — Build TUI Extensions

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 159–166 (8 phases)

---

## Phases

#### Phase 159 — Build dashboard route (`state.build.dashboard`)
**Goal:** `route.register`; product Arc/Phase/Slice/Step hierarchy (product-tier vocabulary, not GSD Milestone/Phase); burndown + verify-pass rate.
**Depends on:** 080, 126
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase 160 — Hierarchy tree component (drill-down, collapse/expand)
**Goal:** SolidJS tree; SSE-driven updates.
**Depends on:** 159
**Requirements:** B-TUI-01
**Parallelizable:** yes with P3..P5

#### Phase 161 — Step detail view (DISCUSS/PLAN/EXECUTE/VERIFY tabs)
**Goal:** Tab component; markdown rendering; file links.
**Depends on:** 159, 135..P5
**Requirements:** B-TUI-02
**Parallelizable:** yes with P2, P4, P5

#### Phase 162 — Commit browser with revert UI
**Goal:** Per-Step commits from events + git; revert triggers `snapshot_revert`.
**Depends on:** 040, 159
**Requirements:** B-TUI-03
**Parallelizable:** yes with P3, P5

#### Phase 163 — Gray-area decision dialog (`ui.DialogSelect`)
**Goal:** Structured options from planner; auto-decide per config with manual override; persists `state.decision.made`.
**Depends on:** 133, 080
**Requirements:** B-TUI-04
**Parallelizable:** yes

#### Phase 164 — Sidebar extensions (build-specific — current Slice DAG mini-view)
**Goal:** Refine 082 sub-component.
**Depends on:** 082
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase 165 — Keyboard shortcuts + command palette integration
**Goal:** Quick-switch commands registered via `command.register`.
**Depends on:** 080
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase 166 — Build TUI integration test
**Goal:** E2E: create Arc → Phase → Slice → Step → ship; all TUI surfaces exercised.
**Depends on:** 159..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

