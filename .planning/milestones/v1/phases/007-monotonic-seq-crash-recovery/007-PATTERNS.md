# Phase 007: Monotonic Seq Crash-Recovery — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 6 (3 modified, 1 new migration, 1 modified test, 1 potential config change)
**Analogs found:** 6/6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/state_core/events.py` | service (event store) | CRUD | `src/state_core/events.py` (self) | exact |
| `src/state_core/database.py` | config/utility | connection management | `src/state_core/database.py` (self) | exact |
| `.state/migrations/0004_uniq_agg_seq.sql` | migration | schema | `src/state_core/migrations.py` (runner pattern) | role-match |
| `tests/test_seq_crash_recovery.py` | test | CRUD | `tests/test_events.py` (Hypothesis pattern) | role-match |

## Pattern Assignments

### `src/state_core/events.py` (service, CRUD) — MODIFY

**Analog:** `src/state_core/events.py` (self — existing patterns to extend)

**Imports pattern** (lines 8-21):
```python
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import aiosqlite
from ulid import ULID

from src.state_core.database import get_connection
from src.state_core.schema import Mode
from src.state_core.sync_mirror import SyncEventMirror
```

**New imports to ADD** (for structlog repair logging + run_repair flag):
```python
import structlog

log = structlog.get_logger(__name__)
```

**Single-transaction write discipline** (lines 90-123) — THIS IS THE CORE PATTERN TO PRESERVE:
```python
async with get_connection() as db:
    await db.execute("PRAGMA synchronous=FULL;")
    await db.execute("BEGIN IMMEDIATE")

    cursor = await db.execute(
        "SELECT seq FROM aggregate_seq WHERE aggregate_id = ?",
        (aggregate_id,),
    )
    row = await cursor.fetchone()
    seq = (row[0] if row else 0) + 1

    await db.execute(
        "INSERT INTO events "
        "(id, seq, aggregate_type, aggregate_id, type, data, ts, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (id_, seq, aggregate_type, aggregate_id, event_type,
         json.dumps(data, sort_keys=True, separators=(",", ":")),
         ts, mode),
    )

    await db.execute(
        "INSERT OR REPLACE INTO aggregate_seq (aggregate_id, seq, updated_at) "
        "VALUES (?, ?, ?)",
        (aggregate_id, seq, ts),
    )

    await db.commit()
```

**repair_aggregate_seqs() recovery routine** (lines 190-245) — THE RECOVERY PATTERN TO WIRE:
```python
async def repair_aggregate_seqs(self) -> list[dict[str, Any]]:
    async with get_connection() as db:
        await db.execute("PRAGMA synchronous=FULL;")
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            "SELECT aggregate_id, MAX(seq) AS max_seq "
            "FROM events GROUP BY aggregate_id"
        )
        event_max = await cursor.fetchall()

        repairs: list[dict[str, Any]] = []
        for row in event_max:
            agg_id: str = row["aggregate_id"]
            max_seq: int = row["max_seq"]

            cursor = await db.execute(
                "SELECT seq FROM aggregate_seq WHERE aggregate_id = ?",
                (agg_id,),
            )
            seq_row = await cursor.fetchone()
            current_seq: int = seq_row[0] if seq_row else 0

            if current_seq != max_seq:
                await db.execute(
                    "INSERT OR REPLACE INTO aggregate_seq "
                    "(aggregate_id, seq, updated_at) "
                    "VALUES (?, ?, ?)",
                    (agg_id, max_seq, "2026-01-01T00:00:00Z"),
                )
                repairs.append({
                    "aggregate_id": agg_id,
                    "old_seq": current_seq,
                    "new_seq": max_seq,
                })

        await db.commit()
    return repairs
```

**`__init__` pattern to ADD** — model after existing constructor-less class, add repair-on-startup flag:
```python
class SqliteEventStore:
    """Concrete EventStore backed by events.sqlite via database.py."""

    def __init__(self, run_repair: bool = False) -> None:
        """Initialize the store.

        Args:
            run_repair: If True, runs repair_aggregate_seqs() on the first
                call to an async context. The actual repair is deferred
                because __init__ is synchronous.
        """
        self._run_repair = run_repair
        self._repair_done = False
```

Note: Since `__init__` is synchronous, the repair call is deferred. The RESEARCH.md suggests two patterns:
- (a) Call `repair_aggregate_seqs()` inside `__init__` — impossible since it's async
- (b) Have a startup step that calls it — e.g., in the daemon startup, or lazily on first `append()`

The simplest approach (matching the research "run_repair flag" suggestion) is to defer the repair to the first `append()` or `read_stream()` call, or to have a separate `start()` async method. The daemon can also call `repair_aggregate_seqs()` directly during startup.

---

### `src/state_core/database.py` (config/utility, connection management) — MODIFY

**Analog:** `src/state_core/database.py` (self)

**Connection factory with WAL + synchronous=NORMAL** (lines 32-48):
```python
@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection to the event store with WAL + synchronous=NORMAL."""
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        yield db
```

**Change needed:** The RESEARCH.md recommends either:
- (a) Changing `PRAGMA synchronous=NORMAL` to `PRAGMA synchronous=FULL`
- (b) Adding a comment documenting that writers MUST override to FULL

If adopting option (a), the change is a one-line edit on line 47 from `NORMAL` to `FULL`:
```python
# Was:  await db.execute("PRAGMA synchronous=NORMAL;")
# Change to:
await db.execute("PRAGMA synchronous=FULL;")
```

---

### `.state/migrations/0004_uniq_agg_seq.sql` (migration, schema) — NEW

**Analog:** `src/state_core/migrations.py` (migration runner — the consumer of SQL files)

**Migration naming convention** (from `migrations.py` line 60):
```python
# Files are globbed as:
migration_files = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))
# Example: 0001_init.sql, 0002_cache.sql, 0003_...
```

**Migration runner pattern** (lines 49-91):
```python
async def migrate() -> None:
    """Apply all unapplied migrations in filename order.
    Safe to call multiple times -- already-applied migrations are skipped.
    """
    # ... scans .state/migrations/, checks _migrations meta-table,
    # applies unapplied ones via db.executescript(sql)
```

**New migration SQL content pattern** — follow the existing migration style (single-file SQL):
```sql
-- 0004_uniq_agg_seq.sql
-- Add UNIQUE index on (aggregate_id, seq) to prevent duplicate seq values
-- after crash-recovery scenarios.
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq
    ON events(aggregate_id, seq);
```

The `IF NOT EXISTS` guard matches the existing migration idempotency pattern.

**Test pattern for verifying the constraint** — analog from `test_migrations.py` lines 196-215:
```python
@pytest.mark.asyncio
async def test_all_indexes_exist() -> None:
    """All 6 indexes exist in sqlite_master."""
    await migrate()
    from src.state_core.database import get_connection

    expected_indexes = {
        "idx_events_agg",
        "idx_events_ts",
        "idx_events_unsynced",
        "idx_steps_slice",
        "idx_steps_state",
        "idx_concepts_learner",
        "idx_events_agg_seq",   # NEW: phase 007
    }
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        actual_indexes = {row[0] for row in await cursor.fetchall()}
    missing = expected_indexes - actual_indexes
    assert not missing, f"Missing indexes: {missing}"
```

---

### `tests/test_seq_crash_recovery.py` (test, CRUD) — MODIFY

**Analog:** `tests/test_events.py` for Hypothesis property test patterns, `tests/test_seq_crash_recovery.py` (self) for existing repair test patterns.

**Test fixture pattern** (`_isolate_db`, from `test_events.py` lines 23-32):
```python
@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)
```

**Store fixture with migrate** (from `test_events.py` lines 35-39):
```python
@pytest.fixture
async def store() -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()
```

**Hypothesis property test pattern** (from `test_events.py` lines 281-295, 303-316) — note the per-example isolation:
```python
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    aggregate_type=st.sampled_from([...]),
    mode_val=st.sampled_from(["build", "teach", "kernel"]),
    data=st.dictionaries(...),
)
async def test_property_append_read_roundtrip(
    tmp_path: Path,
    aggregate_type: str,
    mode_val: str,
    data: dict,
) -> None:
    """Hypothesis property: any valid input round-trips correctly."""
    import os
    import uuid

    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = unique / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    await migrate()
    store = SqliteEventStore()
    # ... test body
```

**Crash simulation pattern (to ADD)** — monkeypatch `db.commit()` to raise mid-transaction:
```python
async def test_crash_mid_append_repair_restores_monotonic(
    store: SqliteEventStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate a crash mid-append: commit fails, data rolls back, repair fixes seq."""
    import aiosqlite

    original_commit = aiosqlite.Connection.commit

    call_count = 0

    async def failing_commit(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Simulated crash mid-transaction")
        return await original_commit(self)

    monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)

    # First append "crashes"
    with pytest.raises(Exception, match="Simulated crash"):
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})

    monkeypatch.undo()

    # Append should succeed now, starting seq at 1 since rollback undid it
    id1 = await store.append("step", "agg-01", "state.step.executed", {"x": 2})
    stream = [e async for e in store.read_stream("agg-01")]
    assert len(stream) == 1
    assert stream[0]["seq"] == 1
    assert stream[0]["id"] == id1
```

**UNIQUE constraint enforcement test (to ADD):**
```python
async def test_unique_constraint_prevents_duplicate_seq(
    store: SqliteEventStore,
) -> None:
    """Direct INSERT of duplicate (aggregate_id, seq) raises IntegrityError."""
    from src.state_core.database import get_connection

    # Insert first event normally
    await store.append("step", "agg-01", "state.step.executed", {"x": 1})

    # Directly insert another event with same aggregate_id and seq
    async with get_connection() as db:
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute(
                "INSERT INTO events (id, seq, aggregate_type, aggregate_id, type, data, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("01ARZ3NDEKTSV4RRFFQ69G5FAV", 1, "step", "agg-01",
                 "state.step.executed", '{"x":2}', "2026-01-01T00:00:00Z"),
            )
            await db.commit()
```

**Repair-on-startup wiring test (to ADD):**
```python
async def test_repair_on_startup_flag(
    store: SqliteEventStore,
) -> None:
    """SqliteEventStore with run_repair=True fixes stale aggregate_seq on first use."""
    # Corrupt aggregate_seq directly
    from src.state_core.database import get_connection

    await store.append("step", "agg-01", "state.step.executed", {"x": 1})
    await store.append("step", "agg-01", "state.step.executed", {"x": 2})

    async with get_connection() as db:
        await db.execute("DELETE FROM aggregate_seq")
        await db.commit()

    # Create a new store with run_repair=True
    repaired_store = SqliteEventStore(run_repair=True)

    # The next append should trigger repair and get correct seq
    id_ = await repaired_store.append(
        "step", "agg-01", "state.step.executed", {"x": 3}
    )
    stream = [e async for e in repaired_store.read_stream("agg-01")]
    assert [e["seq"] for e in stream] == [1, 2, 3]
```

---

## Shared Patterns

### Single-Transaction Write Discipline
**Source:** `src/state_core/events.py` lines 90-123 and 208-243
**Apply to:** All database write operations in events.py
```python
async with get_connection() as db:
    await db.execute("PRAGMA synchronous=FULL;")
    await db.execute("BEGIN IMMEDIATE")
    # ... read data, update, insert ...
    await db.commit()
```

### Migrations Naming and Syntax
**Source:** `src/state_core/migrations.py` lines 49-91
**Apply to:** New migration files in `.state/migrations/`
```python
# File pattern: 0004_*.sql (glob matches [0-9][0-9][0-9][0-9]_*.sql)
# Applied via db.executescript(sql)
# Tracked in _migrations table with checksum verification
```

### Hypothesis Property Test Isolation
**Source:** `tests/test_events.py` lines 281-333 and `tests/test_seq_crash_recovery.py` lines 202-332
**Apply to:** New Hypothesis property tests
```python
# Pattern: unique subdirectory per example
unique = tmp_path / uuid.uuid4().hex
unique.mkdir(parents=True)
db_path = unique / ".state" / "events.sqlite"
os.environ["STATE_DB_PATH"] = str(db_path)
# ... copy migrations, call migrate(), create store
```

### Test Isolation Fixture
**Source:** `tests/test_events.py` lines 23-32
**Apply to:** All database-backed tests
```python
@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)
```

### Row Factory Pattern
**Source:** `src/state_core/events.py` lines 147-148 and `src/state_core/database.py` line 45
**Apply to:** Any database query that returns rows for dict-like access
```python
db.row_factory = aiosqlite.Row
# Then rows support: row["column_name"]
```

### Deterministic JSON Serialization
**Source:** `src/state_core/events.py` line 111
**Apply to:** All event data serialization
```python
json.dumps(data, sort_keys=True, separators=(",", ":"))
```

### Structlog Logging Pattern
**Source:** `src/state_core/reconciler.py` lines 13, 53, 67, 115-118
**Apply to:** New logging in events.py repair/startup flow
```python
import structlog
log = structlog.get_logger(__name__)

# Usage in repair:
log.info("aggregate seq repair complete", repairs=len(repairs))
# Or at startup:
log.info("event store startup: running repair", aggregates_repaired=len(repairs))
```

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| — | — | — | All files have a direct analog in the existing codebase |

## Metadata

**Analog search scope:** `src/state_core/`, `tests/`, `.state/migrations/`
**Files scanned:** 12 Python source files, 8 test files, 0 migration files (migrations directory doesn't exist yet — will be created by migration runner on first call)
**Pattern extraction date:** 2026-04-24
