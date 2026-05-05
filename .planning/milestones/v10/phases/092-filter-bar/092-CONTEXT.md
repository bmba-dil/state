# 092-CONTEXT — Filter Bar

**Phase:** 092 — Filter bar with presets and critical-path computation
**Depends on:** 090, 091
**Target file:** `packages/opencode-plugin/src/tui/dag-viewer.ts`

## Current State

DAG viewer renders all nodes in topological layout. No filtering exists. `DagViewerState` has
`nodes`, `edges`, `selectedNode`, `focusedNode`, `scrollOffset`, `viewportHeight`, `connection`.

Navigation functions (`navigateUp`, `navigateDown`, `selectFocused`, `deselectNode`) work
against the full node list.

## What This Phase Adds

1. `filterPreset` field on `DagViewerState`: `"all" | "active" | "blocked" | "critical"`
2. `filterNodes(state)`: filters LayoutNode[] by current preset
3. `computeCriticalPath(nodes, edges)`: longest-path DP from roots to leaves
4. Filter bar in `renderDagViewer()` output (text line showing preset + counts)
5. Unit tests for each filter preset and critical-path computation

## Key Decisions

- Critical path = longest simple path from any root to any leaf (DP, O(V+E))
- "Active" filter = nodes with status `"running"` OR `"pending"`
- "Blocked" filter = nodes with status `"blocked"`
- Filter bar renders as a single text line between legend and canvas
- Filter operates on LayoutNode results (post-layout computation)

## Edge Cases

- Empty node list: filter bar shows "0 nodes"
- No roots/leaves for critical path: returns empty set
- Filtered to zero nodes: canvas shows "No nodes match filter"
- Multiple equal-length critical paths: all returned
