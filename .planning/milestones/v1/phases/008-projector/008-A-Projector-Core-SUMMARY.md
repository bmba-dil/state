---
phase: 008-projector
plan: A
subsystem: event-store
tags: [projector, cqrs, projection, event-sourcing, sqlite]

# Dependency graph
requires:
  - phase: 004-writer-task
    provides: EventStore append() with monotonic seq
provides:
  - Projector class with full rebuild (rebuild_all) and live update (apply_event)
  - 19 pure projection handler functions registered via @_register_handler decorator
  - Handler registry pattern extensible to future event types
  - _validate_table whitelist guard against SQL injection
affects:
  - 009-cli-integration (uses Projector for `state events rebuild-projections`)
  - 010-test-suite (tests all handlers and Projector methods)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CQRS-style projection engine with decorator-based handler registration
    - Pure projection handlers: (current_state, event_data) -> new_state_dict
    - Single-transaction rebuild with BEGIN IMMEDIATE atomicity
    - Deterministic JSON serialization for frontmatter accumulation

key-files:
  created:
    - src/state_core/projector.py (663 lines — module skeleton, 19 handlers, Projector class)
  modified: []

key-decisions:
  - "Unknown event types silently ignored with debug log — future-proofing for new event types"
  - "rebuild_all() opens its OWN connection via get_connection() to avoid EventStore lock contention"
  - "apply_event() opens its own connection for the same reason"
  - "Non-cache aggregate types (arc, phase, decision, auth, mode, drill) silently skipped — no cache table for those aggregates"
  - "Frontmatter accumulation uses json.dumps(sort_keys=True, separators=(',', ':')) for deterministic serialization"
  - "step.reverted sets state to 'reverted' (terminal state) — snapshot replay for actual undo is handled by the snapshot module, not the projector"

patterns-established:
  - "Handler registration: @_register_handler('state.step.xxx') def _handle_step_xxx(current, data) -> dict"
  - "Frontmatter merging: parse current frontmatter JSON, merge event data on top, re-serialize"
  - "Table column definitions as module-level tuple constants for reuse across rebuild_all and apply_event"

requirements-completed:
  - EVT-02

# Metrics
duration: ~30min
completed: 2026-04-24
---

# Phase 008 Plan A: Projector Core Module Summary

**CQRS-style projection engine with decorator-based handler registry, 19 pure projection handlers (10 step + 4 slice + 5 concept), and Projector class with single-transaction full rebuild and live single-event upsert**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-24
- **Completed:** 2026-04-24
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Created `src/state_core/projector.py` with module skeleton, handler registry, and all infrastructure
- Implemented 10 step projection handlers covering the full `state.step.*` event lifecycle (discussed → planned → executing → verified → blocked → snapshotted → reverted)
- Implemented 4 slice handlers tracking worktree lifecycle (planned → in_progress → shipped → reverted)
- Implemented 5 concept handlers tracking teach-mode concept progression with mastery probability computation
- Built `Projector.rebuild_all()` — full cache table rebuild in a single `BEGIN IMMEDIATE`...`COMMIT` transaction, reading events in aggregate+seq order, applying all handlers, and writing `INSERT OR REPLACE` to the appropriate cache table
- Built `Projector.apply_event()` — live single-event upsert for post-append cache synchronization, with current-state read and handler dispatch
- Added `_validate_table()` whitelist guard preventing SQL injection on table name interpolation
- No non-deterministic imports (datetime.now, random, uuid, time, secrets) — all handlers are pure functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Module skeleton + handler registry pattern** — `ecaf766` (feat)
2. **Task 2: 19 projection handler functions** — `cf54dae` (feat)
3. **Task 3: Projector class with rebuild_all + apply_event** — `b864047` (feat)

## Files Created/Modified

- `src/state_core/projector.py` — Module skeleton, `_merge_frontmatter` helper, 19 handler functions, `_STEP_COLUMNS`/`_SLICE_COLUMNS`/`_CONCEPT_COLUMNS` tuple definitions, and the `Projector` class with `rebuild_all()`, `apply_event()`, and `_read_events()` — 663 lines total

## Decisions Made

- **Own connection for Projector:** Both `rebuild_all()` and `apply_event()` open their own connection via `get_connection()` rather than using the EventStore's connection. This prevents lock contention and keeps the Projector read-only from the event store's perspective.
- **Non-cache aggregates silently skipped:** Events for aggregate types without a cache table (arc, phase, decision, auth, mode, drill) are silently skipped during rebuild. This is correct — no cache table means no projection needed.
- **Unknown event types silently logged:** Handler lookup returns `None` for unregistered event types, which are silently skipped with a debug log. This provides future-proofing as new event types are added in later phases.
- **step.reverted as terminal state:** The revert handler sets state to `"reverted"` rather than attempting to restore a previous state. Actual revert-to-previous-state requires snapshot replay (handled by a separate module), not projection.
- **Concept mastery probability computed heuristically:** `_handle_concept_drilled` computes `mastery_probability = min(1.0, score / max(items_attempted, 1))` and `scaffold_level = max(0, 5 - items_attempted // 3)` as reasonable defaults. These are documented defaults that can be refined later.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Ready for Plan B (CLI Integration — `state events rebuild-projections` command)
- Ready for Plan C (Test Suite — comprehensive projection handler and Projector tests)
- All 19 handlers registered, Projector class complete, module structure follows the same pattern as `reconciler.py`

---

*Phase: 008-projector*
*Plan: A*
*Completed: 2026-04-24*
