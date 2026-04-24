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
async def test_connection_synchronous_full(tmp_path: Path) -> None:
    """Connection has synchronous=FULL."""
    db_path = tmp_path / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("PRAGMA synchronous")
            row = await cursor.fetchone()
            assert row is not None
            sync_val = int(row[0])
            # 1 = NORMAL, 2 = FULL
            assert sync_val == 2, f"Expected FULL (2), got {sync_val}"
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
            keys = list(row.keys())
            assert "col_a" in keys
            assert "col_b" in keys
    finally:
        os.environ.pop("STATE_DB_PATH", None)
