# 095-VERIFICATION — Large-Graph Performance

## Test Results

```
cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts
```

### Layout cache tests (5 pass)
- layoutCacheKey produces deterministic string (same nodes → same key regardless of order)
- Different nodes produce different keys
- memoizeLayout returns same reference on cache hit
- memoizeLayout recomputes after cache invalidation
- 500-node chain: layout computed correctly (500 nodes, no overlapping positions), cache hit on second call

### Viewport clipping test (2 pass)
- 150-node chain (above VIEWPORT_THRESHOLD of 100): renders fewer rows than total
- Small graph (2 nodes) below threshold: renders normally

### Performance verification
- Layout cache avoids O(V+E) recomputation on every frame for unchanged graphs
- Viewport clipping skips off-screen rows when >100 nodes
- Invalidate cache triggers: node/edge changes (via key comparison), explicit invalidateLayoutCache()

### Full suite: 67/67 pass, 0 fail
