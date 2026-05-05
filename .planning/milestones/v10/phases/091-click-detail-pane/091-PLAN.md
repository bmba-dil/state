---
phase: 091
goal: "Side panel renders markdown content; scroll sync."
wave: 1
depends_on: [090]
files_modified: [src/tui/dag-viewer.ts]
autonomous: true
must_haves:
  - Side panel layout with canvas + detail split
  - Detail shows node metadata and description
  - Arrow-key navigation between nodes
  - Enter selects node for detail view
---

# Plan 091-1: Click-to-Detail Pane + Navigation

**Goal:** Add split-view layout (DAG canvas + detail side panel), markdown content area, and arrow-key/Enter navigation for node selection.

## Tasks

### 091.1 Split-view layout in DAG viewer

**Acceptance:** `renderDagViewer()` returns a horizontal split: left (70% canvas) + right (30% detail panel) when a node is selected

**Estimated effort:** Medium

**Dependencies:** 090

**Details:**
- Refactor `renderDagViewer()` to use `Box({ flexDirection: "row" })` for split layout
- Left panel: existing DAG canvas (title, connection, legend, nodes)
- Right panel: detail card with node name, kind badge, status dot, description, edges
- Detail content: rendered markdown from node description (plain text fallback)
- Unselected state: full-width canvas, centered hint "Use arrow keys to navigate, Enter to select"
- Scroll sync: detail panel scrolls independently via state.scrollOffset
- Consumers: route render function in tui.ts

**Files to modify:**
- `packages/opencode-plugin/src/tui/dag-viewer.ts`

### 091.2 Keyboard navigation (arrow keys, Enter)

**Acceptance:** Arrow up/down moves focus between nodes; Enter selects the focused node; Escape deselects

**Estimated effort:** Medium

**Dependencies:** 091.1

**Details:**
- Add `focusedNode: string | null` to `DagViewerState`
- Arrow up/down: move focus to previous/next node in topological order
- Enter: set `selectedNode = focusedNode`
- Escape: set `selectedNode = null`
- Visual: focused node gets `[bracket]` indicator; selected node gets border highlight
- Render: focused node shown with distinct border color
- Consumers: route component handles keyboard events via opencode keybind API

**Files to modify:**
- `packages/opencode-plugin/src/tui/dag-viewer.ts`

### 091.3 Update tests

**Acceptance:** Navigation and split-view tests pass

**Estimated effort:** Small

**Dependencies:** 091.1, 091.2

**Details:**
- Add test: selected node shows detail panel content
- Add test: unselected state shows no detail panel
- Add test: focused node renders with bracket indicator
- Consumers: CI pipeline

**Files to modify:**
- `packages/opencode-plugin/src/tui/dag-viewer.test.ts`

### 091.4 Run build and verify

**Acceptance:** `bun test` passes, `bun build` succeeds

**Estimated effort:** Small

**Dependencies:** 091.3

### Integration Notes
- Phase 092 (filter bar) and 094 (keyboard nav) will build on this navigation system
- The side panel layout is the foundation for future detail views (STEP.md / SLICE.md content)
