# v23 — Teach TUI Extensions

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 215–222 (8 phases)

---

## Phases

#### Phase 215 — Teach dashboard route (`state.teach.dashboard`)
**Goal:** `route.register`; subject picker + concept graph + mastery heatmap.
**Depends on:** 080, 168
**Requirements:** T-TUI-01
**Parallelizable:** yes

#### Phase 216 — Concept graph visualization (SolidJS + opentui)
**Goal:** Topological layout; prereq edges; clickable concepts.
**Depends on:** 215
**Requirements:** T-TUI-01
**Parallelizable:** yes with P3, P4, P5

#### Phase 217 — Mastery heatmap (concept × mastery band)
**Goal:** Color-coded grid; hover → detail.
**Depends on:** 215, 170
**Requirements:** T-TUI-01
**Parallelizable:** yes with P2, P4, P5

#### Phase 218 — Drill UI (`ui.Prompt` replacement during drill)
**Goal:** Replace session prompt with drill question card + answer input + timer + feedback panel.
**Depends on:** 215, 181
**Requirements:** T-TUI-02
**Parallelizable:** yes with P2, P3, P5

#### Phase 219 — Mental-model viewer (concept tree + mastery badges)
**Goal:** Tree component; last-drilled / next-review dates; badge colors.
**Depends on:** 215, 170
**Requirements:** T-TUI-03
**Parallelizable:** yes with P2, P3, P4

#### Phase 220 — Session timeline (observations, mode transitions, drill history)
**Goal:** Chronological timeline; filter by aggregate.
**Depends on:** 215, 009
**Requirements:** T-TUI-04
**Parallelizable:** yes

#### Phase 221 — Sidebar extension (teach — refines 083)
**Goal:** Current concept + Kolb stage + mastery bar + next-drill timer.
**Depends on:** 083
**Requirements:** TUI-02 (teach side)
**Parallelizable:** yes

#### Phase 222 — Teach TUI integration test
**Goal:** E2E: subject → concept → drill → mastered; all surfaces exercised.
**Depends on:** 215..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

