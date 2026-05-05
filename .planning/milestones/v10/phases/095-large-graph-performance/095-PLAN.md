# 095-PLAN — Large-Graph Performance

## Tasks

### T1 — Implement layout cache key
```
function layoutCacheKey(nodes: DagNode[], edges: DagEdge[]): string
```
Deterministic string from sorted IDs and edge pairs.

### T2 — Implement memoizeLayout()
Module-level cache:
```
let _layoutCacheKey: string = "";
let _layoutCache: LayoutNode[] | null = null;
```
In renderDagViewer, check key before recomputing layout.

### T3 — Implement viewport clipping
In renderDagViewer canvas loop:
```
if (totalRows > 100) {
  // Only render rows [scrollOffset, scrollOffset + viewportH]
}
```
Skip off-screen rows, only emit Box children for visible rows.

### T4 — Add 500-node stress test
Create 500-node chain, verify:
- Layout computed correctly (no overlapping positions)
- Layout cache hit on second call
- Render output only contains visible rows

### T5 — Verify existing tests still pass
All existing layout and render tests must pass with cache + viewport.

## Verification
- `cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts`
