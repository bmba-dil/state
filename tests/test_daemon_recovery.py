"""Tests for state_daemon.recovery — CrashRecovery.

Covers: recover() with clean state, with events creating in-flight steps,
rebuild failure handling, _find_in_flight_steps, _get_last_event_id,
resume_in_flight edge cases, and RecoveryResult dataclass.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.projector import Projector
from src.state_daemon.recovery import CrashRecovery, InFlightStep, RecoveryResult

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_opencode_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:0")


@pytest.fixture
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


@pytest.fixture
def projector(store: SqliteEventStore) -> Projector:
    """Return a Projector backed by the isolated store."""
    return Projector(store)


@pytest.fixture
def recovery(projector: Projector) -> CrashRecovery:
    """Return a CrashRecovery instance backed by the isolated projector."""
    return CrashRecovery(projector)


# ── Helpers ────────────────────────────────────────────────────────────────


async def _append_step_event(
    store: SqliteEventStore,
    step_id: str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> str:
    """Append a step event and return its ULID."""
    return await store.append(
        aggregate_type="step",
        aggregate_id=step_id,
        event_type=event_type,
        data=data or {},
    )


async def _seed_executing_step(
    store: SqliteEventStore, step_id: str = "step-abc-1",
) -> tuple[str, str]:
    """Seed a step through discussed → planned → executed to reach 'executing' state.

    Must also rebuild projections so the steps cache table is populated.
    Returns (step_id, last_event_id).
    """
    events: list[str] = []
    events.append(
        await _append_step_event(
            store, step_id, "state.step.discussed",
            {"slice_id": "slice-1", "approach_summary": "test step"},
        ),
    )
    events.append(
        await _append_step_event(
            store, step_id, "state.step.planned",
            {"slice_id": "slice-1"},
        ),
    )
    events.append(
        await _append_step_event(
            store, step_id, "state.step.executed",
            {"slice_id": "slice-1", "changes_summary": "executed"},
        ),
    )
    return step_id, events[-1]


async def _seed_verifying_step(
    store: SqliteEventStore, step_id: str = "step-xyz-2",
) -> tuple[str, str]:
    """Seed a step through discussed → planned → executed → verify_started.

    Returns (step_id, last_event_id).
    """
    events: list[str] = []
    events.append(
        await _append_step_event(
            store, step_id, "state.step.discussed",
            {"slice_id": "slice-2", "approach_summary": "verify step"},
        ),
    )
    events.append(
        await _append_step_event(
            store, step_id, "state.step.planned",
            {"slice_id": "slice-2"},
        ),
    )
    events.append(
        await _append_step_event(
            store, step_id, "state.step.executed",
            {"slice_id": "slice-2", "changes_summary": "done"},
        ),
    )
    events.append(
        await _append_step_event(
            store, step_id, "state.step.verify_started",
            {"slice_id": "slice-2"},
        ),
    )
    return step_id, events[-1]


# ── RecoveryResult Dataclass ──────────────────────────────────────────────


class TestRecoveryResult:
    """RecoveryResult dataclass field defaults."""

    def test_defaults(self) -> None:
        result = RecoveryResult(events_replayed=0)
        assert result.events_replayed == 0
        assert result.in_flight_steps == []
        assert result.projection_valid is True
        assert result.last_event_id is None

    def test_full_fields(self) -> None:
        result = RecoveryResult(
            events_replayed=42,
            in_flight_steps=["s1", "s2"],
            projection_valid=True,
            last_event_id="01JABCDEFGH",
        )
        assert result.events_replayed == 42
        assert result.in_flight_steps == ["s1", "s2"]
        assert result.projection_valid is True
        assert result.last_event_id == "01JABCDEFGH"


# ── Recovery: Clean State (No Events) ─────────────────────────────────────


@pytest.mark.asyncio
class TestRecoverCleanState:
    """Recovery when the event store is empty."""

    async def test_clean_state_noop(
        self, recovery: CrashRecovery,
    ) -> None:
        result = await recovery.recover()
        assert result.events_replayed == 0
        assert result.in_flight_steps == []
        assert result.projection_valid is True
        assert result.last_event_id is None

    async def test_clean_state_no_events_no_steps(
        self, recovery: CrashRecovery,
    ) -> None:
        """Empty event store → zero events, zero in-flight steps."""
        result = await recovery.recover()
        assert result.events_replayed == 0
        assert len(result.in_flight_steps) == 0

    async def test_last_event_id_none_on_empty_store(
        self, recovery: CrashRecovery,
    ) -> None:
        """Empty store yields None bookmark."""
        result = await recovery.recover()
        assert result.last_event_id is None


# ── Recovery: With Events ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRecoverWithEvents:
    """Recovery when the event store has data."""

    async def test_rebuild_replays_events(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """After seeding events, rebuild_all replays them and returns count."""
        await _seed_executing_step(store, "step-a")
        await _seed_verifying_step(store, "step-b")

        # Rebuild projections so events are in cache
        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        # Should have replayed all events
        assert result.events_replayed >= 3  # at least the events we seeded
        assert result.projection_valid is True

    async def test_detect_executing_step(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """An executing step is detected as in-flight."""
        step_id, _ = await _seed_executing_step(store, "step-exec-1")

        # Rebuild to populate cache
        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        assert step_id in result.in_flight_steps

    async def test_detect_verifying_step(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """A verifying step is detected as in-flight."""
        step_id, _ = await _seed_verifying_step(store, "step-verify-1")

        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        assert step_id in result.in_flight_steps

    async def test_detect_both_statuses(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Both executing and verifying steps are in the in-flight list."""
        exec_id, _ = await _seed_executing_step(store, "step-e")
        verify_id, _ = await _seed_verifying_step(store, "step-v")

        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        assert exec_id in result.in_flight_steps
        assert verify_id in result.in_flight_steps
        assert len(result.in_flight_steps) == 2

    async def test_completed_steps_not_in_flight(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Steps that finished (verify_passed → 'done') are NOT in-flight."""
        # Execute → verify_started → verify_passed = done
        step_id = "step-done-1"
        await _append_step_event(
            store, step_id, "state.step.discussed",
            {"slice_id": "s1", "approach_summary": "done step"},
        )
        await _append_step_event(
            store, step_id, "state.step.planned",
            {"slice_id": "s1"},
        )
        await _append_step_event(
            store, step_id, "state.step.executed",
            {"slice_id": "s1", "changes_summary": "done"},
        )
        await _append_step_event(
            store, step_id, "state.step.verify_started",
            {"slice_id": "s1"},
        )
        await _append_step_event(
            store, step_id, "state.step.verify_passed",
            {"slice_id": "s1", "duration_ms": 100},
        )

        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        assert step_id not in result.in_flight_steps

    async def test_last_event_id_is_set(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Recovery bookmark reflects the last event ULID."""
        _, last_id = await _seed_executing_step(store, "step-bm-1")

        prj = Projector(store)
        await prj.rebuild_all()

        result = await recovery.recover()
        assert result.last_event_id is not None
        # The last event ULID should be one of the events we appended
        assert result.last_event_id == last_id


# ── InFlightStep Dataclass ────────────────────────────────────────────────


class TestInFlightStep:
    """InFlightStep dataclass."""

    def test_defaults(self) -> None:
        step = InFlightStep(step_id="s1", status="executing")
        assert step.step_id == "s1"
        assert step.status == "executing"
        assert step.slice_id is None
        assert step.title is None

    def test_full(self) -> None:
        step = InFlightStep(
            step_id="s2", status="verifying",
            slice_id="sl-1", title="My Step",
        )
        assert step.step_id == "s2"
        assert step.status == "verifying"
        assert step.slice_id == "sl-1"
        assert step.title == "My Step"


# ── Resume Logic ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestResumeInFlight:
    """resume_in_flight behaviour."""

    async def test_empty_list_noop(
        self, recovery: CrashRecovery,
    ) -> None:
        result = await recovery.resume_in_flight([])
        assert result == []

    async def test_single_step_resumed(
        self, recovery: CrashRecovery,
    ) -> None:
        steps = [InFlightStep(step_id="s1", status="executing")]
        result = await recovery.resume_in_flight(steps)
        assert result == ["s1"]

    async def test_multiple_steps_resumed(
        self, recovery: CrashRecovery,
    ) -> None:
        steps = [
            InFlightStep(step_id="s1", status="executing"),
            InFlightStep(step_id="s2", status="verifying"),
        ]
        result = await recovery.resume_in_flight(steps)
        assert result == ["s1", "s2"]


# ── Rebuild Failure Handling ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestRebuildFailure:
    """Crash recovery handles projector rebuild failures gracefully."""

    async def test_rebuild_failure_returns_invalid(
        self, store: SqliteEventStore,
    ) -> None:
        """When rebuild_all raises, recovery returns projection_valid=False."""
        # Create a projector that will fail on rebuild_all
        class FailingProjector:
            async def rebuild_all(self) -> int:
                raise RuntimeError("simulated corruption")

        recovery = CrashRecovery(FailingProjector())
        result = await recovery.recover()
        assert result.events_replayed == 0
        assert result.in_flight_steps == []
        assert result.projection_valid is False
        assert result.last_event_id is None
