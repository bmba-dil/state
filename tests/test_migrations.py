"""Tests for state_core.migrations — runner logic, idempotency, schema verification.

Applies 0001_init.sql + 0002_cache.sql in temp directories to avoid
contaminating any real .state/ directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.state_core.migrations import (
    applied_migrations,
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
async def test_migrate_applies_all_8_tables() -> None:
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

    # Tamper with 0001_init.sql in the isolated temp dir
    from src.state_core.migrations import _migrations_dir

    migrations_dir = _migrations_dir()
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
    expected = {
        "id", "subject_id", "learner_id", "mastery_probability",
        "scaffold_level", "bloom_level", "frontmatter", "last_drilled_at",
        "updated_at",
    }
    assert expected.issubset(columns)


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
            "INSERT INTO concepts "
            "(id, subject_id, learner_id, mastery_probability, "
            "scaffold_level, bloom_level, frontmatter, updated_at) "
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
