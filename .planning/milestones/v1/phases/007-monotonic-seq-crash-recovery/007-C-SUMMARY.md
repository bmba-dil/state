---
phase: 007-monotonic-seq-crash-recovery
plan: C
subsystem: database, event-store
tags: [crash-recovery, repair, structlog, startup-ordering]

# Dependency graph
requires:
  - phase: 007-monotonic-seq-crash-recovery
    provides: repair_aggregate_seqs() method on SqliteEventStore
provides:
  - Lazy repair-once-per-session via _maybe_repair() in append()/read_stream()
  - run_repair_now() public method for daemon startup (repair before migrate)
  - Structlog logging for all repair actions (trigger, corrections, summary)
  - Startup ordering docstring (repair -> migrate -> reconciler) with Phase 006 integration boundary
affects:
  - 004-writer-task (append path)
  - 005-sync-event-mirror (read_stream path)
  - 006-startup-reconciliation (reconciler startup ordering)

# Tech tracking
tech-stack:
  added: [structlog — module-level logger in events.py]
  patterns:
    - "Lazy repair-once-per-session guard with _repair_done flag"
    - "Source-triggered logging for startup ordering auditability"
    - "Public run_repair_now() for explicit daemon startup sequencing"

key-files:
  modified: [src/state_core/events.py]

key-decisions:
  - "run_repair parameter reserved for future use; always initializes _repair_done=False"
  - "_maybe_repair fires on first append()/read_stream() for backward compat with existing callers"
  - "run_repair_now() skips _repair_done flag for explicit daemon startup sequencing"
  - "Structlog logging uses structured key=value pairs, not string formatting"

patterns-established:
  - "Repair-before-migrate: startup repair must run before migration 0004 UNIQUE index creation"
  - "Lazy one-shot: _repair_done flag prevents redundant repair_aggregate_seqs() calls"
  - "Source-tagged logging: every repair trigger logs its source (append/read_stream/run_repair_now)"

requirements-completed: [EVT-03]
---

# Plan C: Startup Repair Wiring Summary

**SqliteEventStore lazy-repair wiring with structlog logging and startup ordering documentation**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-24T10:00:00Z
- **Completed:** 2026-04-24T10:10:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Added structlog logger to events.py (consistent with reconciler.py, sync_mirror.py, config.py)
- Added `__init__` with `_repair_done` flag for lazy one-shot repair
- Added `_maybe_repair()` helper called at top of `append()` and `read_stream()`
- Added `run_repair_now()` public method for daemon startup sequencing
- Added per-correction structlog logging with direction (stale/future) tracking
- Added Phase 006 integration boundary documentation in class docstring
- 82 tests pass across 4 test files (test_events, test_seq_crash_recovery, test_reconciler, test_sync_mirror)

## Task Commits

Each task was committed atomically:

1. **C.1: Add __init__ and lazy repair to SqliteEventStore** - `ac172c1` (feat)
2. **C.2: Add per-repair structlog logging to repair_aggregate_seqs** - `77a7ee2` (feat)
3. **C.3: Document Phase 006 integration boundary** - `f50437d` (docs)

## Files Modified
- `src/state_core/events.py` - Added __init__, _maybe_repair, run_repair_now, structlog logging, docstring (75 insertions, 1 deletion)

## Decisions Made
- `run_repair` parameter on `__init__` is reserved for future use; the flag is always initialized to `False` and repair runs lazily on first access
- `run_repair_now()` explicitly skips the `_repair_done` guard so daemon startup can force repair before migration even if lazy repair hasn't triggered
- Structlog events use structured key=value pairs (not string formatting) for machine-parseable logs
- Direction tracking (stale vs future) in per-correction logs enables monitoring of crash recovery patterns

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None — all changes were straightforward file modifications to events.py. Existing callers all use `SqliteEventStore()` with no arguments, so the `run_repair=False` default is fully backward compatible.

## Next Phase Readiness
- Plan C wiring is complete: `_maybe_repair` guards `append()` and `read_stream()`, `run_repair_now()` available for daemon startup
- Ready for Plan D (migration 0004 UNIQUE index) — repair will clean duplicates first via `run_repair_now()` before migrate applies the index
- Structlog logging provides observability into repair actions during startup

---
*Phase: 007-monotonic-seq-crash-recovery*
*Plan: C*
*Completed: 2026-04-24*
