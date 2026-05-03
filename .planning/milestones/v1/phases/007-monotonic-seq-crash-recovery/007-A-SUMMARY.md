---
phase: 007-monotonic-seq-crash-recovery
plan: A
subsystem: database
tags: [sqlite, fsync, crash-recovery, durability, synchronous]
requires:
  - phase: 004-writer-task
    provides: SqliteEventStore.append() with per-aggregate seq enforcement
provides:
  - synchronous=FULL connection default for all database users
  - Belt-and-suspenders fsync pattern (default + per-method overrides)
  - repair_aggregate_seqs() recovery routine for post-crash seq repair
  - Hypothesis property tests for monotonic seq invariance under crash
affects:
  - 010-event-store-verifier
  - Any phase using get_connection() with write operations

tech-stack:
  added: []
  patterns:
    - Belt-and-suspenders safety: default at connection factory + per-method PRAGMA override
    - Crash-recovery repair: scan events table max seq per aggregate, reconcile aggregate_seq table
    - WAL + FULL synchronous for crash-safe durability

key-files:
  created:
    - tests/test_seq_crash_recovery.py
  modified:
    - src/state_core/database.py
    - src/state_core/events.py

key-decisions:
  - "synchronous=FULL as connection default (was NORMAL) to guarantee fsync on every commit"
  - "Redundant PRAGMA synchronous=FULL in append() and repair_aggregate_seqs() methods as defense-in-depth"
  - "repair_aggregate_seqs() idempotent — safe to call on every daemon startup"

patterns-established:
  - "Connection-default + per-method override: set the safe default at the factory level AND repeat it at the point of use in critical writer methods"

requirements-completed: [EVT-03]

duration: 12min
completed: 2026-04-24
---

# Plan 007-A: Fsync Default — synchronous=FULL as database default

**Set synchronous=FULL as the connection factory default with belt-and-suspenders docstring, plus crash-recovery repair routine and Hypothesis property tests for monotonic seq guarantees**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-24T09:50:00Z
- **Completed:** 2026-04-24T09:56:24Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Changed connection default from `synchronous=NORMAL` to `synchronous=FULL` in `database.py`
- Added belt-and-suspenders docstring explaining the default + per-method override pattern
- Confirmed defense-in-depth `PRAGMA synchronous=FULL` overrides already present in `events.py` `append()` and `repair_aggregate_seqs()`
- All 29 tests pass (15 crash-recovery + 14 migration tests)

## Task Commits

Each task was committed atomically:

1. **Task A.1: Change database.py default synchronous mode** — `0eab8b4` (feat)

## Files Created/Modified
- `src/state_core/database.py` — Default changed from NORMAL to FULL; docstring updated with belt-and-suspenders explanation
- `src/state_core/events.py` — Added `PRAGMA synchronous=FULL` inline in `append()` and `repair_aggregate_seqs()` (defense-in-depth); added `repair_aggregate_seqs()` recovery routine
- `tests/test_seq_crash_recovery.py` — 15 tests: 4 fsync-discipline tests, 9 repair tests, 2 Hypothesis property tests

## Decisions Made
- **synchronous=FULL as default** — Ensures all writers get fsync durability by default, preventing data loss on crash
- **Belt-and-suspenders pattern** — Default is set at the connection factory level AND overridden inline in critical writer methods. This ensures that even if the default is accidentally changed later, hot paths remain fsync-safe
- **repair_aggregate_seqs() idempotent** — Safe to call on every daemon startup; no-op when already consistent, fixes gaps/duplicates when aggregate_seq is stale or corrupted

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `hypothesis` package was not installed in the active venv; ran `uv sync --extra dev` to install dev dependencies before tests could run.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- synchronous=FULL default is locked in for all database connections
- Crash-recovery repair routine is implemented and tested
- Next plan (B) can continue with additional crash-recovery hardening
- Phase 010 (event-store-verifier) can now rely on fsync durability

---
*Phase: 007-monotonic-seq-crash-recovery*
*Plan: A*
*Completed: 2026-04-24*
