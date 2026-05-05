# 095-CONTEXT — Large-Graph Performance

**Phase:** 095 — Virtualized rendering; clip off-screen; layout cache
**Depends on:** 090, 092
**Target file:** `packages/opencode-plugin/src/tui/dag-viewer.ts`

## Current State

`computeTopologicalLayout` runs on every render call — O(V+E) per frame. All rows are
rendered regardless of viewport — O(rows) render cost. No memoization or viewport clipping.

## What This Phase Adds

1. Layout cache: `memoizeLayout()` wrapper around computeTopologicalLayout
2. Cache key: hash of node IDs + edge pairs (sorted for determinism)
3. Cache invalidation: any change to nodes or edges clears cache
4. Viewport clipping: with >100 nodes, only render rows within `[scrollOffset, scrollOffset + viewportHeight]`
5. 500-node stress test

## Key Decisions

- Cache uses a simple string key: `JSON.stringify(sorted node IDs + sorted edge pairs)`
- Cache is module-level Map with weak-ish invalidation (clear on any mutation)
- Viewport clipping is per-row: skip rows outside visible range
- Threshold: >100 nodes activates viewport mode

## Edge Cases

- Nodes added: invalidate cache (key changes)
- Edge added: invalidate cache (key changes)
- Status change only: layout is same, cache hit is valid
- Scroll beyond bounds: clamped to valid range
- 500-node chain: layout computed once, all subsequent renders are viewport-clipped
