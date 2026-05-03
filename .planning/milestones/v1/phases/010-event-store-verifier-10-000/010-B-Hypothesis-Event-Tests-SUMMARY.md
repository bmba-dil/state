---
phase: 010-event-store-verifier-10-000
plan: B
subsystem: testing
tags: [hypothesis, property-testing, event-store, sqlite, pydantic]
requires:
  - phase: 010-event-store-verifier-10-000-A
    provides: golden fixture generator, 10K-event fixture, checksum verification pattern
provides:
  - Per-event-type data strategies for all 34 event types matching Pydantic schemas
  - Hypothesis property tests covering all 34 event types with deterministic ULID verification
  - Idempotent re-append tests (IntegrityError on duplicate aggregate_id+seq)
  - Mode-filtering correctness property (count_events with mode filter sum to total)
  - Explicit id_ determinism verification across aggregates
affects: [event-store verification, future schema changes]

tech-stack:
  added: []
  patterns:
    - "Hypothesis property tests use st.data() for per-type data strategies inside @given"
    - "Deterministic ULID injection for all 34 event types to prove idempotent round-trip"
    - "Aggregate mapping via AGGREGATE_FOR_EVENT dict for type-safe event-to-aggregate lookup"

key-files:
  modified:
    - tests/test_events.py

key-decisions:
  - "CLARIFIED: ULID is PRIMARY KEY (id TEXT PRIMARY KEY in migration 0001), so same ULID across aggregates raises IntegrityError. Adapted test_explicit_id_determinism to use unique ULIDs while still proving data/ts/mode determinism."
  - "CLARIFIED: Plan's .example() pattern is invalid inside @given. Used st.data().draw() instead per Hypothesis best practices."
  - "First commit (Task 1): adds AGGREGATE_FOR_EVENT + EVENT_DATA_STRATEGIES dicts with all 34 types"
  - "Second commit (Tasks 2-5): adds all 5 test functions/classes"

patterns-established:
  - "Properties: use st.data() with data.draw(strategy) for event-specific data inside @given tests"
  - "Use st.fixed_dictionaries() for Pydantic data models with extra='forbid' — guarantees each drawn dict matches the schema exactly"

requirements-completed: [EVT-06]

# Metrics
duration: 12min
completed: 2026-04-25
---

# Plan 010-B: Hypothesis Event Tests Summary

**Property-based Hypothesis tests covering all 34 event types with per-type data strategies, idempotent append verification, mode-filtering correctness, and deterministic ULID testing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-25T12:17:00Z
- **Completed:** 2026-04-25T12:29:00Z
- **Tasks:** 5
- **Files modified:** 1 (tests/test_events.py: 333 → 697 lines, +364)

## Accomplishments

- Defined `AGGREGATE_FOR_EVENT` dict mapping all 34 event types to their aggregate type
- Defined `EVENT_DATA_STRATEGIES` dict with Hypothesis data strategies matching every Pydantic data model
- Added `test_property_all_event_types_roundtrip` — 100 Hypothesis examples proving all 34 types round-trip through append → read_stream with deterministic ULID injection
- Added `TestIdempotentAppend` — verifies UNIQUE(aggregate_id, seq) constraint raises IntegrityError on duplicate, and same data with different ULIDs correctly increments seq
- Added `test_property_mode_filtering` — 50 Hypothesis examples proving mode-filtered count_events sums match total
- Added `test_explicit_id_determinism` — proves identical data/ts/mode inputs produce identical stored values across different aggregates

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-event-type data strategies** — `21c3346` (feat)
2. **Task 2: Add Hypothesis all-event-types round-trip test** — `94e53e0` (feat)
3. **Task 3: Add idempotent re-append tests** — `94e53e0` (feat, same commit as Tasks 2/4/5)
4. **Task 4: Add mode-filtering property test** — `94e53e0` (feat, same commit as Tasks 2/3/5)
5. **Task 5: Add explicit id_ determinism test** — `94e53e0` (feat, same commit as Tasks 2/3/4)

## Files Created/Modified

- `tests/test_events.py` — Added AGGREGATE_FOR_EVENT dict (34 entries), EVENT_DATA_STRATEGIES dict (34 entries), TestIdempotentAppend class, test_property_all_event_types_roundtrip, test_property_mode_filtering, test_explicit_id_determinism

## Decisions Made

- **ULID PRIMARY KEY constraint:** The `id` column is `TEXT PRIMARY KEY` (migration 0001), so the same ULID cannot be reused across aggregates. Adapted `test_explicit_id_determinism` to use unique ULIDs while still proving data/ts/mode determinism across aggregates.
- **st.data() instead of .example():** Hypothesis raises `HypothesisException` when `.example()` is called inside `@given`. Used `st.data()` with `data.draw(strategy)` instead — the idiomatic Hypothesis pattern for drawing from strategies within a test body.
- **Combined commit for Tasks 2-5:** All test additions made in a single editing pass since they're additive to the same file section. Each test is independently verifiable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cannot reuse same ULID across different aggregates**
- **Found during:** Task 5 (test_explicit_id_determinism)
- **Issue:** Plan called for `store.append("step", "step-b", ..., id_=custom_id)` with same ULID as previously inserted — `id TEXT PRIMARY KEY` in migration 0001 enforces table-wide uniqueness, not per-aggregate
- **Fix:** Changed test to use auto-generated ULIDs (which are always unique) while still asserting data/ts/mode fields are identical across aggregates
- **Files modified:** tests/test_events.py
- **Verification:** Test passes, still proves determinism (same inputs → same stored values for non-PK fields)
- **Committed in:** 94e53e0 (Tasks 2-5 commit)

**2. [Rule 1 - Bug] Plan used .example() inside @given test**
- **Found during:** Task 2 (test_property_all_event_types_roundtrip)
- **Issue:** `strategy.example()` raises `HypothesisException` inside `@given` — explicitly disallowed by Hypothesis
- **Fix:** Replaced with `st.data()` parameter and `data.draw(EVENT_DATA_STRATEGIES[event_type])` — the correct Hypothesis pattern
- **Files modified:** tests/test_events.py
- **Verification:** Test passes at 100 examples without warnings
- **Committed in:** 94e53e0 (Tasks 2-5 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in plan)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- **ULID uniqueness scope:** The plan assumed ULIDs could be reused across different aggregates, but migration 0001 defines `id TEXT PRIMARY KEY` (table-wide). Any future plans referencing ULID reuse should account for this constraint.
- **Hypothesis .example() restriction:** Plan's test template used `.example()` which is explicitly forbidden inside `@given`. The `st.data()` pattern is the idiomatic alternative and is already used in the existing codebase patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 34 event types have per-type data strategies ready for any schema-respecting property tests
- Deterministic ULID injection pattern established for future event store tests
- Ready for schema evolution verification (if schema.py models change, the strategies will need updating)
- Full test suite at 32 tests in test_events.py (+5 new), all passing

---
*Plan: 010-B-Hypothesis-Event-Tests*
*Completed: 2026-04-25*
