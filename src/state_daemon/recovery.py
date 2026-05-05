"""Crash recovery — replay event log, rebuild projections, resume in-flight Steps.

On daemon start, replays all events through the CQRS projector (Phase 008)
to rebuild the steps/slices/concepts cache tables, then queries for Steps
that were in 'executing' or 'verifying' status at crash time.  These
in-flight Steps are resumed: ``state.step.resumed`` events are emitted to
the event store so the worker agent can pick up where it left off.

The last replayed event ULID is tracked as a recovery bookmark, enabling
incremental recovery in future optimizations.

Phase 038 (worktree snapshots) is a soft dependency — recovery functions
without snapshots via best-effort resume.
"""

from __future__ import annotations

import os
import structlog
from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite

from state_core.database import get_connection
from state_core.events import SqliteEventStore
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
class ResumeAction:
    """Result of resuming a single in-flight Step.

    Attributes:
        step_id: The Step that was resumed.
        status: Pre-crash status ('executing' or 'verifying').
        snapshot_available: Whether a worktree snapshot was found
            for this step (Phase 038 soft dep).
    """

    step_id: str
    status: str
    snapshot_available: bool = False


def _check_snapshot(snapshot_root: Path, step_id: str) -> bool:
    """Check whether a worktree snapshot directory exists for *step_id*.

    Snapshots are expected at ``{snapshot_root}/{step_id}/``.
    This is a best-effort check — the snapshot directory may exist
    but be incomplete.  The worker agent handles the actual restore.

    Args:
        snapshot_root: Root directory for snapshots.
        step_id: The step ID to look up.

    Returns:
        True if a subdirectory exists for this step, False otherwise.
    """
    snapshot_dir = snapshot_root / step_id
    if snapshot_dir.is_dir():
        log.debug(
            "crash_recovery.snapshot_found",
            step_id=step_id,
            path=str(snapshot_dir),
        )
        return True
    log.debug(
        "crash_recovery.snapshot_not_found",
        step_id=step_id,
    )
    return False


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
        store: SqliteEventStore,
        in_flight: list[InFlightStep],
        *,
        snapshot_root: str | Path | None = None,
    ) -> list[ResumeAction]:
        """Resume in-flight Steps after crash recovery.

        For each in-flight Step:

        1. Checks for a worktree snapshot (Phase 038, soft dep):
           if ``snapshot_root`` is provided and a snapshot subdirectory
           exists for the step, the worker should restore from it.
           Otherwise, resume with bare working tree state.
        2. Emits a ``state.step.resumed`` event to the event store with
           the pre-crash status and snapshot availability so the worker
           agent can pick up where it left off.

        Args:
            store: The event store for emitting ``state.step.resumed`` events.
            in_flight: InFlightStep records to resume (pre-crash status).
            snapshot_root: Root directory for worktree snapshots
                (defaults to ``.state/snapshots``).  If a subdirectory
                matching the step ID exists, a snapshot is available.

        Returns:
            List of ResumeAction records describing the outcome for
            each resumed step.

        Raises:
            RuntimeError: If event emission fails for any step (the caller
                should treat this as a fatal error — the event store may
                be corrupt).
        """
        if snapshot_root is None:
            snapshot_root = Path(os.getcwd()) / ".state" / "snapshots"
        elif isinstance(snapshot_root, str):
            snapshot_root = Path(snapshot_root)
        # Ensure snapshot_root is Path from here on
        snapshot_root = snapshot_root  # type: Path

        actions: list[ResumeAction] = []
        for step in in_flight:
            snapshot_available = _check_snapshot(snapshot_root, step.step_id)

            log.info(
                "crash_recovery.resuming_step",
                step_id=step.step_id,
                status=step.status,
                snapshot_available=snapshot_available,
            )

            try:
                await store.append(
                    aggregate_type="step",
                    aggregate_id=step.step_id,
                    event_type="state.step.resumed",
                    data={
                        "step_id": step.step_id,
                        "pre_crash_status": step.status,
                        "reason": "crash_recovery",
                        "snapshot_available": snapshot_available,
                    },
                )
            except Exception:
                log.critical(
                    "crash_recovery.resume_event_failed",
                    step_id=step.step_id,
                    exc_info=True,
                )
                raise

            actions.append(ResumeAction(
                step_id=step.step_id,
                status=step.status,
                snapshot_available=snapshot_available,
            ))

        if actions:
            log.info(
                "crash_recovery.resume_complete",
                count=len(actions),
                executing=sum(1 for a in actions if a.status == "executing"),
                verifying=sum(1 for a in actions if a.status == "verifying"),
                with_snapshot=sum(1 for a in actions if a.snapshot_available),
            )
        else:
            log.info("crash_recovery.resume_noop")

        return actions
