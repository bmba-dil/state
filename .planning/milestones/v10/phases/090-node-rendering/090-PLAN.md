---
phase: 090
goal: "Status palette: pending/in-progress/done/failed/blocked; colors from opencode theme."
wave: 1
depends_on: [089]
files_modified: [src/tui/dag-viewer.ts, src/tui/build-progress.ts]
autonomous: true
must_haves:
  - Shared status palette module with consistent color/dot/label mappings
  - Colors derived from opencode theme tokens
  - Both dag-viewer and build-progress use the shared palette
  - Node rendering in dag-viewer applies correct status colors
---

# Plan 090-1: Shared Status Palette + Node Color Rendering

**Goal:** Extract status palette (colors, dots, labels) into a shared module consumed by both dag-viewer and build-progress. Ensure colors match opencode theme tokens. Apply status rendering to DAG nodes.

## Tasks

### 090.1 Create shared status-palette module

**Acceptance:** `src/tui/status-palette.ts` exists with exported status color/dot/label maps, consumed by dag-viewer and build-progress

**Estimated effort:** Medium

**Dependencies:** None (new file)

**Details:**
- Create `src/tui/status-palette.ts`
- Define canonical `StepStatus` type: `"pending" | "running" | "done" | "failed" | "blocked" | "retry" | "unknown"`
- Note: "idle" and "busy" are sub-states of "done" and "running" respectively — map them
- Export palette maps derived from opencode theme tokens:
  - `STATUS_COLORS`: maps each status to a hex color from theme.json
  - `STATUS_CHARS`: maps each status to a Unicode dot character
  - `STATUS_LABELS`: maps each status to a human-readable label
- Color mapping:
  - `pending` → T.textMuted (#64748B)  
  - `running` → T.accent (#6366F1)
  - `done` → T.success (#10B981)
  - `failed` → T.error (#EF4444)
  - `blocked` → T.warning (#F59E0B)
  - `retry` → T.info (#3B82F6)
  - `unknown` → T.textMuted (#64748B)
- Dot mapping:
  - `pending` → ○ (U+25CB)
  - `running` → ◉ (U+25C9)
  - `done` → ● (U+25CF)
  - `failed` → ✗ (U+2717)
  - `blocked` → ◍ (U+25CD) or ⏸
  - `retry` → ↻ (U+21BB)
  - `unknown` → ○ (U+25CB)
- Label mapping:
  - `pending` → "Pending"
  - `running` → "In Progress"
  - `done` → "Done"
  - `failed` → "Failed"
  - `blocked` → "Blocked"
  - `retry` → "Retrying"
  - `unknown` → "Unknown"
- Consumers: dag-viewer.ts and build-progress.ts import these maps instead of defining their own

**Files to create:**
- `packages/opencode-plugin/src/tui/status-palette.ts`

### 090.2 Update dag-viewer to use shared palette

**Acceptance:** `dag-viewer.ts` imports status maps from `status-palette.ts`, no longer defines its own statusColor/STATUS_DOTS/STATUS_LABELS

**Estimated effort:** Small

**Dependencies:** 090.1

**Details:**
- Replace inline `statusColor()`, `STATUS_DOTS`, `STATUS_LABELS` with imports from `status-palette.ts`
- Update `LayoutNode` status type to include "failed"
- Update legend row to show all 5 core statuses (pending, running, done, failed, blocked)
- Update detail pane to display correct status label
- Consumers: `renderDagViewer()` reads palette from shared module

**Files to modify:**
- `packages/opencode-plugin/src/tui/dag-viewer.ts`

### 090.3 Update build-progress to use shared palette

**Acceptance:** `build-progress.ts` imports status maps from `status-palette.ts`

**Estimated effort:** Small

**Dependencies:** 090.1

**Details:**
- Replace inline `stepStatusColor()`, `STATUS_DOTS` constants with imports from `status-palette.ts`
- Re-export `stepStatusColor` as an alias for backward compatibility (it's in the public API)
- Update `StepStatus` type to include "failed"
- Update `renderDagBox()` to use imported STATUS_CHARS and STATUS_COLORS
- Update `renderBuildProgress()` to use imported STATUS_LABELS
- Consumers: existing sidebar rendering and tests continue to work

**Files to modify:**
- `packages/opencode-plugin/src/tui/build-progress.ts`

### 090.4 Write tests for status-palette

**Acceptance:** `src/tui/status-palette.test.ts` covers all status mappings

**Estimated effort:** Small

**Dependencies:** 090.1

**Details:**
- Test `statusColor()` for all 7 statuses returns correct hex
- Test `statusChar()` for all 7 statuses returns correct Unicode char
- Test `statusLabel()` for all 7 statuses returns correct label
- Test color values match theme.json tokens
- Test that "idle" maps to "done" and "busy" maps to "running"
- Consumers: regression guard for palette changes

**Files to create:**
- `packages/opencode-plugin/src/tui/status-palette.test.ts`

### 090.5 Run build and verify

**Acceptance:** `bun test` passes, `bun build` succeeds

**Estimated effort:** Small

**Dependencies:** 090.1, 090.2, 090.3, 090.4

**Details:**
- Run `bun test` in packages/opencode-plugin
- Run `bun build src/index.ts --outdir=dist ...`
- Verify no regressions in existing tests
- Verify color consistency across both components
- Consumers: CI pipeline

### Integration Notes
- The shared palette module is the foundation for Phase 091 (click-to-detail pane) which also needs status displays
- Status "failed" is newly introduced — existing code uses "blocked" for failures but the ROADMAP explicitly calls for "failed"
- Backward compatibility: build-progress public API (`stepStatusColor`) must remain unbroken

### Deviation Notes
- ROADMAP says "colors from opencode theme" — the opencode theme colors are defined in theme.json; our palette derives from these tokens
