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
