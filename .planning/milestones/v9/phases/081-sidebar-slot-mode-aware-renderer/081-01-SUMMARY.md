---
phase: 081-sidebar-slot-mode-aware-renderer
plan: 01
subsystem: ui
tags: [solid-js, opentui, sidebar, mode-renderer, tui-slot, constructs-api]

# Dependency graph
requires:
  - phase: 080-tui-entry-module-tuipluginmodule-export
    provides: TuiPlugin slot registration, theme.json installation, sidebar_content slot placeholder
provides:
  - Mode-aware SidebarContentRenderer rendering into sidebar_content TUI slot
  - resolveMode() pure function for mode resolution with strict validation
  - Placeholder anchor points for Phase 082 BuildProgress and 083 TeachConcept
  - Text truncation at 28 chars with U+2026 ellipsis
affects: [082-build-progress, 083-teach-concept, 084-statusline, sidebar_content]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@opentui/core constructs API (Box, Text) for TUI renderable trees — no JSX required"
    - "Sync mode.json read (readFileSync) for small local config — appropriate for <100B files"
    - "Theme color tokens hardcoded as fallback constants matching theme.json exactly"
    - "createTextAttributes() for bold/dim text styling via @opentui/core"

key-files:
  created:
    - packages/opencode-plugin/src/tui/sidebar-content-renderer.ts
    - packages/opencode-plugin/src/tui/sidebar-content-renderer.test.ts
  modified:
    - packages/opencode-plugin/src/tui.ts

key-decisions:
  - "Used @opentui/core constructs API (Box, Text functions) instead of JSX to avoid bun test JSX-runtime dependency on @opentui/solid/bun-plugin"
  - "Used sync readFileSync instead of SolidJS createResource for mode.json — file is <100B local, no async benefit; Phase 082/083 will add reactive SSE updates"
  - "Type cast slot handler return via `as unknown as string` to bridge constructs ProxiedVNode types with slot system's JSX.Element expectation"
  - "Color tokens (accent, success, info, textMuted, error, text, border) hardcoded as const T object matching theme.json exactly — no runtime theme API dependency"

patterns-established:
  - "Constructs-first TUI component pattern: Build renderable trees with @opentui/core Box/Text functions, export pure functions for bun test, use type casts for slot integration"
  - "Copywriting contract enforcement: All user-visible strings match UI-SPEC §Copywriting Contract character-for-character"
  - "28-cell width constraint with U+2026 ellipsis truncation for sidebar_content slot"

requirements-completed: [TUI-02]

# Metrics
duration: 15min
completed: 2026-05-05
---

# Phase 081 Plan 01: SidebarContentRenderer — mode-aware TUI slot renderer

**Mode-aware renderer for sidebar_content slot: reads .state/mode.json, renders 4 conditional states (loading/empty/active/error) with Nerd Font mode indicators, 28-cell divider, and Phase 082/083 placeholder stubs using @opentui/core constructs API.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 (Task 1 TDD with 2 commits, Task 2 with 1 commit)
- **Files created:** 2 (renderer 309 lines, tests 112 lines)
- **Files modified:** 1 (tui.ts slot integration)
- **Tests:** 13 passing, 36 assertions

## Accomplishments

- Created `SidebarContentRenderer` component using `@opentui/core` constructs API (Box, Text) — no JSX dependency
- Implemented 4 conditional rendering states: loading ("Reading mode…"), empty (mode-specific messages), active (BuildProgress/TeachConcept placeholders), error (recovery instructions)
- Mode indicator row with Nerd Font glyphs ( BUILD,  TEACH, 󰘨 BOTH, ○ IDLE) and mode-color-coded text
- 28-cell content divider (─ × 28) separating indicator from content area
- Placeholder stubs for Phase 082 (BuildProgress) and 083 (TeachConcept) as box-drawing bordered rectangles
- Strict mode.json validation — unknown/invalid mode values map to "unknown" (T-081-01 mitigated)
- Integrated into `tui.ts` sidebar_content slot handler, replacing empty-string placeholder

## Task Commits

1. **RED: test(081-01)** - `2a7249d` — Failing tests for resolveMode (7 cases), getModeIndicator (4 cases), renderBuildPlaceholder, renderTeachPlaceholder
2. **GREEN: feat(081-01)** - `fac2054` — SidebarContentRenderer component implementation (309 lines)
3. **Task 2: feat(081-01)** - `766b599` — tui.ts slot integration (import + slot handler replacement)

## Files Created/Modified

- `packages/opencode-plugin/src/tui/sidebar-content-renderer.ts` — Mode-aware renderer (309 lines): resolveMode pure function, getModeIndicator, placeholder builders, SidebarContentRenderer default export using @opentui/core constructs
- `packages/opencode-plugin/src/tui/sidebar-content-renderer.test.ts` — Unit tests (112 lines): 13 test cases covering mode resolution, indicator generation, and placeholder rendering
- `packages/opencode-plugin/src/tui.ts` — Modified: added SidebarContentRenderer import, replaced sidebar_content slot handler (3 other slots unchanged)

## Decisions Made

- **Constructs API over JSX**: Used `@opentui/core` `Box()` and `Text()` function calls instead of JSX. The bun test environment lacks the `@opentui/solid/bun-plugin` JSX transform, making `.tsx` files unparseable during `bun test`. Constructs produce identical renderable trees.
- **Sync read over createResource**: Used `readFileSync` for `.state/mode.json` instead of SolidJS `createResource`. The file is <100 bytes, always local, and resolves in microseconds. Phase 082/083 will add reactive SSE updates for session state.
- **Type cast for slot integration**: The slot handler expects `JSX.Element` (which includes `string`), but constructs return `ProxiedVNode`. Used `as unknown as string` cast to satisfy TypeScript while preserving correct runtime behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] @opentui/solid JSX runtime not available for bun test**
- **Found during:** Task 1 (GREEN phase — first bun test run)
- **Issue:** `@opentui/solid/jsx-runtime` is types-only (`.d.ts`), no runtime JS module. bun test cannot parse `.tsx` files using `@opentui/solid` JSX without the bun-plugin configured.
- **Fix:** Rewrote component as `.ts` using `@opentui/core` constructs API (`Box()`, `Text()`) instead of JSX. Same renderable output, no JSX dependency.
- **Files modified:** `sidebar-content-renderer.tsx` → `sidebar-content-renderer.ts` (file renamed)
- **Verification:** `bun test` passes (13/13), `tsc --noEmit` passes
- **Committed in:** `fac2054` (GREEN commit)

**2. [Rule 1 - Bug] Incorrect @opentui/core import path for createTextAttributes**
- **Found during:** Task 1 (first bun test run)
- **Issue:** Imported `createTextAttributes` from `@opentui/core/utils` but the package only exports from main entry (`@opentui/core`)
- **Fix:** Changed import to `import { createTextAttributes } from "@opentui/core"`
- **Files modified:** `sidebar-content-renderer.ts`
- **Verification:** Import resolves, `createTextAttributes({ bold: true })` returns `1`
- **Committed in:** `fac2054` (GREEN commit)

**3. [Rule 1 - Bug] Text construct function children type mismatch**
- **Found during:** Task 1 (`tsc --noEmit`)
- **Issue:** `Text({ fg: "red" }, "content")` failed — children parameter type `VChild[] | TextNodeRenderable[]` doesn't accept raw string arguments
- **Fix:** Created `Txt()` helper that passes content via `Text({ fg: "red", content: "..." })` prop instead of children
- **Files modified:** `sidebar-content-renderer.ts`
- **Verification:** `tsc --noEmit` passes with zero errors
- **Committed in:** `fac2054` (GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs)
**Impact on plan:** All fixes necessary for build correctness. The constructs API produces the same renderable output as JSX would. No scope creep. One planned feature deferred: SolidJS `createResource` async read replaced by sync `readFileSync` (appropriate for the file size).

## Issues Encountered

- bun test JSX compatibility: `@opentui/solid` JSX requires a bun build plugin for transform — not active during `bun test`. Resolved by using constructs API directly.
- Type bridge between constructs `ProxiedVNode` and slot system `JSX.Element`: resolved with type cast in slot handler.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| BuildProgress placeholder | `sidebar-content-renderer.ts` | 123 | Phase 082 will replace with real BuildProgress component |
| TeachConcept placeholder | `sidebar-content-renderer.ts` | 128 | Phase 083 will replace with real TeachConcept component |
| Hardcoded theme colors | `sidebar-content-renderer.ts` | 39-46 | Theme API (`api.theme.get()`) not accessible in slot renderer; fallback matches theme.json exactly |

All stubs are intentional, documented in the plan, and owned by downstream phases.

## Next Phase Readiness

- `sidebar_content` slot now renders meaningful content based on `.state/mode.json`
- Phase 082 (BuildProgress) can import and replace the `renderBuildPlaceholder()` stub
- Phase 083 (TeachConcept) can import and replace the `renderTeachPlaceholder()` stub
- Copywriting contract enforced — all strings match UI-SPEC verbatim
- Color tokens match theme.json — no visual drift when theme is swapped

---

## Self-Check: PASSED

- [x] `packages/opencode-plugin/src/tui/sidebar-content-renderer.ts` — exists (309 lines)
- [x] `packages/opencode-plugin/src/tui/sidebar-content-renderer.test.ts` — exists (112 lines)
- [x] `081-01-SUMMARY.md` — exists
- [x] RED commit `2a7249d` — exists in git log
- [x] GREEN commit `fac2054` — exists in git log
- [x] Task 2 commit `766b599` — exists in git log
- [x] `tsc --noEmit` — passes with zero errors
- [x] `bun test` — 13/13 pass, 36 assertions
- [x] Copywriting audit — all strings match UI-SPEC §Copywriting Contract
- [x] Color token audit — all hex values match theme.json exactly
- [x] No import cycles between tui.ts and sidebar-content-renderer.ts

---

*Phase: 081-sidebar-slot-mode-aware-renderer*
*Completed: 2026-05-05*
