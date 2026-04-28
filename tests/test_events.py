"""Tests for state_core.events — SqliteEventStore append + read_stream.

Covers: basic round-trip, seq enforcement, determinism, mode storage,
edge cases, and Hypothesis property tests.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import aiosqlite
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store() -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


# ── Helpers ────────────────────────────────────────────────────────────────


def _sorted_json(data: dict) -> str:
    """Serialize with same deterministic settings used by append()."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


# ── Event-type data strategies ────────────────────────────────────────────
# Maps each of 34 event types to its aggregate type and a Hypothesis strategy
# that produces valid data dicts matching the corresponding Pydantic model.
# These are used by Hypothesis property tests to verify round-trip behavior
# across all event types.

AGGREGATE_FOR_EVENT: dict[str, str] = {
    # Arc (3)
    "state.arc.created": "arc",
    "state.arc.retired": "arc",
    "state.arc.updated": "arc",
    # Phase (4)
    "state.phase.planned": "phase",
    "state.phase.started": "phase",
    "state.phase.verified": "phase",
    "state.phase.completed": "phase",
    # Slice (4)
    "state.slice.planned": "slice",
    "state.slice.worktree_ready": "slice",
    "state.slice.shipped": "slice",
    "state.slice.reverted": "slice",
    # Step (10)
    "state.step.discussed": "step",
    "state.step.planned": "step",
    "state.step.executed": "step",
    "state.step.verify_started": "step",
    "state.step.verify_passed": "step",
    "state.step.verify_failed": "step",
    "state.step.advanced": "step",
    "state.step.blocked": "step",
    "state.step.snapshotted": "step",
    "state.step.reverted": "step",
    # Concept (5)
    "state.concept.introduced": "concept",
    "state.concept.observed": "concept",
    "state.concept.drilled": "concept",
    "state.concept.mastered": "concept",
    "state.concept.reviewed": "concept",
    # Drill (3)
    "state.drill.prepared": "drill",
    "state.drill.submitted": "drill",
    "state.drill.graded": "drill",
    # Mode (1)
    "state.mode.activated": "mode",
    # Decision (2)
    "state.decision.asked": "decision",
    "state.decision.made": "decision",
    # Auth (2)
    "state.auth.refreshed": "auth",
    "state.auth.rotated": "auth",
}

EVENT_DATA_STRATEGIES: dict[str, st.SearchStrategy[dict]] = {
    # ── Arc ────────────────────────────────────────────────────────────────
    "state.arc.created": st.fixed_dictionaries({
        "title": st.just("Arc Title"),
        "goal": st.just("Build the thing"),
    }),
    "state.arc.retired": st.fixed_dictionaries({
        "reason": st.just("Completed"),
    }),
    "state.arc.updated": st.fixed_dictionaries({
        "changed_fields": st.just(["title"]),
    }),
    # ── Phase ──────────────────────────────────────────────────────────────
    "state.phase.planned": st.fixed_dictionaries({
        "phase_number": st.integers(min_value=1, max_value=100),
        "title": st.just("Phase Title"),
        "goal": st.just("Achieve the goal"),
    }),
    "state.phase.started": st.fixed_dictionaries({}),
    "state.phase.verified": st.fixed_dictionaries({
        "passed": st.just(True),
        "summary": st.just("All criteria met"),
    }),
    "state.phase.completed": st.fixed_dictionaries({
        "passed": st.just(True),
    }),
    # ── Slice ──────────────────────────────────────────────────────────────
    "state.slice.planned": st.fixed_dictionaries({
        "slice_number": st.integers(min_value=1, max_value=50),
        "title": st.just("Slice Title"),
        "goal": st.just("Slice goal"),
    }),
    "state.slice.worktree_ready": st.fixed_dictionaries({
        "worktree_name": st.just("feature-branch"),
        "branch": st.just("main"),
        "dir": st.just("/tmp/worktree"),
    }),
    "state.slice.shipped": st.fixed_dictionaries({
        "snapshot_hash": st.just("abc123def456"),
    }),
    "state.slice.reverted": st.fixed_dictionaries({
        "reason": st.just("Issues found"),
    }),
    # ── Step ───────────────────────────────────────────────────────────────
    "state.step.discussed": st.fixed_dictionaries({
        "approach_summary": st.just("Use TDD approach"),
    }),
    "state.step.planned": st.fixed_dictionaries({
        "goal": st.just("Implement feature"),
        "verify_contract": st.just([{"check": "unit tests pass"}]),
    }),
    "state.step.executed": st.fixed_dictionaries({
        "changes_summary": st.just("Wrote implementation"),
    }),
    "state.step.verify_started": st.fixed_dictionaries({
        "contract": st.just([{"check": "all tests pass"}]),
    }),
    "state.step.verify_passed": st.fixed_dictionaries({
        "duration_ms": st.integers(min_value=0, max_value=60000),
    }),
    "state.step.verify_failed": st.fixed_dictionaries({
        "reason": st.just("Assertion failed"),
        "details": st.just("Expected True, got False"),
    }),
    "state.step.advanced": st.fixed_dictionaries({
        "new_state": st.just("completed"),
    }),
    "state.step.blocked": st.fixed_dictionaries({
        "reason": st.just("Waiting for review"),
    }),
    "state.step.snapshotted": st.fixed_dictionaries({
        "snapshot_hash": st.just("abc123def456"),
        "tier": st.just("step"),
    }),
    "state.step.reverted": st.fixed_dictionaries({
        "snapshot_hash": st.just("abc123def456"),
        "reason": st.just("Found regression"),
    }),
    # ── Concept ────────────────────────────────────────────────────────────
    "state.concept.introduced": st.fixed_dictionaries({
        "concept_id": st.just("conc-01"),
        "name": st.just("Factory Pattern"),
        "prerequisites": st.just([]),
    }),
    "state.concept.observed": st.fixed_dictionaries({
        "observation": st.just("Learner understood abstraction"),
        "classification": st.just("positive"),
    }),
    "state.concept.drilled": st.fixed_dictionaries({
        "score": st.floats(min_value=0.0, max_value=10.0),
        "items_attempted": st.integers(min_value=1, max_value=20),
    }),
    "state.concept.mastered": st.fixed_dictionaries({
        "mastery_probability": st.floats(min_value=0.0, max_value=1.0),
    }),
    "state.concept.reviewed": st.fixed_dictionaries({
        "mastery_delta": st.floats(min_value=-1.0, max_value=1.0),
    }),
    # ── Drill ──────────────────────────────────────────────────────────────
    "state.drill.prepared": st.fixed_dictionaries({
        "question_count": st.integers(min_value=1, max_value=20),
    }),
    "state.drill.submitted": st.fixed_dictionaries({
        "answers": st.just([{"q": 1, "a": "answer"}]),
    }),
    "state.drill.graded": st.fixed_dictionaries({
        "score": st.floats(min_value=0.0, max_value=100.0),
        "max_score": st.floats(min_value=1.0, max_value=100.0),
    }),
    # ── Mode ───────────────────────────────────────────────────────────────
    "state.mode.activated": st.fixed_dictionaries({
        "mode_value": st.just("build"),
    }),
    # ── Decision ───────────────────────────────────────────────────────────
    "state.decision.asked": st.fixed_dictionaries({
        "question": st.just("What approach?"),
        "options": st.just([{"option": "A"}]),
    }),
    "state.decision.made": st.fixed_dictionaries({
        "answer": st.just("Option A"),
        "reason": st.just("Best trade-off"),
    }),
    # ── Auth ───────────────────────────────────────────────────────────────
    "state.auth.refreshed": st.fixed_dictionaries({
        "provider": st.just("anthropic"),
        "outcome": st.just("success"),
    }),
    "state.auth.rotated": st.fixed_dictionaries({
        "provider": st.just("anthropic"),
        "index": st.integers(min_value=0, max_value=5),
    }),
}


# ── Basic round-trip ──────────────────────────────────────────────────────


class TestBasicRoundTrip:
    """Fundamental append → read_stream round-trip."""

    async def test_append_returns_ulid(self, store: SqliteEventStore) -> None:
        id_ = await store.append("step", "step-01", "state.step.executed", {"changes_summary": "x"})
        assert isinstance(id_, str)
        assert len(id_) == 26

    async def test_append_returns_different_id_each_call(self, store: SqliteEventStore) -> None:
        id1 = await store.append("step", "step-01", "state.step.executed", {"changes_summary": "a"})
        id2 = await store.append("step", "step-01", "state.step.executed", {"changes_summary": "b"})
        assert id1 != id2

    async def test_append_default_timestamp(self, store: SqliteEventStore) -> None:
        await store.append("arc", "arc-01", "state.arc.created", {"title": "T", "goal": "G"})
        stream = [e async for e in store.read_stream("arc-01")]
        assert len(stream) == 1
        assert stream[0]["ts"] == "2026-01-01T00:00:00Z"

    async def test_append_explicit_timestamp(self, store: SqliteEventStore) -> None:
        await store.append(
            "arc", "arc-01", "state.arc.created", {"title": "T", "goal": "G"},
            ts="2026-06-15T12:30:00Z",
        )
        stream = [e async for e in store.read_stream("arc-01")]
        assert stream[0]["ts"] == "2026-06-15T12:30:00Z"

    async def test_append_explicit_id(self, store: SqliteEventStore) -> None:
        custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        returned = await store.append(
            "step", "step-01", "state.step.executed", {"changes_summary": "x"},
            id_=custom_id,
        )
        assert returned == custom_id
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["id"] == custom_id

    async def test_append_explicit_id_and_ts(self, store: SqliteEventStore) -> None:
        await store.append(
            "step", "step-01", "state.step.executed", {"changes_summary": "x"},
            id_="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ts="2026-01-01T00:00:00Z",
        )
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert stream[0]["ts"] == "2026-01-01T00:00:00Z"


# ── Seq enforcement ──────────────────────────────────────────────────────


class TestSeqEnforcement:
    """Per-aggregate monotonic sequence enforcement."""

    async def test_seq_starts_at_one(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "a"})
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["seq"] == 1

    async def test_seq_increments(self, store: SqliteEventStore) -> None:
        for i in range(5):
            await store.append("step", "step-01", "state.step.executed", {"changes_summary": str(i)})
        stream = [e async for e in store.read_stream("step-01")]
        assert len(stream) == 5
        assert [e["seq"] for e in stream] == [1, 2, 3, 4, 5]

    async def test_seq_independent_per_aggregate(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "a"})
        await store.append("step", "step-02", "state.step.executed", {"changes_summary": "b"})
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "c"})
        await store.append("step", "step-02", "state.step.executed", {"changes_summary": "d"})

        stream_a = [e async for e in store.read_stream("step-01")]
        stream_b = [e async for e in store.read_stream("step-02")]

        assert [e["seq"] for e in stream_a] == [1, 2]
        assert [e["seq"] for e in stream_b] == [1, 2]

    async def test_read_stream_from_seq(self, store: SqliteEventStore) -> None:
        for i in range(5):
            await store.append("step", "step-01", "state.step.executed", {"changes_summary": str(i)})
        stream = [e async for e in store.read_stream("step-01", after_seq=2)]
        assert [e["seq"] for e in stream] == [3, 4, 5]

    async def test_read_stream_from_zero_includes_all(self, store: SqliteEventStore) -> None:
        for i in range(3):
            await store.append("step", "step-01", "state.step.executed", {"changes_summary": str(i)})
        stream = [e async for e in store.read_stream("step-01", after_seq=0)]
        assert [e["seq"] for e in stream] == [1, 2, 3]


# ── Determinism + mode ──────────────────────────────────────────────────


class TestDeterminismAndMode:
    """Deterministic payloads and mode discriminator."""

    async def test_default_mode_is_kernel(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "x"})
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["mode"] == "kernel"

    async def test_explicit_modes_stored(self, store: SqliteEventStore) -> None:
        for mode in ("build", "teach", "kernel"):
            await store.append(
                "step", "step-01", "state.step.executed",
                {"changes_summary": mode},
                mode=mode,  # type: ignore[arg-type]
            )
        stream = [e async for e in store.read_stream("step-01")]
        assert [e["mode"] for e in stream] == ["build", "teach", "kernel"]

    async def test_deterministic_json_serialization(self, store: SqliteEventStore) -> None:
        data = {"z": 1, "a": 2, "nested": {"b": 3, "c": 4}}
        await store.append("step", "step-01", "state.step.executed", data)
        stream = [e async for e in store.read_stream("step-01")]
        expected = _sorted_json(data)
        assert stream[0]["data"] == json.loads(expected)

    async def test_id_and_ts_injected_values_stored(self, store: SqliteEventStore) -> None:
        custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        custom_ts = "2026-06-01T12:00:00Z"
        returned = await store.append(
            "step", "step-01", "state.step.executed", {"changes_summary": "a"},
            id_=custom_id,
            ts=custom_ts,
        )
        assert returned == custom_id
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["id"] == custom_id
        assert stream[0]["ts"] == custom_ts

    async def test_different_aggregates_same_mode_mixed_seq(self, store: SqliteEventStore) -> None:
        await store.append("arc", "arc-01", "state.arc.created", {"title": "A", "goal": "G"}, mode="build")
        await store.append("arc", "arc-02", "state.arc.created", {"title": "B", "goal": "G"}, mode="build")
        await store.append("arc", "arc-01", "state.arc.updated", {"changed_fields": ["title"]}, mode="build")
        stream_a = [e async for e in store.read_stream("arc-01")]
        stream_b = [e async for e in store.read_stream("arc-02")]
        assert [e["seq"] for e in stream_a] == [1, 2]
        assert [e["seq"] for e in stream_b] == [1]
        assert all(e["mode"] == "build" for e in stream_a)
        assert all(e["mode"] == "build" for e in stream_b)

    async def test_explicit_id_determinism(self, store: SqliteEventStore) -> None:
        """Same data + ts + mode produces identical stored field values across aggregates.

        The ULID is the PRIMARY KEY, so each event must have a unique id, but
        all other explicit inputs (data, ts, mode) should be stored identically
        regardless of the aggregate they belong to.
        """
        custom_ts = "2026-01-01T00:00:00Z"
        data = {"changes_summary": "deterministic"}

        id1 = await store.append(
            "step", "step-a", "state.step.executed", data,
            ts=custom_ts, mode="build",
        )
        id2 = await store.append(
            "step", "step-b", "state.step.executed", data,
            ts=custom_ts, mode="build",
        )
        assert id1 != id2  # ULIDs must differ (PRIMARY KEY)

        # Verify the stored fields are deterministic (same inputs -> same outputs)
        stream_a = [e async for e in store.read_stream("step-a")]
        stream_b = [e async for e in store.read_stream("step-b")]
        assert stream_a[0]["data"] == stream_b[0]["data"]
        assert stream_a[0]["ts"] == stream_b[0]["ts"]
        assert stream_a[0]["mode"] == stream_b[0]["mode"]


# ── Edge cases ──────────────────────────────────────────────────────────


class TestEdgeCases:
    """Boundary and edge-case behavior."""

    async def test_empty_stream(self, store: SqliteEventStore) -> None:
        stream = [e async for e in store.read_stream("nonexistent")]
        assert stream == []

    async def test_after_seq_beyond_max(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "a"})
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "b"})
        stream = [e async for e in store.read_stream("step-01", after_seq=99)]
        assert stream == []

    async def test_empty_data_dict(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {})
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["data"] == {}
        assert stream[0]["type"] == "state.step.executed"

    async def test_complex_nested_data(self, store: SqliteEventStore) -> None:
        data = {
            "list": [1, 2, {"deep": "value"}],
            "null_val": None,
            "bool_val": False,
            "number": 3.14,
        }
        await store.append("step", "step-01", "state.step.executed", data)
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["data"] == json.loads(_sorted_json(data))
        assert stream[0]["data"]["list"][2]["deep"] == "value"
        assert stream[0]["data"]["null_val"] is None
        assert stream[0]["data"]["bool_val"] is False

    async def test_long_aggregate_ids(self, store: SqliteEventStore) -> None:
        long_id = "a" * 500
        await store.append("step", long_id, "state.step.executed", {"changes_summary": "x"})
        stream = [e async for e in store.read_stream(long_id)]
        assert len(stream) == 1
        assert stream[0]["aggregate_id"] == long_id

    async def test_multi_mode_seq_continuity(self, store: SqliteEventStore) -> None:
        for mode in ("build", "teach", "kernel", "build", "teach"):
            await store.append("step", "step-01", "state.step.executed", {}, mode=mode)
        stream = [e async for e in store.read_stream("step-01")]
        assert [e["seq"] for e in stream] == [1, 2, 3, 4, 5]
        assert [e["mode"] for e in stream] == ["build", "teach", "kernel", "build", "teach"]


# ── Idempotent append ─────────────────────────────────────────────────────


class TestIdempotentAppend:
    """Appending the exact same event twice is idempotent."""

    async def test_same_ulid_same_seq_raises_integrity_error(
        self, store: SqliteEventStore,
    ) -> None:
        """Same (aggregate_id, seq) pair raises IntegrityError on second insert."""
        custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        id1 = await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "first"},
            id_=custom_id,
        )
        assert id1 == custom_id
        # Direct SQL test: re-inserting same (aggregate_id, seq) hits UNIQUE constraint
        async with get_connection() as db:
            with pytest.raises(aiosqlite.IntegrityError):
                await db.execute(
                    "INSERT INTO events (id, seq, aggregate_type, aggregate_id, "
                    "type, data, ts) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("01ARZ3NDEKTSV4RRFFQ69G5FAV", 1, "step", "step-01",
                     "state.step.executed", '{"x":1}', "2026-01-01T00:00:00Z"),
                )
                await db.commit()

    async def test_append_same_data_different_ulid_seq_increments(
        self, store: SqliteEventStore,
    ) -> None:
        """Same data with different ULID produces new seq (no data corruption)."""
        id1 = await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "same"},
        )
        id2 = await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "same"},
        )
        assert id1 != id2
        stream = [e async for e in store.read_stream("step-01")]
        assert len(stream) == 2
        assert stream[0]["seq"] == 1
        assert stream[1]["seq"] == 2
        # Data must be identical
        assert stream[0]["data"] == stream[1]["data"]


# ── Protocol conformance ──────────────────────────────────────────────────


class TestProtocolConformance:
    """SqliteEventStore conforms to the EventStore protocol."""

    def test_has_append_with_correct_params(self) -> None:
        import inspect
        sig = inspect.signature(SqliteEventStore.append)
        params = list(sig.parameters.keys())
        assert "aggregate_type" in params
        assert "aggregate_id" in params
        assert "event_type" in params
        assert "data" in params
        assert "mode" in params
        assert "ts" in params
        assert "id_" in params

    def test_has_read_stream_method(self) -> None:
        assert hasattr(SqliteEventStore, "read_stream")

    def test_read_stream_returns_async_iterator(self, store: SqliteEventStore) -> None:
        stream = store.read_stream("nonexistent")
        assert hasattr(stream, "__aiter__")

    async def test_append_returns_string(self, store: SqliteEventStore) -> None:
        result = await store.append("step", "step-01", "state.step.executed", {})
        assert isinstance(result, str)


# ── Property-based tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    aggregate_type=st.sampled_from(["arc", "phase", "slice", "step", "concept", "drill", "decision", "auth", "mode"]),
    mode_val=st.sampled_from(["build", "teach", "kernel"]),
    data=st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.one_of(st.integers(min_value=0, max_value=100), st.text(max_size=20)),
        min_size=0,
        max_size=5,
    ),
)
async def test_property_append_read_roundtrip(
    tmp_path: Path,
    aggregate_type: str,
    mode_val: str,
    data: dict,
) -> None:
    """Hypothesis property: any valid input round-trips correctly.

    Uses a unique subdirectory per example to avoid cross-contamination.
    """
    import os
    import uuid

    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = unique / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    await migrate()
    store = SqliteEventStore()

    id_ = await store.append(
        aggregate_type, f"{aggregate_type}-01", f"state.{aggregate_type}.created",
        data,
        mode=mode_val,
    )

    assert len(id_) == 26

    stream = [e async for e in store.read_stream(f"{aggregate_type}-01")]
    assert len(stream) == 1
    row = stream[0]
    assert row["seq"] == 1
    assert row["mode"] == mode_val
    assert row["id"] == id_
    assert row["aggregate_type"] == aggregate_type
    assert row["data"] == data


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    event_type=st.sampled_from(sorted(EVENT_DATA_STRATEGIES.keys())),
    mode_val=st.sampled_from(["build", "teach", "kernel"]),
    data=st.data(),
)
async def test_property_all_event_types_roundtrip(
    tmp_path: Path,
    event_type: str,
    mode_val: str,
    data: st.DataObject,
) -> None:
    """Hypothesis property: every event type round-trips through append -> read_stream."""
    import os
    import uuid

    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = unique / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    await migrate()
    store = SqliteEventStore()

    aggregate_type = AGGREGATE_FOR_EVENT[event_type]
    aggregate_id = f"{aggregate_type}-test-01"
    event_data = data.draw(EVENT_DATA_STRATEGIES[event_type])

    # Use explicit deterministic ULID
    custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    returned_id = await store.append(
        aggregate_type, aggregate_id, event_type, event_data,
        mode=mode_val, id_=custom_id,
    )
    assert returned_id == custom_id, "Explicit ULID must round-trip"

    stream = [e async for e in store.read_stream(aggregate_id)]
    assert len(stream) == 1
    row = stream[0]
    assert row["id"] == custom_id
    assert row["type"] == event_type
    assert row["aggregate_type"] == aggregate_type
    assert row["mode"] == mode_val
    assert row["seq"] == 1
    # Data must be stored and retrieved as the same dict (JSON round-trip)
    assert row["data"] == event_data


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    build_count=st.integers(min_value=0, max_value=10),
    teach_count=st.integers(min_value=0, max_value=10),
    kernel_count=st.integers(min_value=0, max_value=10),
)
async def test_property_mode_filtering(
    tmp_path: Path,
    build_count: int,
    teach_count: int,
    kernel_count: int,
) -> None:
    """Hypothesis property: mode-filtered counts sum to total."""
    import os
    import uuid

    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = unique / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    await migrate()
    store = SqliteEventStore()

    mode_counts = {"build": build_count, "teach": teach_count, "kernel": kernel_count}
    total = 0
    for mode, count in mode_counts.items():
        for i in range(count):
            await store.append(
                "step", "step-01", "state.step.executed",
                {"i": i}, mode=mode,
            )
        total += count

    assert await store.count_events() == total
    for mode in ("build", "teach", "kernel"):
        expected = mode_counts[mode]
        actual = await store.count_events(mode=mode)
        assert actual == expected, f"Mode {mode}: expected {expected}, got {actual}"
