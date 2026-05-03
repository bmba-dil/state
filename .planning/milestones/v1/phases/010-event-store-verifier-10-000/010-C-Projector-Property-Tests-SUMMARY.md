---
phase: 010-event-store-verifier-10-000
plan: C
subsystem: testing
tags: [hypothesis, property-testing, projector, determinism, frontmatter]

# Dependency graph
requires:
  - phase: 010-event-store-verifier-10-000
    provides: PROJECTOR_EVENT_DATA strategies, AGGREGATE_FOR_EVENT mapping, test infrastructure
provides:
  - Hypothesis property test covering all 9 aggregate types (34 event types) for rebuild determinism
  - Frontmatter integrity test proving bit-identical JSON across rebuilds and cross-DB scenarios
  - Verification that non-projection event types (arc, phase, drill, decision, auth, mode) do not crash rebuild

affects: [future projector/extensibility phases, any phase modifying the handler registry]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hypothesis property tests with st.data() draw pattern for event data generation"
    - "Cross-DB determinism verification pattern (same events, independent databases)"
    - "PROJECTOR_EVENT_DATA dict mirrors EVENT_DATA_STRATEGIES but uses st.just() for deterministic data"

key-files:
  created: []
  modified:
    - tests/test_projector.py

key-decisions:
  - "Used data.draw() instead of .example() for Hypothesis strategy drawing — modern Hypothesis rejects .example() inside @given"
  - "Measured events-table count AFTER append but BEFORE rebuild to correctly verify events-table immutability"
  - "Imported AGGREGATE_FOR_EVENT from test_events.py instead of duplicating the mapping"

patterns-established:
  - "PROJECTOR_EVENT_DATA: fixed-dictionary strategies for all 34 event types, grouped by aggregate with clear 'handled/NOT handled' comments"
  - "Cross-DB determinism: save STATE_DB_PATH, create independent DB, restore env var"

requirements-completed: [EVT-06]

# Metrics
duration: 25min
completed: 2026-04-25
---

# Plan C: Projector Property Tests Summary

**Hypothesis property test covering all 9 aggregate types (34 event types) for rebuild determinism, plus frontmatter integrity test proving bit-identical JSON across rebuilds**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-25T12:25:00Z
- **Completed:** 2026-04-25T12:28:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `test_property_all_aggregates_rebuild_determinism` — Hypothesis test running 50 examples with random sequences of up to 20 events across all 34 event types; verifies checksum identity after two rebuilds and events-table immutability
- `test_property_frontmatter_determinism` — Proves frontmatter JSON is bit-identical across two rebuilds on the same DB and across two independent DBs with identical events
- Non-projection event types (arc, phase, drill, decision, auth, mode) are included in PROJECTOR_EVENT_DATA and proven not to crash rebuild_all()

## Task Commits

Each task was committed atomically:

1. **Task 1: Hypothesis property test for rebuild determinism across all aggregate types** - `1ce9da1` (test)
2. **Task 2: Frontmatter determinism property test** - `ad0e759` (test)

**Plan metadata:** N/A (no separate plan commit)

## Files Created/Modified
- `tests/test_projector.py` - Added PROJECTOR_EVENT_DATA strategies dict (34 event types), AGGREGATE_FOR_EVENT import, _read_table_frontmatter helper, two new property tests

## Decisions Made
- Used `data.draw()` pattern instead of `.example()` for Hypothesis strategy drawing — modern Hypothesis rejects `.example()` inside `@given` tests
- Measured events-table count AFTER appending events but BEFORE rebuilding to correctly verify events-table immutability (plan had before-append measurement which would always fail)
- Imported `AGGREGATE_FOR_EVENT` from `test_events.py` instead of duplicating the mapping

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Broken behavior] Hypothesis .example() call rejected inside @given test**
- **Found during:** Task 1 (test_property_all_aggregates_rebuild_determinism)
- **Issue:** Plan specified `PROJECTOR_EVENT_DATA[event_type].example()` inside a `@given` test, which Hypothesis 6.x rejects with `HypothesisException`
- **Fix:** Changed to `data.draw(PROJECTOR_EVENT_DATA[event_type])` using `st.data()` parameter, matching the existing pattern in `test_events.py`
- **Files modified:** tests/test_projector.py
- **Verification:** All 50 Hypothesis examples pass
- **Committed in:** 1ce9da1 (Task 1 commit)

**2. [Rule 1 - Broken behavior] Events-table count measurement logic**
- **Found during:** Task 1 (test_property_all_aggregates_rebuild_determinism)
- **Issue:** Plan measured `before` count BEFORE appending events, then checked `assert before == after` after rebuild — but events were appended between measurements, so `before=0, after=N` always failed for non-empty sequences
- **Fix:** Moved `before` measurement to AFTER appending events but BEFORE rebuilding, so the assertion correctly verifies rebuild does not mutate the events table
- **Files modified:** tests/test_projector.py
- **Verification:** All 50 Hypothesis examples pass for sequences of all lengths (0-20 events)
- **Committed in:** 1ce9da1 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
- None — both deviations were straightforward auto-fixes

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- All projector property tests are in place and passing
- Foundation for future projector extensibility testing (new event types can be added to PROJECTOR_EVENT_DATA)
- The _read_table_frontmatter helper provides a building block for frontmatter-specific assertions

---
*Phase: 010-event-store-verifier-10-000*
*Completed: 2026-04-25*
