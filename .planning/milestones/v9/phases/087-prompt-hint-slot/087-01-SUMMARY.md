---
phase: 087-prompt-hint-slot
plan: 01
subsystem: ui
tags: [opencode-plugin, tui, prompt-hint, sse, constructs-api, @opentui/core, bun-test, bun]

# Dependency graph
requires:
  - phase: 084-statusline
    provides: "formatCost pure function, statusline event-wiring pattern, Txt/truncate helpers"
  - phase: 082-build-progress
    provides: "module-level state + sync render pattern, constructs API patterns"
provides:
  - "PromptHint component with module-level SSE state and sync render via @opentui/core constructs API"
  - "session_prompt_right TUI slot wired to renderPromptHint()"
  - "shortenModelID pure function for model ID display truncation"
affects: [088-bun-test-suite, future-tui-slots, session_prompt_right]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level mutable state + synchronous render (inherited from 080/084)"
    - "SSE event bus subscription pattern via api.event.on (match statusline.ts)"
    - "Pure function exports for testability (shortenModelID)"
    - "Cross-module function import (formatCost from statusline.ts, not duplicated)"

key-files:
  created:
    - "packages/opencode-plugin/src/tui/prompt-hint.ts (232 lines)"
    - "packages/opencode-plugin/src/tui/prompt-hint.test.ts (104 lines)"
  modified:
    - "packages/opencode-plugin/src/tui.ts (3 edits: import, setup call, slot replacement)"

key-decisions:
  - "formatCost imported from statusline.ts rather than re-implemented — single source of truth for cost formatting"
  - "ATTR_DIM applied to whole line when disconnected (rather than per-segment) — matches statusline.ts dim pattern"
  - "Step counter displays 'Step N' only when connected; falls back to em dash otherwise"

patterns-established:
  - "PromptHintState: connection, model, cost, stepCount — minimal fields for session_prompt_right"
  - "shortenModelID: last-segment extraction with defensive empty/undefined fallback to em dash"
  - "T-087-01 mitigation: typeof + isFinite guard on cost before storing to state"
  - "T-087-02 mitigation: shortenModelID empty-string/undefined fallback prevents rendering untrusted strings"

requirements-completed:
  - TUI-03

# Metrics
duration: 5min
completed: 2026-05-05
---

# Phase 087 Plan 01: Prompt Hint Slot Summary

**PromptHint component with SSE event wiring, model abbreviation rendering, and session_prompt_right slot activation using @opentui/core constructs API**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-05T14:35:10Z
- **Completed:** 2026-05-05T14:39:48Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Created `prompt-hint.ts` (232 LOC) with full SSE event wiring: subscribes to `session.next.model.switched`, `session.next.step.ended`, and `session.status` events via `api.event.on`
- `shortenModelID` pure function extracts last segment of full model IDs (e.g., `deepseek/deepseek-v4-pro` → `deepseek-v4-pro`) with em dash fallback for empty/undefined
- `renderPromptHint()` returns compact single-line Box: `{model} · {cost} · Step {N}` with 28-cell max width truncation; model in accent bold, cost/step in textMuted; unreachable state shows dimmed em dash, disconnected applies ATTR_DIM to last-known data
- `session_prompt_right` slot wired from empty `""` placeholder to live `renderPromptHint()`
- `formatCost` imported from `statusline.ts` — no duplicate implementation
- 14 unit tests pass (5 shortenModelID, 4 PROMPT_HINT_STATE defaults, 5 renderPromptHint); 120 total tests across TUI suite with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing test for prompt-hint** — `e793b42` (test)
2. **Task 1 GREEN: implement prompt-hint component** — `5868313` (feat)
3. **Task 2: wire prompt-hint into tui.ts** — `a1119a3` (feat)

## Files Created/Modified
- `packages/opencode-plugin/src/tui/prompt-hint.ts` — PromptHint component: types, theme, state, shortenModelID, renderPromptHint, setupPromptHint (232 lines)
- `packages/opencode-plugin/src/tui/prompt-hint.test.ts` — Unit tests: shortenModelID (5), state defaults (4), render output (5) [104 lines]
- `packages/opencode-plugin/src/tui.ts` — Import prompt-hint, call setupPromptHint(api), replace session_prompt_right placeholder with renderPromptHint() (+6/-2 lines)

## Decisions Made
- `formatCost` imported from `statusline.ts` rather than re-implemented — single source of truth for cost formatting, consistent with plan's "do not re-implement" directive
- `ATTR_DIM` applied to whole line when disconnected (rather than per-segment) — matches statusline.ts dim pattern for visual consistency
- `stepCount` always incremented on `step.ended` (no guard) — the increment is simple arithmetic; threat model accepts IEEE 754 overflow as negligible risk (T-087-04)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Threat Model Compliance

All 5 threats from plan's STRIDE register addressed:

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-087-01 (cost tampering) | `typeof cost === "number" && isFinite(cost)` guard before storing | ✓ Implemented |
| T-087-02 (model ID tampering) | `shortenModelID` empty/undefined fallback to `"—"` | ✓ Implemented |
| T-087-03 (cost disclosure) | Cost already visible in statusline; no new boundary | ✓ Accepted |
| T-087-04 (step counter overflow) | IEEE 754 double; state reset on dispose | ✓ Accepted |
| T-087-05 (model string privilege) | Model ID is display-only, not used for auth/routing | ✓ Accepted |

## Next Phase Readiness
- Ready for Phase 088 (bun test suite — cross-component integration tests)
- PromptHint component is fully self-contained with its own test coverage
- No blocking dependencies or known issues

---
## Self-Check: PASSED

- ✅ `packages/opencode-plugin/src/tui/prompt-hint.ts` exists (232 lines)
- ✅ `packages/opencode-plugin/src/tui/prompt-hint.test.ts` exists (104 lines)
- ✅ `087-01-SUMMARY.md` exists
- ✅ Commit `e793b42` (RED) found in git log
- ✅ Commit `5868313` (GREEN) found in git log
- ✅ Commit `a1119a3` (Task 2) found in git log
- ✅ All 120 TUI tests pass (14 new + 106 existing), zero regressions
- ✅ formatCost imported from statusline.ts (not duplicated)
- ✅ session_prompt_right slot returns renderPromptHint() (not empty string)
- ✅ setupPromptHint(api) called after setupStatusline(api)

---
*Phase: 087-prompt-hint-slot*
*Completed: 2026-05-05*
