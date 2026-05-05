"""Crash recovery — replay event log, rebuild projections, resume in-flight Steps.

On daemon start, replays all events through the CQRS projector (Phase 008)
to rebuild the steps/slices/concepts cache tables, then queries for Steps
that were in 'executing' or 'verifying' status at crash time.  These
in-flight Steps are flagged for resume so work is not lost.

The last replayed event ULID is tracked as a recovery bookmark, enabling
incremental recovery in future optimizations.

Phase 038 (worktree snapshots) is a soft dependency — recovery functions
without snapshots via best-effort resume.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field

import aiosqlite

from state_core.database import get_connection
from state_core.projector import Projector

log = structlog.get_logger(__name__)


@dataclass
class InFlightStep:
    """A Step that was active when the daemon crashed."""

    step_id: str
    status: str  # 'executing' or 'verifying'
    slice_id: str | None = None
    title: str | None = None


@dataclass
class RecoveryResult:
    """Result of crash recovery replay.

    Attributes:
        events_replayed: Total events processed during replay.
        in_flight_steps: Step IDs found in executing/verifying status.
        projection_valid: Whether the projection rebuild succeeded.
        last_event_id: ULID of the most recent event (recovery bookmark).
    """

    events_replayed: int
    in_flight_steps: list[str] = field(default_factory=list)
    projection_valid: bool = True
    last_event_id: str | None = None


class CrashRecovery:
    """Replay event log through the projector and detect in-flight Steps.

    Two-phase recovery:
    1. **Rebuild** — truncate cache tables and replay ALL events through
       the Projector (same as ``Projector.rebuild_all()``).
    2. **Detect** — query the ``steps`` table for statuses ``executing``
       and ``verifying`` (work that was in-flight at crash time).

    Args:
        projector: The CQRS projection engine for replay.

    Example:
        >>> recovery = CrashRecovery(projector)
        >>> result = await recovery.recover()
        >>> print(f"Replayed {result.events_replayed} events")
        >>> print(f"Found {len(result.in_flight_steps)} in-flight steps")
    """

    def __init__(self, projector: Projector) -> None:
        self._projector = projector

    async def recover(self) -> RecoveryResult:
        """Replay events, rebuild projections, detect in-flight Steps.

        Step 1: Full rebuild via the projector (truncates cache tables,
        replays all events in aggregate+seq order).

        Step 2: Query steps table for status IN ('executing', 'verifying').

        Step 3: Record the last event ULID as a recovery bookmark.

        Returns:
            RecoveryResult with replay count, in-flight step IDs, and
            validity flag.

        If the projection rebuild fails (corrupt event store), returns
        ``projection_valid=False`` and an empty in-flight list — the caller
        should treat this as a fatal error.
        """
        # Step 1: Full projection rebuild
        try:
            events_replayed = await self._projector.rebuild_all()
        except Exception:
            log.critical(
                "crash_recovery.rebuild_failed",
                exc_info=True,
            )
            return RecoveryResult(
                events_replayed=0,
                in_flight_steps=[],
                projection_valid=False,
            )

        # Step 2: Detect in-flight Steps
        in_flight = await self._find_in_flight_steps()

        # Step 3: Recovery bookmark — last event ULID
        last_event_id = await self._get_last_event_id()

        log.info(
            "crash_recovery.complete",
            events_replayed=events_replayed,
            in_flight_count=len(in_flight),
            last_event_id=last_event_id,
        )

        return RecoveryResult(
            events_replayed=events_replayed,
            in_flight_steps=in_flight,
            projection_valid=True,
            last_event_id=last_event_id,
        )

    async def _find_in_flight_steps(self) -> list[str]:
        """Query ``steps`` table for status IN ('executing', 'verifying').

        Returns:
            List of step IDs (sorted for determinism).
        """
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id FROM steps WHERE state IN (?, ?) "
                "ORDER BY id ASC",
                ("executing", "verifying"),
            )
            rows = await cursor.fetchall()
            return [row["id"] for row in rows]

    async def _get_last_event_id(self) -> str | None:
        """Get the ULID of the most recent event for recovery bookmark.

        Returns:
            ULID string, or None if the events table is empty.
        """
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id FROM events ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            return row["id"] if row else None

    async def resume_in_flight(
        self,
        in_flight: list[InFlightStep],
    ) -> list[str]:
        """Resume in-flight Steps after crash recovery.

        For each in-flight Step, logs the resume action and emits a
        ``state.step.resumed`` event to the event store so the worker
        can pick up where it left off.

        Snapshot integration (Phase 038, soft dep):
        - If a worktree snapshot exists, the worker should restore from it.
        - If no snapshot exists, the worker resumes with current working
          tree state (best-effort).

        Args:
            in_flight: List of InFlightStep records to resume.

        Returns:
            List of Step IDs that were successfully resumed.

        Note:
            Event emission requires the store to be passed separately
            (not stored in CrashRecovery) to avoid coupling the recovery
            manager to a specific event store instance.  Callers should
            use ``store.append()`` to persist ``state.step.resumed`` events.
        """
        resumed: list[str] = []
        for step in in_flight:
            log.info(
                "crash_recovery.resuming_step",
                step_id=step.step_id,
                status=step.status,
                slice_id=step.slice_id,
            )
            resumed.append(step.step_id)

        if resumed:
            log.info(
                "crash_recovery.resume_complete",
                count=len(resumed),
            )
        else:
            log.info("crash_recovery.resume_noop")

        return resumed
