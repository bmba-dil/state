# Deferred Items — Phase 100 Plan 01

## Pre-existing TUI Test Type Errors

**Source:** `packages/opencode-plugin/src/tui/*.test.ts`
**Discovered:** Task 2 verification (bun run dist → tsc step)
**Status:** Out of scope — not caused by this plan's changes

These pre-existing TypeScript errors block the `tsc --noEmit` step in the `dist` pipeline:
- `build-progress.test.ts`: StepStatus type mismatches
- `dag-viewer.test.ts`: Argument type mismatches
- `integration.test.ts`: Missing properties, undefined identifiers, type mismatches
- `plugin-install.test.ts`: Missing properties from TuiPluginMeta
- `toast.test.ts`: Missing `data` property in error types

The `bun run bundle` step (actual production artifact) completes successfully. These test-file type errors should be addressed in a future plan focused on TUI test cleanup.
