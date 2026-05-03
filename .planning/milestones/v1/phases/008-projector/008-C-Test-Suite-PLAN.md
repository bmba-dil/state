---
phase: 008
plan: 3 of 3
type: auto
autonomous: true
wave: 2
depends_on:
  - PLAN-001-Projector-Core
files_modified:
  - tests/test_projector.py
requirements:
  - EVT-02
---

# Plan 3: Test Suite

<objective>
Create `tests/test_projector.py` with comprehensive test coverage for the `Projector` class and its projection handlers. Covers: per-event-type projection correctness for all 19 handlers, multi-event replay, full rebuild, rebuild idempotency, crash-atomicity (transaction rollback), empty event log, unknown event type tolerance, and Hypothesis property tests for determinism.

Pattern follows `tests/test_reconciler.py` (DB isolation fixtures, `store` fixture, `_append_events` helper, `@pytest.mark.asyncio` test classes).
</objective>

<threat_model>
| Severity | Threat | Mitigation |
|----------|--------|------------|
| **LOW** | Test leakage across Hypothesis examples — each example shares a DB if isolation is not per-example | Hypothesis `@given` tests use `uuid.uuid4().hex` subdirectory per example, identical to the pattern in `tests/test_events.py` lines 303-313 |
| **LOW** | Test false positive if handler returns wrong but test checks wrong column | Every projection assertion checks ALL columns of the cache table, not just the `state` field. Full row dict comparison where possible |
| **LOW** | Missing edge case — empty event log not tested | Test `test_rebuild_empty_log` explicitly: zero events → all cache tables empty |
</threat_model>

<tasks>

### Task 1: Fixtures, imports, and helper functions

<read_first>
- tests/test_reconciler.py lines 1-79 (fixtures + helper pattern — exact structural analog)
- tests/test_events.py lines 1-48 (DB isolation fixture pattern)
- src/state_core/projector.py (Plan 1 — the module under test)
- .state/migrations/0002_cache.sql (table schemas for verification queries)
</read_first>

<action>
Create `tests/test_projector.py` with the full structure.

**Imports at the top of the file:**
```python
"""Tests for state_core.projector — Projector + projection handlers.

Covers: per-event-type projection for all 19 handlers, multi-event replay,
full rebuild, rebuild idempotency, crash-atomicity rollback, empty event log,
unknown event type tolerance, and Hypothesis property tests for determinism.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.projector import HANDLERS, Projector
```

**DB isolation fixture** (autouse=True, identical to test_reconciler.py lines 38-48):
```python
@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)
```

**Store fixture** (identical to test_reconciler.py lines 50-54):
```python
@pytest.fixture
async def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()
```

**Event append helper** (generalized version of test_reconciler.py lines 65-79):
```python
async def _append_events(
    store: SqliteEventStore,
    events: list[tuple[str, str, str, dict[str, Any]]],
) -> list[str]:
    """Append multiple events and return their IDs.

    Each tuple is (aggregate_type, aggregate_id, event_type, data).
    """
    ids: list[str] = []
    for aggregate_type, aggregate_id, event_type, data in events:
        id_ = await store.append(
            aggregate_type, aggregate_id, event_type, data,
        )
        ids.append(id_)
    return ids
```

**Cache table read helper** (for verification queries):
```python
async def _read_table(table: str) -> list[dict[str, Any]]:
    """Return all rows from a cache table as dicts with JSON-typed columns parsed."""
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(f"SELECT * FROM {table} ORDER BY id")
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("frontmatter"), str):
                d["frontmatter"] = json.loads(d["frontmatter"])
            result.append(d)
        return result
```
</action>

<acceptance_criteria>
- File `tests/test_projector.py` exists
- `grep -c "_isolate_db" tests/test_projector.py` returns 1
- `grep -c "async def store" tests/test_projector.py` returns 1
- `grep -c "def _append_events" tests/test_projector.py` returns 1
- `grep -c "def _read_table" tests/test_projector.py` returns 1
- `grep -c "from src.state_core.projector import" tests/test_projector.py` returns 1
- `python3 -c "import ast; ast.parse(open('tests/test_projector.py').read())"` exits 0
</acceptance_criteria>

---

### Task 2: Per-event-type projection test classes (all 19 handlers)

<read_first>
- tests/test_projector.py (file from Task 1 — must read before adding test classes)
- src/state_core/projector.py (all 19 handler implementations — test each one)
- .state/migrations/0002_cache.sql (cache table column types for verification)
</read_first>

<action>
Add three test classes, each covering exactly the handlers for that aggregate.

**`class TestStepProjection`** — 10 test methods, one per `state.step.*` event type.

Each test method:
1. Appends a single step event to the store
2. Creates a `Projector(store)` instance
3. Reads the event back (via `[e async for e in store.read_stream(agg_id)]`)
4. Calls `await projector.apply_event(event_row)` where `event_row` is the full event dict
5. Reads the `steps` cache table via `_read_table("steps")`
6. Asserts the row exists and has correct values for ALL columns:
   - `id` matches aggregate_id
   - `state` matches the expected state transition
   - `title` matches expected title
   - `slice_id` is populated (from event data)
   - `frontmatter` is a non-empty dict with expected keys

Test methods to create:

| Method | Event Type | Data | Expected State | Key Assertions |
|--------|-----------|------|---------------|----------------|
| `test_step_discussed` | `state.step.discussed` | `{"approach_summary": "Explore options"}` | `"discussing"` | title="Explore options", frontmatter has approach_summary |
| `test_step_planned` | `state.step.planned` | `{"goal": "Build X", "verify_contract": [{"check": "works"}]}` | `"planning"` | goal and verify_contract in frontmatter |
| `test_step_executed` | `state.step.executed` | `{"changes_summary": "Added feature Y"}` | `"executing"` | changes_summary in frontmatter |
| `test_step_verify_started` | `state.step.verify_started` | `{"contract": [{"check": "works"}]}` | `"verifying"` | state changes only |
| `test_step_verify_passed` | `state.step.verify_passed` | `{"duration_ms": 1500}` | `"done"` | duration_ms in frontmatter |
| `test_step_verify_failed` | `state.step.verify_failed` | `{"reason": "Bug", "details": "Crash on input X"}` | `"executing"` | reason and details in frontmatter |
| `test_step_advanced` | `state.step.advanced` | `{"new_state": "reviewing"}` | `"reviewing"` | state matches data.new_state |
| `test_step_blocked` | `state.step.blocked` | `{"reason": "Waiting for API key"}` | `"blocked"` | reason in frontmatter |
| `test_step_snapshotted` | `state.step.snapshotted` | `{"snapshot_hash": "abc123", "tier": "1"}` | (preserves prior state) | snapshot_hash in frontmatter, state unchanged |
| `test_step_reverted` | `state.step.reverted` | `{"snapshot_hash": "def456", "reason": "Bug found"}` | (preserves prior state) | snapshot_hash and reason in frontmatter |

For sequential state tests (verify_failed, snapshotted, reverted), append a prior event first (e.g., discussed → planned → executed → the target event) and verify the state transitions as well.

**`class TestSliceProjection`** — 4 test methods:

| Method | Event Type | Data | Expected State | Key Assertions |
|--------|-----------|------|---------------|----------------|
| `test_slice_planned` | `state.slice.planned` | `{"slice_number": 1, "title": "Core", "goal": "Build core"}` | `"planned"` | title, slice_number, goal in frontmatter |
| `test_slice_worktree_ready` | `state.slice.worktree_ready` | `{"worktree_name": "feat-x", "branch": "feat/x", "dir": "/tmp/wt"}` | `"in_progress"` | worktree_dir, worktree_branch set |
| `test_slice_shipped` | `state.slice.shipped` | `{"snapshot_hash": "abc123"}` | `"shipped"` | snapshot_hash in frontmatter |
| `test_slice_reverted` | `state.slice.reverted` | `{"reason": "Bug found"}` | `"reverted"` | reason in frontmatter |

For worktree_ready → shipped → reverted, build on prior events.

**`class TestConceptProjection`** — 5 test methods:

| Method | Event Type | Data | Expected State | Key Assertions |
|--------|-----------|------|---------------|----------------|
| `test_concept_introduced` | `state.concept.introduced` | `{"concept_id": "c01", "name": "Polymorphism", "prerequisites": ["classes"]}` | `"introduced"` | name, prerequisites in frontmatter |
| `test_concept_observed` | `state.concept.observed` | `{"observation": "Student confused", "classification": "misconception"}` | `"observed"` | observation, classification in frontmatter |
| `test_concept_drilled` | `state.concept.drilled` | `{"score": 0.8, "items_attempted": 5}` | `"drilled"` | score, items_attempted in frontmatter; mastery_probability updated |
| `test_concept_mastered` | `state.concept.mastered` | `{"mastery_probability": 0.95}` | `"mastered"` | mastery_probability set in row |
| `test_concept_reviewed` | `state.concept.reviewed` | `{"mastery_delta": 0.05}` | `"reviewed"` | mastery_delta in frontmatter |
</action>

<acceptance_criteria>
- `grep -c "class TestStepProjection" tests/test_projector.py` returns 1
- `grep -c "class TestSliceProjection" tests/test_projector.py` returns 1
- `grep -c "class TestConceptProjection" tests/test_projector.py` returns 1
- `grep -c "@pytest.mark.asyncio" tests/test_projector.py` returns >= 3
- Number of `async def test_` methods = 19 (10 + 4 + 5)
- `python3 -m pytest tests/test_projector.py::TestStepProjection -x --no-header -q 2>&1 | tail -5` passes all step projection tests
- `python3 -m pytest tests/test_projector.py::TestSliceProjection -x --no-header -q 2>&1 | tail -5` passes all slice projection tests
- `python3 -m pytest tests/test_projector.py::TestConceptProjection -x --no-header -q 2>&1 | tail -5` passes all concept projection tests
</acceptance_criteria>

---

### Task 3: Integration tests — rebuild, idempotency, crash, edge cases, Hypothesis

<read_first>
- tests/test_projector.py (file from Tasks 1-2)
- tests/test_events.py lines 281-333 (Hypothesis property test pattern for DB isolation)
- tests/test_reconciler.py lines 323-385 (sweep/integration test patterns)
</read_first>

<action>
Add the following test classes after the per-event-type tests.

**`class TestFullRebuild`** — rebuild_all() integration tests:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_rebuild_empty_log` | Zero events → empty cache tables | No events, call rebuild_all, assert all 3 tables have 0 rows |
| `test_rebuild_multi_aggregate` | Append events for 2 steps, 1 slice, 1 concept → rebuild → verify all cache rows | Append 4 events (2 step, 1 slice, 1 concept), rebuild, verify 2 step rows, 1 slice row, 1 concept row, each with correct state |
| `test_rebuild_event_count` | N events → rebuild returns N | Append 5 events, rebuild returns 5 |
| `test_rebuild_multi_event_per_aggregate` | 3 events for same step → final state in cache | Append discussed → planned → executed for step-01, rebuild, verify step row state="executing" |

**`class TestRebuildIdempotency`** — rebuild is deterministic and repeatable:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_rebuild_idempotent` | Two rebuilds produce identical cache tables | Append 3 events, rebuild, capture checksums of all 3 tables (json.dumps(sorted rows)), rebuild again, assert checksums identical |
| `test_rebuild_deterministic` | Same events → same projections in a fresh DB | Rebuild in DB-A, rebuild in DB-B (same events), assert cache tables byte-identical |

**`class TestCrashAtomicity`** — transaction rollback on failure:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_rebuild_atomicity_rollback` | If crash happens mid-rebuild, cache tables are preserved | Append events to seed cache. Replace `get_connection` with one that raises after the first INSERT OR REPLACE. Call rebuild_all, catch exception. Assert cache tables still contain the pre-rebuild rows (not truncated + empty) |

Implementation: use `monkeypatch.setattr` to inject a connection wrapper that raises after N queries. Or simpler: assert that the `BEGIN IMMEDIATE` + rollback semantics work by triggering a deliberate SQL error (e.g., `PRAGMA synchronous=INVALID`).

**`class TestLiveUpdate`** — apply_event() live mode:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_live_single_event` | apply_event after append updates cache | Append event, read its row, call apply_event, assert cache table has 1 row with correct state |
| `test_live_event_accumulation` | Multiple apply_event calls build up state | Append 3 events for same step-01, call apply_event for each, assert final state matches |

**`class TestEdgeCases`**:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_unknown_event_type_ignored` | Event type not in HANDLERS does not crash | Append `state.step.nonexistent` event (or use a future event type not in registry), call apply_event, assert no row created in any cache table |
| `test_non_cache_aggregate_ignored` | Decision/arc/mode/auth events don't touch cache | Append a `state.decision.asked` event, apply_event, assert all 3 cache tables empty |
| `test_events_table_unchanged_after_rebuild` | Full rebuild does not modify or delete events | Append 5 events, capture `SELECT COUNT(*) FROM events`, rebuild, assert count unchanged |
| `test_multi_mode_events_separate_aggregates` | Events for different aggregates don't interfere | Append to step-01 and step-02 interleaved, rebuild, verify independent states |

**`class TestHypothesisProperty`** — property-based tests:

```python
@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_events=st.integers(min_value=0, max_value=10),
)
async def test_property_rebuild_no_side_effects(
    tmp_path: Path,
    n_events: int,
) -> None:
    """Hypothesis property: rebuild never modifies events table."""
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

    # Append n_events deterministically
    ids = []
    for i in range(n_events):
        id_ = await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": f"event-{i}"},
        )
        ids.append(id_)

    # Count events before
    async with get_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        before = (await cursor.fetchone())[0]

    # Rebuild
    projector = Projector(db=store)
    count = await projector.rebuild_all()

    # Count events after
    async with get_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        after = (await cursor.fetchone())[0]

    assert before == after
    assert count == n_events
```

**`class TestHandlerRegistry`** — registry completeness:

| Method | Description | Steps |
|--------|-------------|-------|
| `test_handler_registry_has_19_handlers` | Registry has exactly 19 handlers | `assert len(HANDLERS) == 19` |
| `test_handler_registry_keys_are_valid_event_types` | All keys start with `"state."` | `assert all(k.startswith("state.") for k in HANDLERS)` |
| `test_all_step_events_registered` | All 10 state.step.* event types are in HANDLERS | Check `state.step.discussed`, `planned`, `executed`, `verify_started`, `verify_passed`, `verify_failed`, `advanced`, `blocked`, `snapshotted`, `reverted` |
| `test_all_slice_events_registered` | All 4 state.slice.* event types | Check `planned`, `worktree_ready`, `shipped`, `reverted` |
| `test_all_concept_events_registered` | All 5 state.concept.* event types | Check `introduced`, `observed`, `drilled`, `mastered`, `reviewed` |
</action>

<acceptance_criteria>
- `grep -c "class TestFullRebuild" tests/test_projector.py` returns 1
- `grep -c "class TestRebuildIdempotency" tests/test_projector.py` returns 1
- `grep -c "class TestCrashAtomicity" tests/test_projector.py` returns 1
- `grep -c "class TestLiveUpdate" tests/test_projector.py` returns 1
- `grep -c "class TestEdgeCases" tests/test_projector.py` returns 1
- `grep -c "class TestHypothesisProperty" tests/test_projector.py` returns 1
- `grep -c "class TestHandlerRegistry" tests/test_projector.py` returns 1
- `python3 -m pytest tests/test_projector.py -x --no-header -q 2>&1 | grep -c "passed"` shows all tests passing
- Hypothesis test runs with 50 examples and passes
</acceptance_criteria>

</tasks>

<verification>
1. **Full test suite:** `python3 -m pytest tests/test_projector.py -x -v 2>&1` shows all tests PASSED.
2. **Hypothesis property test:** `python3 -m pytest tests/test_projector.py::TestHypothesisProperty -x -v 2>&1` shows the property test passing with 50 examples.
3. **Registry completeness:** `python3 -c "from src.state_core.projector import HANDLERS; assert len(HANDLERS) == 19; print(f'{len(HANDLERS)} handlers OK')"` exits 0.
4. **No existing test regressions:** `python3 -m pytest tests/ -x --no-header -q 2>&1` shows no pre-existing test failures.
5. **Edge case coverage confirmed:** Empty log, unknown event type, non-cache aggregate, event count integrity — all tested explicitly.
</verification>

<must_haves>
- [x] DB isolation fixture using `tmp_path` + `monkeypatch.setenv("STATE_DB_PATH", ...)` (identical to existing test pattern)
- [x] `_append_events` helper for populating test data
- [x] `_read_table` helper for verifying cache table contents
- [x] 19 per-event-type projection tests (10 step + 4 slice + 5 concept) — one per registered handler
- [x] Full rebuild integration tests: empty log, multi-aggregate, event count, multi-event per aggregate
- [x] Rebuild idempotency tests: two rebuilds produce identical cache tables
- [x] Crash atomicity test: transaction rollback preserves pre-rebuild state
- [x] Live update tests: single event and multi-event accumulation
- [x] Edge case tests: unknown event type, non-cache aggregate, event table unchanged
- [x] Hypothesis property test: rebuild never modifies events table (50 examples)
- [x] Handler registry completeness test: exactly 19 handlers, all expected keys present
- [x] All tests pass without errors
</must_haves>
