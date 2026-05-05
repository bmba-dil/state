---
phase: 090
goal: "Status palette: pending/in-progress/done/failed/blocked; colors from opencode theme."
status: passed
verified: 2026-05-05
---

# VERIFICATION: Phase 090 — Node Rendering

## Must-Haves

| # | Requirement | Status |
|---|------------|--------|
| 1 | Shared status palette module with consistent color/dot/label mappings | PASS |
| 2 | Colors derived from opencode theme tokens | PASS |
| 3 | Both dag-viewer and build-progress use the shared palette | PASS |
| 4 | Node rendering applies correct status colors | PASS |

## Evidence

### 1. Shared Palette Module
- `src/tui/status-palette.ts` (132 LOC): Canonical status palette with:
  - `StepStatus` type: pending, running, done, failed, blocked, retry, unknown
  - `STATUS_COLORS`: Record<StepStatus, string> — 7 color mappings
  - `STATUS_CHARS`: Record<string, string> — 7 dot characters + compat aliases (idle, busy, in-progress)
  - `STATUS_LABELS`: Record<string, string> — 7 labels + compat aliases
  - `statusColor()`, `statusChar()`, `statusLabel()` — pure functions
  - `STATUS_COLORS_COMPAT` — backward compat map for idle/busy

### 2. Theme-Derived Colors
| Status | Hex | Theme Token |
|--------|-----|------------|
| pending | #64748B | T.textMuted |
| running | #6366F1 | T.accent |
| done | #10B981 | T.success |
| failed | #EF4444 | T.error |
| blocked | #F59E0B | T.warning |
| retry | #3B82F6 | T.info |
| unknown | #64748B | T.textMuted |

### 3. Component Migration
- `build-progress.ts`: Imports `STATUS_CHARS`, `STATUS_LABELS`, `statusColor`, `stepStatusColor` from status-palette. Re-exports `statusColor`, `stepStatusColor`. Removed inline `STATUS_DOTS` constant and `stepStatusColor` function.
- `dag-viewer.ts`: Imports `STATUS_CHARS`, `STATUS_LABELS`, `statusColor` from status-palette. Removed duplicate inline definitions.

### 4. Test Results
```
src/tui/status-palette.test.ts: 29 pass, 0 fail
src/tui/dag-viewer.test.ts: 15 pass, 0 fail
src/tui/build-progress.test.ts: 40 pass, 0 fail
src/tui/*.test.ts (all): 548 pass, 5 fail (5 pre-existing dist/)
Build (index.js): 58.34 KB (20 modules)
```

The 5 failures are pre-existing in `dist/tui/integration.test.js` (stale compiled output, not source-level).

## Human Verification Items

None — all requirements are machine-verifiable.
