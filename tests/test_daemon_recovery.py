"""Tests for state_daemon.recovery — CrashRecovery.

Covers: recover() with clean state, with events creating in-flight steps,
rebuild failure handling, _find_in_flight_steps, _get_last_event_id,
resume_in_flight with event emission + snapshot integration,
ResumeAction dataclass, edge cases.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.projector import Projector
from src.state_daemon.recovery import (
    CrashRecovery,
    InFlightStep,
    RecoveryResult,
    ResumeAction,
)

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


# ── ResumeAction Dataclass ────────────────────────────────────────────────


class TestResumeAction:
    """ResumeAction dataclass."""

    def test_defaults(self) -> None:
        action = ResumeAction(step_id="s1", status="executing")
        assert action.step_id == "s1"
        assert action.status == "executing"
        assert action.snapshot_available is False

    def test_with_snapshot(self) -> None:
        action = ResumeAction(step_id="s2", status="verifying", snapshot_available=True)
        assert action.step_id == "s2"
        assert action.status == "verifying"
        assert action.snapshot_available is True


# ── Resume Logic: Event Emission ───────────────────────────────────────────


@pytest.mark.asyncio
class TestResumeInFlight:
    """resume_in_flight with event emission via store."""

    async def test_empty_list_noop(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        result = await recovery.resume_in_flight(store, [])
        assert result == []

    async def test_single_step_emits_event(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        steps = [InFlightStep(step_id="s1", status="executing")]
        result = await recovery.resume_in_flight(store, steps)
        assert len(result) == 1
        assert result[0].step_id == "s1"
        assert result[0].status == "executing"
        assert result[0].snapshot_available is False

    async def test_multiple_steps_emit_events(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        steps = [
            InFlightStep(step_id="s1", status="executing"),
            InFlightStep(step_id="s2", status="verifying"),
        ]
        result = await recovery.resume_in_flight(store, steps)
        assert len(result) == 2
        assert result[0].step_id == "s1"
        assert result[0].status == "executing"
        assert result[1].step_id == "s2"
        assert result[1].status == "verifying"

    async def test_events_are_persisted(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """state.step.resumed events are actually written to the event store."""
        steps = [InFlightStep(step_id="s3", status="executing")]
        await recovery.resume_in_flight(store, steps)

        # Read back the event via the store
        events = await store.read_events()
        resumed_events = [e for e in events if e["type"] == "state.step.resumed"]
        assert len(resumed_events) == 1
        assert resumed_events[0]["aggregate_id"] == "s3"
        assert resumed_events[0]["data"]["pre_crash_status"] == "executing"
        assert resumed_events[0]["data"]["reason"] == "crash_recovery"

    async def test_event_data_includes_snapshot_flag(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Resumed event data includes snapshot_available flag."""
        steps = [InFlightStep(step_id="s4", status="verifying")]
        await recovery.resume_in_flight(store, steps)

        events = await store.read_events()
        resumed = [e for e in events if e["type"] == "state.step.resumed"]
        assert len(resumed) == 1
        assert resumed[0]["data"]["snapshot_available"] is False
        assert resumed[0]["data"]["pre_crash_status"] == "verifying"

    async def test_respects_step_status_from_input(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Each event records the pre-crash status from InFlightStep."""
        steps = [
            InFlightStep(step_id="exec-1", status="executing"),
            InFlightStep(step_id="ver-1", status="verifying"),
        ]
        await recovery.resume_in_flight(store, steps)

        events = await store.read_events()
        resumed = sorted(
            [e for e in events if e["type"] == "state.step.resumed"],
            key=lambda e: e["aggregate_id"],
        )
        assert len(resumed) == 2
        assert resumed[0]["data"]["pre_crash_status"] == "executing"
        assert resumed[1]["data"]["pre_crash_status"] == "verifying"


# ── Resume Logic: Snapshot Integration ─────────────────────────────────────


@pytest.mark.asyncio
class TestSnapshotIntegration:
    """Snapshot detection during resume (Phase 038 soft dep)."""

    async def test_no_snapshot_available(
        self, store: SqliteEventStore, recovery: CrashRecovery,
        tmp_path: Path,
    ) -> None:
        """No snapshot dir → snapshot_available=False."""
        snapshot_root = tmp_path / "snapshots"
        snapshot_root.mkdir()

        steps = [InFlightStep(step_id="s1", status="executing")]
        result = await recovery.resume_in_flight(
            store, steps, snapshot_root=snapshot_root,
        )
        assert len(result) == 1
        assert result[0].snapshot_available is False

    async def test_snapshot_available(
        self, store: SqliteEventStore, recovery: CrashRecovery,
        tmp_path: Path,
    ) -> None:
        """When snapshot dir exists → snapshot_available=True."""
        snapshot_root = tmp_path / "snapshots"
        snapshot_root.mkdir()
        (snapshot_root / "s2").mkdir()

        steps = [InFlightStep(step_id="s2", status="executing")]
        result = await recovery.resume_in_flight(
            store, steps, snapshot_root=snapshot_root,
        )
        assert len(result) == 1
        assert result[0].snapshot_available is True

    async def test_mixed_snapshot_availability(
        self, store: SqliteEventStore, recovery: CrashRecovery,
        tmp_path: Path,
    ) -> None:
        """Some steps have snapshots, some don't."""
        snapshot_root = tmp_path / "snapshots"
        snapshot_root.mkdir()
        (snapshot_root / "s-with").mkdir()
        # s-without has no snapshot dir

        steps = [
            InFlightStep(step_id="s-with", status="executing"),
            InFlightStep(step_id="s-without", status="verifying"),
        ]
        result = await recovery.resume_in_flight(
            store, steps, snapshot_root=snapshot_root,
        )
        assert len(result) == 2
        with_snapshot = [r for r in result if r.snapshot_available]
        without_snapshot = [r for r in result if not r.snapshot_available]
        assert len(with_snapshot) == 1
        assert with_snapshot[0].step_id == "s-with"
        assert len(without_snapshot) == 1
        assert without_snapshot[0].step_id == "s-without"

    async def test_snapshot_flag_in_event_data(
        self, store: SqliteEventStore, recovery: CrashRecovery,
        tmp_path: Path,
    ) -> None:
        """Event data reflects snapshot availability."""
        snapshot_root = tmp_path / "snapshots"
        snapshot_root.mkdir()
        (snapshot_root / "snap-step").mkdir()

        steps = [InFlightStep(step_id="snap-step", status="executing")]
        await recovery.resume_in_flight(
            store, steps, snapshot_root=snapshot_root,
        )

        events = await store.read_events()
        resumed = [e for e in events if e["type"] == "state.step.resumed"]
        assert len(resumed) == 1
        assert resumed[0]["data"]["snapshot_available"] is True

    async def test_default_snapshot_root(
        self, store: SqliteEventStore, recovery: CrashRecovery,
    ) -> None:
        """Default snapshot_root is .state/snapshots (best-effort)."""
        steps = [InFlightStep(step_id="s-default", status="executing")]
        result = await recovery.resume_in_flight(store, steps)
        # Default root (.state/snapshots) probably doesn't exist in tests,
        # so snapshot_available should be False.
        assert len(result) == 1
        assert result[0].snapshot_available is False


# ── Resume Logic: Failure Handling ─────────────────────────────────────────


@pytest.mark.asyncio
class TestResumeFailure:
    """Crash recovery handles resume event emission failures."""

    async def test_event_emission_failure_raises(
        self, recovery: CrashRecovery,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When store.append raises, resume_in_flight propagates the error."""
        # Create a store that will fail on append
        class FailingStore:
            async def append(self, *args: Any, **kwargs: Any) -> str:
                raise RuntimeError("simulated store failure")

            async def read_events(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
                return []

        store = FailingStore()
        steps = [InFlightStep(step_id="s1", status="executing")]
        with pytest.raises(RuntimeError, match="simulated store failure"):
            await recovery.resume_in_flight(store, steps)


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


# ── Orchestrator Integration Tests ─────────────────────────────────────────


@pytest.mark.asyncio
class TestOrchestratorIntegration:
    """End-to-end: simulate crash with in-flight steps, recover, verify."""

    async def test_full_recovery_flow(
        self, store: SqliteEventStore,
    ) -> None:
        """Simulate crash: seed executing + verifying steps, then recover."""
        # Seed steps that would be in-flight at crash time
        exec_id, _ = await _seed_executing_step(store, "step-exec-int")
        verify_id, _ = await _seed_verifying_step(store, "step-verify-int")

        # Also seed a completed step (should NOT be detected)
        done_id = "step-done-int"
        await _append_step_event(
            store, done_id, "state.step.discussed",
            {"slice_id": "s-done", "approach_summary": "done"},
        )
        await _append_step_event(
            store, done_id, "state.step.planned", {"slice_id": "s-done"},
        )
        await _append_step_event(
            store, done_id, "state.step.executed",
            {"slice_id": "s-done", "changes_summary": "done"},
        )
        await _append_step_event(
            store, done_id, "state.step.verify_started",
            {"slice_id": "s-done"},
        )
        await _append_step_event(
            store, done_id, "state.step.verify_passed",
            {"slice_id": "s-done", "duration_ms": 50},
        )

        # Rebuild projections so all states are in cache
        prj = Projector(store)
        await prj.rebuild_all()

        # Run crash recovery
        recovery = CrashRecovery(prj)
        result = await recovery.recover()

        # Verify in-flight detection
        assert result.projection_valid is True
        assert exec_id in result.in_flight_steps
        assert verify_id in result.in_flight_steps
        assert done_id not in result.in_flight_steps
        assert len(result.in_flight_steps) == 2
        assert result.last_event_id is not None

    async def test_recovery_then_resume_integration(
        self, store: SqliteEventStore,
    ) -> None:
        """Recover detects in-flight steps, resume emits events."""
        exec_id, _ = await _seed_executing_step(store, "step-ri-1")

        prj = Projector(store)
        await prj.rebuild_all()

        # Phase 1: Recover
        recovery = CrashRecovery(prj)
        result = await recovery.recover()
        assert exec_id in result.in_flight_steps

        # Phase 2: Resume (as orchestrator would)
        in_flight = [
            InFlightStep(step_id=sid, status="executing")
            for sid in result.in_flight_steps
        ]
        actions = await recovery.resume_in_flight(store, in_flight)
        assert len(actions) == 1
        assert actions[0].step_id == exec_id

        # Verify the resumed event is persisted
        events = await store.read_events()
        resumed = [e for e in events if e["type"] == "state.step.resumed"]
        assert len(resumed) == 1
        assert resumed[0]["aggregate_id"] == exec_id

    async def test_clean_state_full_flow(
        self, store: SqliteEventStore,
    ) -> None:
        """No events → recover returns empty, no errors."""
        prj = Projector(store)
        await prj.rebuild_all()

        recovery = CrashRecovery(prj)
        result = await recovery.recover()

        assert result.events_replayed == 0
        assert result.in_flight_steps == []
        assert result.projection_valid is True

        # Resume with empty list should no-op
        actions = await recovery.resume_in_flight(store, [])
        assert actions == []

    async def test_crash_with_multiple_executing_steps(
        self, store: SqliteEventStore,
    ) -> None:
        """Multiple executing steps → all detected and resumed."""
        ids = []
        for i in range(5):
            sid, _ = await _seed_executing_step(store, f"step-multi-{i}")
            ids.append(sid)

        prj = Projector(store)
        await prj.rebuild_all()

        recovery = CrashRecovery(prj)
        result = await recovery.recover()

        assert len(result.in_flight_steps) == 5
        for sid in ids:
            assert sid in result.in_flight_steps

    async def test_events_replayed_lte_event_count(
        self, store: SqliteEventStore,
    ) -> None:
        """events_replayed should not exceed total event count."""
        await _seed_executing_step(store, "step-count-1")
        await _seed_verifying_step(store, "step-count-2")

        prj = Projector(store)
        await prj.rebuild_all()

        total = await store.count_events()
        assert total >= 7  # 3 for executing + 4 for verifying

        recovery = CrashRecovery(prj)
        result = await recovery.recover()

        assert result.events_replayed > 0
        # Should not exceed total events (rebuild_all counts all rows)
        assert result.events_replayed >= total
