# 092-PLAN — Filter Bar

## Tasks

### T1 — Add filterPreset to DagViewerState
Add `filterPreset: "all" | "active" | "blocked" | "critical"` (default `"all"`).

### T2 — Implement computeCriticalPath()
DP algorithm:
1. Build adjacency, compute in-degree
2. Topological order (Kahn)
3. Forward pass: longest distance from any root to each node
4. Backtrack from max-distance leaf to roots to collect path
5. Return Set of node IDs on the critical path

### T3 — Implement filterNodes()
Takes state, uses computeTopologicalLayout, filters by preset:
- `"all"`: return all layout nodes
- `"active"`: only `"running"` or `"pending"` status
- `"blocked"`: only `"blocked"` status  
- `"critical"`: only nodes on critical path

### T4 — Add filter bar to renderDagViewer()
Between legend and canvas, render:
```
Filter: all ▸ 5 nodes (▴3 ↑2 ●1)
```
where ▸ = critical, ↑ = running, ● = done, etc.

### T5 — Add tests
- Each filter preset returns correct subset
- computeCriticalPath for chain, diamond, disconnected graphs
- Critical path on single node, equal-length paths
- Render output includes filter bar text

## Verification
- `cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts`
- Manual: route shows filter bar, toggling filters redraws canvas
