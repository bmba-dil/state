---
phase: 104-mode-activation-event
plan: 01
subsystem: daemon
tags: [mode, event, activation, SIGHUP, SSE]
requires:
  provides:
    - state.mode.activated event emission from daemon SIGHUP handler
    - ModeActivatedData schema with old_mode + new_mode fields
  affects: [plugin-hot-reload, MCP-registration, SSE-subscribers]
tech-stack:
  added: []
  patterns: [signal-handler-event-emission, module-level-store-reference, post-commit-sse-fanout]
key-files:
  created: []
  modified:
    - src/state_core/schema.py
    - src/state_daemon/orchestrator.py
    - tests/test_schema.py
    - tests/test_daemon_middleware.py
key-decisions:
  - "ModeActivatedData uses old_mode + new_mode (both str, no Literal validation) instead of mode_value"
  - "Event emitted with mode='kernel' for cross-mode SSE visibility"
  - "aggregate_id follows 'mode-{new_mode}' pattern for retrospective query grouping"
  - "No-op SIGHUP (unchanged mode) skips event emission entirely"
  - "_emit_mode_event() called via asyncio.create_task from synchronous signal handler"
patterns-established:
  - "Module-level _event_store global pattern for signal handler access to async store"
  - "Mode comparison (get_current_mode vs load_mode_config) before event emission"
  - "Direct function testing (_emit_mode_event) with isolated SqliteEventStore + migrations"
requirements-completed:
  - MODE-03
  - MODE-05
metrics:
  duration: 30m
  completed: 2026-05-05
---

# Phase 104 Plan 01: Mode Activation Event (state.mode.activated) Summary

**One-liner:** Daemon SIGHUP handler emits `state.mode.activated` event with old_mode/new_mode through SQLite event store; SSE fan-out is automatic via existing post-commit callback.

## Completed Tasks

### Task 1: Update ModeActivatedData schema with old_mode and new_mode (TDD)

- **RED** (`165ca74`): Added 3 failing tests — `test_mode_activated_data_old_mode_new_mode`, `test_mode_activated_data_rejects_mode_value`, `test_mode_activated_data_rejects_extra_fields`
- **GREEN** (`4c9c1fd`): Replaced `mode_value: str` with `old_mode: str` and `new_mode: str` in `ModeActivatedData`. Added docstring documenting mode transition semantics. Updated 2 existing test references in `test_schema.py` (`test_all_data_models_reject_extra`, `test_event_construction`). All 126 test_schema.py tests pass.

### Task 2: Emit state.mode.activated event from daemon SIGHUP handler (TDD)

- **RED** (`6fbbe3d`): Added `TestModeActivatedEvent` class with 5 tests (event persistence, aggregate_id pattern, kernel mode, no-store noop, envelope field completeness)
- **GREEN** (`97a6fd0`): Implemented in `orchestrator.py`:
  - Added `_event_store: SqliteEventStore | None = None` module-level global
  - Stored event store reference during `startup()`
  - Modified `_schedule_mode_reload()` to compare `get_current_mode()` vs `load_mode_config()` and emit event on actual change
  - Added `_emit_mode_event()` async function wiring through `SqliteEventStore.append()` with `mode="kernel"` and `aggregate_id="mode-{new_mode}"`
  - Imported `get_current_mode` from middleware

## Deviations from Plan

None. Plan executed exactly as written.

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_daemon_middleware.py -x -k "TestModeActivatedEvent" -v` | 5 passed |
| 2 | `grep -c "old_mode" src/state_core/schema.py` | 2 (≥ 1) |
| 3 | `grep -c "new_mode" src/state_core/schema.py` | 2 (≥ 1) |
| 4 | `grep -c "state.mode.activated" src/state_daemon/orchestrator.py` | 3 (≥ 1) |
| 5 | `grep -c "_emit_mode_event" src/state_daemon/orchestrator.py` | 2 (≥ 1) |
| 6 | `pytest tests/ -x -k "not slow"` | 1456+ passed, only pre-existing failures |

## Commits

| # | Hash | Type | Message |
|---|------|------|---------|
| 1 | `165ca74` | test | add failing tests for ModeActivatedData old_mode/new_mode schema |
| 2 | `4c9c1fd` | feat | replace ModeActivatedData.mode_value with old_mode and new_mode |
| 3 | `6fbbe3d` | test | add failing tests for _emit_mode_event and mode activation |
| 4 | `97a6fd0` | feat | emit state.mode.activated event from daemon SIGHUP handler |

## Files Modified

| File | Changes |
|------|---------|
| `src/state_core/schema.py` | `ModeActivatedData`: replaced `mode_value` with `old_mode` + `new_mode`, added docstring |
| `src/state_daemon/orchestrator.py` | Added `_event_store` global, `get_current_mode` import, modified `_schedule_mode_reload()`, added `_emit_mode_event()` |
| `tests/test_schema.py` | Replaced old `test_mode_activated_data` with 3 new tests; updated 2 `mode_value` references in parameterized tests |
| `tests/test_daemon_middleware.py` | Added `TestModeActivatedEvent` class with 5 async tests + `_setup_store()` helper |

## Known Stubs

None.

## Self-Check

- [x] `src/state_core/schema.py` exists and has `old_mode`/`new_mode` fields
- [x] `src/state_daemon/orchestrator.py` exists and has `_emit_mode_event()` function
- [x] `tests/test_daemon_middleware.py` has `TestModeActivatedEvent` class with 5 tests
- [x] All 4 commits verified in git log
- [x] All new tests pass (`pytest -k "TestModeActivatedEvent"`)
- [x] No production code references to `mode_value` remain
- [x] Broader test suite shows no regressions

## Self-Check: PASSED
