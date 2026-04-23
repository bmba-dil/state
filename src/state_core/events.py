"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture.

Uses database.py for connection factory (WAL mode, synchronous=NORMAL).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

import aiosqlite

from src.state_core.database import get_connection


class EventStore(Protocol):
    """Protocol for writing and reading domain events."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> str: ...

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]: ...


class SqliteEventStore:
    """Concrete EventStore backed by events.sqlite via database.py."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> str:
        """Append an event row and return its id.

        NOTE: This is a stub for Phase 003. Per-aggregate seq enforcement,
        ULID generation, and commit-then-emit logic will be added in Phase 004.
        """
        raise NotImplementedError("append() is implemented in Phase 004")

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]:
        """Read events for an aggregate, ordered by seq, starting after_seq.

        Yields event rows as dicts.
        """
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, synced_to_opencode "  # noqa: E501
                "FROM events "
                "WHERE aggregate_id = ? AND seq > ? "
                "ORDER BY seq ASC",
                (aggregate_id, after_seq),
            )
            rows = await cursor.fetchall()
            for row in rows:
                yield dict(row)
