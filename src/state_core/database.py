"""Async SQLite connection factory with WAL mode, synchronous=FULL, path resolution.

Every daemon connection goes through this module to enforce:
- WAL journal mode (PRAGMA journal_mode=WAL)
- synchronous = FULL (fsync on every commit — crash-safe default)
- Configurable path via STATE_DB_PATH env var, defaulting to .state/events.sqlite

Belt-and-suspenders pattern
----------------------------
The connection default is synchronous=FULL. Critical writer methods in
``events.py`` (``append()``, ``repair_aggregate_seqs()``) also set
``PRAGMA synchronous=FULL`` inline as defense-in-depth, so even if the
default ever changes, those hot paths remain fsync-safe.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


def _resolve_db_path() -> Path:
    """Resolve the database file path.

    Priority:
    1. STATE_DB_PATH environment variable
    2. `.state/events.sqlite` relative to project root
    """
    env_path = os.environ.get("STATE_DB_PATH")
    if env_path:
        return Path(env_path).resolve()
    return Path.cwd() / ".state" / "events.sqlite"


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection to the event store with WAL + synchronous=FULL.

    Ensures the parent directory exists, then opens the database
    and applies the required pragmas on every connection open.

    Yields:
        An aiosqlite.Connection with WAL mode and synchronous=FULL.
    """
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=FULL;")
        yield db


def get_db_path() -> Path:
    """Return the resolved database path without opening a connection."""
    return _resolve_db_path()
