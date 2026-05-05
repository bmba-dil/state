---
phase: 047-reactive-trigger
plan: "01"
subsystem: scheduler
tags: [event-driven, asyncio, dag, post-commit, structlog]

# Dependency graph
requires:
  - phase: 042-045-dag-scheduler
    provides: DAGScheduler.tick(), Node, Edge types, frontier computation
  - phase: 009-event-store
    provides: SqliteEventStore.add_post_commit_callback()
  - phase: 054-sse-bus
    provides: SseBus.on_event() pattern (sync callback → asyncio.create_task)
provides:
  - ReactiveTrigger class with event-type filtering and async tick dispatch
  - Event-driven DAG scheduler activation (no polling)
  - Daemon wiring: post-commit callback → DAGScheduler.tick()
affects: [048-dag-state, schema]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Sync callback → asyncio.create_task() → async handler (SseBus pattern)
    - frozenset for immutable configuration sets (thread-safe, hashable)
    - Callable injection for dag_provider (same as StepExecutor pattern)
    - structlog.get_logger(__name__) for logging (consistent with all other modules)

key-files:
  created:
    - src/state_core/reactive.py
    - tests/test_reactive_trigger.py
  modified:
    - src/state_core/__init__.py
    - src/state_daemon/orchestrator.py

key-decisions:
  - "Used frozenset for watched_events — immutable under threading, same guarantee as SseBus"
  - "Followed SseBus on_event() pattern: sync callback creates asyncio task, never awaits"
  - "dag_provider starts empty in daemon — DAG state population deferred to phases 048+"
  - "Concurrency cap defaults to 4 in daemon (matches SchedulerConfig default)"

patterns-established:
  - "Event-driven trigger pattern: post_commit_callback → event_type filter → async dispatch"
  - "dag_provider injection pattern: Callable[[], tuple[list[Node], list[Edge]]]"

requirements-completed: [DAG-04]

# Metrics
duration: 15min
completed: 2026-05-04
---

# Phase 47 Plan 01: Event-driven DAG scheduler activation via post-commit callbacks

**ReactiveTrigger wires DAGScheduler.tick() to event-store post-commit callbacks — no polling, pure event-driven activation on step/slice/phase completions.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-05T01:45:00Z
- **Completed:** 2026-05-05T02:00:29Z
- **Tasks:** 2
- **Files modified/created:** 4

## Accomplishments
- `ReactiveTrigger` class with `on_event()` sync callback compatible with `SqliteEventStore.add_post_commit_callback()`
- Event-type filtering: only `state.step.advanced`, `state.slice.worktree_ready`, and `state.phase.planned` trigger ticks
- Async tick dispatch via `asyncio.create_task()` (fire-and-forget, follows SseBus pattern)
- `tick()` failure isolation via try/except with structlog logging (T-047-01 mitigation)
- Daemon orchestrator wires reactive trigger as post-commit callback (Step 3.6)
- All 8 behavioral tests pass + 2 property tests = 10 total
- Zero regressions in existing test suite

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `ede0a77` (test)
2. **Task 1 (GREEN): ReactiveTrigger implementation** - `9bedd1f` (feat)
3. **Task 2: Package export + daemon wiring** - `e8ded3e` (chore)

_Note: TDD task (Task 1) produced RED → GREEN commits. No REFACTOR needed — implementation was clean on first pass._

## Files Created/Modified
- `src/state_core/reactive.py` - ReactiveTrigger class (96 lines): event filtering, async tick dispatch, structlog error logging
- `tests/test_reactive_trigger.py` - 10 async/sync tests covering event filtering, dag_provider injection, custom watched_events, multiple rapid events, missing-key safety
- `src/state_core/__init__.py` - Added ReactiveTrigger import and __all__ export (alphabetical order)
- `src/state_daemon/orchestrator.py` - Imported ReactiveTrigger + DAGScheduler/Edge/Node; wired reactive_trigger.on_event as post-commit callback (Step 3.6)

## Decisions Made
- **frozenset for watched_events:** Immutable, hashable, thread-safe — same reasoning as other configuration sets in the codebase
- **Fire-and-forget via asyncio.create_task():** The post-commit path must never block on tick execution — matches SseBus pattern exactly
- **Empty dag_provider at daemon start:** The trigger mechanism is Phase 047's deliverable; DAG state population from event projections is phases 048+
- **Concurrency cap 4:** Default matching SchedulerConfig, overridable in config.toml when populated

## Deviations from Plan

None — plan executed exactly as written. All 8 test scenarios implemented as specified.

## Issues Encountered
- Two pre-existing flaky tests (`test_orchestrator_import_failure_does_not_abort_boot`, `test_repair_logs_info_when_repairs_happen`) fail in full suite due to structlog global state pollution from other tests. Both pass individually. No regressions from Phase 047 changes.
- Concurrent commit from Phase 059 (`51b2dc3`) landed between GREEN and Task 2 commits — no conflict (touches only `auth_manager.py`).

## Known Stubs

The `dag_state` and `dag_edges` lists in `orchestrator.py` start empty — the DAG state is populated by downstream phases 048+ that build DAG state from event projections. This is intentional and documented: Phase 047 delivers the trigger mechanism; DAG state population is a separate concern.

## Threat Flags

No new threat surface beyond the plan's threat model. The `on_event` callback path (T-047-01) is the only new entry point into scheduling logic and is mitigated per the plan's threat register.

## Next Phase Readiness
- Reactive trigger mechanism complete — DAG scheduler now receives ticks on state-change events
- Phases 048+ can populate `dag_state`/`dag_edges` lists to enable actual scheduling
- Requirement DAG-04 satisfied: "DAG scheduler receives event-stream notifications"

---
*Phase: 047-reactive-trigger*
*Completed: 2026-05-04*
