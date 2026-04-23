"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture.

Uses database.py for connection factory (WAL mode, synchronous=NORMAL).
Phase 004: full append() with ULID generation, per-aggregate seq enforcement,
deterministic JSON serialization, mode storage, single-transaction commit.
"""

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


class EventStore(Protocol):
    """Protocol for writing and reading domain events."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
        *,
        mode: Mode = "kernel",
        ts: str | None = None,
        id_: str | None = None,
        mirror: SyncEventMirror | None = None,
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
        *,
        mode: Mode = "kernel",
        ts: str | None = None,
        id_: str | None = None,
        mirror: SyncEventMirror | None = None,
    ) -> str:
        """Append an event row with ULID generation and seq enforcement.

        Every call generates a new ULID *id_* (unless explicitly provided),
        reads and increments the per-aggregate sequence number, serializes
        *data* deterministically (sort_keys, compact separators), and commits
        atomically within a single transaction.

        If *mirror* is provided, a fire-and-forget task is scheduled after
        commit to POST the event to opencode's SyncEvent endpoint.

        Args:
            aggregate_type: Aggregate discriminator (e.g. 'step', 'arc').
            aggregate_id: ID of the aggregate instance.
            event_type: Event type string (e.g. 'state.step.verify_passed').
            data: Event-specific payload dict.
            mode: Execution mode (build, teach, or kernel). Defaults to kernel.
            ts: ISO 8601 timestamp. If None, uses a fixed epoch string for
                determinism during testing. Production callers should pass
                an explicit timestamp.
            id_: ULID for the event. If None, auto-generated from system time.
            mirror: Optional SyncEventMirror for fire-and-forget HTTP emission
                to opencode.

        Returns:
            The ULID string of the newly-inserted event.
        """
        if id_ is None:
            id_ = str(ULID())
        if ts is None:
            ts = "2026-01-01T00:00:00Z"

        async with get_connection() as db:
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
                (
                    id_,
                    seq,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    json.dumps(data, sort_keys=True, separators=(",", ":")),
                    ts,
                    mode,
                ),
            )

            await db.execute(
                "INSERT OR REPLACE INTO aggregate_seq (aggregate_id, seq, updated_at) "
                "VALUES (?, ?, ?)",
                (aggregate_id, seq, ts),
            )

            await db.commit()

        if mirror is not None:
            event_row: dict[str, Any] = {
                "id": id_,
                "seq": seq,
                "aggregate_id": aggregate_id,
                "type": event_type,
                "data": data,
                "ts": ts,
                "mode": mode,
            }
            asyncio.ensure_future(mirror.emit(event_row))

        return id_

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]:
        """Read events for an aggregate, ordered by seq, starting after_seq.

        Deserializes the *data* column from JSON text to a Python dict.
        Yields event rows as dicts.
        """
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode, synced_to_opencode "  # noqa: E501
                "FROM events "
                "WHERE aggregate_id = ? AND seq > ? "
                "ORDER BY seq ASC",
                (aggregate_id, after_seq),
            )
            rows = await cursor.fetchall()
            for row in rows:
                d = dict(row)
                if isinstance(d.get("data"), str):
                    d["data"] = json.loads(d["data"])
                yield d
