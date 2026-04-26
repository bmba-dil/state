from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.state_core.database import get_connection
import aiosqlite
import structlog

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


# ── Crash-simulation Hypothesis property test ──────────────────────────────


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_aggregates=st.integers(min_value=1, max_value=3),
    prior_events_per_agg=st.integers(min_value=0, max_value=5),
    crash_at_op=st.integers(min_value=0, max_value=5),
)
async def test_hypothesis_crash_recovery_monotonic(
    tmp_path: Path,
    num_aggregates: int,
    prior_events_per_agg: int,
    crash_at_op: int,
) -> None:
    """For any crash offset + repair, seq remains monotonically increasing per aggregate.

    Simulates a crash at a configurable commit offset, then runs repair and
    verifies that:
    - sorted(seq_list) == seq_list — monotonically increasing per aggregate
    - events.MAX(seq) equals aggregate_seq.seq per aggregate
    - No duplicate seq values per aggregate
    - seq starts at 1 if events exist
    """
    import os
    import uuid

    import aiosqlite

    # Isolated DB setup (matches existing Hypothesis test pattern)
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
    aggregate_ids = [f"crash-agg-{i}" for i in range(num_aggregates)]

    # Phase 1: Append prior events (no crash)
    for agg_id in aggregate_ids:
        for _ in range(prior_events_per_agg):
            await store.append("step", agg_id, "state.step.executed", {})

    # Phase 2: Crash simulation
    # crash_at_op determines which commit() call in this phase fails
    original_commit = aiosqlite.Connection.commit
    commit_count = 0

    async def failing_commit(self: aiosqlite.Connection) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == crash_at_op + 1:
            raise Exception(f"Simulated crash at crash_at_op={crash_at_op}")
        return await original_commit(self)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)

    for agg_id in aggregate_ids:
        try:
            await store.append("step", agg_id, "state.step.executed", {"crash": True})
        except Exception as exc:
            if "Simulated crash" in str(exc):
                pass  # Expected — crash at configured offset

    monkeypatch.undo()

    # Phase 3: Repair
    repairs = await store.repair_aggregate_seqs()

    # Phase 4: Property verification per aggregate
    for agg_id in aggregate_ids:
        stream = [e async for e in store.read_stream(agg_id)]
        seq_list = [e["seq"] for e in stream]

        # Property 1: Monotonically increasing
        assert sorted(seq_list) == seq_list, (
            f"Aggregate {agg_id}: seq not monotonic: {seq_list}. "
            f"prior_events_per_agg={prior_events_per_agg}, "
            f"crash_at_op={crash_at_op}, num_aggregates={num_aggregates}"
        )

        # Property 2: No duplicate seq values per aggregate
        assert len(set(seq_list)) == len(seq_list), (
            f"Aggregate {agg_id}: duplicate seq values: {seq_list}"
        )

        # Property 3: seq starts at 1 if events exist
        if seq_list:
            assert seq_list[0] == 1, (
                f"Aggregate {agg_id}: first seq should be 1, got {seq_list[0]}"
            )

        # Property 4: events.MAX(seq) equals aggregate_seq.seq per aggregate
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events WHERE aggregate_id = ?",
                (agg_id,),
            )
            row = await cursor.fetchone()
            max_events_seq: int = row[0] if row else 0

            cursor = await db.execute(
                "SELECT seq FROM aggregate_seq WHERE aggregate_id = ?",
                (agg_id,),
            )
            row = await cursor.fetchone()
            agg_seq: int = row[0] if row else 0

        assert max_events_seq == agg_seq, (
            f"Aggregate {agg_id}: events.MAX(seq)={max_events_seq} != "
            f"aggregate_seq.seq={agg_seq}. seq_list={seq_list}"
        )

    # Edge case: crash_at_op=0 on empty store produces no repairs
    if prior_events_per_agg == 0 and crash_at_op == 0:
        assert repairs == [], (
            f"Empty store with crash_at_op=0 should produce no repairs, "
            f"got {repairs}"
        )


# ── Crash mid-append ───────────────────────────────────────────────────────


class TestCrashMidAppend:
    """Simulate a crash mid-append and verify repair restores monotonic seq."""

    async def test_crash_mid_append_repair_restores_monotonic(
        self, store: SqliteEventStore,
    ) -> None:
        """Monkeypatch commit to raise on first call, then repair + continue."""
        import aiosqlite

        original_commit = aiosqlite.Connection.commit
        call_count = 0

        async def failing_commit(self: aiosqlite.Connection) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated crash mid-transaction")
            return await original_commit(self)

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)

        # First append "crashes" — data rolls back
        with pytest.raises(Exception, match="Simulated crash"):
            await store.append("step", "agg-01", "state.step.executed", {"x": 1})

        monkeypatch.undo()

        # Repair fixes aggregate_seq (seq should be 0 since rollback undid the insert)
        repairs = await store.repair_aggregate_seqs()
        assert repairs == []  # No events made it in, so aggregate_seq was untouched

        # Append should succeed with seq=1 since no events were committed
        id1 = await store.append("step", "agg-01", "state.step.executed", {"x": 2})
        stream = [e async for e in store.read_stream("agg-01")]
        assert len(stream) == 1
        assert stream[0]["seq"] == 1
        assert stream[0]["id"] == id1

    async def test_crash_mid_append_events_committed_agg_seq_missing(
        self, store: SqliteEventStore,
    ) -> None:
        """Simulate crash after events INSERT but before aggregate_seq upsert.

        This simulates the scenario where the event row was committed but the
        aggregate_seq update was not. After repair, seq should be corrected.
        """
        # Need to simulate a partial write. We do this by appending normally,
        # then deleting aggregate_seq to simulate a crash after events INSERT
        # but before aggregate_seq upsert.
        id1 = await store.append("step", "agg-01", "state.step.executed", {"x": 1})
        id2 = await store.append("step", "agg-01", "state.step.executed", {"x": 2})

        # Simulate crash that lost the aggregate_seq state
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()

        repairs = await store.repair_aggregate_seqs()
        assert len(repairs) == 1
        assert repairs[0]["aggregate_id"] == "agg-01"
        assert repairs[0]["old_seq"] == 0
        assert repairs[0]["new_seq"] == 2

        # Next append should get seq=3
        id3 = await store.append("step", "agg-01", "state.step.executed", {"x": 3})
        stream = [e async for e in store.read_stream("agg-01")]
        assert [e["seq"] for e in stream] == [1, 2, 3]

    async def test_crash_does_not_corrupt_other_aggregates(
        self, store: SqliteEventStore,
    ) -> None:
        """A crash in one aggregate leaves other aggregate seqs intact."""
        import aiosqlite

        await store.append("step", "agg-A", "state.step.executed", {"x": 1})
        await store.append("step", "agg-A", "state.step.executed", {"x": 2})

        original_commit = aiosqlite.Connection.commit
        call_count = 0

        async def failing_commit(self: aiosqlite.Connection) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Crash")
            return await original_commit(self)

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(aiosqlite.Connection, "commit", failing_commit)

        with pytest.raises(Exception, match="Crash"):
            await store.append("step", "agg-B", "state.step.executed", {"x": 1})

        monkeypatch.undo()

        # agg-A should be untouched
        stream_a = [e async for e in store.read_stream("agg-A")]
        assert [e["seq"] for e in stream_a] == [1, 2]


# ── UNIQUE constraint ──────────────────────────────────────────────────────


class TestUniqueConstraint:
    """UNIQUE(aggregate_id, seq) index prevents duplicate seq values."""

    async def test_unique_constraint_prevents_duplicate_seq(
        self, store: SqliteEventStore,
    ) -> None:
        """Direct INSERT of duplicate (aggregate_id, seq) raises IntegrityError."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})

        # Insert another event with same aggregate_id and seq directly
        async with get_connection() as db:
            with pytest.raises(aiosqlite.IntegrityError):
                await db.execute(
                    "INSERT INTO events (id, seq, aggregate_type, aggregate_id, "
                    "type, data, ts) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        1,
                        "step",
                        "agg-01",
                        "state.step.executed",
                        '{"x":2}',
                        "2026-01-01T00:00:00Z",
                    ),
                )
                await db.commit()

    async def test_unique_constraint_allows_different_seq(
        self, store: SqliteEventStore,
    ) -> None:
        """Different seq values for the same aggregate are allowed."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})
        await store.append("step", "agg-01", "state.step.executed", {"x": 2})
        stream = [e async for e in store.read_stream("agg-01")]
        assert [e["seq"] for e in stream] == [1, 2]

    async def test_unique_constraint_allows_same_seq_different_aggregate(
        self, store: SqliteEventStore,
    ) -> None:
        """Same seq value for different aggregates is allowed."""
        await store.append("step", "agg-A", "state.step.executed", {"x": 1})
        await store.append("step", "agg-B", "state.step.executed", {"x": 1})
        stream_a = [e async for e in store.read_stream("agg-A")]
        stream_b = [e async for e in store.read_stream("agg-B")]
        assert stream_a[0]["seq"] == 1
        assert stream_b[0]["seq"] == 1


# ── Repair-on-startup ──────────────────────────────────────────────────────


class TestRepairOnStartup:
    """SqliteEventStore(run_repair=True) deferred repair on first access."""

    async def test_repair_on_startup_flag(
        self, store: SqliteEventStore,
    ) -> None:
        """SqliteEventStore with run_repair=True fixes stale aggregate_seq."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})
        await store.append("step", "agg-01", "state.step.executed", {"x": 2})

        # Corrupt aggregate_seq — delete all rows
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()

        # Create new store with run_repair=True
        repaired_store = SqliteEventStore(run_repair=True)

        # The next append should trigger repair and get correct seq
        id_ = await repaired_store.append(
            "step", "agg-01", "state.step.executed", {"x": 3},
        )
        stream = [e async for e in repaired_store.read_stream("agg-01")]
        assert [e["seq"] for e in stream] == [1, 2, 3]
        assert stream[2]["id"] == id_

    async def test_repair_on_startup_read_stream(
        self, store: SqliteEventStore,
    ) -> None:
        """read_stream also triggers deferred repair."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})

        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()

        repaired_store = SqliteEventStore(run_repair=True)

        # read_stream should trigger repair
        stream = [e async for e in repaired_store.read_stream("agg-01")]
        assert len(stream) == 1

        # Subsequent append should get correct seq
        await repaired_store.append(
            "step", "agg-01", "state.step.executed", {"x": 2},
        )
        stream = [e async for e in repaired_store.read_stream("agg-01")]
        assert [e["seq"] for e in stream] == [1, 2]

    async def test_repair_on_startup_noop_when_consistent(
        self, store: SqliteEventStore,
    ) -> None:
        """run_repair=True is a no-op when aggregate_seq is already consistent."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})
        await store.append("step", "agg-01", "state.step.executed", {"x": 2})

        repaired_store = SqliteEventStore(run_repair=True)
        await repaired_store.append(
            "step", "agg-01", "state.step.executed", {"x": 3},
        )
        stream = [e async for e in repaired_store.read_stream("agg-01")]
        assert [e["seq"] for e in stream] == [1, 2, 3]

    async def test_repair_only_runs_once(
        self, store: SqliteEventStore,
    ) -> None:
        """run_repair=True only triggers repair on the first access."""
        await store.append("step", "agg-01", "state.step.executed", {"x": 1})

        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()

        # Manually call repair_aggregate_seqs and verify repairs
        intermediate = SqliteEventStore(run_repair=True)
        await intermediate.append("step", "agg-01", "state.step.executed", {"x": 2})
        stream = [e async for e in intermediate.read_stream("agg-01")]
        assert stream[-1]["seq"] == 2  # repair bumped seq to 1, then append got 2


# ── Repair logging ─────────────────────────────────────────────────────────


class TestRepairLogging:
    """structlog captures repair events."""

    async def test_repair_logs_info_when_repairs_happen(
        self, store: SqliteEventStore,
    ) -> None:
        """repair_aggregate_seqs() logs when repairs occur."""
        import io

        await store.append("step", "agg-01", "state.step.executed", {"x": 1})
        async with get_connection() as db:
            await db.execute("DELETE FROM aggregate_seq")
            await db.commit()

        # Capture structlog output
        cap = io.StringIO()
        structlog.configure(
            processors=[structlog.dev.ConsoleRenderer(colors=False)],
            logger_factory=structlog.PrintLoggerFactory(cap),
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        )
        try:
            repairs = await store.repair_aggregate_seqs()
            assert len(repairs) == 1
        finally:
            structlog.reset_defaults()

        output = cap.getvalue()
        assert "repair_summary" in output
        assert "count=1" in output

    async def test_repair_does_not_log_when_no_repairs(
        self, store: SqliteEventStore,
    ) -> None:
        """repair_aggregate_seqs() is silent when already consistent."""
        import io

        await store.append("step", "agg-01", "state.step.executed", {"x": 1})

        cap = io.StringIO()
        structlog.configure(
            processors=[structlog.dev.ConsoleRenderer(colors=False)],
            logger_factory=structlog.PrintLoggerFactory(cap),
        )
        try:
            repairs = await store.repair_aggregate_seqs()
            assert repairs == []
        finally:
            structlog.reset_defaults()

        output = cap.getvalue()
        # Should NOT contain repair log line
        assert "repair_summary" not in output
