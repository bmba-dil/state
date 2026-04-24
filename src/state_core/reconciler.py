"""Startup reconciliation — unsent-event replay to opencode.

On daemon start (and periodically every 60s), query all unsent events
(synced_to_opencode=0) and deliver them one-by-one via
SyncEventMirror.emit(). Exponential backoff handles opencode-unreachable.
"""

from __future__ import annotations

import asyncio
import contextlib

import structlog

from src.state_core.events import SqliteEventStore
from src.state_core.sync_mirror import SyncEventMirror

log = structlog.get_logger(__name__)

BACKOFF_INITIAL: float = 1.0
BACKOFF_MULTIPLIER: float = 2.0
BACKOFF_MAX: float = 60.0
CONSECUTIVE_FAILURES_WARN_THRESHOLD: int = 10


class StartupReconciler:
    """Reconcile unsent events on startup and periodically thereafter.

    Args:
        db: The event store for querying unsynced events.
        mirror: The SyncEventMirror for emitting individual events.
        sweep_interval: Seconds between periodic sweep ticks when idle.
    """

    def __init__(
        self,
        db: SqliteEventStore,
        mirror: SyncEventMirror,
        sweep_interval: float = 60.0,
    ) -> None:
        self._db = db
        self._mirror = mirror
        self._sweep_interval = sweep_interval
        self._task: asyncio.Task[None] | None = None
        self._consecutive_failures = 0

    async def start(self) -> None:
        """Run immediate reconciliation, then start periodic sweep.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._task is not None:
            log.debug("reconciler already started — no-op")
            return
        await self._reconcile_once()
        self._task = asyncio.create_task(self._sweep_loop())

    async def stop(self) -> None:
        """Cancel the periodic sweep task.

        Safe to call multiple times. Events remain unsent in the DB.
        """
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
            log.debug("reconciler stopped")

    async def _reconcile_once(self) -> int:
        """Single reconciliation pass — emit all unsent events.

        Returns:
            Number of events emitted.
        """
        events = await self._db.get_unsynced_events()
        if not events:
            return 0
        count = 0
        any_succeeded = False
        for event_row in events:
            ok = await self._mirror.emit(event_row)
            if ok:
                count += 1
                any_succeeded = True
        if any_succeeded:
            self._consecutive_failures = 0
        return count

    async def _sweep_loop(self) -> None:
        """Periodic sweep loop with idle suppression and exponential backoff.

        Uses ``_reconcile_once()``'s return value (events emitted) rather than
        a post-reconcile ``count_unsynced_events()`` to decide whether to
        increment the backoff counter. This prevents inflation when Phase 005
        adds new events during reconciliation — a zero-emit pass while unsent
        events remain is the only signal that opencode is unreachable.
        """
        while True:
            remaining = await self._db.count_unsynced_events()
            if remaining == 0:
                self._consecutive_failures = 0
                await asyncio.sleep(self._sweep_interval)
                continue

            emitted = await self._reconcile_once()

            if emitted > 0:
                self._consecutive_failures = 0
                await asyncio.sleep(self._sweep_interval)
                continue

            self._consecutive_failures += 1
            if self._consecutive_failures >= CONSECUTIVE_FAILURES_WARN_THRESHOLD:
                log.warning(
                    "reconciler consecutive failures",
                    count=self._consecutive_failures,
                )

            delay = self._compute_backoff_delay()
            await asyncio.sleep(delay)

    def _compute_backoff_delay(self) -> float:
        """Compute exponential backoff delay based on consecutive failures.

        The sweep loop increments ``_consecutive_failures`` before calling
        this method, so the first failure (count=1) yields a 1-second delay:
        ``BACKOFF_INITIAL * BACKOFF_MULTIPLIER^0 = 1.0``.

        Returns:
            Delay in seconds, capped at BACKOFF_MAX (60.0).
        """
        return min(
            BACKOFF_INITIAL * (BACKOFF_MULTIPLIER ** (self._consecutive_failures - 1)),
            BACKOFF_MAX,
        )
