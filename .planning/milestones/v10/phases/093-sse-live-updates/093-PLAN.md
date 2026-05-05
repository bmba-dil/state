# 093-PLAN — SSE Live Updates

## Tasks

### T1 — Implement applyStatusPatch()
```
applyStatusPatch(nodes: DagNode[], patches: Array<{ id: string; status: StepStatus }>): DagNode[]
```
- For each patch, find matching node by id
- Only update if status differs (diff check)
- Return new array (or mutate existing — use module-level pattern)

### T2 — Subscribe to session.next.step.ended
In setupDagViewer, add event subscription:
```
api.event.on("session.next.step.ended", (event) => {
  // Extract step ID and status from event properties
  // Call applyStatusPatch to update DAG_VIEWER_STATE.nodes
})
```

### T3 — Handle session.next.step.failed
On step failure, update node status to "failed".

### T4 — Add tests
- applyStatusPatch updates matching node
- applyStatusPatch ignores non-matching IDs
- applyStatusPatch is no-op when status unchanged (diff)
- Multiple patches applied correctly
- SSE event handler correctly extracts step data

## Verification
- `cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts`
- Mock SSE events verify state mutation
