"""Tests for state_core.projector — Projector + projection handlers.

Covers: per-event-type projection for all 19 handlers, multi-event replay,
full rebuild, rebuild idempotency, crash-atomicity rollback, empty event log,
unknown event type tolerance, and Hypothesis property tests for determinism.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.projector import HANDLERS, Projector

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


# ── Helpers ────────────────────────────────────────────────────────────────


async def _append_events(
    store: SqliteEventStore,
    events: list[tuple[str, str, str, dict[str, Any]]],
) -> list[str]:
    """Append multiple events and return their IDs.

    Each tuple is (aggregate_type, aggregate_id, event_type, data).
    """
    ids: list[str] = []
    for aggregate_type, aggregate_id, event_type, data in events:
        id_ = await store.append(
            aggregate_type, aggregate_id, event_type, data,
        )
        ids.append(id_)
    return ids


async def _read_table(table: str) -> list[dict[str, Any]]:
    """Return all rows from a cache table as dicts with JSON-typed columns parsed."""
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(f"SELECT * FROM {table} ORDER BY id")
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("frontmatter"), str):
                d["frontmatter"] = json.loads(d["frontmatter"])
            result.append(d)
        return result
