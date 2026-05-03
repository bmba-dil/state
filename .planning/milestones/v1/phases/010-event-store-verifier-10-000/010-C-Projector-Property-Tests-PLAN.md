---
phase: 010-event-store-verifier-10-000
plan: C
type: tdd
autonomous: false
wave: 1
depends_on: []
files_modified:
  - tests/test_projector.py
requirements: [EVT-06]
---

<objective>
Extend projector property tests to cover ALL aggregate types (not just step). Add Hypothesis test proving frontmatter determinism across random event sequences. Prove rebuild_all() is deterministic for any mix of event types.
</objective>

<threat_model>
ASVS L1 threats for Plan C:
- V5 (Validation): Hypothesis strategies must match projector handler expectations — all handler functions use `data.get()` which is lenient, but frontmatter JSON must round-trip deterministically.
- V10 (Logic): The projector uses `json.dumps(sort_keys=True, separators=(",", ":"))` for frontmatter. Tests must use the SAME serialization settings when comparing — separator mismatch causes false negatives.
- V12 (File Resources): Tests use temp-isolated DBs — no persistent state risk.
</threat_model>

<read_first>
- tests/test_projector.py (existing patterns: _isolate_db fixture, store fixture, _append_events helper, _read_table helper, _table_checksums helper)
- tests/test_events.py (EVENT_DATA_STRATEGIES and AGGREGATE_FOR_EVENT from Plan B — these must be importable)
- src/state_core/projector.py (HANDLERS dict has 19 handlers for step/slice/concept; other event types are silently skipped)
- src/state_core/schema.py (all event types — projector handles 19 of 34; the non-handled 15 must not cause crashes)
- .planning/milestones/v1/phases/010-event-store-verifier-10-000/010-RESEARCH.md (section 1.2: handler registry, section 6: extension plan)
</read_first>

## Tasks

### Task 1: Add Hypothesis test for rebuild determinism across all aggregate types

<read_first>
- tests/test_projector.py (lines 793-840 — existing Hypothesis test `test_property_rebuild_no_side_effects`)
- tests/test_projector.py (lines 547-616 — TestRebuildIdempotency class)
- tests/test_events.py (EVENT_DATA_STRATEGIES, AGGREGATE_FOR_EVENT — must import from test_events or define inline)
</read_first>

<action>
Add a new Hypothesis test `test_property_all_aggregates_rebuild_determinism` that extends the existing rebuild test to cover ALL aggregate types (not just step):

1. Define inline strategies (or import from test_events if the module structure allows) for all event types whose aggregate types appear in the step/slice/concept groups (these are the ones the projector actually processes). Also include non-handled types (arc, phase, drill, decision, auth, mode) to prove they don't cause crashes.

2. Use a strategy that generates a list of `(aggregate_type, aggregate_id, event_type, data)` tuples.

3. Append all events to an isolated DB.

4. Call `rebuild_all()` twice, compute `_table_checksums()` after each.

5. Assert checksums are identical (determinism).

```python
ALL_AGGREGATE_TYPES = ["arc", "phase", "slice", "step", "concept", "drill", "decision", "auth", "mode"]

# Per-event-type data templates for projects
PROJECTOR_EVENT_DATA = {
    # Step events (10)
    "state.step.discussed": st.fixed_dictionaries({"approach_summary": st.just("Approach")}),
    "state.step.planned": st.fixed_dictionaries({"goal": st.just("Goal"), "verify_contract": st.just([{"check": "x"}])}),
    "state.step.executed": st.fixed_dictionaries({"changes_summary": st.just("Changes")}),
    "state.step.verify_started": st.fixed_dictionaries({"contract": st.just([{"check": "x"}])}),
    "state.step.verify_passed": st.fixed_dictionaries({"duration_ms": st.just(100)}),
    "state.step.verify_failed": st.fixed_dictionaries({"reason": st.just("Bug"), "details": st.just("Details")}),
    "state.step.advanced": st.fixed_dictionaries({"new_state": st.just("reviewing")}),
    "state.step.blocked": st.fixed_dictionaries({"reason": st.just("Blocked")}),
    "state.step.snapshotted": st.fixed_dictionaries({"snapshot_hash": st.just("abc"), "tier": st.just("1")}),
    "state.step.reverted": st.fixed_dictionaries({"snapshot_hash": st.just("abc"), "reason": st.just("Revert")}),
    # Slice events (4)
    "state.slice.planned": st.fixed_dictionaries({"slice_number": st.just(1), "title": st.just("S"), "goal": st.just("G")}),
    "state.slice.worktree_ready": st.fixed_dictionaries({"worktree_name": st.just("wt"), "branch": st.just("main"), "dir": st.just("/tmp")}),
    "state.slice.shipped": st.fixed_dictionaries({"snapshot_hash": st.just("abc")}),
    "state.slice.reverted": st.fixed_dictionaries({"reason": st.just("Bug")}),
    # Concept events (5)
    "state.concept.introduced": st.fixed_dictionaries({"concept_id": st.just("c01"), "name": st.just("C"), "prerequisites": st.just([])}),
    "state.concept.observed": st.fixed_dictionaries({"observation": st.just("O"), "classification": st.just("correct")}),
    "state.concept.drilled": st.fixed_dictionaries({"score": st.just(4.0), "items_attempted": st.just(5)}),
    "state.concept.mastered": st.fixed_dictionaries({"mastery_probability": st.just(0.95)}),
    "state.concept.reviewed": st.fixed_dictionaries({"mastery_delta": st.just(0.05)}),
    # Non-projection event types (15) — minimal data
    "state.arc.created": st.fixed_dictionaries({"title": st.just("A"), "goal": st.just("G")}),
    "state.arc.retired": st.fixed_dictionaries({"reason": st.just("Done")}),
    "state.arc.updated": st.fixed_dictionaries({"changed_fields": st.just(["title"])}),
    "state.phase.planned": st.fixed_dictionaries({"phase_number": st.just(1), "title": st.just("P"), "goal": st.just("G")}),
    "state.phase.started": st.fixed_dictionaries({}),
    "state.phase.verified": st.fixed_dictionaries({"passed": st.just(True), "summary": st.just("OK")}),
    "state.phase.completed": st.fixed_dictionaries({"passed": st.just(True)}),
    "state.drill.prepared": st.fixed_dictionaries({"question_count": st.just(5)}),
    "state.drill.submitted": st.fixed_dictionaries({"answers": st.just([{"q": 1}])}),
    "state.drill.graded": st.fixed_dictionaries({"score": st.just(8.0), "max_score": st.just(10.0)}),
    "state.mode.activated": st.fixed_dictionaries({"mode_value": st.just("build")}),
    "state.decision.asked": st.fixed_dictionaries({"question": st.just("Q"), "options": st.just([{"opt": "A"}])}),
    "state.decision.made": st.fixed_dictionaries({"answer": st.just("A"), "reason": st.just("Best")}),
    "state.auth.refreshed": st.fixed_dictionaries({"provider": st.just("anthropic"), "outcome": st.just("ok")}),
    "state.auth.rotated": st.fixed_dictionaries({"provider": st.just("anthropic"), "index": st.just(1)}),
}
```

```python
@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    event_sequence=st.lists(
        st.sampled_from(sorted(PROJECTOR_EVENT_DATA.keys())),
        min_size=0, max_size=20,
    ),
)
async def test_property_all_aggregates_rebuild_determinism(
    tmp_path: Path,
    event_sequence: list[str],
) -> None:
    """Hypothesis property: any event sequence → rebuild is deterministic.

    For any sequence of event types (including non-projection types like
    arc, phase, drill), running rebuild_all() twice produces identical
    cache tables and the events table is never modified.
    """
    import os, uuid, shutil
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

    # Build a deterministic mapping from event_type to aggregate_type
    event_to_agg = {et: AGGREGATE_FOR_EVENT[et] for et in PROJECTOR_EVENT_DATA if et in AGGREGATE_FOR_EVENT}

    # Count events before
    async with get_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        before = (await cursor.fetchone())[0]

    # Append the event sequence (each to its own aggregate instance)
    for i, event_type in enumerate(event_sequence):
        agg_type = event_to_agg.get(event_type, "step")
        agg_id = f"{agg_type}-{i}"
        data = PROJECTOR_EVENT_DATA[event_type].example()
        await store.append(agg_type, agg_id, event_type, data)

    # Run rebuild_all() twice
    projector = Projector(db=store)
    count1 = await projector.rebuild_all()
    checksum_1 = await _table_checksums()

    count2 = await projector.rebuild_all()
    checksum_2 = await _table_checksums()

    # Assertions
    assert count1 == len(event_sequence)
    assert count1 == count2  # Same number of events processed each time
    assert checksum_1 == checksum_2, "Rebuild must be deterministic"

    # Events table unchanged
    async with get_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        after = (await cursor.fetchone())[0]
    assert before == after
```

Key design:
- Uses `PROJECTOR_EVENT_DATA` with all 34 event types
- Non-projection event types (arc, phase, drill, etc.) MUST be included to prove they don't crash rebuild
- Each event goes to its own aggregate (i-based ID) so seq starts at 1 each time
- Checksum comparison proves bit-identical cache table output
- Deadline=None for safety (10K-scale check could be slow)

</action>

<acceptance_criteria>
- `test_property_all_aggregates_rebuild_determinism` passes at 50 Hypothesis examples
- Non-projection event types (arc, phase, drill, decision, auth, mode) are included and don't cause crashes
- `checksum_1 == checksum_2` is asserted
- events table count is unchanged before/after rebuild
</acceptance_criteria>

### Task 2: Add frontmatter determinism property test

<read_first>
- src/state_core/projector.py (_merge_frontmatter — lines 58-75, uses `json.dumps(sort_keys=True, separators=(",", ":"))`)
- tests/test_projector.py (TestRebuildIdempotency class, _table_checksums function)
</read_first>

<action>
Add `test_property_frontmatter_determinism` to TestRebuildIdempotency class:

```python
async def test_property_frontmatter_determinism(self, store: SqliteEventStore) -> None:
    """Same event sequence → identical frontmatter JSON in cache tables.

    The projector's _merge_frontmatter uses sort_keys=True with compact
    separators. Two rebuilds must produce bit-identical frontmatter values.
    """
    await _append_events(store, [
        ("step", "step-01", "state.step.discussed", {"approach_summary": "Study"}),
        ("step", "step-01", "state.step.planned", {"goal": "Build X", "verify_contract": [{"check": "works"}]}),
        ("step", "step-01", "state.step.executed", {"changes_summary": "Done"}),
        ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "Core", "goal": "Build core"}),
        ("slice", "slice-01", "state.slice.worktree_ready", {"worktree_name": "feat", "branch": "main", "dir": "/tmp"}),
        ("concept", "concept-01", "state.concept.introduced", {"concept_id": "c01", "name": "Poly", "prerequisites": ["OOP"]}),
        ("concept", "concept-01", "state.concept.drilled", {"score": 4.0, "items_attempted": 5}),
    ])

    projector = Projector(db=store)

    # Rebuild twice
    await projector.rebuild_all()
    fm_1 = await _read_table_frontmatter()
    await projector.rebuild_all()
    fm_2 = await _read_table_frontmatter()

    # Frontmatter must be identical across rebuilds
    assert fm_1 == fm_2

    # Also: rebuild produces same result as apply_event
    # Create a fresh copy of the DB with same events
    import os, uuid
    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path_b = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH_B"] = str(db_path_b)
    old_path = os.environ.get("STATE_DB_PATH", "")
    os.environ["STATE_DB_PATH"] = str(db_path_b)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = unique / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    await migrate()
    store_b = SqliteEventStore()
    # Same events, same order
    for agg_type, agg_id, ev_type, data in [
        ("step", "step-01", "state.step.discussed", {"approach_summary": "Study"}),
        # ... same events
    ]:
        await store_b.append(agg_type, agg_id, ev_type, data)
    projector_b = Projector(db=store_b)
    await projector_b.rebuild_all()
    fm_3 = await _read_table_frontmatter()

    os.environ["STATE_DB_PATH"] = old_path
    del os.environ["STATE_DB_PATH_B"]

    # Same events in different DB → identical frontmatter
    assert fm_1 == fm_3
```

Also add a helper `_read_table_frontmatter()`:

```python
async def _read_table_frontmatter() -> dict[str, str]:
    """Return {table_name: json_dumps_of_frontmatter_column} for all cache tables."""
    result: dict[str, str] = {}
    for table in ("steps", "slices", "concepts"):
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"SELECT id, frontmatter FROM {table} ORDER BY id")
            rows = await cursor.fetchall()
            frontmatters = []
            for row in rows:
                d = dict(row)
                raw = d.get("frontmatter", "{}")
                if isinstance(raw, str):
                    frontmatters.append(json.loads(raw))
                else:
                    frontmatters.append(raw)
            result[table] = json.dumps(frontmatters, sort_keys=True)
    return result
```

</action>

<acceptance_criteria>
- `test_property_frontmatter_determinism` passes
- Frontmatter is bit-identical across two rebuilds
- Frontmatter is bit-identical across two independent DBs with the same events
</acceptance_criteria>

## Verification

1. `pytest tests/test_projector.py -x -v` — all existing + new tests pass (no regressions)
2. `pytest tests/test_projector.py -x -v -k "property"` — both Hypothesis tests pass
3. Manually verify: new Hypothesis test includes non-projection event types (arc, phase, drill, decision, auth, mode)
4. `pytest tests/ --co` — full test suite passes with no regressions from Plan B changes either

## Must Haves

- `test_property_all_aggregates_rebuild_determinism` covers all 9 aggregate types
- Non-handled event types (arc, phase, drill, decision, auth, mode) are INCLUDE in the strategy (not excluded)
- Frontmatter determinism test proves cross-DB identity
- All existing projector tests continue to pass (no modifications to existing test logic)
</must_haves>
