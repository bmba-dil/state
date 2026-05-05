# 093-CONTEXT — SSE Live Updates

**Phase:** 093 — Subscribe to daemon SSE; diff-patch node status
**Depends on:** 090, 092
**Target file:** `packages/opencode-plugin/src/tui/dag-viewer.ts`

## Current State

`setupDagViewer` subscribes to `session.status` and populates placeholder nodes on first
connect. `applyStatusPatch()` does not exist. No incremental update handling.

## What This Phase Adds

1. `applyStatusPatch(nodes, patches)`: merges status updates into node list
2. Diff-patch: only update nodes whose status actually changed
3. Subscribe to `session.next.step.ended` in setupDagViewer
4. On step ended, update the corresponding node status via applyStatusPatch
5. Tests with mocked SSE event handlers

## Key Decisions

- Patches are `Array<{ id: string; status: StepStatus }>`
- Diff check: compare old status with new; only write if different
- Step ended event carries step ID and status → maps to node.id in DAG
- Patch applies to DAG_VIEWER_STATE.nodes (mutable update)

## Edge Cases

- Patch for unknown node ID: silently ignored
- Same status received: no-op (diff check)
- Multiple patches in one event: all applied atomically
- Empty patches array: no change to state
