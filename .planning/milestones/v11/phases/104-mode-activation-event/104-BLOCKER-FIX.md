---
phase: 104
fixed_at: "2026-05-05T00:00:00Z"
review_path: null
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 104: Blocker Fix Report

**Fixed at:** 2026-05-05
**Iteration:** 1

**Summary:**
- Findings in scope: 1
- Fixed: 1
- Skipped: 0

## Fixed Issues

### BLOCKER: Stale mode cache after state.mode.activated event

**Files modified:** `packages/opencode-plugin/src/hooks/event.ts`
**Commit:** `e1fd189`
**Applied fix:** After `state.mode.activated` event handler re-reads `mode.json` via `readModeConfig()`, the module-level cache in `mode-reader.ts` (used by `getCurrentMode()` in command/tool hooks) was not invalidated. This meant hooks continued using the stale cached mode after hot-reload.

**Changes:**
1. Added `import { resetModeCache } from "../mode-reader.js"` to `event.ts` (line 6)
2. Called `resetModeCache()` immediately after `readModeConfig(cwd)` succeeds (line 24), before the transition is logged

This ensures that the next `getCurrentMode()` call in command/tool hooks reads the fresh mode from disk.

---

_Fixed: 2026-05-05_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
