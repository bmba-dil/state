"""Tests for state_core.events — SqliteEventStore append + read_stream.

Covers: basic round-trip, seq enforcement, determinism, mode storage,
edge cases, and Hypothesis property tests.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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
