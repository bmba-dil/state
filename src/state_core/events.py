"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture.

Uses database.py for connection factory (WAL mode, synchronous=FULL).
Phase 004: full append() with ULID generation, per-aggregate seq enforcement,
deterministic JSON serialization, mode storage, single-transaction commit.
Phase 007: fsync discipline (synchronous=FULL default + belt-and-suspenders),
run_repair flag with lazy _maybe_repair on all read/write/count methods,
UNIQUE(aggregate_id, seq) index migration 0004.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import aiosqlite
import structlog
from ulid import ULID

from src.state_core.database import get_connection
from src.state_core.schema import Mode
from src.state_core.sync_mirror import SyncEventMirror

log = structlog.get_logger(__name__)


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

    async def read_events(
        self,
        *,
        from_id: str | None = None,
        to_id: str | None = None,
        mode: str | None = None,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    async def read_events_iter(
        self,
        *,
        from_id: str | None = None,
        to_id: str | None = None,
        mode: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...

    async def count_events(
        self,
        *,
        mode: str | None = None,
    ) -> int:
        ...

    async def get_last_events(
        self,
        count: int = 10,
        *,
        mode: str | None = None,
    ) -> list[dict[str, Any]]:
        ...


class SqliteEventStore:
    """Concrete EventStore backed by events.sqlite via database.py.

    Startup ordering: repair() -> migrate() -> reconciler(). Repair must
    run BEFORE migration 0004 to clean duplicate seq values, otherwise
    UNIQUE index creation will fail. This is enforced by daemon startup
    calling run_repair_now() before migrate().

    **Phase 006 integration:** The StartupReconciler MUST NOT read seq
    values until repair completes. This is enforced by daemon startup
    calling run_repair_now() before migrate(), which runs before the
    reconciler's first sweep.
    """

    def __init__(self, run_repair: bool = False) -> None:
        """Initialize the event store.

        Args:
            run_repair: Reserved for future use. Currently, repair runs
                lazily on first append()/read_stream() or immediately
                when run_repair_now() is called. Defaults to False.
        """
        self._repair_done = False

    async def _maybe_repair(self, source: str = "unknown") -> None:
        """Run repair once per session if not yet done.

        Safe to call multiple times — the _repair_done flag ensures
        repair_aggregate_seqs() is called at most once.

        Args:
            source: Description of what triggered the repair (e.g.
                'append', 'read_stream', 'run_repair_now').
        """
        if not self._repair_done:
            log.info("repair_triggered", source=source)
            repairs = await self.repair_aggregate_seqs()
            self._repair_done = True
            if repairs:
                log.info("repair_completed", count=len(repairs))

    async def run_repair_now(self) -> list[dict[str, Any]]:
        """Force repair immediately, regardless of _repair_done state.

        Called by daemon startup BEFORE migrate() to ensure seq values
        are consistent before migration 0004 creates the UNIQUE index.

        Returns:
            List of repair dicts from repair_aggregate_seqs().
        """
        log.info("repair_forced")
        repairs = await self.repair_aggregate_seqs()
        self._repair_done = True
        log.info("repair_forced_complete", count=len(repairs))
        return repairs

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
        await self._maybe_repair(source="append")

        if id_ is None:
            id_ = str(ULID())
        if ts is None:
            ts = "2026-01-01T00:00:00Z"

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
        await self._maybe_repair(source="read_stream")

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

    async def get_unsynced_events(self) -> list[dict[str, Any]]:
        """Return all events not yet synced to opencode, ordered by id (ULID = time-ordered).

        Loaded entirely into memory. At ~2KB per row, 10k events consume
        ~20MB. If memory proves problematic, add pagination (LIMIT/OFFSET).

        Returns:
            List of event row dicts with keys: id, aggregate_id, seq,
            type, data (deserialized from JSON), mode, ts.
        """
        await self._maybe_repair(source="get_unsynced_events")

        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, aggregate_id, seq, type, data, mode, ts "
                "FROM events "
                "WHERE synced_to_opencode = 0 "
                "ORDER BY id ASC"
            )
            rows = await cursor.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                d = dict(row)
                if isinstance(d.get("data"), str):
                    d["data"] = json.loads(d["data"])
                result.append(d)
            return result

    async def repair_aggregate_seqs(self) -> list[dict[str, Any]]:
        """Detect and repair gaps/duplicates in the *aggregate_seq* table.

        Scans ``events`` for the max seq per aggregate and updates
        ``aggregate_seq`` when a mismatch is found. This is the post-crash
        recovery routine for P0-9 — after a crash with WAL corruption, the
        ``aggregate_seq`` table may trail behind (or race ahead of) the
        committed events.

        Safe to call at any time (idempotent — no-op when already
        consistent). The daemon should invoke this on startup, before
        any consumer reads seq values.

        Returns:
            A list of repair dicts (``aggregate_id``, ``old_seq``,
            ``new_seq``), one per repaired aggregate. Empty list when
            already consistent.
        """
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
                    direction = "stale" if current_seq < max_seq else "future"
                    log.info(
                        "repair_seq_correction",
                        aggregate_id=agg_id,
                        old_seq=current_seq,
                        new_seq=max_seq,
                        direction=direction,
                    )
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

            if not repairs:
                log.info("repair_noop")
            else:
                log.info("repair_summary", count=len(repairs))

            await db.commit()

        return repairs

    async def count_unsynced_events(self) -> int:
        """Return the count of events where synced_to_opencode = 0.

        Used as an idle suppression guard: if this returns 0, the sweep
        loop skips its work cycle entirely.
        """
        await self._maybe_repair(source="count_unsynced_events")

        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM events WHERE synced_to_opencode = 0"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def read_events(
        self,
        *,
        from_id: str | None = None,
        to_id: str | None = None,
        mode: str | None = None,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Read events with optional ULID offset, mode filter, and limit.

        Ordered by id ASC (lexicographic = chronological for ULIDs).
        Deserializes the *data* column from JSON text to a Python dict.

        Args:
            from_id: ULID offset (exclusive lower bound). Events with id > from_id.
            to_id: ULID offset (exclusive upper bound). Events with id < to_id.
            mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.
            limit: Max rows. 0 = no limit.

        Returns:
            List of event row dicts with keys: id, seq, aggregate_type,
            aggregate_id, type, data (deserialized), ts, mode.
        """
        await self._maybe_repair(source="read_events")

        clauses: list[str] = [
            "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
            "FROM events WHERE 1=1"
        ]
        params: list[Any] = []

        if from_id is not None:
            clauses.append("AND id > ?")
            params.append(from_id)
        if to_id is not None:
            clauses.append("AND id < ?")
            params.append(to_id)
        if mode is not None:
            clauses.append("AND mode = ?")
            params.append(mode)

        clauses.append("ORDER BY id ASC")

        if limit > 0:
            clauses.append("LIMIT ?")
            params.append(limit)

        sql = " ".join(clauses)

        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                d = dict(row)
                if isinstance(d.get("data"), str):
                    d["data"] = json.loads(d["data"])
                result.append(d)
            return result

    async def read_events_iter(
        self,
        *,
        from_id: str | None = None,
        to_id: str | None = None,
        mode: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Read events as an async generator — memory-safe for large volumes.

        Ordered by id ASC (lexicographic = chronological for ULIDs).
        Deserializes *data* from JSON text to a Python dict per row.

        Args:
            from_id: ULID offset (exclusive lower bound).
            to_id: ULID offset (exclusive upper bound).
            mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.
        """
        await self._maybe_repair(source="read_events_iter")

        clauses: list[str] = [
            "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
            "FROM events WHERE 1=1"
        ]
        params: list[Any] = []

        if from_id is not None:
            clauses.append("AND id > ?")
            params.append(from_id)
        if to_id is not None:
            clauses.append("AND id < ?")
            params.append(to_id)
        if mode is not None:
            clauses.append("AND mode = ?")
            params.append(mode)

        clauses.append("ORDER BY id ASC")
        sql = " ".join(clauses)

        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            while True:
                row = await cursor.fetchone()
                if row is None:
                    break
                d = dict(row)
                if isinstance(d.get("data"), str):
                    d["data"] = json.loads(d["data"])
                yield d

    async def count_events(self, *, mode: str | None = None) -> int:
        """Count events with optional mode filter.

        Args:
            mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.

        Returns:
            Total event count (optionally filtered by mode).
        """
        await self._maybe_repair(source="count_events")

        if mode is not None:
            sql = "SELECT COUNT(*) FROM events WHERE mode = ?"
            params: list[Any] = [mode]
        else:
            sql = "SELECT COUNT(*) FROM events"
            params = []

        async with get_connection() as db:
            cursor = await db.execute(sql, params)
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_last_events(
        self, count: int = 10, *, mode: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the last N events ordered by id DESC, then reversed to ASC.

        Args:
            count: Number of events to return. Defaults to 10.
            mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.

        Returns:
            List of up to *count* event dicts in id ASC order (oldest first
            within the window), with keys: id, seq, aggregate_type,
            aggregate_id, type, data (deserialized), ts, mode.
        """
        await self._maybe_repair(source="get_last_events")

        clauses: list[str] = [
            "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
            "FROM events WHERE 1=1"
        ]
        params: list[Any] = []

        if mode is not None:
            clauses.append("AND mode = ?")
            params.append(mode)

        clauses.append("ORDER BY id DESC LIMIT ?")
        params.append(count)

        sql = " ".join(clauses)

        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            result: list[dict[str, Any]] = []
            for row in reversed(rows):  # reverse to chronological order
                d = dict(row)
                if isinstance(d.get("data"), str):
                    d["data"] = json.loads(d["data"])
                result.append(d)
            return result
