---
phase: 100
plan: "01"
subsystem: opencode-plugin
tags: [mode-gate, hooks, defense-in-depth, mode-reader, caching]
requires:
  - "099 (readModeConfig from config.ts)"
provides:
  - Cached mode-reader.ts wrapping readModeConfig with module-level caching
  - Mode-gated command.execute.before hook blocking cross-mode slash commands
  - Mode-gated tool.execute.before hook blocking cross-mode MCP tool invocations
  - 20 unit + integration tests covering full mode matrix
affects:
  - "future: daemon HTTP middleware (layer 5 gate)"
tech-stack:
  added: []
  patterns:
    - module-level-caching (getCurrentMode reads file once, resetModeCache for hot-reload)
    - permissive-null-default (absent mode.json = no blocking, defense-in-depth ordering)
key-files:
  created:
    - packages/opencode-plugin/src/mode-reader.ts
    - packages/opencode-plugin/src/__tests__/mode-reader.test.ts
    - packages/opencode-plugin/src/__tests__/hooks/mode-gate.test.ts
  modified:
    - packages/opencode-plugin/src/hooks/command-execute-before.ts
    - packages/opencode-plugin/src/hooks/tool-execute-before.ts
key-decisions:
  - "Mode reading uses module-level caching — file read once, not on every hook invocation"
  - "Both hooks use process.cwd() as projectDir (same assumption as config.ts)"
  - "Null mode (absent/invalid mode.json) is permissive — canonical gate at layer 5 provides authoritative block"
  - "Both mode explicitly permissive — user explicitly chose no blocking"
  - "Kernel mode not present in mode.json — internal-only, not persistable"
patterns-established:
  - "Cached wrapper pattern: thin module wrapping a read-once function with explicit reset for hot-reload"
  - "Hook gate pattern: early-return for permissive modes, prefix-matching for cross-mode blocking"
requirements-completed:
  - MODE-04
metrics:
  duration: 5m
  completed: 2026-05-05
---

# Phase 100 Plan 01: Plugin Hook Mode Gate Summary

**One-liner:** Replaced `process.env.STATE_MODE` in command/tool hooks with a cached `.state/mode.json` reader, enforcing cross-mode isolation at layer 4 of the 6-layer defense-in-depth.

## Tasks Completed

| # | Name | Commit | Type |
|---|------|--------|------|
| 1 | Create mode-reader.ts with cached getCurrentMode() + tests | `7a77338` | feat |
| 2 | Update command and tool hooks to use getCurrentMode() + mode gate tests | `e59d15a` | feat |

## Implementation Summary

### Task 1: mode-reader.ts

Created `packages/opencode-plugin/src/mode-reader.ts` wrapping `readModeConfig` from `config.ts` (Phase 099) with module-level caching:

- **`getCurrentMode(projectDir)`** — reads `.state/mode.json` on first call, returns cached `ResolvedMode` on subsequent calls. Returns `null` when file is absent/malformed/invalid.
- **`resetModeCache()`** — invalidates cache for hot-reload on mode change.
- 8 unit tests covering cache hits, mode validation (build/teach/both), invalid mode rejection, null-mode fallback, and cache invalidation.

### Task 2: Hook Updates

**command-execute-before.ts:**
- Replaced `process.env.STATE_MODE` with `await getCurrentMode(process.cwd())`
- Removed `"kernel"` mode handling (not in mode.json)
- Added permissive early-return for `"both"` and `null` modes
- Blocking logic unchanged: `/state:build:*` blocked in teach mode, `/state:teach:*` blocked in build mode

**tool-execute-before.ts:**
- Same mode source replacement as command hook
- Same permissive early-return for `"both"` and `null` modes
- Tool blocking logic preserved: `mcp__state-teach__*` blocked in build mode, `mcp__state-build__*` blocked in teach mode
- Path-rewriting logic (`rewriteStatePaths`, `isStateTool`) preserved unchanged

**mode-gate.test.ts:**
- 12 integration tests covering the full mode enforcement matrix
- Command hook: 6 tests (build↔teach blocking/allowing, both-mode permissive, null-mode permissive)
- Tool hook: 6 tests (build↔teach blocking/allowing, both-mode permissive, null-mode permissive)

## Verification Results

| Check | Result |
|-------|--------|
| `process.env.STATE_MODE` references in hooks | ✓ 0 found |
| `getCurrentMode` imports in hooks | ✓ Both hooks import from mode-reader |
| mode-reader tests (8) | ✓ All pass |
| mode-gate tests (12) | ✓ All pass |
| Bundle build (bun build) | ✓ 23 modules bundled in 12ms |
| TypeScript (plan files only) | ✓ No errors in new/modified files |

## Deviations from Plan

### Pre-existing Issues (Out of Scope)

**1. TUI test type errors block full `tsc` in dist pipeline**
- **Found during:** Verification step (bun run dist)
- **Issue:** Pre-existing TypeScript errors in `src/tui/*.test.ts` (build-progress, dag-viewer, integration, plugin-install, toast) cause `tsc --noEmit` to fail
- **Disposition:** Out of scope — these files were not modified by this plan. The `bun run bundle` step (actual production artifact) completes successfully
- **Logged to:** `.planning/milestones/v11/phases/100-plugin-hook-mode-gate/deferred-items.md`

None — plan executed exactly as written with zero auto-fixes needed.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: tampering | mode-reader.ts | .state/mode.json content crosses trust boundary — mitigated by readModeConfig validation (Phase 099) returning null on invalid content |

## Self-Check: PASSED

- [x] `packages/opencode-plugin/src/mode-reader.ts` exists
- [x] `packages/opencode-plugin/src/__tests__/mode-reader.test.ts` exists
- [x] `packages/opencode-plugin/src/__tests__/hooks/mode-gate.test.ts` exists
- [x] Commit `7a77338` exists in git log
- [x] Commit `e59d15a` exists in git log
- [x] All 20 tests pass (8 mode-reader + 12 mode-gate)
- [x] Zero `process.env.STATE_MODE` references in hook files
- [x] Both hooks import `getCurrentMode` from mode-reader
