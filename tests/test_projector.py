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
from tests.test_events import AGGREGATE_FOR_EVENT

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
async def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


# ── Helpers ────────────────────────────────────────────────────────────────


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


# ── Projector event data strategies ────────────────────────────────────────
# Maps each of 34 event types to a Hypothesis strategy producing valid data
# dicts. Non-projection event types (arc, phase, drill, decision, auth, mode)
# are included to verify they don't cause crashes during rebuild.

PROJECTOR_EVENT_DATA: dict[str, st.SearchStrategy[dict]] = {
    # Step events (10 — handled by the projector)
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
    # Slice events (4 — handled by the projector)
    "state.slice.planned": st.fixed_dictionaries({"slice_number": st.just(1), "title": st.just("S"), "goal": st.just("G")}),
    "state.slice.worktree_ready": st.fixed_dictionaries({"worktree_name": st.just("wt"), "branch": st.just("main"), "dir": st.just("/tmp")}),
    "state.slice.shipped": st.fixed_dictionaries({"snapshot_hash": st.just("abc")}),
    "state.slice.reverted": st.fixed_dictionaries({"reason": st.just("Bug")}),
    # Concept events (5 — handled by the projector)
    "state.concept.introduced": st.fixed_dictionaries({"concept_id": st.just("c01"), "name": st.just("C"), "prerequisites": st.just([])}),
    "state.concept.observed": st.fixed_dictionaries({"observation": st.just("O"), "classification": st.just("correct")}),
    "state.concept.drilled": st.fixed_dictionaries({"score": st.just(4.0), "items_attempted": st.just(5)}),
    "state.concept.mastered": st.fixed_dictionaries({"mastery_probability": st.just(0.95)}),
    "state.concept.reviewed": st.fixed_dictionaries({"mastery_delta": st.just(0.05)}),
    # Arc events (3 — NOT handled by the projector)
    "state.arc.created": st.fixed_dictionaries({"title": st.just("A"), "goal": st.just("G")}),
    "state.arc.retired": st.fixed_dictionaries({"reason": st.just("Done")}),
    "state.arc.updated": st.fixed_dictionaries({"changed_fields": st.just(["title"])}),
    # Phase events (4 — NOT handled by the projector)
    "state.phase.planned": st.fixed_dictionaries({"phase_number": st.just(1), "title": st.just("P"), "goal": st.just("G")}),
    "state.phase.started": st.fixed_dictionaries({}),
    "state.phase.verified": st.fixed_dictionaries({"passed": st.just(True), "summary": st.just("OK")}),
    "state.phase.completed": st.fixed_dictionaries({"passed": st.just(True)}),
    # Drill events (3 — NOT handled by the projector)
    "state.drill.prepared": st.fixed_dictionaries({"question_count": st.just(5)}),
    "state.drill.submitted": st.fixed_dictionaries({"answers": st.just([{"q": 1}])}),
    "state.drill.graded": st.fixed_dictionaries({"score": st.just(8.0), "max_score": st.just(10.0)}),
    # Mode events (1 — NOT handled by the projector)
    "state.mode.activated": st.fixed_dictionaries({"mode_value": st.just("build")}),
    # Decision events (2 — NOT handled by the projector)
    "state.decision.asked": st.fixed_dictionaries({"question": st.just("Q"), "options": st.just([{"opt": "A"}])}),
    "state.decision.made": st.fixed_dictionaries({"answer": st.just("A"), "reason": st.just("Best")}),
    # Auth events (2 — NOT handled by the projector)
    "state.auth.refreshed": st.fixed_dictionaries({"provider": st.just("anthropic"), "outcome": st.just("ok")}),
    "state.auth.rotated": st.fixed_dictionaries({"provider": st.just("anthropic"), "index": st.just(1)}),
}


# ── Per-event-type projection tests ───────────────────────────────────────
# Each test method appends an event, reads it back, calls apply_event,
# then verifies the cache table row.


@pytest.mark.asyncio
class TestStepProjection:
    """10 step-state projection handlers — one per state.step.* event type."""

    async def test_step_discussed(self, store: SqliteEventStore) -> None:
        """state.step.discussed → state='discussing', title from approach_summary."""
        await store.append("step", "step-01", "state.step.discussed", {"approach_summary": "Explore options"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        assert len(events) == 1
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "discussing"
        assert row["title"] == "Explore options"
        assert row["frontmatter"]["approach_summary"] == "Explore options"

    async def test_step_planned(self, store: SqliteEventStore) -> None:
        """state.step.planned → state='planning', goal+verify_contract in frontmatter."""
        await store.append(
            "step", "step-01", "state.step.planned",
            {"goal": "Build X", "verify_contract": [{"check": "works"}]},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "planning"
        assert row["frontmatter"]["goal"] == "Build X"
        assert row["frontmatter"]["verify_contract"] == [{"check": "works"}]

    async def test_step_executed(self, store: SqliteEventStore) -> None:
        """state.step.executed → state='executing', changes_summary in frontmatter."""
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "Added feature Y"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "executing"
        assert row["frontmatter"]["changes_summary"] == "Added feature Y"

    async def test_step_verify_started(self, store: SqliteEventStore) -> None:
        """state.step.verify_started → state='verifying'."""
        await store.append("step", "step-01", "state.step.verify_started", {"contract": [{"check": "works"}]})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "verifying"

    async def test_step_verify_passed(self, store: SqliteEventStore) -> None:
        """state.step.verify_passed → state='done', duration_ms in frontmatter."""
        await store.append("step", "step-01", "state.step.verify_passed", {"duration_ms": 1500})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "done"
        assert row["frontmatter"]["duration_ms"] == 1500

    async def test_step_verify_failed(self, store: SqliteEventStore) -> None:
        """state.step.verify_failed → state='executing', reason+details in frontmatter.

        Sequential: discussed → planned → executed → verify_failed.
        """
        events_data = [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Test approach"}),
            ("step", "step-01", "state.step.planned", {"goal": "Verify something"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "Implemented"}),
            ("step", "step-01", "state.step.verify_failed", {"reason": "Bug", "details": "Crash on input X"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 4

        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        assert len(events) == 4
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "executing"
        assert row["frontmatter"]["reason"] == "Bug"
        assert row["frontmatter"]["details"] == "Crash on input X"

    async def test_step_advanced(self, store: SqliteEventStore) -> None:
        """state.step.advanced → state matches data.new_state."""
        await store.append("step", "step-01", "state.step.advanced", {"new_state": "reviewing"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "reviewing"
        assert row["frontmatter"]["new_state"] == "reviewing"

    async def test_step_blocked(self, store: SqliteEventStore) -> None:
        """state.step.blocked → state='blocked', reason in frontmatter."""
        await store.append("step", "step-01", "state.step.blocked", {"reason": "Waiting for API key"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "blocked"
        assert row["frontmatter"]["reason"] == "Waiting for API key"

    async def test_step_snapshotted(self, store: SqliteEventStore) -> None:
        """state.step.snapshotted → state preserved, snapshot_hash in frontmatter.

        Sequential: discussed → snapshotted (state stays 'discussing').
        """
        events_data = [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Snapshot test"}),
            ("step", "step-01", "state.step.snapshotted", {"snapshot_hash": "abc123", "tier": "1"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 2

        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        assert len(events) == 2
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "discussing"  # Preserved from prior event
        assert row["frontmatter"]["snapshot_hash"] == "abc123"
        assert row["frontmatter"]["tier"] == "1"

    async def test_step_reverted(self, store: SqliteEventStore) -> None:
        """state.step.reverted → state='reverted', snapshot_hash+reason in frontmatter.

        Sequential: discussed → executed → reverted.
        """
        events_data = [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Revert test"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "Work done"}),
            ("step", "step-01", "state.step.reverted", {"snapshot_hash": "def456", "reason": "Bug found"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 3

        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        assert len(events) == 3
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("steps")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "step-01"
        assert row["state"] == "reverted"
        assert row["frontmatter"]["snapshot_hash"] == "def456"
        assert row["frontmatter"]["reason"] == "Bug found"


@pytest.mark.asyncio
class TestSliceProjection:
    """4 slice-state projection handlers — one per state.slice.* event type."""

    async def test_slice_planned(self, store: SqliteEventStore) -> None:
        """state.slice.planned → state='planned', title+goal in frontmatter."""
        await store.append(
            "slice", "slice-01", "state.slice.planned",
            {"slice_number": 1, "title": "Core", "goal": "Build core"},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("slice-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("slices")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "slice-01"
        assert row["state"] == "planned"
        assert row["frontmatter"]["title"] == "Core"
        assert row["frontmatter"]["goal"] == "Build core"

    async def test_slice_worktree_ready(self, store: SqliteEventStore) -> None:
        """state.slice.worktree_ready → state='in_progress', worktree_dir+branch set.

        Sequential: planned → worktree_ready.
        """
        events_data = [
            ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "Feat X", "goal": "Build X"}),
            ("slice", "slice-01", "state.slice.worktree_ready", {"worktree_name": "feat-x", "branch": "feat/x", "dir": "/tmp/wt"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 2

        projector = Projector(store)
        events = [e async for e in store.read_stream("slice-01")]
        assert len(events) == 2
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("slices")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "slice-01"
        assert row["state"] == "in_progress"
        assert row["worktree_dir"] == "/tmp/wt"
        assert row["worktree_branch"] == "feat/x"

    async def test_slice_shipped(self, store: SqliteEventStore) -> None:
        """state.slice.shipped → state='shipped', snapshot_hash in frontmatter.

        Sequential: planned → worktree_ready → shipped.
        """
        events_data = [
            ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "Feature", "goal": "Deliver"}),
            ("slice", "slice-01", "state.slice.worktree_ready", {"worktree_name": "feat-y", "branch": "feat/y", "dir": "/tmp/wt"}),
            ("slice", "slice-01", "state.slice.shipped", {"snapshot_hash": "abc123"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 3

        projector = Projector(store)
        events = [e async for e in store.read_stream("slice-01")]
        assert len(events) == 3
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("slices")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "slice-01"
        assert row["state"] == "shipped"
        assert row["frontmatter"]["snapshot_hash"] == "abc123"
        # Worktree info should survive the state transition
        assert row["worktree_dir"] == "/tmp/wt"
        assert row["worktree_branch"] == "feat/y"

    async def test_slice_reverted(self, store: SqliteEventStore) -> None:
        """state.slice.reverted → state='reverted', reason in frontmatter.

        Sequential: planned → worktree_ready → shipped → reverted.
        """
        events_data = [
            ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "Feat", "goal": "Goal"}),
            ("slice", "slice-01", "state.slice.worktree_ready", {"worktree_name": "feat-z", "branch": "feat/z", "dir": "/tmp/wt"}),
            ("slice", "slice-01", "state.slice.shipped", {"snapshot_hash": "xyz789"}),
            ("slice", "slice-01", "state.slice.reverted", {"reason": "Bug found in QA"}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 4

        projector = Projector(store)
        events = [e async for e in store.read_stream("slice-01")]
        assert len(events) == 4
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("slices")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "slice-01"
        assert row["state"] == "reverted"
        assert row["frontmatter"]["reason"] == "Bug found in QA"


@pytest.mark.asyncio
class TestConceptProjection:
    """5 concept-state projection handlers — one per state.concept.* event type."""

    async def test_concept_introduced(self, store: SqliteEventStore) -> None:
        """state.concept.introduced → state='introduced', name+prerequisites in frontmatter."""
        await store.append(
            "concept", "concept-01", "state.concept.introduced",
            {"concept_id": "c01", "name": "Polymorphism", "prerequisites": ["classes"]},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("concept-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("concepts")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "concept-01"
        # Concept cache table has no "state" column — verify mastery fields instead
        assert row["mastery_probability"] == 0.0
        assert row["scaffold_level"] == 0
        assert row["bloom_level"] == "remember"
        assert row["frontmatter"]["name"] == "Polymorphism"
        assert row["frontmatter"]["prerequisites"] == ["classes"]

    async def test_concept_observed(self, store: SqliteEventStore) -> None:
        """state.concept.observed → state='observed', observation+classification in frontmatter."""
        await store.append(
            "concept", "concept-01", "state.concept.observed",
            {"observation": "Student confused", "classification": "misconception"},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("concept-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("concepts")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "concept-01"
        assert row["frontmatter"]["observation"] == "Student confused"
        assert row["frontmatter"]["classification"] == "misconception"

    async def test_concept_drilled(self, store: SqliteEventStore) -> None:
        """state.concept.drilled → state='drilled', mastery_probability computed."""
        await store.append(
            "concept", "concept-01", "state.concept.drilled",
            {"score": 4.0, "items_attempted": 5},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("concept-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("concepts")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "concept-01"
        # mastery_probability = min(1.0, score / max(items_attempted, 1)) = min(1.0, 0.8) = 0.8
        assert row["mastery_probability"] == 0.8
        # scaffold_level = max(0, 5 - items_attempted // 3) = max(0, 5 - 1) = 4
        assert row["scaffold_level"] == 4
        assert row["frontmatter"]["score"] == 4.0

    async def test_concept_mastered(self, store: SqliteEventStore) -> None:
        """state.concept.mastered → state='mastered', mastery_probability set."""
        await store.append(
            "concept", "concept-01", "state.concept.mastered",
            {"mastery_probability": 0.95},
        )
        projector = Projector(store)
        events = [e async for e in store.read_stream("concept-01")]
        await projector.apply_event(events[0])
        rows = await _read_table("concepts")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "concept-01"
        assert row["mastery_probability"] == 0.95
        assert row["frontmatter"]["mastery_probability"] == 0.95

    async def test_concept_reviewed(self, store: SqliteEventStore) -> None:
        """state.concept.reviewed → state='reviewed', mastery_updated by delta.

        Sequential: introduced (mastery=0.0) → drilled (mastery=0.8) → reviewed.
        With mastery_delta=0.05: 0.8 + 0.05 = 0.85
        """
        events_data = [
            ("concept", "concept-01", "state.concept.introduced", {"concept_id": "c01", "name": "Inheritance", "prerequisites": ["classes"]}),
            ("concept", "concept-01", "state.concept.drilled", {"score": 4.0, "items_attempted": 5}),
            ("concept", "concept-01", "state.concept.reviewed", {"mastery_delta": 0.05}),
        ]
        ids = await _append_events(store, events_data)
        assert len(ids) == 3

        projector = Projector(store)
        events = [e async for e in store.read_stream("concept-01")]
        assert len(events) == 3
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("concepts")
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "concept-01"
        # After drilled: mastery=0.8, then reviewed: 0.8 + 0.05 = 0.85
        assert row["mastery_probability"] == pytest.approx(0.85)


# ── Full rebuild integration tests ─────────────────────────────────────────


@pytest.mark.asyncio
class TestFullRebuild:
    """rebuild_all() integration — empty log, multi-aggregate, event count."""

    async def test_rebuild_empty_log(self, store: SqliteEventStore) -> None:
        """Zero events → all cache tables empty."""
        projector = Projector(store)
        count = await projector.rebuild_all()
        assert count == 0
        assert await _read_table("steps") == []
        assert await _read_table("slices") == []
        assert await _read_table("concepts") == []

    async def test_rebuild_multi_aggregate(self, store: SqliteEventStore) -> None:
        """Append events for 2 steps, 1 slice, 1 concept → rebuild → all rows correct."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "First"}),
            ("step", "step-02", "state.step.planned", {"goal": "Second"}),
            ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "Core"}),
            ("concept", "concept-01", "state.concept.introduced", {"name": "Abstraction"}),
        ])

        projector = Projector(store)
        count = await projector.rebuild_all()
        assert count == 4

        steps = await _read_table("steps")
        assert len(steps) == 2
        step_ids = {s["id"] for s in steps}
        assert "step-01" in step_ids
        assert "step-02" in step_ids
        states = {s["id"]: s["state"] for s in steps}
        assert states["step-01"] == "discussing"
        assert states["step-02"] == "planning"

        slices = await _read_table("slices")
        assert len(slices) == 1
        assert slices[0]["state"] == "planned"

        concepts = await _read_table("concepts")
        assert len(concepts) == 1

    async def test_rebuild_event_count(self, store: SqliteEventStore) -> None:
        """N events → rebuild returns N."""
        await _append_events(store, [
            ("step", "step-01", "state.step.executed", {"changes_summary": str(i)})
            for i in range(5)
        ])
        projector = Projector(store)
        count = await projector.rebuild_all()
        assert count == 5

    async def test_rebuild_multi_event_per_aggregate(self, store: SqliteEventStore) -> None:
        """3 events for same step → final state in cache reflects last event."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Start"}),
            ("step", "step-01", "state.step.planned", {"goal": "Middle"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "End"}),
        ])
        projector = Projector(store)
        count = await projector.rebuild_all()
        assert count == 3

        rows = await _read_table("steps")
        assert len(rows) == 1
        assert rows[0]["state"] == "executing"


# ── Rebuild idempotency ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRebuildIdempotency:
    """rebuild_all is deterministic and repeatable."""

    async def test_rebuild_idempotent(self, store: SqliteEventStore) -> None:
        """Two rebuilds produce identical cache tables."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Idempotent"}),
            ("slice", "slice-01", "state.slice.planned", {"slice_number": 1, "title": "S1"}),
            ("concept", "concept-01", "state.concept.introduced", {"name": "Idempotency"}),
        ])

        projector = Projector(store)

        # First rebuild
        await projector.rebuild_all()
        checksum_1 = await _table_checksums()

        # Second rebuild
        await projector.rebuild_all()
        checksum_2 = await _table_checksums()

        assert checksum_1 == checksum_2

    async def test_rebuild_deterministic(self, store: SqliteEventStore, tmp_path: Path) -> None:
        """Same events → same projections in a fresh DB."""
        import os
        import uuid

        # Append events in DB-A (the fixture DB)
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Det"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "Work"}),
        ])
        projector = Projector(store)
        await projector.rebuild_all()
        checksum_a = await _table_checksums()

        # Create DB-B with same events
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
        await _append_events(store_b, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Det"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "Work"}),
        ])
        projector_b = Projector(store_b)
        await projector_b.rebuild_all()
        checksum_b = await _table_checksums()

        # Restore original STATE_DB_PATH
        os.environ["STATE_DB_PATH"] = old_path
        del os.environ["STATE_DB_PATH_B"]

        assert checksum_a == checksum_b


async def _table_checksums() -> dict[str, str]:
    """Return a dict of {table_name: json_dumps_of_sorted_rows} for all cache tables."""
    result: dict[str, str] = {}
    for table in ("steps", "slices", "concepts"):
        rows = await _read_table(table)
        # Convert to JSON-serializable form (frontmatter is already parsed)
        serializable = []
        for row in rows:
            r = dict(row)
            if isinstance(r.get("frontmatter"), dict):
                r["frontmatter"] = json.dumps(r["frontmatter"], sort_keys=True, separators=(",", ":"))
            serializable.append(r)
        result[table] = json.dumps(serializable, sort_keys=True)
    return result


# ── Crash atomicity ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCrashAtomicity:
    """Transaction rollback on failure preserves pre-rebuild state."""

    async def test_rebuild_atomicity_rollback(
        self, store: SqliteEventStore, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If a handler crashes mid-rebuild, cache tables preserve prior state."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Atomicity"}),
        ])

        # Pre-populate cache via rebuild
        projector = Projector(store)
        await projector.rebuild_all()
        rows_before = await _read_table("steps")
        assert len(rows_before) == 1
        assert rows_before[0]["state"] == "discussing"

        # Cause a crash during rebuild by making the discussed handler throw
        original_handler = HANDLERS["state.step.discussed"]
        monkeypatch.setitem(
            HANDLERS, "state.step.discussed",
            lambda current, data: (_ for _ in ()).throw(RuntimeError("simulated-crash")),
        )

        with pytest.raises(RuntimeError, match="simulated-crash"):
            await projector.rebuild_all()

        # Cache should be preserved (transaction rolled back)
        rows_after = await _read_table("steps")
        assert len(rows_after) == 1
        assert rows_after[0]["state"] == "discussing"


# ── Live update tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestLiveUpdate:
    """apply_event() live mode — single and multi-event accumulation."""

    async def test_live_single_event(self, store: SqliteEventStore) -> None:
        """apply_event after append updates cache with one row."""
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "Live test"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])

        rows = await _read_table("steps")
        assert len(rows) == 1
        assert rows[0]["id"] == "step-01"
        assert rows[0]["state"] == "executing"

    async def test_live_event_accumulation(self, store: SqliteEventStore) -> None:
        """Multiple apply_event calls build up state correctly."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "Accum start"}),
            ("step", "step-01", "state.step.planned", {"goal": "Accum middle"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "Accum end"}),
        ])

        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        for event in events:
            await projector.apply_event(event)

        rows = await _read_table("steps")
        assert len(rows) == 1
        assert rows[0]["id"] == "step-01"
        assert rows[0]["state"] == "executing"
        assert rows[0]["frontmatter"]["approach_summary"] == "Accum start"
        assert rows[0]["frontmatter"]["goal"] == "Accum middle"
        assert rows[0]["frontmatter"]["changes_summary"] == "Accum end"


# ── Edge cases ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEdgeCases:
    """Boundary and edge-case behavior."""

    async def test_unknown_event_type_ignored(self, store: SqliteEventStore) -> None:
        """Event type not in HANDLERS does not crash or create cache rows."""
        await store.append("step", "step-01", "state.step.nonexistent", {"data": "x"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("step-01")]
        await projector.apply_event(events[0])

        assert await _read_table("steps") == []
        assert await _read_table("slices") == []
        assert await _read_table("concepts") == []

    async def test_non_cache_aggregate_ignored(self, store: SqliteEventStore) -> None:
        """Decision/arc/mode/auth events don't touch cache tables."""
        await store.append("decision", "decision-01", "state.decision.asked", {"question": "Q?"})
        projector = Projector(store)
        events = [e async for e in store.read_stream("decision-01")]
        await projector.apply_event(events[0])

        assert await _read_table("steps") == []
        assert await _read_table("slices") == []
        assert await _read_table("concepts") == []

    async def test_events_table_unchanged_after_rebuild(self, store: SqliteEventStore) -> None:
        """Full rebuild does not modify or delete events."""
        await _append_events(store, [
            ("step", "step-01", "state.step.executed", {"changes_summary": str(i)})
            for i in range(5)
        ])

        async with get_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            before = (await cursor.fetchone())[0]
        assert before == 5

        projector = Projector(store)
        await projector.rebuild_all()

        async with get_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
            after = (await cursor.fetchone())[0]

        assert before == after

    async def test_multi_mode_events_separate_aggregates(self, store: SqliteEventStore) -> None:
        """Events for different aggregates don't interfere when interleaved."""
        await _append_events(store, [
            ("step", "step-01", "state.step.discussed", {"approach_summary": "S1"}),
            ("step", "step-02", "state.step.planned", {"goal": "S2"}),
            ("step", "step-01", "state.step.executed", {"changes_summary": "S1 done"}),
            ("step", "step-02", "state.step.executed", {"changes_summary": "S2 done"}),
        ])

        projector = Projector(store)

        # Apply events for both aggregates
        for agg_id in ("step-01", "step-02"):
            events = [e async for e in store.read_stream(agg_id)]
            for event in events:
                await projector.apply_event(event)

        rows = await _read_table("steps")
        rows_dict = {r["id"]: r for r in rows}
        assert rows_dict["step-01"]["state"] == "executing"
        assert rows_dict["step-02"]["state"] == "executing"

        # Verify independent frontmatter
        assert rows_dict["step-01"]["frontmatter"]["approach_summary"] == "S1"
        assert rows_dict["step-02"]["frontmatter"]["goal"] == "S2"


# ── Hypothesis property test ──────────────────────────────────────────────


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
    for i in range(n_events):
        await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": f"event-{i}"},
        )

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


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    event_sequence=st.lists(
        st.sampled_from(sorted(PROJECTOR_EVENT_DATA.keys())),
        min_size=0, max_size=20,
    ),
    data=st.data(),
)
async def test_property_all_aggregates_rebuild_determinism(
    tmp_path: Path,
    event_sequence: list[str],
    data: st.DataObject,
) -> None:
    """Hypothesis property: any event sequence → rebuild is deterministic.

    For any sequence of event types (including non-projection types like
    arc, phase, drill), running rebuild_all() twice produces identical
    cache tables and the events table is never modified.
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

    # Build a deterministic mapping from event_type to aggregate_type
    event_to_agg = {et: AGGREGATE_FOR_EVENT[et] for et in PROJECTOR_EVENT_DATA if et in AGGREGATE_FOR_EVENT}

    # Append the event sequence (each to its own aggregate instance)
    for i, event_type in enumerate(event_sequence):
        agg_type = event_to_agg.get(event_type, "step")
        agg_id = f"{agg_type}-{i}"
        event_data = data.draw(PROJECTOR_EVENT_DATA[event_type])
        await store.append(agg_type, agg_id, event_type, event_data)

    # Count events before rebuild (must match after rebuild — rebuild does not mutate events)
    async with get_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        before = (await cursor.fetchone())[0]

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


# ── Handler registry completeness ─────────────────────────────────────────


class TestHandlerRegistry:
    """Registry completeness: all expected handlers registered."""

    def test_handler_registry_has_19_handlers(self) -> None:
        """Registry has exactly 19 handlers."""
        assert len(HANDLERS) == 19

    def test_handler_registry_keys_are_valid_event_types(self) -> None:
        """All keys start with 'state.'."""
        assert all(k.startswith("state.") for k in HANDLERS)

    def test_all_step_events_registered(self) -> None:
        """All 10 state.step.* event types are registered."""
        step_events = {
            "state.step.discussed",
            "state.step.planned",
            "state.step.executed",
            "state.step.verify_started",
            "state.step.verify_passed",
            "state.step.verify_failed",
            "state.step.advanced",
            "state.step.blocked",
            "state.step.snapshotted",
            "state.step.reverted",
        }
        registered_step = {k for k in HANDLERS if k.startswith("state.step.")}
        assert registered_step == step_events

    def test_all_slice_events_registered(self) -> None:
        """All 4 state.slice.* event types are registered."""
        slice_events = {
            "state.slice.planned",
            "state.slice.worktree_ready",
            "state.slice.shipped",
            "state.slice.reverted",
        }
        registered_slice = {k for k in HANDLERS if k.startswith("state.slice.")}
        assert registered_slice == slice_events

    def test_all_concept_events_registered(self) -> None:
        """All 5 state.concept.* event types are registered."""
        concept_events = {
            "state.concept.introduced",
            "state.concept.observed",
            "state.concept.drilled",
            "state.concept.mastered",
            "state.concept.reviewed",
        }
        registered_concept = {k for k in HANDLERS if k.startswith("state.concept.")}
        assert registered_concept == concept_events
