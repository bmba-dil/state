# v5 — DAG Scheduler

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 041–049 (9 phases)

---

## Phases

#### Phase 041 — Scheduler core module (`state_core.scheduler`) — typed `depends_on` edges
**Goal:** Edge kinds `blocks`/`soft`/`data`, pydantic `Edge` model, node registry.
**Depends on:** 001
**Requirements:** DAG-01
**Parallelizable:** yes
**Plans:** 1/1 plans complete

Plans:
- [x] 041-01-PLAN.md — Core scheduler types (Edge, Node, NodeRegistry) with TDD

#### Phase 042 — Topological sort (Kahn's algorithm, stable ordering)
**Goal:** `topo_sort()` returning stable sequence; key = `(slice_id, step_id)`.
**Depends on:** 041
**Requirements:** DAG-01
**Parallelizable:** yes with 043
**Plans:** 1/1 plans complete

Plans:
- [x] 042-01-PLAN.md — Implement topo_sort with Kahn's algorithm, stable ordering, cycle detection

#### Phase 043 — Cycle detection (DFS color marking)
**Goal:** `detect_cycles()` returns cycle paths; used at roadmap validation.
**Depends on:** 041
**Requirements:** DAG-01
**Parallelizable:** yes with 042
**Plans:** 1/1 plans complete

Plans:
- [x] 043-01-PLAN.md — Implement detect_cycles with DFS 3-color marking, TDD with 8 cycle-detection tests

#### Phase 044 — Frontier calculator (unblocked set per tick)
**Goal:** `frontier(state)` — all IDLE nodes whose `blocks`/`data` predecessors are DONE.
**Depends on:** 041
**Requirements:** DAG-01, DAG-02
**Parallelizable:** yes
**Plans:** 1/1 plans complete

Plans:
- [x] 044-01-PLAN.md — Implement frontier() function with TDD (17 tests)

#### Phase 045 — Dispatcher (group by Slice → TaskGroup per Slice, concurrency cap)
**Goal:** `asyncio.gather` across Slices with cap; serial within Slice; configurable cap in `config.toml`.
**Depends on:** 044
**Requirements:** DAG-02
**Parallelizable:** no
**Plans:** 1 plan

Plans:
- [ ] 045-01-PLAN.md — Implement DAGScheduler.tick() with frontier grouping, asyncio.gather dispatch, SchedulerConfig from config.toml

#### Phase 046 — TaskGroup watchdog (P0-16 defence)
**Goal:** Nested TaskGroup regression harness; watchdog detects `CancelledError` swallow via exception group inspection; fails loud.
**Depends on:** 045
**Requirements:** DAG-03
**Parallelizable:** no
**P0 pitfall:** P0-16

#### Phase 047 — Reactive trigger (subscribe to v1 event stream)
**Goal:** On `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` → recompute frontier; no polling.
**Depends on:** 045, 009
**Requirements:** DAG-04
**Parallelizable:** no

#### Phase 048 — Priority inversion + silent deadlock detection
**Goal:** Heuristic: if critical-path Step is blocked on `soft` edge, warn; if all in-flight are blocked on descoped/missing predecessors, emit `state.scheduler.deadlock` → TUI surfaces.
**Depends on:** 047
**Requirements:** DAG-05, DAG-06
**Parallelizable:** yes

#### Phase 049 — CLI: `state dag show [--arc|--phase|--slice]` ASCII renderer
**Goal:** Box-drawing rendering with status colors; Hypothesis property test: any valid graph renders without crash.
**Depends on:** 042, 044
**Requirements:** DAG-07
**Parallelizable:** yes

---

