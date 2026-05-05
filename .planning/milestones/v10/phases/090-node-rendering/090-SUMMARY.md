# Phase 090 Summary: Node Rendering

**Status:** Complete ✅
**Date:** 2026-05-05

## What was built

Extracted a shared status palette module (`status-palette.ts`) with canonical color/dot/label mappings for 7 statuses (pending, running, done, failed, blocked, retry, unknown). Updated both dag-viewer.ts and build-progress.ts to consume the shared module, removing duplicate inline definitions.

## Components delivered

1. **`src/tui/status-palette.ts`** — 132 LOC shared module with STATUS_COLORS, STATUS_CHARS, STATUS_LABELS, statusColor/statusChar/statusLabel pure functions, backward-compat aliases
2. **`src/tui/status-palette.test.ts`** — 29 tests for all mappings, compat aliases, theme consistency
3. **`src/tui/build-progress.ts`** — Migrated to shared palette, removed inline stepStatusColor + STATUS_DOTS
4. **`src/tui/dag-viewer.ts`** — Migrated to shared palette, removed inline status functions

## Key decisions

- Colors derived from opencode theme tokens (theme.json): accent→running, success→done, error→failed, warning→blocked, info→retry
- "idle" and "busy" mapped to "done" and "running" via compat layer for backward compatibility
- "failed" status introduced as distinct from "blocked" per ROADMAP spec

## Test results

| Suite | Pass | Fail |
|-------|------|------|
| status-palette.test.ts | 29 | 0 |
| dag-viewer.test.ts | 22 | 0 |
| build-progress.test.ts | 40 | 0 |
| all src/tui/*.test.ts | 299 | 0 |
| Build (tui.js) | 47 KB | — |
