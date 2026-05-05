---
phase: 104-mode-activation-event
plan: 02
subsystem: plugin
tags: [typescript, opencode-plugin, mcp, mode-activation, event-hook, hot-reload]

# Dependency graph
requires:
  - phase: 099-mcp-registration-toggle
    provides: "config.ts (readModeConfig, applyMcpRegistration), event.ts scaffold"
provides:
  - "getMcpServersForMode() pure function in config.ts — shared mode→server mapping for config + event hooks"
  - "Completed event.ts hot-reload: reads mode.json, computes MCP server list, logs structured transition"
affects: [061-daemon-client-api, mode-activation, mcp-hot-reload]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Pure function extraction for shared logic across hook boundaries", "Structured log objects with action description for DEBUG-gated event hooks"]

key-files:
  created: []
  modified:
    - "packages/opencode-plugin/src/hooks/config.ts — added getMcpServersForMode(), refactored applyMcpRegistration()"
    - "packages/opencode-plugin/src/hooks/event.ts — imported/used getMcpServersForMode(), updated logging, removed scaffold comments"

key-decisions:
  - "Extracted getMcpServersForMode() as a pure switch-based function rather than keeping mode→server mapping inline — enables event.ts to compute server list without coupling to Config mutation"
  - "Event hook computes and logs server list but does NOT call applyMcpRegistration() — Config mutation requires the daemon client API (Phase 061) since EventInput lacks input.plugin"
  - "Used switch statement over if-else chain for getMcpServersForMode() — exhaustive, readable, returns [] as default for null/invalid modes"

patterns-established:
  - "Pure function extraction for shared logic across hook boundaries: when two hooks (config + event) need the same mapping, extract into an exported pure function"
  - "Structured log objects with action descriptions: event hooks should log not just the triggering event but computed state + human-readable action summary"

requirements-completed: [MODE-03]

# Metrics
duration: 5min
completed: 2026-05-05
---

# Phase 104 Plan 02: Event Hook Hot-Reload Completion Summary

**Extracted `getMcpServersForMode()` pure function, refactored `applyMcpRegistration()` to delegate, completed event.ts hot-reload with server list computation and structured logging.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-05 (executor spawned)
- **Completed:** 2026-05-05
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extracted `getMcpServersForMode(mode: string | null): string[]` — a pure switch-based function that returns `["state-build"]`, `["state-teach"]`, `["state-build", "state-teach"]`, or `[]` for each valid mode
- Refactored `applyMcpRegistration()` to delegate server selection to `getMcpServersForMode()` — behavior-preserving, identical `input.plugin` output for all inputs
- Completed event.ts hot-reload: on `state.mode.activated`, re-reads mode.json, computes the MCP server list, and logs a structured transition message with `new_mode`, `mcp_servers` array, and human-readable `action` description
- Removed scaffold comments referencing "when Phase 104 ships" — replaced with concise forward reference to Phase 061 daemon client API

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract getMcpServersForMode()** - `5d7de4f` (refactor)
2. **Task 2: Complete event.ts hot-reload** - `d6795dc` (feat)

## Files Created/Modified

- `packages/opencode-plugin/src/hooks/config.ts` - Added `getMcpServersForMode()` pure function (lines 37-54), refactored `applyMcpRegistration()` to delegate via `input.plugin.push(...getMcpServersForMode(mode))`
- `packages/opencode-plugin/src/hooks/event.ts` - Imported and called `getMcpServersForMode()`, replaced scaffold note with concise Phase 061 reference, updated log to include `new_mode`, `mcp_servers`, and `action` fields

## Decisions Made

- **Pure function extraction:** `getMcpServersForMode()` is a `switch`-based pure function returning `string[]`. Chosen over `if-else` for exhaustiveness and readability. Both config and event hooks now import this shared mapping.
- **Event hook does NOT re-register MCP servers:** Event hook computes and logs the server list but cannot call `applyMcpRegistration()` because `EventInput` lacks `input.plugin`. Dynamic re-registration requires the daemon client API (Phase 061) or an opencode session restart.
- **Log structure:** Event hook logs `msg`, `new_mode`, `mcp_servers` array, and `action` (human-readable summary like "MCP servers to activate: state-build, state-teach"). All log output gated behind `STATE_DEBUG=1`.

## Deviations from Plan

None — plan executed exactly as written. Pre-existing TypeScript errors in `src/tui/*.test.ts` files (StepStatus union, ApiError data, type mismatches in test mocks) are out of scope and did not affect build output for hook files.

## Issues Encountered

- `bun run typecheck` and `bun run build` report errors in pre-existing test files (`src/tui/build-progress.test.ts`, `dag-viewer.test.ts`, `toast.test.ts`, etc.). These are out of scope — no new errors in `config.ts` or `event.ts`. The TypeScript compiler successfully emits `dist/hooks/config.js` and `dist/hooks/event.js` with the correct function references.

## Threat Surface

All threats covered by plan's threat model:
- **T-104-05 (Spoofing):** `event.ts` string-compares `eventType` to `"state.mode.activated"` — identical to Phase 099 pattern. No new risk.
- **T-104-06 (Tampering):** `readModeConfig()` validates mode ∈ {build, teach, both} — unchanged. Corrupted JSON returns null → `getMcpServersForMode(null)` returns `[]` gracefully.
- **T-104-07 (Info Disclosure):** `log()` output gated behind `STATE_DEBUG=1`. New log fields (`new_mode`, `mcp_servers`, `action`) contain only mode strings and server names — no secrets.

No new threat surface beyond what was modeled.

## Self-Check: PASSED

- [x] `packages/opencode-plugin/src/hooks/config.ts` — exists, contains `getMcpServersForMode()` + refactored `applyMcpRegistration()`
- [x] `packages/opencode-plugin/src/hooks/event.ts` — exists, imports `getMcpServersForMode`, computes servers, logs transition
- [x] `packages/opencode-plugin/dist/hooks/config.js` — contains compiled `getMcpServersForMode()` and delegation call
- [x] `packages/opencode-plugin/dist/hooks/event.js` — contains compiled `getMcpServersForMode()` import and invocation
- [x] Commit `5d7de4f` (Task 1) verified in git log
- [x] Commit `d6795dc` (Task 2) verified in git log
- [x] `grep -c "getMcpServersForMode" config.ts` = 3 (≥2 expected) — definition, doc comment, delegation call
- [x] `grep -c "getMcpServersForMode" event.ts` = 2 (≥1 expected) — import + invocation

## Next Phase Readiness

- Event hook fully prepared for Phase 061 daemon client API — when `state.mode.activated` fires, the plugin detects the mode change, re-reads mode.json, and knows exactly which MCP servers should be active
- `getMcpServersForMode()` is now a single source of truth for mode→server mapping across plugin hooks
- No blockers — the event hook's role (detect, re-read, compute, log) is complete

---

*Phase: 104-mode-activation-event*
*Plan: 02*
*Completed: 2026-05-05*
