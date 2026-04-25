---
phase: 009-cli-state-events-tail-replay
plan: A
subsystem: event-store
tags: [sqlite, events, queries, migration, index]
# Dependency graph
requires:
  - phase: 007-repair-reconciler-fsync
    provides: SqliteEventStore with _maybe_repair, get_connection, migrations
provides:
  - Migration 0005 — index on events(id ASC) for ULID-offset queries
  - read_events() with from_id/to_id/mode/limit filter parameters
  - read_events_iter() async generator for memory-safe streaming
  - count_events() with optional mode filter
  - get_last_events() returning chronological window via DESC+reverse
affects: [009-B, 009-C]

# Tech tracking
tech-stack:
  added: none
  patterns:
    - clauses-list + params pattern for dynamic SQL with parameterized placeholders
    - AsyncIterator[yield] pattern for memory-safe large-volume reads
    - DESC+reversed(rows) pattern for chronological last-N queries

key-files:
  created:
    - .state/migrations/0005_add_events_id_index.sql
  modified:
    - src/state_core/events.py

key-decisions:
  - "Both list-return and async-iterator variants of read_events provided — callers choose based on volume"
  - "get_last_events uses ORDER BY id DESC LIMIT + reversed() to avoid full table scan"
  - "Migration 0005 index on events(id ASC) ensures ULID-offset WHERE id > ? queries are fast"

patterns-established:
  - "Dynamic SQL: list of clauses joined with ' '.join(), parameters in separate list, all user input bound via ? placeholders"
  - "Async generator: async def with yield inside get_connection() context manager for streaming reads"
  - "Chronological window: SELECT ... ORDER BY id DESC LIMIT N + reversed(rows) for last-N events"

requirements-completed: [EVT-07, EVT-08]

# Metrics
duration: 18min
completed: 2026-04-25
---

# Phase 009-A: Event Store Queries Summary

**Four global-read methods on SqliteEventStore (read_events, read_events_iter, count_events, get_last_events) plus migration 0005 index for ULID-offset query performance**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-25
- **Completed:** 2026-04-25
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Created migration 0005 adding `idx_events_id` index on `events(id ASC)` for fast ULID-offset queries
- Added `read_events()` with 4 optional filter parameters (from_id, to_id, mode, limit) — all via parameterized queries
- Added `read_events_iter()` async generator variant for memory-safe large-volume event streaming
- Added `count_events()` with optional mode filter for event counting
- Added `get_last_events(count, mode)` returning chronological-order windows via DESC+reverse pattern
- All methods follow existing patterns: `_maybe_repair()` on entry, `get_connection()` context manager, `aiosqlite.Row` row factory, JSON data deserialization

## Task Commits

Each task was committed atomically:

1. **Task 1: Create migration 0005** — `fdd0300` (feat)
2. **Task 2: Add read_events() and read_events_iter()** — `b91710a` (feat)
3. **Task 3: Add count_events() and get_last_events()** — `cd25390` (feat)

## Files Created/Modified
- `.state/migrations/0005_add_events_id_index.sql` - Migration adding `CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC)`
- `src/state_core/events.py` - Added 4 new methods to SqliteEventStore class (read_events, read_events_iter, count_events, get_last_events)

## Decisions Made
- Provided both list-return (`read_events`) and async-generator (`read_events_iter`) variants: callers choose based on expected volume
- `get_last_events` uses `ORDER BY id DESC LIMIT N` then `reversed(rows)` — avoids full table scan while returning chronological order
- Migration 0005 index is critical for `WHERE id > ? ORDER BY id ASC` query performance across potentially large event tables
- All methods follow the clauses-list + parameterized params pattern established by existing read methods — zero SQL injection vectors

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- **Migration verification with STATE_DB_PATH:** The verification script from the plan creates a fresh database at a custom path, but the migration runner resolves migration files relative to the database path, not the project root. This is expected behavior — migration files live alongside the database. The index was confirmed present in both the default database and through direct verification.
- **Test script assertion error:** One inline test had a logic error in data comparison — corrected and re-run successfully.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Four new query methods ready for CLI commands (tail, replay, export)
- Migration 0005 index ensures performant ULID-offset queries
- Plan B (CLI tail/replay/export commands) can consume these methods directly

---
*Phase: 009-A-EventStore-Queries*
*Completed: 2026-04-25*
