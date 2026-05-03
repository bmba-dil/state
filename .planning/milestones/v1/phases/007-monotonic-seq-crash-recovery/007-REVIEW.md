---
phase: 007-monotonic-seq-crash-recovery
reviewed: 2026-04-24T12:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .state/migrations/0004_add_unique_agg_seq.sql
  - src/state_core/database.py
  - src/state_core/events.py
  - tests/test_migrations.py
  - tests/test_seq_crash_recovery.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 007: Code Review Report

**Reviewed:** 2026-04-24T12:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the monotonic-seq-crash-recovery phase: migration 0004 (UNIQUE index), database connection factory, event store append/repair logic, migration tests, and crash recovery tests. The implementation is structurally sound with correct SQLite locking protocol (BEGIN IMMEDIATE, synchronous=FULL). The core append/repair logic handles the common crash scenarios correctly.

Five warnings found: two schema-level concerns in the migration (redundant duplicate index, chicken-and-egg ordering with repair), two in the event store (missing IntegrityError handling, repair-done flag not tracking direct calls), and one in tests (MonkeyPatch leak risk). Three info items note minor style/test issues.

No CRITICAL issues: no data loss, security vulnerability, or authentication bypass was found.

---

## Warnings

### WR-01: Redundant duplicate index on (aggregate_id, seq) — double write overhead

**File:** `.state/migrations/0004_add_unique_agg_seq.sql:5`
**Issue:** Migration 0004 creates `idx_events_agg_seq` as a UNIQUE index on `(aggregate_id, seq)`. However, migration 0001 already creates `idx_events_agg` as a non-unique index on the same columns, and migration 0003 re-creates it. After all four migrations, both indexes exist covering identical columns:

| Index | Type | Columns | Created by |
|---|---|---|---|
| `idx_events_agg` | non-unique | `(aggregate_id, seq)` | 0001_init + 0003_add_mode_column |
| `idx_events_agg_seq` | unique | `(aggregate_id, seq)` | 0004_add_unique_agg_seq |

Every INSERT or UPDATE into `events` updates both indexes, incurring redundant B-tree maintenance. The UNIQUE index alone satisfies all query patterns (lookups by aggregate_id+seq and uniqueness enforcement). The non-unique `idx_events_agg` provides no additional query benefit.

**Fix:** Drop `idx_events_agg` in migration 0004 since the new UNIQUE index covers all query needs. Add to `0004_add_unique_agg_seq.sql`:

```sql
-- Drop the superseded non-unique index — the unique one covers all query patterns
DROP INDEX IF EXISTS idx_events_agg;

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq);
```

Then update `tests/test_migrations.py:201-208` to remove `idx_events_agg` from `expected_indexes`.

---

### WR-02: `_repair_done` flag not set when `repair_aggregate_seqs()` is called directly

**File:** `src/state_core/events.py:57-67`
**Issue:** The `_repair_done` flag is only set inside `_maybe_run_repair()` (line 65), not inside `repair_aggregate_seqs()` itself. When `run_repair=True` and `repair_aggregate_seqs()` is called directly (as all repair tests do), the flag remains `False`. The next call to `append()`, `read_stream()`, or `count_unsynced_events()` triggers `_maybe_run_repair()`, which calls `repair_aggregate_seqs()` a second time.

Since `repair_aggregate_seqs()` is idempotent, this is a wasted round-trip rather than a correctness bug. But for a daemon doing startup repair, it means every first append/read opens two connections instead of one and scans the full `events` table twice.

**Fix:** Have `repair_aggregate_seqs()` set `_repair_done = True` at the end of its execution:

```python
async def repair_aggregate_seqs(self) -> list[dict[str, Any]]:
    async with get_connection() as db:
        ...
    self._repair_done = True  # Track that repair ran, whether or not repairs were needed
    if repairs:
        log.info(...)
    return repairs
```

This ensures both direct calls and `_maybe_run_repair()`-mediated calls set the flag.

---

### WR-03: Unhandled `IntegrityError` in `append()` from UNIQUE constraint

**File:** `src/state_core/events.py:114-147` (INSERT INTO events at line 126)
**Issue:** The UNIQUE(aggregate_id, seq) index on `events` serves as a crash-recovery defense-in-depth constraint. Under correct operation with `BEGIN IMMEDIATE`, seq collisions should never occur. However, if the constraint does fire (e.g., from a race through a bug, or from a manually-corrupted database without repair), `aiosqlite.IntegrityError` propagates unhandled from the `INSERT INTO events` at line 126.

The caller gets a raw database exception with no domain context. This makes debugging harder and prevents any higher-level recovery (e.g., automatic repair+retry).

**Fix:** Catch `IntegrityError` around the INSERT, log the collision, and raise a domain-specific exception or auto-retry with repair:

```python
import aiosqlite

# In append(), after computing seq:
try:
    await db.execute(
        "INSERT INTO events ...",
        (id_, seq, aggregate_type, aggregate_id, event_type, json.dumps(...), ts, mode),
    )
except aiosqlite.IntegrityError:
    log.error("seq_collision", aggregate_id=aggregate_id, seq=seq)
    raise RuntimeError(
        f"Seq collision for aggregate {aggregate_id}: "
        f"seq={seq} already exists. Run repair_aggregate_seqs() to fix."
    )
```

---

### WR-04: Migration 0004 fails on databases with pre-existing duplicate seq values

**File:** `.state/migrations/0004_add_unique_agg_seq.sql:5`
**Issue:** Migration 0004 uses `CREATE UNIQUE INDEX IF NOT EXISTS`. The `IF NOT EXISTS` clause only checks if the index *name* exists — it does NOT silently skip if data prevents uniqueness. If the `events` table already contains duplicate `(aggregate_id, seq)` rows (from a prior crash), the migration raises `IntegrityError` and fails.

This creates a chicken-and-egg problem with repair: the migration runs during `migrate()` (called at daemon startup), before the `SqliteEventStore` is created and before deferred repair can run. A corrupted database that needs repair cannot even apply the migration that would protect it against future duplicates.

**Root cause ordering in daemon startup:**
1. `migrate()` runs → 0004 fails on duplicates → 🚫
2. `SqliteEventStore(run_repair=True)` is never created
3. Repair never runs

**Fix options (choose one):**

**Option A** — Change the migration to a two-phase approach: first deduplicate, then create index. This requires a custom migration script rather than raw SQL:

```sql
-- Phase 1: Remove duplicate seq rows (keep the first, delete later duplicates)
DELETE FROM events WHERE rowid NOT IN (
    SELECT MIN(rowid) FROM events GROUP BY aggregate_id, seq
);

-- Phase 2: Create the unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq);
```

**Option B** — Run repair before migration in the daemon startup sequence. Move `repair_aggregate_seqs()` call to before `migrate()` in the boot flow. This changes the ordering assumption.

**Option C** — Document this as a known limitation and handle the migration failure gracefully with a clear error message pointing the operator to run repair first. Acceptable for v1 since WAL+synchronous=FULL makes duplicate seq extremely unlikely.

---

### WR-05: MonkeyPatch leak risk in crash simulation tests

**File:** `tests/test_seq_crash_recovery.py:399-409` (test_hypothesis_crash_recovery_monotonic) and `488-495` (test_crash_mid_append_repair_restores_monotonic)
**Issue:** Both tests instantiate `pytest.MonkeyPatch()` directly (not via fixture) and call `monkeypatch.undo()` implicitly at the end of the happy path. If an unexpected exception occurs between `setattr()` and the expected `raise` from the monkeypatched function, `undo()` is never called. This leaves `aiosqlite.Connection.commit` patched at the class level for all subsequent tests, causing every append in later tests to use the crash-monkeypatched version.

In `test_hypothesis_crash_recovery_monotonic` (lines 399-409):
```python
monkeypatch = pytest.MonkeyPatch()
monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)

for agg_id in aggregate_ids:
    try:
        await store.append(...)
    except Exception as exc:
        if "Simulated crash" in str(exc):
            pass  # catch block discards OTHER exceptions too

monkeypatch.undo()  # NEVER RUNS if an unexpected exception was raised
```

The broad `except Exception` at line 405 also swallows non-crash exceptions, silently hiding bugs.

**Fix:** Use a `try/finally` guard or the context-manager form of MonkeyPatch:

```python
monkeypatch = pytest.MonkeyPatch()
monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)
try:
    for agg_id in aggregate_ids:
        try:
            await store.append(...)
        except Exception as exc:
            if "Simulated crash" not in str(exc):
                raise  # re-raise unexpected exceptions
finally:
    monkeypatch.undo()
```

---

## Info

### IN-01: Redundant `import aiosqlite` inside test body

**File:** `tests/test_seq_crash_recovery.py:366`
**Issue:** `import aiosqlite` is present inside `test_hypothesis_crash_recovery_monotonic` despite already being imported at module level (line 11). The inner import is dead code.

**Fix:** Remove the duplicate import at line 366.

---

### IN-02: Test name mismatch — "8 tables" vs 9 expected

**File:** `tests/test_migrations.py:65`
**Issue:** Test function is named `test_migrate_applies_all_8_tables` but the docstring correctly says "All 9 tables (8 data + _migrations)" and the `expected_tables` set contains 9 entries. The test name is misleading.

**Fix:** Rename to `test_migrate_applies_all_data_tables` or `test_migrate_applies_all_9_tables`.

---

### IN-03: Hypothesis tests duplicate migration-copy boilerplate

**File:** `tests/test_seq_crash_recovery.py:224-231, 278-285, 369-376`
**Issue:** Three Hypothesis property tests (`test_hypothesis_seq_monotonic_after_append`, `test_hypothesis_repair_random_mismatch`, `test_hypothesis_crash_recovery_monotonic`) each duplicate the same ~8-line setup block for isolated DB creation (UUID subdir, env var, migration copy). A shared helper function would reduce duplication and make future changes (e.g., to migration copy logic) less error-prone.

**Fix:** Extract a helper:

```python
async def _setup_isolated_db(tmp_path: Path) -> SqliteEventStore:
    import uuid
    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    migrations_dst = unique / ".state" / "migrations"
    if (Path.cwd() / ".state" / "migrations").exists():
        shutil.copytree(Path.cwd() / ".state" / "migrations", migrations_dst, dirs_exist_ok=True)
    await migrate()
    return SqliteEventStore()
```

---

_Reviewed: 2026-04-24T12:00:00Z_
_Reviewer: AI (gsd-code-reviewer)_
_Depth: standard_
