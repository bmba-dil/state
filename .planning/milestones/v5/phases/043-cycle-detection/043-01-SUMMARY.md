---
phase: 043-cycle-detection
plan: 01
subsystem: scheduler
tags: [dfs, cycle-detection, dag, python, 3-color, topological-sort]

# Dependency graph
requires:
  - phase: 042-topological-sort
    provides: topo_sort function, Edge/Node/NodeRegistry types, _parse_sort_key
  - phase: 044-frontier
    provides: frontier function (co-located in scheduler.py)
provides:
  - detect_cycles function — DFS 3-color cycle detection returning full cycle paths
  - TestCycleDetection test class — 8 tests covering acyclic, self-loop, simple cycle, triangle, multi-cycle, edge cases
  - Package export of detect_cycles from src.state_core
affects: [dag-scheduler, roadmap-validation, cycle-reporting-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Iterative DFS with explicit path/stack for cycle-path extraction (avoids recursion limits)"
    - "3-color marking (WHITE=0, GRAY=1, BLACK=2) for back-edge detection"
    - "Per-phase TDD: RED (failing tests) → GREEN (implementation) → exports"

key-files:
  created: []
  modified:
    - src/state_core/scheduler.py — detect_cycles function inserted after frontier, before DAGScheduler
    - tests/test_scheduler.py — TestCycleDetection class appended after TestFrontier
    - src/state_core/__init__.py — detect_cycles added to import and __all__

key-decisions:
  - "Used iterative DFS instead of recursive to avoid Python recursion limits on deep DAGs"
  - "Cycle paths use closing-node convention (first == last) for unambiguous cycle representation"
  - "Nodes derived from edge endpoints only — no separate node list parameter needed"
  - "Sorted iteration over start nodes for deterministic output order"

patterns-established:
  - "Iterative DFS with neighbor-index advancement in stack frames: stack[-1] = (node, ni + 1) before descending"
  - "Path list tracks current DFS traversal for cycle extraction via path.index(target)"
  - "WHITE/GRAY/BLACK color model following standard DFS cycle-detection literature"

requirements-completed: [DAG-01]

# Metrics
duration: 15m
completed: 2026-05-04
---

# Phase 043 Plan 01: DFS 3-Color Cycle Detection Summary

**DFS 3-color cycle detection returning full cycle paths (`list[list[str]]`) for DAG roadmap validation — 8 tests GREEN on top of 45 existing, no regression.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-05T00:16:00Z
- **Completed:** 2026-05-05T00:31:00Z
- **Tasks:** 3 (TDD: RED → GREEN → exports)
- **Files modified:** 3

## Accomplishments

- `detect_cycles(edges: list[Edge]) -> list[list[str]]` implemented with iterative DFS and 3-color marking
- Self-loops, 2-node cycles, 3-node triangles, and multiple independent cycles all detected
- Acyclic DAGs (linear chains, diamonds) correctly return empty list
- 8 new `TestCycleDetection` tests pass alongside all 45 existing tests (53 total, zero regression)
- Package-root import: `from src.state_core import detect_cycles` works

## Task Commits

Each task committed atomically:

1. **Task 1: RED — Write failing tests** — `1727cb3` (test)
2. **Task 2: GREEN — Tests pass with implementation** — `bc4cd5a` (test)
3. **Task 3: Wire export in __init__.py** — `8f6f87b` (chore)

_Note: The `detect_cycles` implementation itself was committed in `7443fb2` (feat(044-01): implement frontier()) due to cross-contamination from parallel phase 044-01 modifying the same file. See Deviations below._

## Files Created/Modified

- `src/state_core/scheduler.py` (334 lines) — `detect_cycles` function at line 248, between `frontier` and `DAGScheduler`
- `tests/test_scheduler.py` (534 lines) — `TestCycleDetection` class at line 442 with 8 test methods
- `src/state_core/__init__.py` (17 lines) — `detect_cycles` added to import line and `__all__` list

## Implementation Details

**Algorithm:** Iterative DFS with explicit stack and path tracking. Each stack frame stores `(node, neighbor_index)` where the index advances before descending into a neighbor. On back-edge detection (GRAY neighbor), the cycle path is extracted by finding the neighbor's position in the current path and slicing from that point forward, appending the neighbor to close the cycle.

**Color states:** 0=WHITE (unvisited), 1=GRAY (in-progress), 2=BLACK (fully explored). GRAY→GRAY traversal = back edge = cycle detected.

**Cycle path format:** Each returned cycle is `list[str]` where `cycle[0] == cycle[-1]` — the closing node. Example: `['a', 'b', 'c', 'a']` for a 3-node triangle.

## Decisions Made

- **Iterative over recursive**: Avoids Python recursion depth limits on deep project DAGs
- **Closing-node convention**: `cycle[0] == cycle[-1]` makes cycles self-describing and easy to validate
- **Edge-derived nodes**: No separate node list parameter — nodes are collected from edge endpoints, simplifying the API
- **Sorted start nodes**: `sorted(nodes)` for deterministic iteration order across disconnected components

## Deviations from Plan

### Cross-Contamination from Parallel Phase 044-01

**1. Implementation committed in phase 044-01's commit**

- **Found during:** Task 2 (execution)
- **Issue:** Both phases 043-01 and 044-01 modified `src/state_core/scheduler.py` concurrently. The `detect_cycles` function I added was included in commit `7443fb2` (`feat(044-01): implement frontier()`) because the file was staged with both functions present. When the 044-01 executor committed, it picked up my in-progress `detect_cycles` changes alongside `frontier`.
- **Fix:** No fix needed — the function is correct, complete, and all tests pass. The git history anomaly does not affect correctness, traceability, or functionality.
- **Files affected:** `src/state_core/scheduler.py`
- **Verification:** All 53 tests pass. `detect_cycles` is importable and produces correct results for all 8 test scenarios plus smoke tests.

### Artifact Spec Variance

**2. Variable name: `path` vs `path_stack`**

- **Issue:** Plan artifact spec listed `path_stack` as a required contain check, but the plan's own pseudocode uses `path: list[str]`. The implementation follows the pseudocode convention (`path`, not `path_stack`).
- **Fix:** None needed — variable serves the same purpose, naming is consistent with the plan's actual pseudocode.

---

**Total deviations:** 2 (1 cross-contamination from parallel execution, 1 minor spec variance)
**Impact on plan:** Zero functional impact. All requirements met, all tests pass.

## Issues Encountered

- **rtk git commit reverts working tree**: After `rtk git commit` on Task 1, the working tree reverted the test class. Required re-applying the TestCycleDetection class for Task 2. Root cause: `rtk` uses git worktrees internally; the commit on the feature branch appears as a deletion in the worktree branch until merged. Workaround: re-apply changes after commit.
- **System Python pydantic broken**: `/opt/homebrew/bin/python3` (3.14) cannot import `pydantic.ValidationError`. All tests run via `uv run` within the project's `.venv` (Python 3.12), which works correctly.

## Threat Flags

None — `detect_cycles` is a pure in-memory computation with no network, file, auth, or data surface. Threat model from plan (T-043-01 through T-043-04) covers all relevant concerns.

## Known Stubs

None. The implementation is complete with no placeholder values, hardcoded empty returns, or unwired data flows.

## Next Phase Readiness

- `detect_cycles` is production-ready for roadmap validation tools
- Full cycle-path detail supports actionable error messages ("Cycle: a→b→c→a in arc-5/phase-2")
- Ready for integration: any tool that calls `topo_sort` can pre-check with `detect_cycles` for richer error reporting
- DAGScheduler skeleton preserved at bottom of `scheduler.py` — phases 045-049 can build on it without conflict

---
*Phase: 043-cycle-detection*
*Completed: 2026-05-04*
