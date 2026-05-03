---
phase: 010-event-store-verifier-10-000
plan: B
type: tdd
autonomous: false
wave: 1
depends_on: []
files_modified:
  - tests/test_events.py
requirements: [EVT-06]
---

<objective>
Add Hypothesis property tests to test_events.py that cover ALL 34 event types with per-type data strategies matching Pydantic schemas. Add idempotent re-append test (same ULID raises IntegrityError), mode-filtering correctness property, and deterministic strategy verification that all strategies use explicit id_ parameters.
</objective>

<threat_model>
ASVS L1 threats for Plan B:
- V5 (Input Validation): Hypothesis strategies must generate valid data that passes Pydantic's extra="forbid" validation. Invalid test data would test the wrong thing.
- V12 (File Resources): Tests operate on temp-isolated SQLite databases — no persistent state.
- V7 (Error Handling): The idempotent re-append test intentionally raises IntegrityError—ensure it's caught and asserted, not silently swallowed.
</threat_model>

<read_first>
- tests/test_events.py (existing patterns: _isolate_db fixture, store fixture, Hypothesis test boilerplate, `_sorted_json` helper)
- src/state_core/events.py (append signature, id_ parameter, seq enforcement)
- src/state_core/schema.py (all 34 event types with exact field names and types for each Data model)
- .planning/milestones/v1/phases/010-event-store-verifier-10-000/010-RESEARCH.md (section 1: strategies, section 6: extension plan)
</read_first>

## Tasks

### Task 1: Add per-event-type data strategies matching all 34 Pydantic schemas

<read_first>
- tests/test_events.py (lines 278-333 — existing Hypothesis test `test_property_append_read_roundtrip`)
- src/state_core/schema.py (all Data models with their field names and types)
</read_first>

<action>
Add new data strategies to `tests/test_events.py` that map each of the 34 event types to its valid data shape:

1. **Define `AGGREGATE_FOR_EVENT` dict** mapping each of the 34 event type strings to its aggregate type string (e.g. `"state.arc.created"` → `"arc"`).

2. **Define `EVENT_DATA_STRATEGIES` dict** mapping each event type to a Hypothesis strategy that produces valid data for that type's Pydantic model. Use `st.fixed_dictionaries()` or `st.builds()` with st.just() for scalars. Examples:

   ```python
   EVENT_DATA_STRATEGIES = {
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
       # ... all 34 types
       "state.step.verify_passed": st.fixed_dictionaries({
           "duration_ms": st.integers(min_value=0, max_value=60000),
       }),
       "state.concept.drilled": st.fixed_dictionaries({
           "score": st.floats(min_value=0.0, max_value=10.0),
           "items_attempted": st.integers(min_value=1, max_value=20),
       }),
       "state.decision.asked": st.fixed_dictionaries({
           "question": st.just("What approach?"),
           "options": st.just([{"option": "A"}]),
       }),
       "state.auth.rotated": st.fixed_dictionaries({
           "provider": st.just("anthropic"),
           "index": st.integers(min_value=0, max_value=5),
       }),
       # For types with empty data (PhaseStartedData, etc)
       "state.phase.started": st.fixed_dictionaries({}),
   }
   ```

3. Each strategy must produce dicts that pass `Model(**data)` for the corresponding Pydantic data model with `extra="forbid"`.

</action>

<acceptance_criteria>
- `EVENT_DATA_STRATEGIES` dict has exactly 34 keys matching all event types from schema.py
- `AGGREGATE_FOR_EVENT` dict has exactly 34 entries
- Each strategy produces valid data for its Pydantic model (verified by `Python -c "from src.state_core.schema import *; ..."` test)
</acceptance_criteria>

### Task 2: Add Hypothesis property test for all-34-event-types round-trip

<read_first>
- tests/test_events.py (lines 278-333 — existing Hypothesis pattern with uuid temp dirs)
</read_first>

<action>
Add a new Hypothesis property test `test_property_all_event_types_roundtrip`:

```python
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    event_type=st.sampled_from(sorted(EVENT_DATA_STRATEGIES.keys())),
    mode_val=st.sampled_from(["build", "teach", "kernel"]),
)
async def test_property_all_event_types_roundtrip(
    tmp_path: Path,
    event_type: str,
    mode_val: str,
) -> None:
    """Hypothesis property: every event type round-trips through append → read_stream."""
    import os, uuid
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
    data = EVENT_DATA_STRATEGIES[event_type].example()

    # Use explicit deterministic ULID
    custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    returned_id = await store.append(
        aggregate_type, aggregate_id, event_type, data,
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
    assert row["data"] == data
```

Key design decisions:
- Uses explicit `id_` parameter to prove deterministic append works for ALL event types
- Asserts the returned ID matches the injected ID
- Asserts data dict is identical after JSON serialization/deserialization
</action>

<acceptance_criteria>
- `test_property_all_event_types_roundtrip` exists and passes at 100 examples
- Every event type is sampled at least once across 100 examples
- `pytest tests/test_events.py::test_property_all_event_types_roundtrip -x --hypothesis-show-statistics` shows all 34 types in the sampled statistics
</acceptance_criteria>

### Task 3: Add same-event idempotent re-append test

<read_first>
- src/state_core/events.py (appends uses UNIQUE(aggregate_id, seq) from migration 0004)
- tests/test_seq_crash_recovery.py (existing UniqueConstraint tests)
</read_first>

<action>
Add `TestIdempotentAppend` class to `tests/test_events.py`:

```python
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
        # Second append with same aggregate_id: seq will be 2 (different from 1)
        # so it won't hit UNIQUE constraint.
        # To test UNIQUE, we need same (aggregate_id, seq).
        # Instead, verify that re-inserting the same id_ returns a new ULID
        # and seq increments correctly — the UNIQUE constraint on (aggregate_id, seq)
        # prevents inserting another row with seq=1 for the same aggregate.
        # Direct SQL test:
        import aiosqlite
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
```

</action>

<acceptance_criteria>
- `TestIdempotentAppend::test_same_ulid_same_seq_raises_integrity_error` passes
- `TestIdempotentAppend::test_append_same_data_different_ulid_seq_increments` passes
- Both tests use explicit id_ parameters or verify ULID determinism
</acceptance_criteria>

### Task 4: Add mode-filtering correctness property test

<read_first>
- src/state_core/events.py (count_events with mode filter — lines 451-472)
- tests/test_events.py (TestDeterminismAndMode class)
</read_first>

<action>
Add `test_property_mode_filtering` to the TestDeterminismAndMode class or as a standalone Hypothesis test:

```python
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
    import os, uuid
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
```

</action>

<acceptance_criteria>
- `test_property_mode_filtering` passes at 50 Hypothesis examples
- Assertion: `count_events("build") + count_events("teach") + count_events("kernel") == count_events()`
</acceptance_criteria>

### Task 5: Verify all Hypothesis strategies use explicit id_ for determinism

<read_first>
- tests/test_events.py (all Hypothesis tests already use explicit id_ in the new Task 2 test)
- Confirm existing test_property_append_read_roundtrip does NOT use explicit id_ (it relies on auto-generated ULID)
</read_first>

<action>
Add a unit test `test_explicit_id_determinism` to `TestDeterminismAndMode`:

```python
async def test_explicit_id_determinism(self, store: SqliteEventStore) -> None:
    """Same explicit id_ + data + ts produces identical stored row (except seq)."""
    custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    custom_ts = "2026-01-01T00:00:00Z"
    data = {"changes_summary": "deterministic"}

    id1 = await store.append(
        "step", "step-a", "state.step.executed", data,
        id_=custom_id, ts=custom_ts, mode="build",
    )
    assert id1 == custom_id

    # Append to a different aggregate with same explicit parameters
    id2 = await store.append(
        "step", "step-b", "state.step.executed", data,
        id_=custom_id, ts=custom_ts, mode="build",
    )
    assert id2 == custom_id

    # Verify the stored JSON is deterministic (same data → same JSON)
    stream_a = [e async for e in store.read_stream("step-a")]
    stream_b = [e async for e in store.read_stream("step-b")]
    assert stream_a[0]["data"] == stream_b[0]["data"]
    assert stream_a[0]["ts"] == stream_b[0]["ts"]
    assert stream_a[0]["mode"] == stream_b[0]["mode"]
```

</action>

<acceptance_criteria>
- `test_explicit_id_determinism` passes
- It proves that identical inputs (id_, ts, data, mode) produce identical stored values across different aggregates
</acceptance_criteria>

## Verification

1. `pytest tests/test_events.py -x -v` — all existing + new tests pass
2. `pytest tests/test_events.py -x -v -k "property"` — all Hypothesis tests pass
3. Verify `EVENT_DATA_STRATEGIES` contains exactly 34 keys by running:
   ```python
   from tests.test_events import EVENT_DATA_STRATEGIES
   assert len(EVENT_DATA_STRATEGIES) == 34
   ```
4. `pytest tests/ --co` (quick check) — no regressions in any test file

## Must Haves

- `EVENT_DATA_STRATEGIES` dict with 34 entries — one per event type from schema.py
- `AGGREGATE_FOR_EVENT` dict with 34 entries
- Property test covering all 34 event types with 100 Hypothesis examples
- Idempotent re-append test (IntegrityError on same aggregate_id+seq)
- Mode-filtering property test (counts sum correctly)
- All new tests use explicit custom ULIDs where relevant (proving deterministic append)
- No modification to existing test logic — only additions
</must_haves>
