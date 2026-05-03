---
phase: 008-projector
plan: B
subsystem: event-store
tags: [cli, typer, projector, command-line, projection]
dependency-graph:
  requires:
    - phase: 008-A-Projector-Core
      provides: Projector class with rebuild_all() and Projector import
  provides:
    - `state events rebuild-projections` CLI command
    - events Typer sub-app following db_app pattern
    - Async runner with migrate-before-rebuild ordering
  affects:
    - 010-test-suite (tests CLI command via CliRunner)
key-files:
  modified:
    - src/state_cli/main.py
requirements-completed:
  - EVT-02
metrics:
  duration: ~10min
  completed: 2026-04-24
---

# Phase 008 Plan B: CLI Integration Summary

**`state events rebuild-projections` CLI command following the existing `db` sub-app pattern, with error handling, migrate-before-rebuild ordering, and late import for circular-import safety**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-24
- **Completed:** 2026-04-24
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `events` Typer sub-app (`events_app`) registered on the root `app` Typer, following the exact pattern of the existing `db_app` — symmetric sub-app registration ensures discoverable CLI hierarchy
- Added `from src.state_core.projector import Projector as _Projector` module-level import for safe reference across the CLI module
- Implemented `rebuild-projections` command on `events_app` wrapping an async runner in try/except with user-friendly error message and `typer.Exit(code=1)`
- Async runner `_do_rebuild_projections()` calls `_migrate()` first, then creates `SqliteEventStore` + `Projector`, invokes `rebuild_all()`, and reports the event count
- Late import of `SqliteEventStore` inside the async function avoids circular imports at module load time
- Verified via `CliRunner` that `state events --help` lists `rebuild-projections` with correct description

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `events` Typer sub-app + import block** — `a33bd54` (feat)
2. **Task 2: Add `rebuild-projections` command** — `cb02d56` (feat)

## Files Modified

- `src/state_cli/main.py` — Added `Projector` import, `events_app` sub-app definition, `rebuild-projections` command function, and `_do_rebuild_projections` async runner (46 lines total, +25 lines from prior state)

## Decisions Made

- **Late import for SqliteEventStore:** The `SqliteEventStore` is imported inside `_do_rebuild_projections()` rather than at module top level. This prevents circular import issues since `projector.py` already imports from `events.py`. The `_Projector` alias at module level is safe because `projector.py` does not import from `main.py`.
- **Wrapped async in try/except at command boundary:** The `rebuild_projections()` sync command function wraps all async execution in a try/except that prints the exception message to stderr and exits with code 1. This prevents raw Python tracebacks from appearing when the event store or projector encounters a problem.
- **Verified via CliRunner, not __main__:** The `__main__` guard (`if __name__ == "__main__"`) is absent from the CLI module; verification used `typer.testing.CliRunner` instead.

## Minor Note on Verification

The plan's acceptance criteria included `g.name` on `typer.Typer.registered_groups` items, but in the installed version of Typer (`>=0.15`), `g.name` returns a `DefaultPlaceholder` rather than the actual name string. The actual name is accessible via `g.typer_instance.info.name`. All verification steps were adjusted to use this property instead. The CLI behavior is correct — `state events --help` lists `rebuild-projections` as expected.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Ready for Plan C (Test Suite — comprehensive projection handler and Projector tests)
- CLI command is invocable and reachable via `state events rebuild-projections`
- Async runner correctly chains: migrations → event store → projector → rebuild → report

---

*Phase: 008-projector*
*Plan: B*
*Completed: 2026-04-24*
