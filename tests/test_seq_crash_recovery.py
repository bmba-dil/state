from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store() -> SqliteEventStore:
    await migrate()
    return SqliteEventStore()


# ── Fsync discipline ──────────────────────────────────────────────────────


class TestFsyncDiscipline:
    """PRAGMA synchronous=FULL is set during append for crash durability."""

    async def test_fsync_does_not_break_append(self, store: SqliteEventStore) -> None:
        id_ = await store.append("step", "step-01", "state.step.executed", {"x": "y"})
        stream = [e async for e in store.read_stream("step-01")]
        assert len(stream) == 1
        assert stream[0]["id"] == id_
        assert stream[0]["seq"] == 1

    async def test_fsync_multiple_appends_all_succeed(self, store: SqliteEventStore) -> None:
        for i in range(10):
            await store.append("step", "step-01", "state.step.executed", {"i": i})
        stream = [e async for e in store.read_stream("step-01")]
        assert len(stream) == 10
        assert [e["seq"] for e in stream] == list(range(1, 11))

    async def test_fsync_across_multiple_aggregates(self, store: SqliteEventStore) -> None:
        for agg in ("agg-a", "agg-b", "agg-c"):
            for i in range(3):
                await store.append("step", agg, "state.step.executed", {"i": i})
        for agg in ("agg-a", "agg-b", "agg-c"):
            stream = [e async for e in store.read_stream(agg)]
            assert [e["seq"] for e in stream] == [1, 2, 3]

    async def test_fsync_with_explicit_id_and_ts(self, store: SqliteEventStore) -> None:
        id_ = await store.append(
            "step", "agg-01", "state.step.executed", {"x": "y"},
            id_="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ts="2026-06-01T00:00:00Z",
        )
        assert id_ == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        stream = [e async for e in store.read_stream("agg-01")]
        assert stream[0]["ts"] == "2026-06-01T00:00:00Z"


# ── Repair aggregate_seq ──────────────────────────────────────────────────


class TestRepairAggregateSeqs:
    """SqliteEventStore.repair_aggregate_seqs() recovery routine."""

    async def test_repair_no_events_returns_empty(self, store: SqliteEventStore) -> None:
        repairs = await store.repair_aggregate_seqs()
        assert repairs == []

    async def test_repair_already_consistent(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "y"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "z"})
        repairs = await store.repair_aggregate_seqs()
        assert repairs == []

    async def test_repair_empty_aggregate_seq(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "y"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "z"})
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 1
        assert repairs[0]["aggregate_id"] == "agg-01"
        assert repairs[0]["old_seq"] == 0
        assert repairs[0]["new_seq"] == 2

    async def test_repair_stale_seq(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "a"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "b"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "c"})
        async with get_connection() as db:
            await db.execute(
                "UPDATE aggregate_seq SET seq = 1 WHERE aggregate_id = ?",
                ("agg-01",),
            )
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 1
        assert repairs[0]["aggregate_id"] == "agg-01"
        assert repairs[0]["old_seq"] == 1
        assert repairs[0]["new_seq"] == 3

    async def test_repair_future_seq(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "a"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "b"})
        async with get_connection() as db:
            await db.execute(
                "UPDATE aggregate_seq SET seq = 99 WHERE aggregate_id = ?",
                ("agg-01",),
            )
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 1
        assert repairs[0]["aggregate_id"] == "agg-01"
        assert repairs[0]["old_seq"] == 99
        assert repairs[0]["new_seq"] == 2

    async def test_repair_multiple_aggregates(self, store: SqliteEventStore) -> None:
        for i in range(5):
            await store.append("arc", "arc-A", "state.arc.created", {"i": i})
            await store.append("arc", "arc-B", "state.arc.created", {"i": i})
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 2
        repair_map = {r["aggregate_id"]: r for r in repairs}
        assert repair_map["arc-A"]["old_seq"] == 0
        assert repair_map["arc-A"]["new_seq"] == 5
        assert repair_map["arc-B"]["old_seq"] == 0
        assert repair_map["arc-B"]["new_seq"] == 5

    async def test_repair_mixed_mismatches(self, store: SqliteEventStore) -> None:
        await store.append("arc", "agg-A", "state.arc.created", {"x": 1})
        await store.append("arc", "agg-A", "state.arc.created", {"x": 2})
        await store.append("arc", "agg-B", "state.arc.created", {"x": 1})
        await store.append("arc", "agg-C", "state.arc.created", {"x": 1})
        await store.append("arc", "agg-C", "state.arc.created", {"x": 2})
        await store.append("arc", "agg-C", "state.arc.created", {"x": 3})
        async with get_connection() as db:
            await db.execute("UPDATE aggregate_seq SET seq = 0 WHERE aggregate_id = 'agg-A'")
            await db.execute("UPDATE aggregate_seq SET seq = 42 WHERE aggregate_id = 'agg-C'")
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        repair_map = {r["aggregate_id"]: r for r in repairs}
        assert len(repairs) == 2
        assert repair_map["agg-A"]["new_seq"] == 2
        assert repair_map["agg-C"]["new_seq"] == 3
        assert "agg-B" not in repair_map

    async def test_append_after_repair_gets_correct_seq(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "a"})
        await store.append("step", "agg-01", "state.step.executed", {"x": "b"})
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()
        await store.repair_aggregate_seqs()
        id_ = await store.append("step", "agg-01", "state.step.executed", {"x": "c"})
        stream = [e async for e in store.read_stream("agg-01")]
        assert len(stream) == 3
        assert [e["seq"] for e in stream] == [1, 2, 3]
        assert stream[2]["id"] == id_

    async def test_repair_twice_idempotent(self, store: SqliteEventStore) -> None:
        await store.append("step", "agg-01", "state.step.executed", {"x": "a"})
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()
        r1 = await store.repair_aggregate_seqs()
        r2 = await store.repair_aggregate_seqs()
        assert len(r1) == 1
        assert r2 == []

    async def test_repair_multiple_aggregates_some_consistent(self, store: SqliteEventStore) -> None:
        await store.append("arc", "agg-A", "state.arc.created", {"x": 1})
        await store.append("arc", "agg-A", "state.arc.created", {"x": 2})
        await store.append("arc", "agg-B", "state.arc.created", {"x": 1})
        async with get_connection() as db:
            await db.execute("UPDATE aggregate_seq SET seq = 1 WHERE aggregate_id = 'agg-A'")
            await db.commit()
        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 1
        assert repairs[0]["aggregate_id"] == "agg-A"
        assert repairs[0]["old_seq"] == 1
        assert repairs[0]["new_seq"] == 2


# ── Hypothesis property tests ─────────────────────────────────────────────


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    num_aggregates=st.integers(min_value=1, max_value=5),
    ops_per_agg=st.lists(
        st.integers(min_value=1, max_value=10),
        min_size=1,
        max_size=5,
    ),
)
async def test_hypothesis_seq_monotonic_after_append(
    tmp_path: Path,
    num_aggregates: int,
    ops_per_agg: list[int],
) -> None:
    """For any sequence of appends across aggregates, seq is strictly increasing."""
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

    aggregate_ids = [f"agg-{i}" for i in range(num_aggregates)]
    for agg_idx, count in enumerate(ops_per_agg[:num_aggregates]):
        agg_id = aggregate_ids[agg_idx]
        for i in range(count):
            await store.append(
                "step", agg_id, "state.step.executed",
                {"i": i},
            )

    for agg_id in aggregate_ids:
        stream = [e async for e in store.read_stream(agg_id)]
        seqs = [e["seq"] for e in stream]
        if len(seqs) > 1:
            assert all(seqs[i] < seqs[i + 1] for i in range(len(seqs) - 1)), (
                f"Seq not monotonic for {agg_id}: {seqs}"
            )
        # seq must start at 1
        if seqs:
            assert seqs[0] == 1


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    num_events=st.integers(min_value=1, max_value=20),
    num_aggregates=st.integers(min_value=1, max_value=5),
)
async def test_hypothesis_repair_random_mismatch(
    tmp_path: Path,
    num_events: int,
    num_aggregates: int,
) -> None:
    """After randomly scrambling aggregate_seq, repair restores correctness.

    Events are appended to random aggregates, then aggregate_seq is
    arbitrarily corrupted (some rows deleted, some set to wrong values).
    After repair, the next append gets the correct seq.
    """
    import os
    import random
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

    rng = random.Random(uuid.uuid4().int)
    aggregate_ids = [f"agg-{i}" for i in range(num_aggregates)]

    event_counts: dict[str, int] = {}
    for _ in range(num_events):
        agg_id = rng.choice(aggregate_ids)
        await store.append("step", agg_id, "state.step.executed", {"x": 1})
        event_counts[agg_id] = event_counts.get(agg_id, 0) + 1

    async with get_connection() as db:
        for agg_id in aggregate_ids:
            if rng.random() < 0.5:
                await db.execute("DELETE FROM aggregate_seq WHERE aggregate_id = ?", (agg_id,))
            elif rng.random() < 0.5:
                wrong_seq = rng.randint(0, 999)
                await db.execute(
                    "UPDATE aggregate_seq SET seq = ? WHERE aggregate_id = ?",
                    (wrong_seq, agg_id),
                )
        await db.commit()

    repairs = await store.repair_aggregate_seqs()

    for agg_id in aggregate_ids:
        expected_seq = event_counts.get(agg_id, 0)
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT seq FROM aggregate_seq WHERE aggregate_id = ?", (agg_id,),
            )
            row = await cursor.fetchone()
        current_seq = row[0] if row else 0
        assert current_seq == expected_seq, (
            f"Aggregate {agg_id}: expected seq={expected_seq}, got {current_seq}. "
            f"Repairs: {repairs}"
        )

    for agg_id in aggregate_ids:
        count = event_counts.get(agg_id, 0)
        if count > 0:
            next_id = await store.append("step", agg_id, "state.step.executed", {"x": "post-repair"})
            stream = [e async for e in store.read_stream(agg_id)]
            assert stream[-1]["seq"] == count + 1, (
                f"Aggregate {agg_id}: expected seq={count + 1} after repair, "
                f"got {stream[-1]['seq']}. Events: {[e['seq'] for e in stream]}"
            )
            assert stream[-1]["id"] == next_id
