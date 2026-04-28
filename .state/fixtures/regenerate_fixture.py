#!/usr/bin/env python3
"""Regenerate the golden 10,000-event fixture database.

Idempotent: rerunning produces a bit-identical SQLite file (same SHA-256).
All events use deterministic ULIDs (f"{i:024d}01"), fixed timestamps,
and cycled modes (build/teach/kernel).

Usage:
    python3 .state/fixtures/regenerate_fixture.py [--output PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from freezegun import freeze_time

# ── Path setup ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Event type lists (matching schema.py exactly) ─────────────────────────

ARC_EVENT_TYPES = [
    "state.arc.created",
    "state.arc.retired",
    "state.arc.updated",
]

PHASE_EVENT_TYPES = [
    "state.phase.planned",
    "state.phase.started",
    "state.phase.verified",
    "state.phase.completed",
]

SLICE_EVENT_TYPES = [
    "state.slice.planned",
    "state.slice.worktree_ready",
    "state.slice.shipped",
    "state.slice.reverted",
]

STEP_EVENT_TYPES = [
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
]

CONCEPT_EVENT_TYPES = [
    "state.concept.introduced",
    "state.concept.observed",
    "state.concept.drilled",
    "state.concept.mastered",
    "state.concept.reviewed",
]

DRILL_EVENT_TYPES = [
    "state.drill.prepared",
    "state.drill.submitted",
    "state.drill.graded",
]

DECISION_EVENT_TYPES = [
    "state.decision.asked",
    "state.decision.made",
]

AUTH_EVENT_TYPES = [
    "state.auth.refreshed",
    "state.auth.rotated",
]

MODE_EVENT_TYPES = [
    "state.mode.activated",
]

# ── Aggregate configuration ───────────────────────────────────────────────
# (aggregate_type, agg_count, events_per_agg, event_types)

AGGREGATE_CONFIGS = [
    ("step", 100, 30, STEP_EVENT_TYPES),
    ("slice", 50, 30, SLICE_EVENT_TYPES),
    ("arc", 50, 20, ARC_EVENT_TYPES),
    ("phase", 50, 20, PHASE_EVENT_TYPES),
    ("concept", 40, 25, CONCEPT_EVENT_TYPES),
    ("drill", 25, 30, DRILL_EVENT_TYPES),
    ("decision", 25, 30, DECISION_EVENT_TYPES),
    ("auth", 20, 25, AUTH_EVENT_TYPES),
    ("mode", 20, 25, MODE_EVENT_TYPES),
]

# Verify total = 10000
assert sum(c[1] * c[2] for c in AGGREGATE_CONFIGS) == 10000, (
    f"Total events != 10000: {sum(c[1] * c[2] for c in AGGREGATE_CONFIGS)}"
)

MODES = ["build", "teach", "kernel"]

FIXED_TS = "2026-01-01T00:00:00Z"

# Verify all 34 event types are covered
_ALL_EVENT_TYPES = set()
for _name, _count, _per_agg, types in AGGREGATE_CONFIGS:
    _ALL_EVENT_TYPES.update(types)
assert len(_ALL_EVENT_TYPES) == 34, f"Expected 34 event types, got {len(_ALL_EVENT_TYPES)}"


# ── Data generator ───────────────────────────────────────────────────────


def _make_data(event_type: str, idx: int) -> dict:
    """Generate deterministic data dict matching the event type's Pydantic schema.

    Args:
        event_type: The event type string (e.g. 'state.step.executed').
        idx: Global event index (1..10000) for varied but deterministic values.

    Returns:
        Dict matching the event type's data schema (extra="forbid").
    """
    data_by_type: dict[str, dict] = {
        # Arc
        "state.arc.created": {"title": f"Arc {idx}", "goal": f"Goal for arc event {idx}"},
        "state.arc.retired": {"reason": f"Completed arc at event {idx}"},
        "state.arc.updated": {"changed_fields": [f"field_{idx % 5}"]},
        # Phase
        "state.phase.planned": {"phase_number": idx % 100, "title": f"Phase {idx}", "goal": f"Goal {idx}"},
        "state.phase.started": {},
        "state.phase.verified": {"passed": idx % 2 == 0, "summary": f"Verified at event {idx}"},
        "state.phase.completed": {"passed": idx % 2 == 0},
        # Slice
        "state.slice.planned": {"slice_number": idx % 50, "title": f"Slice {idx}", "goal": f"Goal {idx}"},
        "state.slice.worktree_ready": {
            "worktree_name": f"wt-{idx}", "branch": f"feat/slice-{idx}", "dir": f"/tmp/.state/wt-{idx}",
        },
        "state.slice.shipped": {"snapshot_hash": f"sha256:{idx:064x}"},
        "state.slice.reverted": {"reason": f"Reverted at event {idx}"},
        # Step
        "state.step.discussed": {"approach_summary": f"Approach for step event {idx}"},
        "state.step.planned": {
            "goal": f"Step goal {idx}",
            "verify_contract": [{"check": f"check_{idx}", "expected": f"result_{idx}"}],
        },
        "state.step.executed": {"changes_summary": f"Changes for step event {idx}"},
        "state.step.verify_started": {"contract": [{"check": f"check_{idx}", "expected": f"result_{idx}"}]},
        "state.step.verify_passed": {"duration_ms": (idx % 1000) * 10},
        "state.step.verify_failed": {"reason": f"Failure at event {idx}", "details": f"Details: {idx}"},
        "state.step.advanced": {"new_state": f"state_{idx % 5}"},
        "state.step.blocked": {"reason": f"Blocked at event {idx}"},
        "state.step.snapshotted": {"snapshot_hash": f"sha256:{idx:064x}", "tier": "step"},
        "state.step.reverted": {"snapshot_hash": f"sha256:{idx:064x}", "reason": f"Revert at event {idx}"},
        # Concept
        "state.concept.introduced": {
            "concept_id": f"concept-{idx % 40}", "name": f"Concept {idx}",
            "prerequisites": [f"prereq-{(idx + i) % 10}" for i in range(idx % 4)],
        },
        "state.concept.observed": {"observation": f"Observation {idx}", "classification": "correct" if idx % 3 else "needs_review"},
        "state.concept.drilled": {"score": min(1.0, (idx % 10) / 10.0), "items_attempted": (idx % 10) + 1},
        "state.concept.mastered": {"mastery_probability": min(1.0, (idx % 100) / 100.0)},
        "state.concept.reviewed": {"mastery_delta": ((idx % 20) - 10) / 100.0},
        # Drill
        "state.drill.prepared": {"question_count": (idx % 10) + 5},
        "state.drill.submitted": {"answers": [{"q": i, "a": f"answer_{i}"} for i in range(idx % 5 + 1)]},
        "state.drill.graded": {"score": float((idx * 7) % 100), "max_score": 100.0},
        # Decision
        "state.decision.asked": {
            "question": f"Decision question {idx}",
            "options": [{"label": "A", "description": f"Option A for {idx}"}, {"label": "B", "description": f"Option B for {idx}"}],
        },
        "state.decision.made": {"answer": f"Answer {idx % 3}", "reason": f"Because {idx}"},
        # Auth
        "state.auth.refreshed": {"provider": "anthropic", "outcome": "ok" if idx % 5 else "rate_limited"},
        "state.auth.rotated": {"provider": "anthropic", "index": idx % 10},
        # Mode
        "state.mode.activated": {"mode_value": MODES[idx % 3]},
    }
    result = data_by_type.get(event_type)
    if result is None:
        msg = f"Unknown event type: {event_type!r}"
        raise ValueError(msg)
    return result


# ── Async generation ─────────────────────────────────────────────────────


async def _generate_events(output_path: Path) -> dict[str, str]:
    """Generate 10,000 events in a temp DB, copy to output, compute checksums.

    Args:
        output_path: Where to write the golden fixture DB.

    Returns:
        Dict with three checksum keys: db_sha256, export_jsonl_sha256,
        projection_snapshot_sha256.
    """
    # ── Step 1: Create temp directory and set up DB ──────────────────────
    with tempfile.TemporaryDirectory(prefix="state-fixture-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # Copy migrations from project
        migrations_src = PROJECT_ROOT / ".state" / "migrations"
        migrations_dst = tmpdir / ".state" / "migrations"
        if migrations_src.exists():
            shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

        # Set STATE_DB_PATH to temp dir
        temp_db_path = tmpdir / ".state" / "events.sqlite"
        os.environ["STATE_DB_PATH"] = str(temp_db_path)

        # Bootstrap migrations
        from src.state_core.migrations import migrate

        await migrate()

        # Fix _migrations.applied_at timestamps for determinism
        # SQLite's datetime('now') is a C-level SQL function not affected by
        # freezegun; we override after migrate() for bit-identical output.
        from src.state_core.database import get_connection

        async with get_connection() as db:
            await db.execute(
                "UPDATE _migrations SET applied_at = ?",
                (FIXED_TS,),
            )
            await db.commit()

        # ── Step 2: Generate 10,000 events ───────────────────────────────
        from src.state_core.events import SqliteEventStore

        store = SqliteEventStore()

        global_idx = 0

        for agg_type, agg_count, events_per_agg, event_types in AGGREGATE_CONFIGS:
            for agg_num in range(1, agg_count + 1):
                aggregate_id = f"{agg_type}-{agg_num:03d}"
                for e_idx in range(events_per_agg):
                    global_idx += 1
                    event_type = event_types[e_idx % len(event_types)]
                    data = _make_data(event_type, global_idx)
                    mode = MODES[(global_idx - 1) % 3]
                    ulid = f"{global_idx:024d}01"

                    await store.append(
                        agg_type,
                        aggregate_id,
                        event_type,
                        data,
                        mode=mode,
                        ts=FIXED_TS,
                        id_=ulid,
                    )

        assert global_idx == 10000, f"Generated {global_idx} events, expected 10000"

        # ── Step 3: Copy to output path ──────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(temp_db_path), str(output_path))

    # ── Step 4: Compute checksums ────────────────────────────────────────
    # Order: export (read-only) → rebuild_all (modifies) → db_sha256 last
    # so checksums reflect the final shipped DB file.
    os.environ["STATE_DB_PATH"] = str(output_path)

    # 4a. export_jsonl_sha256 (read-only, no DB mutation)
    store = SqliteEventStore()
    all_events = await store.read_events()
    jsonl_lines = [
        json.dumps(e, sort_keys=True, separators=(",", ":")) for e in all_events
    ]
    jsonl_text = "\n".join(jsonl_lines) + "\n"
    export_jsonl_sha256 = hashlib.sha256(jsonl_text.encode()).hexdigest()

    # 4b. projection_snapshot_sha256: rebuild_all() THEN dump cache tables
    from src.state_core.projector import Projector

    projector = Projector(store)
    await projector.rebuild_all()

    async with get_connection() as db:
        db.row_factory = None  # default row_factory for simple tuples
        combined: dict[str, list[dict]] = {}
        for table in ["steps", "slices", "concepts"]:
            cursor = await db.execute(f"SELECT * FROM {table} ORDER BY id")
            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            combined[table] = [dict(zip(columns, row)) for row in rows]

    snapshot_json = json.dumps(combined, sort_keys=True, separators=(",", ":"), default=str)
    projection_snapshot_sha256 = hashlib.sha256(snapshot_json.encode()).hexdigest()

    # 4c. db_sha256: SHA-256 of the entire output SQLite file (final state
    # after rebuild_all has populated cache tables).
    db_bytes = output_path.read_bytes()
    db_sha256 = hashlib.sha256(db_bytes).hexdigest()

    return {
        "db_sha256": db_sha256,
        "export_jsonl_sha256": export_jsonl_sha256,
        "projection_snapshot_sha256": projection_snapshot_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate golden 10K-event fixture")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / ".state" / "fixtures" / "golden-10k.sqlite"),
        help="Output path for the golden fixture DB",
    )
    args = parser.parse_args()

    output_path = Path(args.output).resolve()

    # Wrap the entire async execution in frozen time so that any Python-level
    # datetime.now() / time.time() calls produce deterministic values. Note:
    # SQLite's datetime('now') SQL function is unaffected; we manually fix
    # _migrations.applied_at inside _generate_events.
    with freeze_time(FIXED_TS):
        checksums = asyncio.run(_generate_events(output_path))

    # Write checksums
    checksums_path = output_path.parent / "golden-10k-checksums.json"
    checksums_path.write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n"
    )

    print(
        f"Fixture generated: {output_path} "
        f"(10000 events, SHA-256: {checksums['db_sha256']})"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
