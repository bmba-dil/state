# 096-CONTEXT — Integration Smoke Test

**Phase:** 096 — Verify DAG viewer works in build and teach modes
**Depends on:** 089-095
**Target file:** `packages/opencode-plugin/src/tui/dag-viewer.test.ts`

## Current State

All unit tests for individual functions pass. No cross-mode integration test exists.
The dag-viewer component is designed for build-mode DAGs but should handle teach-mode
concept graphs.

## What This Phase Adds

1. Integration test that creates build-mode DAG nodes (arc→phase→slice→step)
2. Verifies status colors render correctly
3. Verifies navigation works end-to-end
4. Verifies filter works end-to-end
5. Creates teach-mode nodes (subject→lesson→concept→drill) and verifies rendering

## Key Decisions

- Test uses direct module-level state mutation (no SSE needed)
- Build-mode: arc/phase/slice/step hierarchy
- Teach-mode: subject/lesson/concept/drill hierarchy
- Both use same render path (renderDagViewer is mode-agnostic)

## Edge Cases

- Empty teach DAG: renders empty state message
- Mixed statuses: all status colors appear in legend
