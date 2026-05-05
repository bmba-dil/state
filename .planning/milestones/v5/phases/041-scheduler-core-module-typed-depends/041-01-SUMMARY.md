---
phase: 041-scheduler-core-module-typed-depends
plan: "01"
subsystem: scheduler
tags: [pydantic, dag, literal, registry, frozen-models]

# Dependency graph
requires: []
provides:
  - EdgeKind Literal type (blocks / soft / data) — dependency edge kind discriminator
  - Edge pydantic model (frozen, extra="forbid") — directed dependency between two DAG nodes
  - Node pydantic model (frozen, extra="forbid") — unit-of-work node with lifecycle status
  - NodeRegistry class — O(1) dict-backed in-memory registry of all DAG nodes
  - Package exports from src.state_core: Edge, EdgeKind, Node, NodeRegistry
affects: [042-edge-builder, 043-dag-validator, 044-scheduler-tick, 045-status-transitions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Frozen pydantic data models with extra="forbid" (matches schema.py conventions)
    - Literal type aliases for enumerations (EdgeKind, Node.kind, Node.status)
    - Dict-backed in-memory registry with ValueError on duplicate (defense-in-depth)
    - Package __all__ exports for public API surface

key-files:
  created:
    - tests/test_scheduler.py (151 lines, 17 tests)
  modified:
    - src/state_core/scheduler.py (11→99 lines)
    - src/state_core/__init__.py (5→14 lines)

key-decisions:
  - "Frozen pydantic models prevent post-construction mutation — matching schema.py conventions and threat model T-041-01 mitigation"
  - "Duplicate NodeRegistry.register() raises ValueError (not silent overwrite) — preventing accidental ID collisions per T-041-02 mitigation"
  - "NodeRegistry is a plain class (not pydantic model) since it's mutable in-memory storage, not a serialized data type"
  - "DAGScheduler skeleton preserved at end of file — phases 042-049 add scheduling logic"

patterns-established:
  - "Scheduler types follow schema.py patterns: from __future__ import annotations, pydantic BaseModel with ConfigDict(extra='forbid', frozen=True)"
  - "Test grouping by model class (TestEdgeModel, TestNodeModel, TestNodeRegistry) matching test_schema.py structure"
  - "TDD RED/GREEN cycle: tests committed first (failing imports), then implementation committed"

requirements-completed:
  - DAG-01

# Metrics
duration: 8min
completed: 2026-05-04
---

# Phase 041 Plan 01: Scheduler Core Module Summary

**Pydantic Edge/Node frozen models with `extra="forbid"` validation, `EdgeKind` literal (`blocks`/`soft`/`data`), and `NodeRegistry` with O(1) dict-backed storage — the typed DAG graph representation that phases 042-049 build upon.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-04T18:35:00-05:00
- **Completed:** 2026-05-04T18:40:23-05:00
- **Tasks:** 3 (TDD: 1 RED + 2 GREEN)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `EdgeKind` literal type: `"blocks"`, `"soft"`, `"data"` — typed dependency edge discriminator
- `Edge` frozen pydantic model (`source_node: str`, `target_node: str`, `kind: EdgeKind`) with `extra="forbid"`
- `Node` frozen pydantic model (`id: str`, `kind: Literal["arc","phase","slice","step"]`, `status: Literal[...]`) with `extra="forbid"` and default `status="idle"`
- `NodeRegistry` class: `register`, `get`, `contains`, `remove`, `all_nodes`, `__len__`, `__contains__` — raises `ValueError` on duplicate, `KeyError` on missing
- Package-level exports from `src.state_core`: `Edge`, `EdgeKind`, `Node`, `NodeRegistry`
- `DAGScheduler` skeleton preserved — no scheduling logic (phases 042-049)
- 17 tests across Edge (5), Node (5), and NodeRegistry (7) — all passing GREEN

## Task Commits

Each task was committed atomically following TDD RED/GREEN:

1. **Task 1 (RED): Write failing tests** — `b5f55a7` (test) — 17 tests, imports fail because types don't exist yet
2. **Task 2 (GREEN): Implement EdgeKind, Edge, Node** — `e2177ed` (feat) — Edge/Node models with frozen extra="forbid"
3. **Task 3 (GREEN): Implement NodeRegistry + wire exports** — `9fbcaa6` (feat) — NodeRegistry dict-backed storage, __init__.py exports

## Files Created/Modified

- `tests/test_scheduler.py` — 17 tests: 5 Edge model, 5 Node model, 7 NodeRegistry (151 lines)
- `src/state_core/scheduler.py` — Added EdgeKind, Edge, Node, NodeRegistry types; DAGScheduler skeleton preserved (99 lines)
- `src/state_core/__init__.py` — Added package exports for all scheduler types (14 lines)

## Decisions Made

- **Frozen models:** Both Edge and Node use `frozen=True` to prevent post-construction mutation, matching schema.py conventions and the plan's threat model (T-041-01: tampering prevention)
- **ValueError on duplicate:** `NodeRegistry.register()` raises `ValueError` on duplicate ID rather than silently overwriting, satisfying T-041-02 (tampering prevention)
- **Plain class for registry:** `NodeRegistry` is a plain Python class (not pydantic model) because it's mutable in-memory storage — it's not a serialized data type
- **Skeleton preservation:** DAGScheduler stub with `tick()` method preserved at end of file — phases 042-049 will add scheduling logic

## Deviations from Plan

None — plan executed exactly as written.

### TDD Verification Note

Task 2's Edge and Node model tests could not run independently before Task 3 because the test file imports all four types (`Edge, EdgeKind, Node, NodeRegistry`) in a single `from` statement. The import error from missing `NodeRegistry` prevented all test collection. Edge/Node model correctness was verified via the plan's import check: `python3 -c "from src.state_core.scheduler import Edge, Node, EdgeKind; print('OK')".` After Task 3 implemented NodeRegistry, all 17 tests passed in a single run.

## Issues Encountered

None — all three tasks executed cleanly on first pass.

## User Setup Required

None — no external service configuration required. This is a pure data model module.

## Next Phase Readiness

- Core typed DAG model ready for downstream phases:
  - Phase 042: Edge builder (construct edges from event stream)
  - Phase 043: DAG validator (cycle detection, well-formedness)
  - Phase 044: Scheduler tick (compute unblocked Steps)
  - Phase 045: Status transitions (Node status lifecycle)
- All types importable from both `src.state_core.scheduler` and `src.state_core`
- 17 tests provide regression safety for model contracts

---

*Phase: 041-scheduler-core-module-typed-depends*
*Plan: 01*
*Completed: 2026-05-04*
