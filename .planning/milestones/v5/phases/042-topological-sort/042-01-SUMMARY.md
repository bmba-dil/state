---
phase: 042-topological-sort
plan: 01
subsystem: scheduler
tags: [dag, topological-sort, kahn, stable-ordering, scheduler]

# Dependency graph
requires: [041-scheduler-core-module-typed-depends]
provides: [topo_sort, _parse_sort_key]
affects: [043-cycle-detection, 044-frontier-calculator, 049-cli-renderer]

# Tech stack
added: []
patterns:
  - Pure-Python Kahn's algorithm (no networkx)
  - Stable frontier ordering by (slice_id, step_id) derived from node.id
  - TDD RED/GREEN/GREEN cycle per plan

# Key files
created: []
modified:
  - src/state_core/scheduler.py — added _parse_sort_key and topo_sort
  - tests/test_scheduler.py — added TestTopoSort class (11 tests)
  - src/state_core/__init__.py — added topo_sort export

# Key decisions
decisions:
  - "Used pure Python Kahn's algorithm — matching project rejection of networkx; O(V+E) complexity sufficient for DAG scale"
  - "Stable frontier ordering by (slice_id, step_id) derived from node.id path components — ensures deterministic output for same input"
  - "Edge endpoint validation before topology computation — raises ValueError with specific missing node ID rather than silent KeyError"
  - "Cycle detection via remaining untraversed nodes check — raises ValueError with cycle node count and IDs for debuggability"
  - "Non-step nodes (arc, phase, slice) sort before steps via _parse_sort_key fallback to ('', node_id)"

# Patterns established
patterns_established:
  - "TDD: RED test commit → GREEN implementation commit → GREEN wiring commit"
  - "topo_sort(edges, nodes) function signature — parameter order matches Kahn's convention"
  - "_parse_sort_key private helper — prefix scan on '/' delimited node IDs"
  - "Stable sort via sorted() with key function, re-sorted after each frontier round"
  - "Frozen pydantic Node/Edge reused as input to algorithmic function (pure functions on immutable data)"

# Requirements completed
requirements:
  - DAG-01

# Metrics
duration: "5m 7s"
completed: 2026-05-04
---

# Phase 042 Plan 01: Topological Sort (Kahn's algorithm) Summary

**One-liner:** Implemented `topo_sort` using pure-Python Kahn's algorithm with deterministic stable ordering keyed by `(slice_id, step_id)` from node.id, including cycle detection and edge validation.

## Tasks Executed

| Task | Name | Type | Commit | Status |
|------|------|------|--------|--------|
| 1 | Write failing tests for topo_sort | RED (TDD) | `a4edf96` | PASS — 11 tests written, RED at import |
| 2 | Implement _parse_sort_key and topo_sort | GREEN (TDD) | `8a7897f` | PASS — 28/28 tests |
| 3 | Wire topo_sort export in __init__.py | GREEN (TDD) | `fe47dea` | PASS — 28/28 tests |

## Verification Results

| Check | Result |
|-------|--------|
| `topo_sort` import from `src.state_core.scheduler` | ✓ OK |
| `topo_sort` import from `src.state_core` | ✓ OK |
| TestTopoSort (11 new tests) | ✓ 11/11 GREEN |
| Existing tests (17 from Phase 041) | ✓ 17/17 GREEN |
| Linear chain smoke test | ✓ a→b→c = [a, b, c] |
| Cycle detection smoke test | ✓ ValueError with "Cycle detected" |
| Stable ordering smoke test | ✓ arc-1 → step-1 → step-2 |
| Phase 041 regression | ✓ Edge/Node/NodeRegistry functional |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — all threats from plan's `<threat_model>` are mitigated as designed:
- T-042-01 (cycle tampering): Mitigated via `ValueError` on untraversed nodes
- T-042-02 (edge validation): Mitigated via explicit endpoint existence check with offending node ID
- T-042-03 (DoS large graph): Accepted — DAG bounded by project scale
- T-042-04 (info disclosure): Accepted — no secrets in node IDs

## Known Stubs

None — `topo_sort` and `_parse_sort_key` are fully implemented with no placeholder code, TODOs, or FIXMEs.

## Files Modified

```
src/state_core/scheduler.py  | +100 lines (_parse_sort_key + topo_sort functions)
tests/test_scheduler.py       | +117 lines (TestTopoSort class, 11 tests)
src/state_core/__init__.py    | +2/-1 lines (topo_sort import + __all__)
```

## Self-Check: PASSED

- [x] `src/state_core/scheduler.py` exists and contains `_parse_sort_key`, `topo_sort`, `DAGScheduler`
- [x] `tests/test_scheduler.py` exists and contains `TestTopoSort` with 11 tests
- [x] `src/state_core/__init__.py` exports `topo_sort`
- [x] All 3 commits present: `a4edf96`, `8a7897f`, `fe47dea`
- [x] All 28 tests pass via `pytest tests/test_scheduler.py`
- [x] Package-root import works: `from src.state_core import topo_sort`
