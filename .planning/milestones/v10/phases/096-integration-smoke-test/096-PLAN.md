# 096-PLAN — Integration Smoke Test

## Tasks

### T1 — Build-mode integration test
1. Populate DAG_VIEWER_STATE with arc→phase→slice→step hierarchy (6+ nodes)
2. Set various statuses (done, running, pending, blocked, failed)
3. Call renderDagViewer, verify:
   - All node names appear in output
   - Status colors rendered (check JSON for color hex values)
   - Legend has all 5 status types
4. Test navigation: focus through nodes, wrap around
5. Test filter: set preset, verify filtered output

### T2 — Teach-mode integration test
1. Populate DAG_VIEWER_STATE with subject→lesson→concept→drill hierarchy
2. Verify render output includes teach-mode node names
3. Verify same render function works for both modes

### T3 — Verify no regressions
Run full test suite:
```
cd packages/opencode-plugin && bun test src/tui/
```

## Verification
- `cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts`
- All tests pass including new integration tests
