---
phase: 010-event-store-verifier-10-000
plan: D
subsystem: testing
tags: [golden-fixture, e2e, verifier, checksum, integrity, determinism]

# Dependency graph
requires:
  - phase: 010-A
    provides: Golden fixture SQLite DB, regeneration script, triple SHA-256 checksums
  - phase: 007
    provides: SqliteEventStore with crash-safe append and repair_aggregate_seqs
  - phase: 008
    provides: Projector (rebuild_all) for cache-table projections
provides:
  - 9-test E2E verifier suite proving golden fixture integrity
  - Triple checksum assertion (DB = export JSONL = projection snapshot)
  - No-op crash-recovery proof on consistent fixture
  - Mode-filter counting verification
  - Deterministic replay proof (bit-identical across independent reads)
affects: [010-B, 010-C]

# Tech tracking
tech-stack:
  added: []
  patterns: [golden fixture E2E verification, triple-checksum integrity assertion, fixture_copy temp isolation]

key-files:
  created:
    - tests/test_verifier_e2e.py
  modified: []

key-decisions:
  - "Using fixture_copy pattern (copy to temp + STATE_DB_PATH) to never modify the original golden fixture"
  - "Module-scoped checksums fixture loads JSON once per test module (10k events × many tests)"
  - "Projection snapshot checksum uses generator's exact serialization approach (row_factory=None, frontmatter as JSON string)"

patterns-established:
  - "E2E verifier tests: pytest.skip() with clear message when fixture files are missing"
  - "Temp-copy isolation: every test gets a disposable copy via fixture_copy fixture"
  - "Triple checksum assertion: DB SHA-256 = export JSONL SHA-256 = projection snapshot SHA-256"

requirements-completed: [EVT-06]

# Metrics
duration: 10min
completed: 2026-04-25
---

# Phase 010 Plan D: Golden Fixture Verifier Summary

**9-test E2E verifier suite proving golden fixture integrity via triple SHA-256 checksums, no-op crash recovery, mode-filter counting, and deterministic replay**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-25T12:34:00Z
- **Completed:** 2026-04-25T12:44:00Z
- **Tasks:** 6 + 1 fix commit
- **Files modified:** 1

## Accomplishments

- Created `tests/test_verifier_e2e.py` with 9 tests across 5 test classes
- Implemented `test_db_checksum_matches` — synchronous SHA-256 check of golden fixture file against recorded checksum
- Implemented triple checksum assertion: DB SHA-256 = export JSONL SHA-256 = projection snapshot SHA-256 proves all three representations are deterministic
- Implemented crash-recovery no-op proof: `repair_aggregate_seqs()` returns empty on the consistent golden fixture (single and idempotent double call)
- Implemented mode-filter verification: build + teach + kernel = 10000 and all three modes have events > 0
- Implemented deterministic replay proof: `read_events()` vs `read_events_iter()` produce bit-identical 10k event lists; mode-filtered sets are disjoint
- All 9 tests pass; full 321-test suite passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test file with imports and fixtures** - `0274b69` (test)
2. **Task 2: Add TestGoldenFixtureIntegrity** - `714c3f0` (test)
3. **Task 3: Add TestTripleChecksumAssertion** - `1697875` (test)
4. **Task 4: Add TestCrashRecoveryOnGolden** - `efd1f30` (test)
5. **Task 5: Add TestModeFiltering** - `de438c4` (test)
6. **Task 6: Add TestDeterministicReplay** - `1484b7d` (test)
7. **Fix: Align projection snapshot checksum with generator** - `d93f2ca` (fix)

## Files Created/Modified

- `tests/test_verifier_e2e.py` — 258-line E2E verifier with 5 test classes (9 test methods), fixtures for temp-copy isolation and module-scoped checksums

## Decisions Made

- **`row_factory=None` for projection snapshot**: The generator uses `row_factory=None` (not `aiosqlite.Row`) and leaves `frontmatter` as a JSON string. The test was initially parsing frontmatter to dicts, causing a checksum mismatch. Fixed to use the generator's exact serialization approach.
- **Module-scoped checksums**: The `checksums` fixture is `scope="module"` so `golden-10k-checksums.json` is loaded once for the entire test module, avoiding repeated file I/O.
- **Temp-copy isolation**: The `fixture_copy` fixture copies `golden-10k.sqlite` to a temp directory and sets `STATE_DB_PATH`, ensuring tests never modify the original fixture. Migrations dir is also copied for safety.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Projection snapshot checksum mismatch**
- **Found during:** Task 7 (verification run after Task 6)
- **Issue:** `test_projection_snapshot_checksum` failed because the test parsed `frontmatter` from JSON string to dict before serialization, producing a different JSON structure than the generator's `row_factory=None` approach
- **Fix:** Changed test to use `row_factory=None` with `dict(zip(columns, row))`, matching the generator's exact approach. Also removed unused `migrate` import.
- **Files modified:** `tests/test_verifier_e2e.py`
- **Verification:** All 9 tests pass; `projection_snapshot_sha256` matches recorded value
- **Committed in:** `d93f2ca` (Task 7 fix commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix required to correctly validate the checksum. No scope creep.

## Issues Encountered

- **Projection snapshot serialization mismatch**: The plan's sample code used `db.row_factory = aiosqlite.Row` and parsed frontmatter to dicts, but the generator used `row_factory = None` and left frontmatter as JSON string. Had to align the test with the generator's exact approach to produce matching checksums.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- E2E verifier is complete and passes against the golden fixture
- Ready for Plan B (Hypothesis property-test extension) and Plan C (CLI integration tests with golden fixture)
- The verifier can be used as a pre-commit or CI gate to detect fixture tampering

---

*Phase: 010-event-store-verifier-10-000*
*Plan: D - Golden Fixture Verifier*
*Completed: 2026-04-25*
