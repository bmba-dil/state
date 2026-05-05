# v9 — Plugin TUI Bundle

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 080–088 (9 phases)

---

## Phases

#### Phase 080 — TUI entry module + `TuiPluginModule` export
**Goal:** `tui.ts` scaffold, solid-js + @opentui/core + @opentui/solid imports at catalog versions.
**Depends on:** 068
**Requirements:** TUI-01
**Parallelizable:** yes
**Plans:** 1/1 plans complete
- [x] 080-01-PLAN.md — Create theme.json + tui.ts (TuiPluginModule scaffold) + re-export from index.ts

#### Phase 081 — Sidebar slot (`sidebar_content`) — mode-aware renderer
**Goal:** Reads `.state/mode.json` at render; conditional render build-tree vs concept-state.
**Depends on:** 080, 054
**Requirements:** TUI-02
**Parallelizable:** yes with P3..P5
**Plans:** 1 plan
- [ ] 081-01-PLAN.md — SidebarContentRenderer SolidJS component + tui.ts integration

#### Phase 082 — Build-progress sub-component (current Step + Slice DAG mini-view)
**Goal:** Subscribes to daemon SSE; renders Step status colors + Slice DAG thumbnail.
**Depends on:** 081
**Requirements:** TUI-02
**Parallelizable:** yes with P4, P5
**Plans:** 1 plan
- [ ] 082-01-PLAN.md — BuildProgress SolidJS component + event wiring + tui.ts integration

#### Phase 083 — Teach-concept sub-component (current concept + mastery bar)
**Goal:** Subscribes to daemon SSE; renders concept card + Kolb stage + mastery bar.
**Depends on:** 081
**Requirements:** TUI-02
**Parallelizable:** yes with P3, P5

#### Phase 084 — Statusline (`sidebar_footer` / `home_footer`)
**Goal:** One-line mode + scope + provider + session cost; subscribes to cost events.
**Depends on:** 080
**Requirements:** TUI-03
**Parallelizable:** yes

#### Phase 085 — Toast notifications (`ui.toast`)
**Goal:** Slice completion, drill availability, gray-area decisions, auth refresh; de-dup.
**Depends on:** 080
**Requirements:** TUI-04
**Parallelizable:** yes

#### Phase 086 — Plugin install script (`TuiPluginInstallOptions`)
**Goal:** Auto-registers plugin + MCP servers in `opencode.json` on first run.
**Depends on:** 079
**Requirements:** TUI-05
**Parallelizable:** yes

#### Phase 087 — Prompt hint slot (`session_prompt_right`)
**Goal:** Shows model + token cost + Step N.m indicator.
**Depends on:** 084
**Requirements:** TUI-03
**Parallelizable:** yes

#### Phase 088 — Bun test suite for TUI components
**Goal:** `bun test` unit tests for sidebar/statusline/toast logic.
**Depends on:** 081..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

