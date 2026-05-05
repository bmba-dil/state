---
phase: 099-mcp-registration-toggle
plan: 01
subsystem: opencode-plugin
tags: [config-hook, event-hook, mode-enforcement, mcp-registration, layer-3]
requires:
  - "Phase 097-098: Mode schema and .state/mode.json creation"
provides:
  - "Boot-time MCP server registration based on .state/mode.json"
  - "Event hook scaffold for state.mode.activated hot-reload"
affects: ["Phase 104: Mode activation event (daemon SSE)", "Phase 053: Daemon HTTP middleware (layer 5)"]
tech-stack:
  added: []
  patterns:
    - "Config hook pattern: reads filesystem state at boot, mutates config.plugin"
    - "Event hook scaffold pattern: re-reads mode.json and logs, defers full re-registration to daemon client API"
key-files:
  created:
    - packages/opencode-plugin/src/hooks/config.ts
    - packages/opencode-plugin/src/hooks/event.ts
  modified:
    - packages/opencode-plugin/src/index.ts
key-decisions:
  - "Use process.cwd() for project root (Config hook type doesn't expose directory)"
  - "Export readModeConfig and applyMcpRegistration for reuse by event hook"
  - "Use type cast in event.ts for state.mode.activated comparison (event type not yet in opencode SDK union)"
  - "Strict mode validation: only 'build', 'teach', 'both' accepted as valid modes"
patterns-established:
  - "Hook modules export a single named constant with NonNullable<Hooks['hook.name']> type"
  - "Config hook: filesystem read → validate → mutate input.plugin in-place"
  - "Event hook: event.type filter → re-read state → log transition"
requirements-completed: [MODE-03]
metrics:
  duration: "~8 minutes"
  completed: 2026-05-05
---

# Phase 099 Plan 01: MCP Registration Toggle (Config Hook) Summary

**One-liner:** Boot-time dynamic MCP server registration via opencode `config` hook reading `.state/mode.json`, with `event` hook scaffold for hot-reload on mode change.

## Completed Tasks

### Task 1: Create config hook (`config.ts`)

**File:** `packages/opencode-plugin/src/hooks/config.ts` — 71 lines

Implements the canonical type-safe `config` hook for MCP server registration (layer 3 of 6 for mode enforcement).

**Exports:**
- `readModeConfig(projectDir)` — reads `.state/mode.json`, validates `mode` ∈ {build, teach, both}, returns string or null
- `applyMcpRegistration(mode, input)` — filters existing `state-*` entries from `input.plugin`, then pushes correct servers based on mode
- `config` — `NonNullable<Hooks["config"]>` hook wiring both helpers

**Key behaviors:**
- File missing → log warning, no MCP servers registered (graceful degradation)
- Invalid JSON → catch, log error, no servers registered
- Invalid mode value → log error, no servers registered
- `"both"` mode → both `state-build` and `state-teach` registered
- Existing `state-*` entries from previous loads are removed before adding correct ones

**Commands:** Task 1 completed and committed at `09e4393`.

### Task 2: Create event hook and wire into `index.ts`

**Files:**
- `packages/opencode-plugin/src/hooks/event.ts` — 34 lines (event hook scaffold)
- `packages/opencode-plugin/src/index.ts` — modified (imports + server object)

**event.ts:** Listens for `state.mode.activated` events, re-reads `mode.json`, logs the transition. Full MCP re-registration via daemon client API deferred to Phase 104. Uses `as string` type cast because `"state.mode.activated"` is not yet in the opencode SDK `Event.type` union.

**index.ts:** Added `config` and `event` imports between `command-execute-before` and `shell-env` (alphabetical). Server object reordered to full alphabetical sort with all 12 hooks.

**Commands:** Task 2 completed and committed at `3eb0233`.

## Verification Results

| Check | Result |
|-------|--------|
| `config` hook exported from `config.ts` | ✅ PASSED |
| `event` hook exported from `event.ts` | ✅ PASSED |
| `readModeConfig` exported from `config.ts` | ✅ PASSED |
| `applyMcpRegistration` exported from `config.ts` | ✅ PASSED |
| `event.ts` imports `readModeConfig` from `config.ts` | ✅ PASSED (2 references) |
| 11 hook import statements in `index.ts` | ✅ PASSED |
| 12 hook keys in server object (10 existing + 2 new) | ✅ PASSED |
| `bun run typecheck` — zero errors in config/event/index | ✅ PASSED |
| `bun run build` — dist/ populated with config.js, event.js | ✅ PASSED |
| Strict mode validation (build/teach/both only) | ✅ PASSED |
| Graceful degradation (missing/invalid mode.json) | ✅ PASSED |
| All 10 existing hooks remain wired and unchanged | ✅ PASSED |

**Note:** `bun run typecheck` and `bun run build` report pre-existing TypeScript errors in 5 test files (build-progress.test.ts, dag-viewer.test.ts, integration.test.ts, plugin-install.test.ts, toast.test.ts). These are out of scope for this plan and documented in `deferred-items.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] TypeScript strict comparison error in event.ts**
- **Found during:** Task 2 verification (build)
- **Issue:** `"state.mode.activated"` is not in the opencode SDK `Event.type` union, causing TS2367: "comparison appears to be unintentional"
- **Fix:** Added `as string | undefined` type cast to `input.event?.type` assignment, with explanatory comment noting Phase 104 will add the event type
- **Files modified:** `packages/opencode-plugin/src/hooks/event.ts`
- **Commit:** `3eb0233`

### Plan Count Discrepancy

The plan's frontmatter said "9 hooks already implemented" but the actual codebase has 10 existing hooks. The correct totals are:
- 10 existing hook keys + 2 new = 12 total hook keys
- 9 existing import statements + 2 new = 11 total import statements

All counts verified against actual code. No code changes needed — this was a documentation miscount in the plan.

## Known Stubs

| File | Line(s) | Reason |
|------|---------|--------|
| `packages/opencode-plugin/src/hooks/event.ts` | 13, 31 | Event hook is an intentional scaffold. It re-reads `mode.json` and logs the transition, but does not invoke daemon client API for full MCP re-registration. This will be implemented when Phase 104 (mode activation event + daemon SSE) ships. |

## Self-Check: PASSED

- ✅ `packages/opencode-plugin/src/hooks/config.ts` exists
- ✅ `packages/opencode-plugin/src/hooks/event.ts` exists
- ✅ `packages/opencode-plugin/src/index.ts` modified with config+event wiring
- ✅ Commit `09e4393`: Task 1 (config hook)
- ✅ Commit `3eb0233`: Task 2 (event hook + index.ts wiring)
- ✅ All verification criteria met
