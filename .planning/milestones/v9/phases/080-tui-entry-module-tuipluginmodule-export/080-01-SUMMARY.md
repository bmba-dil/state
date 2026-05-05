---
phase: 080-tui-entry-module-tuipluginmodule-export
plan: 01
subsystem: ui
tags: [opencode, plugin, tui, solid-js, @opentui, theme, slot-plugin]

# Dependency graph
requires:
  - phase: 068-079 (v8 Plugin Server Hooks)
    provides: "@state/opencode-plugin TS package scaffold with server module index.ts entry point"
provides:
  - "TuiPluginModule with id @state/opencode-plugin/tui — theme install, 4 slot registrations, SSE subscription"
  - "theme.json with 12 semantic color tokens in dark mode"
  - "index.ts re-export of TuiPluginModule alongside existing server module"
affects: [081-sidebar-content, 082-build-progress, 084-statusline, 085-toasts, 087-prompt-hint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TUI slot plugins via api.slots.register() with order=100 (middle of registration range)"
    - "Empty-string JSX.Element placeholders for scaffolded slots (valid per opentui JSX type)"
    - "Theme install via api.theme.install() with import.meta.url path resolution"
    - "SSE subscription via api.event.on() with cleanup via api.lifecycle.onDispose()"
    - "Inline type imports ({ type X }) to avoid declaration merging conflicts with verbatimModuleSyntax"

key-files:
  created:
    - packages/opencode-plugin/src/theme.json — 12 semantic color tokens, dark mode, valid JSON
    - packages/opencode-plugin/src/tui.ts — TuiPluginModule with theme install, 4 slot plugins, SSE subscription
  modified:
    - packages/opencode-plugin/src/index.ts — re-exports TuiPluginModule from ./tui.js

key-decisions:
  - "Empty-string placeholders (return \"\") used for slot renderers instead of Text component — @opentui/solid does not export a Text function; empty strings are valid JSX.Element per opentui's JSX type (includes string|number|boolean|null|undefined)"
  - "Inline type import syntax ({ type TuiPluginModule }) avoided but required renaming to TuiPluginModuleType due to TS2395 declaration merging conflict with exported const — verbatimModuleSyntax=true in tsconfig requires type/value name disambiguation"
  - "Slot order: 100 — middle of registration range; later phases can override with lower/higher order values"

patterns-established:
  - "Theme JSON: flat object (no nesting), hex strings, alpha as #RRGGBBAA, mode=dark only"
  - "Slot renderers: return type matches JSX.Element (string|null|BaseRenderable|...)"
  - "Plugin lifecycle: api.theme.install() → api.slots.register() → api.event.on() → api.lifecycle.onDispose()"

requirements-completed: [TUI-01]

# Metrics
duration: 11min
completed: 2026-05-05
---

# Phase 080 Plan 01: TUI Entry Module Summary

**TUI plugin module scaffold exporting TuiPluginModule with theme install, 4 placeholder slot registrations, and daemon SSE subscription — all typecheck-clean against opencode catalog versions**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-05T11:22:41Z
- **Completed:** 2026-05-05T11:34:02Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `theme.json` with all 12 UI-SPEC semantic color tokens (dark mode, valid JSON, hex values)
- Built `tui.ts` exporting `TuiPluginModule` with `id: "@state/opencode-plugin/tui"` and `tui` function that installs theme, registers 4 slot plugins (sidebar_content, sidebar_footer, home_footer, session_prompt_right), and subscribes to daemon SSE
- Updated `index.ts` to re-export `TuiPluginModule` alongside existing server hook module — single entry point for both server and TUI plugins
- `bun run typecheck` exits 0 with zero errors across all 3 files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/theme.json** - `96f7c66` (feat)
2. **Task 2: Create src/tui.ts — TuiPluginModule scaffold** - `e3f5bab` (feat)
3. **Task 3: Update src/index.ts — re-export TuiPluginModule** - `163d22f` (feat)

**Plan metadata:** Pending final commit

## Files Created/Modified

- `packages/opencode-plugin/src/theme.json` — Custom dark-mode theme with 12 semantic color tokens (text, textMuted, error, warning, success, info, border, borderActive, background, backgroundPanel, backgroundElement, accent)
- `packages/opencode-plugin/src/tui.ts` — TuiPluginModule: theme install via `api.theme.install()`, 4 slot plugin registrations with `order: 100`, SSE subscription with cleanup
- `packages/opencode-plugin/src/index.ts` — Added `export { TuiPluginModule } from "./tui.js"` re-export (existing server hooks unchanged)

## Decisions Made

- **Empty-string placeholders:** The plan specified `Text({ children: "" })` from `@opentui/solid`, but `Text` is not a top-level export from that package. The `JSX.Element` type in opentui includes `string` as a valid member, so empty strings (`""`) are used instead — they produce zero visual output (zero cells) but prove the slot pipeline is connected. This is simpler and avoids importing an unavailable API.
- **Type import renaming:** The plan specified `import type { TuiPluginModule }` but TS2395 (declaration merging conflict) requires the type import to not share a name with the exported const under `verbatimModuleSyntax: true`. Fixed by importing as `TuiPluginModuleType` and annotating accordingly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `Text` not exported from `@opentui/solid` — replaced with empty-string renderables**
- **Found during:** Task 2 (Create tui.ts)
- **Issue:** The plan's `<interfaces>` block showed `export function Text(props: { children: string }): any;` from `@opentui/solid`, but the actual dist/index.d.ts exports `TextRenderable3` as a class (not a function component), accessible only via `componentCatalogue` namespace or `getComponentCatalogue()`. No direct `Text` function export exists.
- **Fix:** Changed slot renderers to return `""` (empty string), which is a valid `JSX.Element` per opentui's JSX type definition (`string | number | boolean | null | undefined | BaseRenderable`). Produces zero visual output while proving the slot pipeline is connected. Phases 081–088 will replace these with full component instances.
- **Files modified:** `packages/opencode-plugin/src/tui.ts`
- **Committed in:** `e3f5bab` (Task 2 commit)

**2. [Rule 1 - Bug] TS2395 declaration merging conflict with `TuiPluginModule` type import**
- **Found during:** Task 2 (Create tui.ts)
- **Issue:** `import type { TuiPluginModule }` creates a local type-only declaration, while `export const TuiPluginModule` creates an exported value. With `verbatimModuleSyntax: true` in tsconfig.json, TypeScript refuses to merge a local type with an exported value (TS2395: "Individual declarations in merged declaration 'TuiPluginModule' must be all exported or all local"). Using inline `{ type TuiPluginModule }` syntax also failed.
- **Fix:** Renamed imported type to `TuiPluginModuleType` and used that for the annotation: `export const TuiPluginModule: TuiPluginModuleType = { ... }`. Separate `import type` lines for `TuiPlugin`/`TuiSlotPlugin` (no conflict) and `TuiPluginModule as TuiPluginModuleType` (renamed to avoid conflict).
- **Files modified:** `packages/opencode-plugin/src/tui.ts`
- **Committed in:** `e3f5bab` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for type correctness. The empty-string approach is actually simpler and more maintainable than the planned `Text({})` approach. No scope creep.

## Issues Encountered

- `createElement("text", { children: "" })` also produced a TS2554 error ("Expected 1 arguments, but got 2") — the `createElement` export from `@opentui/solid` is typed as a variable (`export var createElement: any`) but TypeScript still flagged the call signature. This was avoided entirely by using empty-string renderables instead.
- TypeScript `verbatimModuleSyntax` and isolatedModules interaction required careful handling of type-only imports when they share names with value exports.

## Threats Verified

All threats from the plan's `<threat_model>` are addressed:
- **T-080-01 (Spoofing/theme path):** Mitigated — theme path constructed from `import.meta.url`, not external input.
- **T-080-02 (Tampering/theme.json):** Accepted — static asset in plugin directory; filesystem tampering is out of TUI scope.
- **T-080-03 (Information Disclosure/SSE logging):** Accepted — console logs session status events for debugging only; no PII or token data logged.

## Next Phase Readiness

- TUI scaffold ready for component population — phases 081–088 can now replace empty-string placeholders with functional `@opentui/solid` components
- `theme.json` provides consistent color contract for all downstream slot renderers
- SSE subscription pipeline proven and ready for reactive state (phases 082–085)
- Single `index.ts` entry point serves both server hooks (v8) and TUI plugins (v9+)

---

*Phase: 080-tui-entry-module-tuipluginmodule-export*
*Completed: 2026-05-05*
