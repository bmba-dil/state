---
phase: 003
plan: C
type: tdd
autonomous: true
wave: 2
depends_on:
  - phase-003-plan-A
  - phase-003-plan-B
files_modified:
  - tests/test_database.py
  - tests/test_migrations.py
requirements:
  - EVT-01
  - EVT-02
---

<objective>
Create comprehensive tests for the database connection factory, the migration runner, and the full schema (both 0001_init + 0002_cache). Tests cover: WAL mode enforcement, migration idempotency, checksum tamper detection, table existence, index existence, raw round-trip insert/select for every table, and the `state db init` CLI command.
</objective>

<read_first>
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/CONTEXT.md
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/003-A-database-connection-and-event-migrations.md (database.py and migrations.py implementation)
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/003-B-cache-tables-migration.md (0002_cache.sql)
  - /Users/tmac/Projects/state/src/state_core/database.py (after Plan A edits)
  - /Users/tmac/Projects/state/src/state_core/migrations.py (after Plan A edits)
  - /Users/tmac/Projects/state/tests/test_schema.py (existing test patterns — pytest, fixtures, assertions style)
  - /Users/tmac/Projects/state/pyproject.toml (pytest config with asyncio_mode=auto)
</read_first>

---

### Task 1: Create `tests/test_database.py` — connection factory tests

<action>
Create `tests/test_database.py`:

```python
"""Tests for state_core.database — connection factory, path resolution, WAL mode."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.state_core.database import get_connection, get_db_path


def test_get_db_path_default() -> None:
    """Default path points to .state/events.sqlite relative to CWD."""
    p = get_db_path()
    assert p.name == "events.sqlite"
    assert p.parent.name == ".state"


def test_get_db_path_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """STATE_DB_PATH env var overrides the default path."""
    monkeypatch.setenv("STATE_DB_PATH", "/tmp/test_state_events.sqlite")
    p = get_db_path()
    assert p == Path("/tmp/test_state_events.sqlite").resolve()


@pytest.mark.asyncio
async def test_connection_wal_mode(tmp_path: Path) -> None:
    """Connection has WAL journal mode enabled."""
    db_path = tmp_path / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row is not None
            # aiosqlite returns Row objects; journal_mode value is the first column
            journal_mode = str(row[0]).lower()
            assert journal_mode == "wal", f"Expected WAL, got {journal_mode}"
    finally:
        os.environ.pop("STATE_DB_PATH", None)


@pytest.mark.asyncio
async def test_connection_synchronous_normal(tmp_path: Path) -> None:
    """Connection has synchronous=NORMAL."""
    db_path = tmp_path / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("PRAGMA synchronous")
            row = await cursor.fetchone()
            assert row is not None
            sync_val = int(row[0])
            # 1 = NORMAL, 2 = FULL
            assert sync_val == 1, f"Expected NORMAL (1), got {sync_val}"
    finally:
        os.environ.pop("STATE_DB_PATH", None)


@pytest.mark.asyncio
async def test_connection_creates_parent_dir(tmp_path: Path) -> None:
    """Connection creates the parent .state/ directory automatically."""
    db_path = tmp_path / "nonexistent" / "subdir" / "events.sqlite"
    assert not db_path.parent.exists()
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("SELECT 1 as ok")
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 1
        assert db_path.parent.exists()
    finally:
        os.environ.pop("STATE_DB_PATH", None)


@pytest.mark.asyncio
async def test_connection_row_factory(tmp_path: Path) -> None:
    """Connection uses aiosqlite.Row row_factory for dict-like access."""
    db_path = tmp_path / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("SELECT 1 as col_a, 2 as col_b")
            row = await cursor.fetchone()
            assert row is not None
            # aiosqlite.Row supports key access
            keys = [k for k in row.keys()]
            assert "col_a" in keys
            assert "col_b" in keys
    finally:
        os.environ.pop("STATE_DB_PATH", None)
```

Verification:
- `uv run python3 -m pytest tests/test_database.py -v --no-header 2>&1 | tail -20` shows all 6 tests pass.
</action>

<acceptance_criteria>
  - `uv run python3 -m pytest tests/test_database.py -v --tb=short 2>&1 | tail -10` shows 6 passed, 0 failed.
  - `ruff check tests/test_database.py --no-cache` exits 0.
  - Tests use `tmp_path` fixture (no cross-test state leakage).
  - The WAL mode test actually asserts 'wal' (not just that pragma returns something).
</acceptance_criteria>

---

### Task 2: Create `tests/test_migrations.py` — migration runner + full schema tests

<action>
Create `tests/test_migrations.py` with the following comprehensive tests:

```python
"""Tests for state_core.migrations — runner logic, idempotency, schema verification.

Applies 0001_init.sql + 0002_cache.sql in temp directories to avoid
contaminating any real .state/ directory.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from src.state_core.migrations import (
    applied_migrations,
    ensure_meta_table,
    migrate,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory for every test.

    Also copy migration files into the temp dir so migrate() can find them.
    """
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    # Copy migration files from the project's migrations dir
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


# ── Migration runner tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_migrate_applies_0001_tables() -> None:
    """After migrate(), the events and aggregate_seq tables exist."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('events', 'aggregate_seq')"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert "events" in tables
    assert "aggregate_seq" in tables


@pytest.mark.asyncio
async def test_migrate_idempotent() -> None:
    """Calling migrate() twice does not raise and produces same state."""
    await migrate()
    await migrate()  # second call must be a no-op
    # If it didn't raise, idempotency holds (tables use IF NOT EXISTS)


@pytest.mark.asyncio
async def test_migrate_applies_all_8_tables(tmp_path: Path) -> None:
    """All 9 tables (8 data + _migrations) exist after full migration."""
    await migrate()
    from src.state_core.database import get_connection

    expected_tables = {
        "events",
        "aggregate_seq",
        "steps",
        "slices",
        "concepts",
        "decisions",
        "tool_calls",
        "auth_rotations",
        "_migrations",
    }
    async with get_connection() as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual_tables = {row[0] for row in await cursor.fetchall()}
    missing = expected_tables - actual_tables
    assert not missing, f"Missing tables: {missing}"


@pytest.mark.asyncio
async def test_migrate_tracks_applied() -> None:
    """Applied migration filenames are recorded in _migrations."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        applied = await applied_migrations(db)
    assert "0001_init.sql" in applied
    assert "0002_cache.sql" in applied


@pytest.mark.asyncio
async def test_migrate_checksum_tamper_detection() -> None:
    """Modifying an already-applied migration raises RuntimeError."""
    await migrate()

    # Tamper with 0001_init.sql
    migrations_dir = Path.cwd() / ".state" / "migrations"
    init_file = migrations_dir / "0001_init.sql"
    init_file.write_text("-- TAMPERED\n")

    with pytest.raises(RuntimeError, match="checksum changed"):
        await migrate()


# ── Schema verification tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_table_columns() -> None:
    """events table has all 8 columns with correct types."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute("PRAGMA table_info(events)")
        columns = {row[1]: row[2] for row in await cursor.fetchall()}
    assert columns["id"] == "TEXT"
    assert columns["seq"] == "INTEGER"
    assert columns["aggregate_type"] == "TEXT"
    assert columns["aggregate_id"] == "TEXT"
    assert columns["type"] == "TEXT"
    assert columns["data"] == "TEXT"
    assert columns["ts"] == "TEXT"
    assert columns["synced_to_opencode"] == "INTEGER"


@pytest.mark.asyncio
async def test_aggregate_seq_table_columns() -> None:
    """aggregate_seq table has correct columns."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute("PRAGMA table_info(aggregate_seq)")
        columns = {row[1]: row[2] for row in await cursor.fetchall()}
    assert "aggregate_id" in columns
    assert "seq" in columns
    assert "updated_at" in columns


@pytest.mark.asyncio
async def test_steps_table_columns() -> None:
    """steps table has correct columns."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute("PRAGMA table_info(steps)")
        columns = {row[1] for row in await cursor.fetchall()}
    expected = {"id", "slice_id", "state", "title", "frontmatter", "updated_at"}
    assert expected.issubset(columns), f"Missing columns: {expected - columns}"


@pytest.mark.asyncio
async def test_slices_table_columns() -> None:
    """slices table has all columns including nullable worktree fields."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute("PRAGMA table_info(slices)")
        columns = {row[1] for row in await cursor.fetchall()}
    expected = {"id", "phase_id", "state", "worktree_dir", "worktree_branch", "frontmatter", "updated_at"}
    assert expected.issubset(columns), f"Missing columns: {expected - columns}"


@pytest.mark.asyncio
async def test_concepts_table_columns() -> None:
    """concepts table has all columns."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        cursor = await db.execute("PRAGMA table_info(concepts)")
        columns = {row[1] for row in await cursor.fetchall()}
    expected = {"id", "subject_id", "learner_id", "mastery_probability", "scaffold_level", "bloom_level", "frontmatter", "last_drilled_at", "updated_at"}
    assert expected.issubset(columns)


@pytest.mark.asyncio
async def test_all_indexes_exist() -> None:
    """All 8 indexes exist in sqlite_master."""
    await migrate()
    from src.state_core.database import get_connection

    expected_indexes = {
        "idx_events_agg",
        "idx_events_ts",
        "idx_events_unsynced",
        "idx_steps_slice",
        "idx_steps_state",
        "idx_concepts_learner",
    }
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        actual_indexes = {row[0] for row in await cursor.fetchall()}
    missing = expected_indexes - actual_indexes
    assert not missing, f"Missing indexes: {missing}"


# ── Round-trip tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_round_trip() -> None:
    """Insert an event row and read it back."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        await db.execute(
            "INSERT INTO events (id, seq, aggregate_type, aggregate_id, type, data, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("01ARZ3NDEKTSV4RRFFQ69G5FAV", 1, "step", "step-01", "state.step.executed",
             '{"changes_summary": "added feature X"}', "2026-01-01T00:00:00Z"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM events WHERE id = ?", ("01ARZ3NDEKTSV4RRFFQ69G5FAV",))
        row = await cursor.fetchone()
        assert row is not None
        assert row["id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert row["seq"] == 1
        assert row["aggregate_type"] == "step"
        assert row["aggregate_id"] == "step-01"
        assert row["type"] == "state.step.executed"
        assert row["data"] == '{"changes_summary": "added feature X"}'
        assert row["ts"] == "2026-01-01T00:00:00Z"
        assert row["synced_to_opencode"] == 0


@pytest.mark.asyncio
async def test_cascade_tables_round_trip() -> None:
    """Insert rows into all 6 cascade tables and read them back."""
    await migrate()
    from src.state_core.database import get_connection

    async with get_connection() as db:
        # steps
        await db.execute(
            "INSERT INTO steps (id, slice_id, state, title, frontmatter, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("step-01", "slice-01", "done", "Initial setup", "{}", "2026-01-01T00:00:00Z"),
        )
        # slices
        await db.execute(
            "INSERT INTO slices (id, phase_id, state, frontmatter, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("slice-01", "phase-01", "active", "{}", "2026-01-01T00:00:00Z"),
        )
        # concepts
        await db.execute(
            "INSERT INTO concepts (id, subject_id, learner_id, mastery_probability, scaffold_level, bloom_level, frontmatter, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("concept-01", "python", "learner-01", 0.75, 2, "apply", "{}", "2026-01-01T00:00:00Z"),
        )
        # decisions
        await db.execute(
            "INSERT INTO decisions (id, session_id, aggregate_id, question, options) "
            "VALUES (?, ?, ?, ?, ?)",
            ("dec-01", "session-01", "phase-01", "Continue?", '["yes", "no"]'),
        )
        # tool_calls
        await db.execute(
            "INSERT INTO tool_calls (id, session_id, call_id, tool, step_id, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("tc-01", "session-01", "call-001", "read", "step-01", "2026-01-01T00:00:00Z"),
        )
        # auth_rotations
        await db.execute(
            "INSERT INTO auth_rotations (id, provider, index_used, ts, outcome) "
            "VALUES (?, ?, ?, ?, ?)",
            ("auth-01", "anthropic", 0, "2026-01-01T00:00:00Z", "ok"),
        )
        await db.commit()

        # Verify all rows readable
        for table in ("steps", "slices", "concepts", "decisions", "tool_calls", "auth_rotations"):
            cursor = await db.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            assert row["cnt"] == 1, f"{table} should have 1 row, got {row['cnt']}"
```


Verification:
- `uv run python3 -m pytest tests/test_migrations.py -v --tb=short 2>&1 | tail -20` shows all tests pass.
</action>

<acceptance_criteria>
  - `uv run python3 -m pytest tests/test_migrations.py -v --tb=short 2>&1 | tail -10` shows `passed` for all tests.
  - `ruff check tests/test_migrations.py --no-cache` exits 0.
  - `uv run mypy tests/test_migrations.py --strict` exits 0.
  - All 14+ test functions pass in isolation.
  - Each test uses `_isolate_db_path` fixture (no dependency on real `.state/` directory).
</acceptance_criteria>

---

<verification>
1. **Full test suite**: `uv run python3 -m pytest tests/test_database.py tests/test_migrations.py -v --tb=short 2>&1 | tail -30` shows all tests passing (20+ tests).
2. **CLI smoke**: `STATE_DB_PATH=/tmp/state_test_db uv run python3 -m src.state_cli.main db init` exits 0, creates `.state/events.sqlite` at the path.
3. **Apply twice**: Running `db init` a second time exits 0 with no errors.
4. **Migration state persistence**: After `db init`, `SELECT filename FROM _migrations` returns `0001_init.sql` and `0002_cache.sql`.
5. **Verify no cross-contamination**: Tests use `tmp_path` with `monkeypatch` for `STATE_DB_PATH` — no test writes to the real `.state/`.
6. **ruff + mypy clean**: `ruff check tests/test_database.py tests/test_migrations.py --no-cache` exits 0. `uv run mypy tests/ --strict` exits 0.
</verification>

<must_haves>
- **`tests/test_database.py`** — 6 tests covering: default path, env var override, WAL mode assertion, synchronous=NORMAL assertion, parent dir creation, row_factory dict-like access
- **`tests/test_migrations.py`** — 14+ tests covering: migration applies events table, migration applies all 8 tables, idempotency (double apply), _migrations tracking, checksum tamper detection, per-table column verification (events, aggregate_seq, steps, slices, concepts), all 6 indexes exist, events round-trip, all 6 cascade tables round-trip
- `_isolate_db_path` fixture protects real database from test writes
- All tests pass with `pytest -v`
- ruff + mypy clean
</must_haves>
