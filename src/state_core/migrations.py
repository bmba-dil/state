"""Numbered SQL migration runner.

Scans .state/migrations/ for 0001_*.sql, 0002_*.sql, etc.
Tracks applied migrations in the _migrations meta-table.
Applies unapplied migrations in filename order on each call to migrate().
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


def _migrations_dir() -> Path:
    """Return the migrations directory path relative to the database."""
    from src.state_core.database import get_db_path

    return get_db_path().parent / "migrations"


async def ensure_meta_table(db: aiosqlite.Connection) -> None:
    """Create the _migrations tracking table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            filename    TEXT PRIMARY KEY,
            checksum    TEXT NOT NULL,
            applied_at  TEXT NOT NULL  -- ISO 8601 UTC
        )
    """)


async def applied_migrations(db: aiosqlite.Connection) -> set[str]:
    """Return the set of already-applied migration filenames."""
    cursor = await db.execute("SELECT filename FROM _migrations ORDER BY filename")
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def _checksum(path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def migrate() -> None:
    """Apply all unapplied migrations in filename order.

    Safe to call multiple times -- already-applied migrations are skipped.
    Raises RuntimeError if a previously-applied migration's checksum changes.
    """
    from src.state_core.database import get_connection

    migrations_dir = _migrations_dir()
    migrations_dir.mkdir(parents=True, exist_ok=True)

    migration_files = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))

    async with get_connection() as db:
        await ensure_meta_table(db)
        applied = await applied_migrations(db)

        for mf in migration_files:
            cs = await _checksum(mf)

            if mf.name in applied:
                # Verify checksum hasn't changed (tamper / accidental edit detection)
                cursor = await db.execute(
                    "SELECT checksum FROM _migrations WHERE filename = ?", (mf.name,)
                )
                row = await cursor.fetchone()
                if row and row[0] != cs:
                    raise RuntimeError(
                        f"Migration {mf.name} checksum changed: "
                        f"expected {row[0]}, got {cs}. "
                        f"Already-applied migrations must not be modified."
                    )
                continue

            sql = mf.read_text()
            await db.executescript(sql)
            await db.execute(
                "INSERT INTO _migrations (filename, checksum, applied_at) "
                "VALUES (?, ?, datetime('now'))",
                (mf.name, cs),
            )
            await db.commit()
            logger.info("Applied migration: %s", mf.name)
