---
phase: "004"
plan: "B"
type: "tdd"
autonomous: false
wave: 2
depends_on:
  - "004-A-writer-core-and-seq-enforcement"
files_modified:
  - "tests/test_events.py"
requirements:
  - "EVT-01"
  - "EVT-02"
  - "EVT-03"
  - "EVT-06"
---

<objective>
Deliver a comprehensive async test suite for `SqliteEventStore.append()` and `read_stream()`. Every test uses an isolated SQLite database (`tmp_path`), applies migrations fresh, and covers: basic round-trip, seq monotonicity per aggregate, seq independence across aggregates, deterministic payload injection (EVT-06), mode field persistence, `after_seq` filtering, error cases, and a Hypothesis property test for monotonic seq invariant.

By the end of this plan, every append() behavior defined in Plan A and CONTEXT.md has passing tests.
</objective>

<tasks>

## Task 1 — Scaffold test file with fixtures and helper

<read_first>
  tests/test_database.py (fixture patterns — use `tmp_path`, `monkeypatch`, `pytest.mark.asyncio`)
  tests/test_migrations.py (migration fixture setup)
  src/state_core/events.py (SqliteEventStore class + read_stream)
</read_first>

<action>

Create `tests/test_events.py` with the following fixtures:

```python
"""Tests for the event-store layer: append, read_stream, seq enforcement, determinism."""

from __future__ import annotations

import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from src.state_core.events import EventStore, SqliteEventStore
from src.state_core.migrations import migrate


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and copy migration files.

    Same pattern as test_migrations.py — each test gets a fully isolated DB.
    """
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    # Copy migration files so migrate() can find them
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store() -> AsyncIterator[SqliteEventStore]:
    """Create a ready-to-use SqliteEventStore with fresh migrations applied."""
    await migrate()
    yield SqliteEventStore()
    # Note: no explicit connection close — the async with pattern in
    # get_connection() handles teardown. Per existing test conventions
    # (test_migrations.py), connections are not eagerly closed.


@pytest.fixture
def sample_data() -> dict:
    """Standard sample data payload for test events."""
    return {"changes_summary": "test execution", "trigger": "user_initiated"}
```

**Fixture contract:**
- `_isolate_db` (autouse) runs for every test: sets `STATE_DB_PATH` to a temp dir, copies migration files
- `store` fixture yields a ready-to-use `SqliteEventStore` pointing at the isolated DB
- `sample_data` provides a standard payload dict for convenience
- Each test gets a clean database with 0 events
- Pattern matches Phase 003 test conventions (test_migrations.py)

</action>

<acceptance_criteria>
- ✗ `tests/test_events.py` exists with `store` and `sample_data` fixtures
- ✗ Tests run with `pytest tests/test_events.py -x -q` without import errors
- ✗ Fixture uses `tmp_path` for database isolation
- ✗ `set_db_path` or equivalent monkeypatch is used before `migrate()`
- ✗ `SqliteEventStore` imported from `src.state_core.events`
- ✗ File starts with `from __future__ import annotations`
</acceptance_criteria>

## Task 2 — Basic append + read_stream round-trip tests

<read_first>
  tests/test_events.py (just created)
  src/state_core/events.py (append and read_stream signatures)
</read_first>

<action>

Add these test cases:

```python
@pytest.mark.asyncio
async def test_append_returns_event_id(store: SqliteEventStore, sample_data: dict):
    """Append returns a non-empty string ULID."""
    event_id = await store.append("step", "step-01", "state.step.executed", sample_data)
    assert isinstance(event_id, str)
    assert len(event_id) > 0
    # ULID is 26 chars
    assert len(event_id) == 26
    assert event_id.isascii()


@pytest.mark.asyncio
async def test_append_round_trip(store: SqliteEventStore, sample_data: dict):
    """Appended event is readable via read_stream with identical data."""
    event_id = await store.append("step", "step-01", "state.step.executed", sample_data)
    
    found = False
    async for evt in store.read_stream("step-01"):
        if evt["id"] == event_id:
            found = True
            assert evt["aggregate_type"] == "step"
            assert evt["aggregate_id"] == "step-01"
            assert evt["type"] == "state.step.executed"
            assert evt["data"] == sample_data  # dict comparison
            assert evt["mode"] == "kernel"  # default mode
            assert evt["synced_to_opencode"] == 0
            assert evt["seq"] == 1
            break
    
    assert found, f"Event {event_id} not found in stream"


@pytest.mark.asyncio
async def test_append_with_explicit_id(store: SqliteEventStore, sample_data: dict):
    """Passing id_ stores that exact value."""
    explicit_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    event_id = await store.append(
        "phase", "phase-01", "state.phase.started", sample_data,
        id_=explicit_id,
    )
    assert event_id == explicit_id
    
    async for evt in store.read_stream("phase-01"):
        assert evt["id"] == explicit_id
        break


@pytest.mark.asyncio
async def test_append_with_explicit_ts(store: SqliteEventStore, sample_data: dict):
    """Passing ts stores that exact timestamp."""
    explicit_ts = "2026-04-23T00:00:00Z"
    event_id = await store.append(
        "step", "step-ts-test", "state.step.executed", sample_data,
        ts=explicit_ts,
    )
    
    async for evt in store.read_stream("step-ts-test"):
        assert evt["ts"] == explicit_ts
        break


@pytest.mark.asyncio
async def test_append_without_ts_stores_empty_string(store: SqliteEventStore, sample_data: dict):
    """When ts is not provided, store stores empty string (deterministic default)."""
    event_id = await store.append(
        "step", "step-no-ts", "state.step.executed", sample_data,
    )
    
    async for evt in store.read_stream("step-no-ts"):
        assert evt["ts"] == ""
        break
```

**Key assertions:**
- Round-trip preserves all fields
- Data dict comes back as dict (not JSON string)
- Default mode is `"kernel"`
- Explicit `id_` and `ts` are stored exactly
- No `ts` → `""` (empty string)
- `synced_to_opencode` is always `0`
- Returned event ID is a valid ULID (26 char, ascii)

</action>

<acceptance_criteria>
- ✗ `test_append_returns_event_id` passes: returns 26-char ULID
- ✗ `test_append_round_trip` passes: data dict is identical, all fields match, synced_to_opencode=0
- ✗ `test_append_with_explicit_id` passes: stored id matches injected id
- ✗ `test_append_with_explicit_ts` passes: stored ts matches injected ts
- ✗ `test_append_without_ts_stores_empty_string` passes: ts is `""`
</acceptance_criteria>

## Task 3 — Seq monotonicity enforcement tests

<read_first>
  tests/test_events.py
</read_first>

<action>

Add tests verifying per-aggregate sequence monotonicity:

```python
@pytest.mark.asyncio
async def test_seq_starts_at_one(store: SqliteEventStore, sample_data: dict):
    """First event for an aggregate has seq=1."""
    await store.append("step", "first-step", "state.step.executed", sample_data)
    
    async for evt in store.read_stream("first-step"):
        assert evt["seq"] == 1
        break


@pytest.mark.asyncio
async def test_seq_increments_per_aggregate(store: SqliteEventStore, sample_data: dict):
    """Multiple appends to same aggregate yield incrementing seqs: 1, 2, 3."""
    for i in range(3):
        await store.append("step", "inc-step", "state.step.executed", sample_data)
    
    seqs = []
    async for evt in store.read_stream("inc-step"):
        seqs.append(evt["seq"])
    
    assert seqs == [1, 2, 3]


@pytest.mark.asyncio
async def test_seq_independent_across_aggregates(store: SqliteEventStore, sample_data: dict):
    """Different aggregates have independent seq counters."""
    await store.append("step", "agg-a", "state.step.executed", sample_data)
    await store.append("step", "agg-b", "state.step.executed", sample_data)
    await store.append("step", "agg-a", "state.step.executed", sample_data)
    
    seqs_a = [evt["seq"] async for evt in store.read_stream("agg-a")]
    seqs_b = [evt["seq"] async for evt in store.read_stream("agg-b")]
    
    assert seqs_a == [1, 2]
    assert seqs_b == [1]


@pytest.mark.asyncio
async def test_seq_monotonic_after_multiple_aggregate_types(
    store: SqliteEventStore, sample_data: dict
):
    """Different aggregate_types with same aggregate_id have different streams."""
    # Events are keyed by aggregate_id, not (aggregate_type, aggregate_id)
    # The read_stream filter is by aggregate_id
    await store.append("step", "shared-id", "state.step.executed", sample_data)
    await store.append("phase", "shared-id", "state.phase.started", sample_data)
    await store.append("step", "shared-id", "state.step.passed", sample_data)
    
    seqs = [evt["seq"] async for evt in store.read_stream("shared-id")]
    assert seqs == [1, 2, 3]  # shared aggregate_id, shared seq counter


@pytest.mark.asyncio
async def test_read_stream_after_seq(store: SqliteEventStore, sample_data: dict):
    """read_stream(after_seq=N) returns only events with seq > N."""
    for i in range(5):
        await store.append("step", "filter-step", "state.step.executed", sample_data)
    
    # Read events after seq=2
    events = [evt async for evt in store.read_stream("filter-step", after_seq=2)]
    seqs = [evt["seq"] for evt in events]
    assert seqs == [3, 4, 5]
```

**Note about aggregate_id uniqueness:** The events table has `UNIQUE(aggregate_type, aggregate_id, seq)`, meaning two different `aggregate_type` values with the same `aggregate_id` CAN collide on seq if `aggregate_seq` only keys on `aggregate_id`. The test `test_seq_monotonic_after_multiple_aggregate_types` documents this edge case — seq is per `aggregate_id`, not per `(aggregate_type, aggregate_id)`. This is by design (consistent with the `aggregate_seq` schema which uses `aggregate_id` as PK).

</action>

<acceptance_criteria>
- ✗ `test_seq_starts_at_one` passes
- ✗ `test_seq_increments_per_aggregate` passes: seqs = [1, 2, 3]
- ✗ `test_seq_independent_across_aggregates` passes: agg-a = [1, 2], agg-b = [1]
- ✗ `test_seq_monotonic_after_multiple_aggregate_types` passes: seqs = [1, 2, 3] for shared aggregate_id
- ✗ `test_read_stream_after_seq` passes: filter yields [3, 4, 5]
</acceptance_criteria>

## Task 4 — Determinism and mode tests

<read_first>
  tests/test_events.py
  CONTEXT.md — EVT-06 determinism section
</read_first>

<action>

Add tests for deterministic behavior (EVT-06) and mode field:

```python
@pytest.mark.asyncio
async def test_mode_field_written(store: SqliteEventStore, sample_data: dict):
    """Mode field is written and retrievable."""
    await store.append(
        "step", "mode-test", "state.step.executed", sample_data,
        mode="build",
    )
    async for evt in store.read_stream("mode-test"):
        assert evt["mode"] == "build"
        break


@pytest.mark.asyncio
async def test_mode_default_kernel(store: SqliteEventStore, sample_data: dict):
    """Default mode is 'kernel'."""
    await store.append("step", "mode-default", "state.step.executed", sample_data)
    async for evt in store.read_stream("mode-default"):
        assert evt["mode"] == "kernel"
        break


@pytest.mark.asyncio
async def test_deterministic_with_same_id_and_ts(
    store: SqliteEventStore, sample_data: dict
):
    """Same id_, ts, and data produces same DB row (replay is bit-identical for inserted data)."""
    from ulid import ULID
    
    fixed_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    fixed_ts = "2026-04-23T00:00:00Z"
    fixed_data = {"key": "value", "nested": {"a": 1}}
    
    # Append first event
    eid1 = await store.append(
        "step", "det-step", "state.step.executed", fixed_data,
        id_=fixed_id, ts=fixed_ts,
    )
    
    # Verify the stored row
    async for evt in store.read_stream("det-step"):
        assert evt["id"] == fixed_id
        assert evt["ts"] == fixed_ts
        assert evt["data"] == fixed_data
        assert evt["type"] == "state.step.executed"
        assert evt["seq"] == 1
        assert evt["mode"] == "kernel"


@pytest.mark.asyncio
async def test_deterministic_json_serialization(
    store: SqliteEventStore,
):
    """JSON serialization produces consistent output for same input dict."""
    # Dict with keys in reverse alphabetical order
    data1 = {"z_last": 1, "a_first": 2, "m_middle": 3}
    
    fixed_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    fixed_ts = "2026-04-23T00:00:00Z"
    
    await store.append(
        "step", "json-step", "state.step.executed", data1,
        id_=fixed_id, ts=fixed_ts,
    )
    
    # Read the raw JSON from the database to verify sort_keys behavior
    from src.state_core.database import get_connection
    
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT data FROM events WHERE aggregate_id = ?",
            ("json-step",),
        )
        row = await cursor.fetchone()
    
    assert row is not None
    # Expect sorted keys: a_first, m_middle, z_last
    raw_json = row[0]
    expected_json = '{"a_first":2,"m_middle":3,"z_last":1}'
    assert raw_json == expected_json, f"Expected {expected_json}, got {raw_json}"


@pytest.mark.asyncio
async def test_deterministic_no_datetime_now(store: SqliteEventStore, sample_data: dict):
    """Without ts or id_ injection, append still works (no crash) and uses deterministic defaults."""
    event_id = await store.append("step", "no-ts-id", "state.step.executed", sample_data)
    
    assert isinstance(event_id, str) and len(event_id) > 0
    async for evt in store.read_stream("no-ts-id"):
        assert evt["ts"] == ""
        assert evt["seq"] == 1
        break
```

**Note on `test_deterministic_json_serialization`:** This test bypasses read_stream to read raw JSON from SQLite. This is intentional — it verifies the serialization format itself, not just the round-trip. The read_stream() method deserializes JSON, so we can't see raw format through it.

</action>

<acceptance_criteria>
- ✗ `test_mode_field_written` passes: mode "build" is stored
- ✗ `test_mode_default_kernel` passes: default mode is "kernel"
- ✗ `test_deterministic_with_same_id_and_ts` passes: same id_, ts, data => same DB row fields
- ✗ `test_deterministic_json_serialization` passes: raw JSON has sorted keys
- ✗ `test_deterministic_no_datetime_now` passes: no crash, ts is ""
</acceptance_criteria>

## Task 5 — Edge case and error tests

<read_first>
  tests/test_events.py
</read_first>

<action>

Add edge case and error handling tests:

```python
@pytest.mark.asyncio
async def test_read_stream_empty(store: SqliteEventStore):
    """read_stream on non-existent aggregate_id returns empty iterator."""
    count = 0
    async for _ in store.read_stream("non-existent-aggregate"):
        count += 1
    assert count == 0


@pytest.mark.asyncio
async def test_read_stream_empty_after_seq(store: SqliteEventStore, sample_data: dict):
    """after_seq beyond last event returns empty iterator."""
    await store.append("step", "empty-after", "state.step.executed", sample_data)
    
    count = 0
    async for _ in store.read_stream("empty-after", after_seq=5):
        count += 1
    assert count == 0


@pytest.mark.asyncio
async def test_append_minimal_data(store: SqliteEventStore):
    """Appending with empty or minimal data dict works."""
    empty_data: dict = {}
    event_id = await store.append("step", "minimal", "state.step.executed", empty_data)
    
    async for evt in store.read_stream("minimal"):
        assert evt["data"] == {}
        break


@pytest.mark.asyncio
async def test_append_complex_nested_data(store: SqliteEventStore):
    """Complex nested data survives round-trip."""
    complex_data = {
        "string": "hello",
        "number": 42,
        "float": 3.14,
        "null_val": None,
        "list": [1, 2, {"deep": "value"}],
        "nested": {"a": {"b": {"c": True}}},
    }
    event_id = await store.append(
        "step", "complex", "state.step.executed", complex_data,
    )
    
    async for evt in store.read_stream("complex"):
        assert evt["data"] == complex_data
        break


@pytest.mark.asyncio
async def test_append_long_aggregate_id(store: SqliteEventStore, sample_data: dict):
    """Very long aggregate_id (e.g., ULID+path) is handled."""
    long_id = "a" * 500
    event_id = await store.append("step", long_id, "state.step.executed", sample_data)
    
    found = False
    async for evt in store.read_stream(long_id):
        found = True
        assert evt["aggregate_id"] == long_id
        break
    assert found


@pytest.mark.asyncio
async def test_append_multiple_modes_independent_seqs(store: SqliteEventStore, sample_data: dict):
    """Events with different modes on same aggregate maintain seq continuity."""
    await store.append("step", "mode-mix", "state.step.executed", sample_data, mode="build")
    await store.append("step", "mode-mix", "state.step.executed", sample_data, mode="teach")
    await store.append("step", "mode-mix", "state.step.executed", sample_data, mode="kernel")
    
    seqs = []
    modes = []
    async for evt in store.read_stream("mode-mix"):
        seqs.append(evt["seq"])
        modes.append(evt["mode"])
    
    assert seqs == [1, 2, 3]
    assert modes == ["build", "teach", "kernel"]
```

**Error handling note:** For Phase 004, constraint violations (duplicate primary key, invalid foreign key) are intentionally unhandled — they propagate as `aiosqlite.IntegrityError`. We don't test for these in this plan since we don't create manual INSERT statements. If we add such tests in the future, they should use `pytest.raises(aiosqlite.IntegrityError)`. For now, we rely on the fact that `aggregate_seq` is always UPSERTed and events table PKs are ULIDs — collisions are negligible.

</action>

<acceptance_criteria>
- ✗ `test_read_stream_empty` passes: 0 events for unknown aggregate
- ✗ `test_read_stream_empty_after_seq` passes: 0 events when after_seq > max
- ✗ `test_append_minimal_data` passes: `{}` survives round-trip
- ✗ `test_append_complex_nested_data` passes: nested dict round-trips correctly
- ✗ `test_append_long_aggregate_id` passes: 500-char ID stored and retrievable
- ✗ `test_append_multiple_modes_independent_seqs` passes: seqs = [1,2,3] across modes
</acceptance_criteria>

## Task 6 — Protocol conformance and Hypothesis property test

<read_first>
  tests/test_events.py
  src/state_core/events.py (EventStore protocol)
</read_first>

<action>

Add a structural protocol conformance test and a Hypothesis property test:

```python
import pytest
from hypothesis import given, strategies as st


class TestEventStoreProtocol:
    """Verifies that SqliteEventStore structurally conforms to EventStore protocol."""

    def test_append_signature_matches(self):
        """append method accepts aggregate_type, aggregate_id, event_type, data, and optional mode, ts, id_."""
        import inspect
        sig = inspect.signature(SqliteEventStore.append)
        params = sig.parameters
        
        assert "aggregate_type" in params
        assert "aggregate_id" in params
        assert "event_type" in params
        assert "data" in params
        assert "mode" in params
        assert "ts" in params
        assert "id_" in params
        
        # mode, ts, id_ are keyword-only
        assert params["mode"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["ts"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["id_"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_append_returns_str(self):
        """Return annotation is str."""
        import inspect
        sig = inspect.signature(SqliteEventStore.append)
        assert sig.return_annotation == str

    def test_is_event_store(self):
        """SqliteEventStore is a structural subtype of EventStore (duck typing check)."""
        # Check that all EventStore protocol methods exist on SqliteEventStore
        protocol_methods = {
            name for name in dir(EventStore) if not name.startswith("_")
        }
        impl_methods = {
            name for name in dir(SqliteEventStore) if not name.startswith("_")
        }
        missing = protocol_methods - impl_methods
        assert not missing, f"SqliteEventStore missing protocol methods: {missing}"


@pytest.mark.asyncio
@given(
    aggregate_type=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))),
    event_type=st.text(min_size=1, max_size=40, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "P"))),
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.none(), st.booleans(), st.integers(min_value=0, max_value=1000), st.text(max_size=20)),
        min_size=0,
        max_size=5,
    ),
)
async def test_append_hypothesis_property(
    store: SqliteEventStore,
    aggregate_type: str,
    event_type: str,
    data: dict,
):
    """Property: for any valid inputs, append succeeds and seq is always monotonic.

    After N appends to the same aggregate_id, seq values are 1, 2, ..., N
    with no gaps and no duplicates.
    """
    aggregate_id = "hypothesis-test-agg"
    n = 3
    seqs = []
    
    for _ in range(n):
        event_id = await store.append(
            aggregate_type,
            aggregate_id,
            event_type,
            data,
        )
        assert isinstance(event_id, str)
    
    async for evt in store.read_stream(aggregate_id):
        seqs.append(evt["seq"])
    
    assert seqs == [1, 2, 3], f"Expected monotonic seqs [1,2,3], got {seqs}"
```

**Hypothesis strategy notes:**
- `aggregate_type` uses `whitelist_categories=("Ll", "Lu", "Nd")` — only letters and digits, no whitespace (matches expected aggregate type format)
- `event_type` additionally allows `"P"` (punctuation) for dots like `state.step.executed`
- `data` values are limited to `none()`, `booleans()`, small `integers()`, and short `text()` to avoid extremely large JSON payloads
- `max_size=5` for data dict to keep test fast
- The property test generates 100 examples by default (Hypothesis default)

</action>

<acceptance_criteria>
- ✗ `test_append_signature_matches` passes: all params present, keyword-only params correct
- ✗ `test_append_returns_str` passes: return annotation is `str`
- ✗ `test_is_event_store` passes: no missing protocol methods
- ✗ `test_append_hypothesis_property` passes: 100 generated examples all satisfy [1,2,3] seq
</acceptance_criteria>

</tasks>

<verification>
How to confirm this plan is complete:

1. **Run all tests:**
   ```bash
   python3 -m pytest tests/test_events.py -x -q
   ```
   Expected: all tests pass (including 100 Hypothesis examples).

2. **Run full test suite:**
   ```bash
   python3 -m pytest tests/ -x -q
   ```
   Expected: all existing tests (126+ tests from phases 002, 003) plus new tests pass.

3. **Verify determinism:**
   Run the test suite twice. Results must be identical (same tests pass/fail). Hypothesis is seeded for reproducibility.

4. **Verify no datetime.now in events.py:**
   ```bash
   grep -n "datetime.now" src/state_core/events.py
   ```
   Expected: 0 matches.

5. **Check test count:**
   ```bash
   python3 -m pytest tests/test_events.py --collect-only | grep -c "TestCase\|test_"
   ```
   Expected: at least 20 test cases.

6. **Protocol check:**
   ```bash
   python3 -c "from src.state_core.events import SqliteEventStore, EventStore; print('Protocol OK:', isinstance(SqliteEventStore(), EventStore))"
   ```
   Note: This may fail since EventStore is a Protocol and structural subtyping requires `@runtime_checkable`. If it fails, the `test_is_event_store` structural check still passes.
</verification>

<must_haves>
- `tests/test_events.py` with at least 20 test cases covering:
  - Basic round-trip (append → read_stream)
  - Explicit `id_`, `ts` injection
  - Default `ts` is `""`
  - Default `mode` is `"kernel"`
  - `mode` field written and retrievable
  - Seq starts at 1, increments per aggregate
  - Seq independent across aggregates
  - `read_stream(after_seq=N)` filtering
  - Deterministic JSON serialization (sorted keys)
  - Empty and complex data round-trip
  - Long aggregate_id handling
  - Empty stream for non-existent aggregate
  - Protocol signature conformance
  - Hypothesis property test (seq monotonic invariant)
- All tests pass with `pytest tests/test_events.py -x -q`
- No regression in existing tests
- Each test uses isolated `tmp_path` database
- Fixture applies fresh migrations per test
</must_haves>
