---
phase: 085-toast-notifications
plan: 01
subsystem: ui
tags: [toast, notification, SSE, de-duplication, opencode-plugin, typescript, bun-test]

# Dependency graph
requires:
  - phase: 084-statusline
    provides: "Event subscription pattern (api.event.on), module-level state, lifecycle cleanup, log convention"
provides:
  - "Toast notification handler with de-duplication and 4 SSE event subscriptions"
  - "Pure functions for message generation, variant/duration mapping, and truncation"
  - "31 unit tests covering all pure functions and de-dup integration"
affects: [086-plugin-install-script, future-teach-mode-daemon-events]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level mutable state for de-duplication history (Map<string, number>)"
    - "Pure function design for all business logic — testable without mocking api"
    - "De-duplication via shouldSuppressToast/recordToast pattern"
    - "Event-type dispatch via switch-based variant/duration mapping functions"
    - "Threat-model mitigations inline: null guards on event properties, 40-char truncation, debounce pruning"

key-files:
  created:
    - "packages/opencode-plugin/src/tui/toast.ts — Toast handler (379 lines): module state, de-dup, message gen, variant/duration mapping, dispatch, event wiring"
    - "packages/opencode-plugin/src/tui/toast.test.ts — 31 unit tests covering pure functions, de-dup, message gen, variant/duration, truncation"
  modified:
    - "packages/opencode-plugin/src/tui.ts — Import setupToast, JSDoc update, setupToast(api) call in plugin init"

key-decisions:
  - "De-duplication window: 10 seconds per 080-UI-SPEC contract — same message suppressed within window"
  - "Drill availability toast (teach-mode) deferred: infrastructure supports it, but daemon events don't exist yet"
  - "Error variant is persistent (duration=0): opencode manages visibility — plugin just doesn't auto-dismiss"
  - "Toast message max 40 chars enforced by truncateToastMessage with U+2026 ellipsis"

patterns-established:
  - "De-dup pattern: shouldSuppressToast (pure check) → recordToast (mutate + prune) → api.ui.toast (dispatch)"
  - "Event wiring pattern: subscribe to 4 event types, each derives variant/duration/message, then dispatches via shared dispatchToast"
  - "Testing pattern: pure functions tested with constructed event objects — no mock TuiPluginApi needed"

requirements-completed:
  - TUI-04

# Metrics
duration: 6min
completed: 2026-05-05
---

# Phase 085 Plan 01: Toast Notification Handler Summary

**Toast notification handler with de-duplication — maps 4 daemon SSE events to transient terminal toasts via api.ui.toast(), with 10s de-duplication window and 40-char message truncation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-05T14:06:14Z
- **Completed:** 2026-05-05T14:12:14Z
- **Tasks:** 2
- **Files created/modified:** 3 (2 created, 1 modified)

## Accomplishments

- Created `toast.ts` (379 lines) with full Section structure: types, module state, de-dup functions, message generation, variant/duration mapping, truncation, dispatch orchestration, and event wiring
- Subscribed to 4 SSE event types: `session.next.step.ended`, `session.next.step.failed`, `session.error`, `server.connected`
- Implemented de-duplication with 10-second window — identical messages suppressed, stale entries pruned on each dispatch
- Enforced 40-character message truncation per 080-UI-SPEC copywriting contract using U+2026 ellipsis
- Wired into `tui.ts` plugin initialization after `setupStatusline(api)` with lifecycle cleanup
- 31 unit tests pass across 11 test suites, 0 failures — full TUI suite (98 tests) passes with 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests** — `fbbc5e1` (test)
2. **Task 1 (GREEN): Implement toast handler** — `ae2d528` (feat)
3. **Task 2: Wire toast into tui.ts** — `2d65529` (feat)

## Files Created/Modified

- `packages/opencode-plugin/src/tui/toast.ts` — Toast notification handler with 8 sections: types, module-level TOAST_HISTORY state, de-dup pure functions (shouldSuppressToast, recordToast), message generation (toastMessageForStepEnded, toastMessageForStepFailed, toastMessageForServerConnected, toastMessageForSessionError), variant/duration mapping (toastVariantForEvent, toastDurationForEvent), truncation utility (truncateToastMessage), dispatch orchestrator (dispatchToast), and event wiring (setupToast)
- `packages/opencode-plugin/src/tui/toast.test.ts` — 31 unit tests in 11 describe blocks: shouldSuppressToast (5), recordToast (3), toastMessageForStepEnded (2), toastMessageForStepFailed (3), toastMessageForServerConnected (1), toastVariantForEvent (6), toastDurationForEvent (6), truncateToastMessage (3), TOAST_HISTORY defaults (1), de-dup integration (1)
- `packages/opencode-plugin/src/tui.ts` — Added import for `setupToast`, JSDoc block update (Phase 085), `setupToast(api)` call after `setupStatusline(api)`

## Decisions Made

- De-duplication window is 10 seconds (per 080-UI-SPEC contract). Module-level `TOAST_HISTORY` Map prunes stale entries on every `recordToast()` call
- Drill availability toast for teach-mode is deferred — `setupToast()` accepts new subscriptions additively when teach-mode daemon events mature
- Error variant toasts use `duration=0` (persistent) — opencode manages visibility, plugin just doesn't set an auto-dismiss timer
- All user-visible strings match the 080-UI-SPEC copywriting contract exactly: ✓ (U+2713 check mark), "Slice {id} complete ✓", "Auth token refreshed"

## Deviations from Plan

None — plan executed exactly as written. TDD cycle completed as specified: RED (failing tests, commit fbbc5e1) → GREEN (implementation, commit ae2d528) → wiring (tui.ts, commit 2d65529).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for Phase 086 (plugin-install-script) — toast handler is self-contained, no shared state with other phases
- Full TUI test suite (98 tests) remains green — no regressions from Phase 085 additions
- Threat model mitigations (T-085-01 through T-085-04) are implemented inline: null guards on event properties, 40-char truncation prevents oversized payloads, de-duplication prevents toast spam from rapid SSE bursts

---
*Phase: 085-toast-notifications*
*Completed: 2026-05-05*
