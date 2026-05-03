---
phase: 008-projector
plan: C
subsystem: event-store
tags: [projector, testing, cqrs, projection, event-sourcing, sqlite, hypothesis]
dependency-graph:
  requires:
    - plan: 008-A-Projector-Core
      provides: Projector class and 19 handler functions
  provides:
    - 38 comprehensive tests covering all projector functionality
    - Regression protection for all 19 handlers
    - Determinism verification via Hypothesis property tests
    - Crash atomicity proof (transaction rollback preserves cache)
key-files:
  created:
    - tests/test_projector.py (895 lines — 38 tests, 12 test classes)
  modified: []
metrics:
  total-tests: 38
  test-classes: 12
  hypothesis-examples: 50
  duration: ~25min
  completed: 2026-04-24
---

# Phase 008 Plan C: Test Suite Summary

**Comprehensive test coverage for `state_core.projector`** — 38 tests across 12 test classes covering all 19 projection handlers, full rebuild, rebuild idempotency, crash atomicity, live updates, edge cases, Hypothesis property tests, and handler registry completeness.

## Test Coverage

| Category | Test Class | Tests | What It Covers |
|----------|-----------|-------|----------------|
| **Per-event-type** | `TestStepProjection` | 10 | Every `state.step.*` handler — discussed, planned, executed, verify_started, verify_passed, verify_failed, advanced, blocked, snapshotted, reverted |
| **Per-event-type** | `TestSliceProjection` | 4 | Every `state.slice.*` handler — planned, worktree_ready, shipped, reverted |
| **Per-event-type** | `TestConceptProjection` | 5 | Every `state.concept.*` handler — introduced, observed, drilled, mastered, reviewed |
| **Full rebuild** | `TestFullRebuild` | 4 | Empty log, multi-aggregate, event count, multi-event per aggregate |
| **Idempotency** | `TestRebuildIdempotency` | 2 | Same-DB idempotency, cross-DB determinism |
| **Crash atomicity** | `TestCrashAtomicity` | 1 | Handler crash mid-rebuild preserves cache via transaction rollback |
| **Live update** | `TestLiveUpdate` | 2 | Single event, multi-event accumulation |
| **Edge cases** | `TestEdgeCases` | 4 | Unknown event type, non-cache aggregate, event count integrity, interleaved aggregates |
| **Property-based** | (standalone) | 1 | Hypothesis: rebuild never modifies events table (50 examples) |
| **Registry** | `TestHandlerRegistry` | 5 | 19 handlers, all keys valid, all step/slice/concept events present |

## Task Commits

Each task was committed atomically:

1. **Task 1: Fixtures, imports, and helpers** — `9409383` (feat)
   - DB isolation fixture (`_isolate_db`), `store` fixture, `_append_events` helper, `_read_table` helper
2. **Task 2: 19 per-event-type projection tests** — `aa087fc` (feat)
   - `TestStepProjection` (10), `TestSliceProjection` (4), `TestConceptProjection` (5)
3. **Task 3: Integration tests — rebuild, idempotency, crash, edge cases, Hypothesis** — `5e492a1` (feat)
   - `TestFullRebuild`, `TestRebuildIdempotency`, `TestCrashAtomicity`, `TestLiveUpdate`, `TestEdgeCases`, Hypothesis property test, `TestHandlerRegistry`

## Files Created

- `tests/test_projector.py` — 895 lines, 38 tests across 12 test classes + 1 standalone Hypothesis test

## Test Patterns Used

- **DB isolation**: `@pytest.fixture(autouse=True)` with `tmp_path` + `monkeypatch.setenv("STATE_DB_PATH", ...)` — identical to `test_events.py` and `test_reconciler.py`
- **Hypothesis isolation**: `uuid.uuid4().hex` subdirectory per example — identical to `test_events.py` lines 303-313
- **Crash atomicity**: `monkeypatch.setitem(HANDLERS, ...)` to inject a failing handler mid-rebuild; verifies transaction rollback preserves cache
- **Cross-DB determinism**: Two independent SQLite databases with identical event streams, rebuilt independently, compared via JSON checksums

## Key Decisions

- **`_read_table` helper parses `frontmatter` JSON**: The helper deserializes `frontmatter` from TEXT to dict so tests can assert on structured data
- **Crash atomicity via handler monkeypatch**: Rather than mocking the database layer, we patch the `HANDLERS` dict to inject a failing handler. This tests the actual transaction rollback path
- **Concept tests don't assert `state` column**: The `concepts` cache table has no `state` column (only step/slice tables do). Concept tests verify mastery fields instead
- **Hypothesis test is standalone function**: Matches the pattern in `test_events.py` where Hypothesis property tests are module-level functions (not class methods)

## Deviations from Plan

- **`TestHypothesisProperty` as standalone function**: The plan's acceptance criteria checks for `class TestHypothesisProperty`, but the code snippet in the plan is a standalone function (matching `test_events.py` pattern). The standalone function was used instead.
- **`_isolate_db` fixture count**: The plan checks `grep -c "_isolate_db"` returns 1, but the fixture definition + explicit dependency in `store` fixture produces 2 matches. Both appearances are correct per the pattern.

## Issues Encountered

1. **Python version mismatch**: System `python3` (3.14) lacks `aiosqlite`. Tests run with `.venv/bin/python3` (3.12). No code fix needed — the virtual environment handles it.
2. **Concept table has no `state` column**: Initial `test_concept_introduced` asserted `row["state"]` which doesn't exist in the concepts cache table. Fixed by removing the state assertion (concepts have mastery fields instead).
3. **Floating-point precision**: `0.8 + 0.05 = 0.8500000000000001`. Fixed by using `pytest.approx(0.85)` in `test_concept_reviewed`.
4. **Interleaved aggregate test misread**: `test_multi_mode_events_separate_aggregates` only read events for `step-01`, missing `step-02`. Fixed by iterating both aggregate IDs.

## Verification Results

- ✅ **Full test suite**: `python3 -m pytest tests/test_projector.py -x -v` — 38 passed
- ✅ **Hypothesis property test**: `test_property_rebuild_no_side_effects` — passed with 50 examples
- ✅ **Registry completeness**: `len(HANDLERS) == 19` — confirmed
- ✅ **No regressions**: `python3 -m pytest tests/ -x --no-header -q` — 279 passed (all existing + 38 new)
- ✅ **Edge case coverage**: Empty log, unknown event type, non-cache aggregate, event count integrity — all tested explicitly

---

*Phase: 008-projector*
*Plan: C*
*Completed: 2026-04-24*
