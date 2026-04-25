---
phase: 010-event-store-verifier-10-000
plan: A
subsystem: testing
tags: [golden-fixture, event-store, sqlite, determinism, idempotency, checksum]

# Dependency graph
requires:
  - phase: 009-c
    provides: CLI query infrastructure for event export/read
  - phase: 008
    provides: Projector (rebuild_all) for cache-table projections
  - phase: 007
    provides: SqliteEventStore with crash-safe append
  - phase: 005
    provides: Event schema (34 types, 9 aggregates)
provides:
  - 10,000-event deterministic golden fixture SQLite DB
  - Regeneration script (idempotent, bit-identical reruns)
  - Three SHA-256 checksums (db, export JSONL, projection snapshot)
  - Gitignore exceptions for .state/fixtures/ directory
affects: [010-B, 010-C, 010-D]

# Tech tracking
tech-stack:
  added: [freezegun>=1.5]
  patterns: [standalone fixture generator, deterministic ULID generation, triple-checksum integrity]

key-files:
  created:
    - .state/fixtures/regenerate_fixture.py
    - .state/fixtures/golden-10k.sqlite
    - .state/fixtures/golden-10k-checksums.json
  modified:
    - .gitignore

key-decisions:
  - "Computing db_sha256 after Projector.rebuild_all() so the stored checksum reflects the final shipped DB (with populated cache tables)"
  - "Using `.state/*` instead of `.state/` in gitignore to allow negation of fixture subdirectory"
  - "Manually fixing _migrations.applied_at after migrate() since SQLite's datetime('now') C function is unaffected by freezegun"
  - "Using .venv/bin/python3 for script execution since freezegun is a dev dependency not available in system python"

patterns-established:
  - "Fixture path: .state/fixtures/ for golden verification databases"
  - "Checksums JSON format: three SHA-256 entries (db, export JSONL, projection snapshot)"
  - "Deterministic ULID: f\"{i:024d}01\" for i=1..10000"

requirements-completed: [EVT-06]

# Metrics
duration: 28min
completed: 2026-04-25
---

# Phase 010 Plan A: Golden Fixture Generator Summary

**Deterministic 10,000-event golden fixture with regeneration script, triple SHA-256 checksums, and git-trackable .state/fixtures/ directory**

## Performance

- **Duration:** 28 min
- **Started:** 2026-04-25T11:45:00Z
- **Completed:** 2026-04-25T12:13:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Updated `.gitignore` to allow `.state/fixtures/` directory while keeping `.state/events.sqlite` and other `.state/` contents properly ignored
- Created `.state/fixtures/regenerate_fixture.py` — standalone Python script producing a bit-identical 10,000-event SQLite fixture DB with deterministic ULIDs, fixed timestamps, cycled modes, and all 34 event types across 9 aggregate types
- Generated `.state/fixtures/golden-10k.sqlite` (3.3 MB) with verified 10,000 events across all distribution targets
- Generated `.state/fixtures/golden-10k-checksums.json` with three SHA-256 checksums (db, export JSONL, projection snapshot) for integrity verification
- Verified idempotency: rerunning produces bit-identical SQLite file with same SHA-256
- Verified all 34 event types present, all 3 modes (build/teach/kernel) present, all 9 aggregate types present

## Task Commits

Each task was committed atomically:

1. **Task 1: Update .gitignore to allow fixture files** - `56d7fac` (fix)
2. **Task 2: Create fixture generator script** - `911f55d` (feat)
3. **Task 3: Generate golden fixture and checksums** - `d0b2638` (feat)

## Files Created/Modified

- `.gitignore` — Changed `.state/` to `.state/*` and added negation rules for `.state/fixtures/`
- `.state/fixtures/regenerate_fixture.py` — 354-line standalone Python script with freezegun wrapping, deterministic ULID generation, 34 event type data generators, triple checksum computation
- `.state/fixtures/golden-10k.sqlite` — 3.3 MB SQLite golden fixture with 10,000 deterministic events
- `.state/fixtures/golden-10k-checksums.json` — JSON file with `db_sha256`, `export_jsonl_sha256`, `projection_snapshot_sha256`

## Decisions Made

- **db_sha256 computed after Projector.rebuild_all()**: The fixture DB's cache tables are populated by rebuild_all() before the SHA-256 is computed, so the stored checksum reflects the final shipped file. Running `shasum -a 256` on the file matches the stored `db_sha256`.
- **`.state/*` instead of `.state/` in gitignore**: Using `.state/*` allows negation rules (`!.state/fixtures/`) to re-include specific subdirectories, which is not possible with `.state/` (parent-directory exclusion rule).
- **Manual _migrations.applied_at fix**: SQLite's `datetime('now')` SQL function (used in `migrations.py` for the `_migrations.applied_at` column) is a C-level call unaffected by Python's `freezegun`. The script explicitly updates `_migrations.applied_at` to the fixed timestamp after `migrate()` for bit-identical output.
- **Venv python**: Since `freezegun` is a dev-dependency, the script must be run with `.venv/bin/python3` (or from within the project's virtual environment).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `sys.path.insert` used wrong path for imports**
- **Found during:** Task 2 (first run of regenerte_fixture.py)
- **Issue:** Script inserted `src/` directory into `sys.path` but imports use `from src.state_core.*` patterns (with `src.` prefix), causing `ModuleNotFoundError`
- **Fix:** Changed `sys.path.insert(0, str(SRC_DIR))` to `sys.path.insert(0, str(PROJECT_ROOT))` so `src.state_core` resolves correctly
- **Files modified:** `.state/fixtures/regenerate_fixture.py`
- **Verification:** Script runs successfully, imports all required modules
- **Committed in:** 911f55d (Task 2 commit)

**2. [Rule 1 - Bug] Checksum ordering produced stored SHA not matching file on disk**
- **Found during:** Task 2 (scripts checksum verification)
- **Issue:** `db_sha256` was computed BEFORE `Projector.rebuild_all()`, but rebuild_all() modifies the DB (writes cache tables). The stored checksum didn't match `shasum -a 256` on the file.
- **Fix:** Moved `db_sha256` computation to AFTER export JSONL (read-only) and projection snapshot (run rebuild, dump caches), so it reflects the final shipped DB
- **Files modified:** `.state/fixtures/regenerate_fixture.py`
- **Verification:** `shasum -a 256` on fixture file now matches stored `db_sha256`; idempotency confirmed (same SHA across reruns)
- **Committed in:** 911f55d (Task 2 commit, before Task 3 generation)

**3. [Rule 3 - Blocking] Gitignore pattern prevented fixture files from being tracked**
- **Found during:** Task 1 (gitignore update verification)
- **Issue:** Original `.state/` pattern ignores the directory itself, making it impossible to re-include subdirectories via negation per git's parent-directory exclusion rule
- **Fix:** Changed `.state/` to `.state/*` which ignores one-level-deep contents but allows negation rules to re-include specific children
- **Files modified:** `.gitignore`
- **Verification:** `git add --dry-run .state/fixtures/golden-10k.sqlite` shows file as trackable; `.state/events.sqlite` remains properly ignored
- **Committed in:** 56d7fac (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correctness and determinism. No scope creep.

## Issues Encountered

- **freezegun can't patch SQLite C functions**: The plan assumed `freezegun.freeze_time` would make `migrations.py`'s `datetime('now')` SQL call deterministic. In reality, SQLite evaluates `datetime('now')` at the C level, unaffected by Python freezegun. Resolved by explicitly updating `_migrations.applied_at` after `migrate()`.
- **Script path resolution**: Used `Path(__file__).resolve()` for robust path resolution regardless of where the script is invoked from.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Golden fixture generation is complete and idempotent
- Ready for Plan B (Hypothesis property-test extension) and Plan D (fixture verifier integration tests)
- The fixture DB can be loaded by tests via `STATE_DB_PATH` env var pointing to `.state/fixtures/golden-10k.sqlite`

---

*Phase: 010-event-store-verifier-10-000*
*Plan: A - Golden Fixture Generator*
*Completed: 2026-04-25*
