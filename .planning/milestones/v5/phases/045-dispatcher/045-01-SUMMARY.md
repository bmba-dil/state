---
phase: 045-dispatcher
plan: 01
subsystem: scheduler
tags: [dag, asyncio, pydantic, toml, dispatcher, frontier, concurrency]

# Dependency graph
requires:
  - phase: 044-frontier-calculator
    provides: "frontier(), _parse_sort_key() — unblocked node calculation and sort key extraction"
provides:
  - "DAGScheduler.tick() — async dispatch loop with Slice grouping and asyncio.gather concurrency"
  - "SchedulerConfig pydantic model with concurrency_cap validation (1–64)"
  - "load_scheduler_config() — TOML config loader with safe defaults fallback"
  - "StepExecutor type alias for injectable async step executors"
  - "Package-level exports of DAGScheduler and SchedulerConfig from src.state_core"
affects: [046-reactive-trigger, 047-event-store-integration, 048-step-executor, 049-status-transitions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Slice grouping via _slice_key(): extracts 'arc-N/phase-N/slice-N' prefix from node IDs"
    - "Concurrent Slice dispatch via asyncio.gather() with cap enforcement"
    - "StepExecutor injection pattern: async Callable[[Node], None] for testability"
    - "TOML config loading with pydantic validation and silent fallback to defaults"
    - "Defense-in-depth concurrency cap: validated at config layer (Field ge/le) AND constructor (max/min clamp)"

key-files:
  created: []
  modified:
    - "src/state_core/scheduler.py — DAGScheduler class with tick(), SchedulerConfig, load_scheduler_config(), _slice_key()"
    - "tests/test_scheduler.py — TestDispatcher class with 17 tests (12 dispatch + 5 config)"
    - "src/state_core/__init__.py — package exports for DAGScheduler and SchedulerConfig"

key-decisions:
  - "DAGScheduler.tick() signature takes (nodes, edges) directly rather than ARC ID — keeps scheduler stateless and testable per invocation"
  - "Slice grouping uses _slice_key() which extracts prefix up to 'slice-N' component; non-step nodes fall back to full node_id as their own group"
  - "Steps within a Slice execute sequentially (serial within group) via for-loop; Slices dispatch concurrently via asyncio.gather()"
  - "Concurrency cap enforced at two layers: pydantic Field(ge=1, le=64) on SchedulerConfig and max(1, min(cap, 64)) in DAGScheduler.__init__"
  - "Config loading silently returns defaults on any error (missing file, invalid TOML, wrong types) — never raises at config-load time"

patterns-established:
  - "_slice_key(): Derive Slice prefix from hierarchical node IDs for dispatch grouping; falls back to full ID for non-slice nodes"
  - "StepExecutor injection: Callable[[Node], Awaitable[None]] passed to DAGScheduler constructor for testability; _default_step_executor as no-op fallback"
  - "Config graceful degradation: load_scheduler_config() returns SchedulerConfig defaults on any failure — no exceptions bubble from config layer"
  - "TDD RED/GREEN/REFACTOR: Each TDD task produces separate commits (test → feat → refactor)"

requirements-completed:
  - DAG-02

# Metrics
duration: 8min
completed: 2026-05-05
---

# Phase 045-01: DAG Dispatcher Summary

**Async DAG dispatch loop with Slice grouping, asyncio.gather concurrency, and TOML config-backed cap — 17 new tests, zero regressions**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-05T00:43:55Z
- **Completed:** 2026-05-05T00:52:11Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `DAGScheduler.tick()` implemented: computes `frontier()`, groups unblocked nodes by Slice, dispatches up to `concurrency_cap` Slices concurrently via `asyncio.gather`, steps within a Slice execute sequentially
- `SchedulerConfig` pydantic model with `concurrency_cap` field validated to [1, 64] with default=4, extra fields forbidden, frozen
- `load_scheduler_config()` reads `.state/config.toml` `[scheduler]` section with graceful fallback to defaults on any error
- `DAGScheduler` and `SchedulerConfig` exported from `src.state_core` package
- 17 new tests pass (12 dispatch + 5 config), zero regressions across 53 existing scheduler tests

## Task Commits

Each TDD task committed atomically (RED → GREEN → REFACTOR):

1. **Task 1 (RED): Write failing async tests for DAGScheduler.tick()** — `67d0be3` (test)
2. **Task 2 (GREEN): Implement DAGScheduler.tick() with frontier grouping and asyncio.gather** — `cecf663` (feat)
3. **Task 3 (REFACTOR): Add SchedulerConfig, load_scheduler_config, and package exports** — `780e1a9` (refactor)

## Files Created/Modified

- `src/state_core/scheduler.py` — `DAGScheduler` class with `tick()` (frontier grouping + asyncio.gather dispatch), `_slice_key()` helper, `SchedulerConfig` model, `load_scheduler_config()`, `StepExecutor` type alias, `_default_step_executor` no-op
- `tests/test_scheduler.py` — `TestDispatcher` class: 12 async dispatch tests + 5 config tests (TOML loading, validation, fallbacks)
- `src/state_core/__init__.py` — Added `DAGScheduler` and `SchedulerConfig` to imports and `__all__`

## Decisions Made

- **Direct node/edge signature on tick()** rather than ARC ID: keeps scheduler stateless, testable per invocation, and defers state management to caller (Phase 046/047)
- **`_slice_key()` extraction**: Uses hierarchical node ID prefix up to `slice-N` component; non-slice nodes use full ID as their own group key
- **Dual-layer concurrency cap**: Pydantic `Field(ge=1, le=64)` for config validation + `max(1, min(cap, 64))` in constructor as defense-in-depth
- **Silent config fallback**: `load_scheduler_config()` never raises — returns defaults on missing file, invalid TOML, or wrong types

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Import stubs needed before RED gate**
- **Found during:** Task 1 (RED phase)
- **Issue:** Test file imported `DAGScheduler`, `SchedulerConfig`, `StepExecutor`, `load_scheduler_config` which didn't exist yet — caused ImportError instead of test failure
- **Fix:** Added minimal stub implementations for all missing symbols so tests could import and FAIL (instead of error) — the RED gate requires failures, not import errors
- **Files modified:** `src/state_core/scheduler.py`
- **Committed in:** `67d0be3` (Task 1 commit)

**2. [Rule 2 - Maintainability] Fixed Pydantic 2.11 deprecation warning**
- **Found during:** Task 3 (REFACTOR phase)
- **Issue:** `defaults.model_fields` accessed on instance triggers deprecation warning in Pydantic ≥2.11
- **Fix:** Changed to `SchedulerConfig.model_fields` (class-level access)
- **Files modified:** `src/state_core/scheduler.py` (1 line)
- **Committed in:** `780e1a9` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 maintainability)
**Impact on plan:** Both fixes trivial. No scope creep. Plan executed essentially as written.

## Issues Encountered

- `rtk pytest` wrapped runs in a Python 3.14 environment missing pydantic; used `.venv/bin/python3` directly for all test runs
- Pre-existing `test_double_start_prevented` failure in `test_daemon_pid.py` confirmed unrelated — 561 other non-scheduler tests pass

## Next Phase Readiness

- `DAGScheduler.tick()` is ready for integration: takes (nodes, edges) → returns dispatched IDs
- `SchedulerConfig` and `load_scheduler_config()` ready for Phase 046 (reactive trigger) which wires the config into daemon startup
- `StepExecutor` injection pattern established — Phase 048 can implement the real OpenCode HTTP executor
- No blocking issues

---
*Phase: 045-dispatcher*
*Plan: 01*
*Completed: 2026-05-05*

## Self-Check: PASSED

- SUMMARY.md exists: PASSED
- Commit 67d0be3 (Task 1 RED): PASSED
- Commit cecf663 (Task 2 GREEN): PASSED
- Commit 780e1a9 (Task 3 REFACTOR): PASSED
- All 70 scheduler tests pass: PASSED
- Package imports verified: PASSED
- Mode isolation grep gate: PASSED
