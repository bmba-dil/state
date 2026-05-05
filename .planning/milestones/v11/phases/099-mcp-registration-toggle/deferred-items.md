
## Pre-existing TypeScript errors (not caused by 099-01)

Found during `bun run typecheck` on 2026-05-05. All in test files with zero reference to config.ts:

- `src/tui/build-progress.test.ts` — 2 errors (StepStatus type mismatch)
- `src/tui/dag-viewer.test.ts` — 5 errors (expect.toBe null vs string)
- `src/tui/integration.test.ts` — 6 errors (missing properties, undefined var, type mismatch)
- `src/tui/plugin-install.test.ts` — 1 error (missing properties)
- `src/tui/toast.test.ts` — 5 errors (EventSessionError property mismatch)

These are pre-existing and out of scope for this plan. New config.ts has zero type errors.
