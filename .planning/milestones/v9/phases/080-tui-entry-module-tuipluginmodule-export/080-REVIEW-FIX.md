---
phase: 080-tui-entry-module-tuipluginmodule-export
fixed_at: 2026-05-05T00:00:00Z
review_path: .planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 080: Code Review Fix Report

**Fixed at:** 2026-05-05
**Source review:** .planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### MF-01: theme.json unavailable after bundling — runtime theme install will fail

**Files modified:** `packages/opencode-plugin/package.json`
**Commit:** `58e90b0`
**Applied fix:** Added `cp src/theme.json dist/` to the `dist` build script so `theme.json` is copied alongside bundled output. The `TuiTheme` API (`@opencode-ai/plugin/tui`) only supports `install(jsonPath: string)`, not an inline object — so inlining was not feasible. The build-script copy (Option B from the review) is the correct approach.

### SF-01: Unsafe type cast in SSE event handler — loss of type safety

**Files modified:** `packages/opencode-plugin/src/tui.ts`
**Commit:** `ccf53b8`
**Applied fix:** Removed `(event as Record<string, unknown>)` unsafe type casts. The `TuiEventBus.on()` method generic already infers the correct type via `Extract<Event, { type: Type }>`, so the handler parameter is typed as `EventSessionStatus`. Also fixed the property path: `event.properties.sessionID` and `event.properties.status` (previously the cast accessed top-level `.sessionID`/`.status` which don't exist on the nested `EventSessionStatus.properties` shape).

### SF-02: console.log used for operational logging — no filtering, no levels

**Files modified:**
- `packages/opencode-plugin/src/logger.ts` (new)
- `packages/opencode-plugin/src/tui.ts`
- `packages/opencode-plugin/src/hooks/chat-message.ts`
- `packages/opencode-plugin/src/hooks/tool-execute-after.ts`
- `packages/opencode-plugin/src/hooks/permission-ask.ts`
- `packages/opencode-plugin/src/hooks/command-execute-before.ts`

**Commit:** `755cef5`
**Applied fix:** Created `src/logger.ts` with a `STATE_DEBUG` env var gate (`log()` is a no-op when `STATE_DEBUG !== "1"`). Replaced all `console.log(JSON.stringify({...}))` calls across 5 files with `log({...})` calls. The structured data shape is preserved — only the gating is added.

### SF-03: Unnecessary async on synchronous server() factory

**Files modified:** `packages/opencode-plugin/src/index.ts`
**Commit:** `e147ace`
**Applied fix:** The `PluginModule["server"]` type is `Plugin = (input, options?) => Promise<Hooks>`. The `Promise<Hooks>` return type mandates the `async` keyword (without it, the plain object return is not assignable). Added a documentation comment above the `server` export explaining this type constraint so future reviewers understand the `async` is not removable overhead.

---

_Fixed: 2026-05-05_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
