"""CQRS-style projection engine — rebuilds cache tables from events.

Handler registry with decorator-based registration, 19 pure projection handler
functions (10 step + 4 slice + 5 concept), and the ``Projector`` class.

Two modes:
1. **Rebuild** — ``rebuild_all()`` truncates cache tables and replays ALL events
   from the ``events`` table in aggregate+seq order.
2. **Live** — ``apply_event()`` updates a single projection row after an event
   has been appended (same-transaction call).

Three cache tables: ``steps``, ``slices``, ``concepts``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import structlog

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore

log = structlog.get_logger(__name__)

_HandlerFn: type = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]
"""Handler signature: (current_state_or_None, event_data_dict) -> new_state_dict."""

_CACHE_TABLES: frozenset = frozenset({"steps", "slices", "concepts"})
"""Whitelist of cache table names — validated before any SQL interpolation."""

HANDLERS: dict[str, _HandlerFn] = {}
"""Event-type-to-handler registry. Populated by the ``_register_handler`` decorator."""


def _register_handler(event_type: str) -> Callable[[_HandlerFn], _HandlerFn]:
    """Decorator that registers a projection handler for *event_type*."""

    def decorator(fn: _HandlerFn) -> _HandlerFn:
        HANDLERS[event_type] = fn
        return fn

    return decorator


def _validate_table(name: str) -> str:
    """Validate *name* is a known cache table; raise ValueError if not."""
    if name not in _CACHE_TABLES:
        raise ValueError(f"Unknown cache table: {name!r}. Expected one of {_CACHE_TABLES}")
    return name


# ── Frontmatter helper ────────────────────────────────────────────────────


def _merge_frontmatter(current: dict[str, Any] | None, data: dict[str, Any]) -> str:
    """Merge *data* into accumulated frontmatter; return deterministic JSON.

    Parses ``current.get("frontmatter", "{}")`` as JSON, merges *data* on top,
    and re-serializes with ``sort_keys=True`` and compact separators.
    """
    frontmatter: dict[str, Any] = {}
    if current is not None:
        raw = current.get("frontmatter", "{}")
        if isinstance(raw, str):
            try:
                frontmatter = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                frontmatter = {}
        elif isinstance(raw, dict):
            frontmatter = raw
    frontmatter.update(data)
    return json.dumps(frontmatter, sort_keys=True, separators=(",", ":"))


# ── Step handlers (10) ────────────────────────────────────────────────────
# Each handler maps one ``state.step.*`` event type to a cache row dict.


@_register_handler("state.step.discussed")
def _handle_step_discussed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step discussing — state becomes 'discussing', title from approach_summary."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": data.get("slice_id", current.get("slice_id", "") if current else ""),
        "state": "discussing",
        "title": data.get("approach_summary", current.get("title", "") if current else ""),
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.planned")
def _handle_step_planned(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step planned — state becomes 'planning', stores goal and verify_contract."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "planning",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.executed")
def _handle_step_executed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step executed — state becomes 'executing', stores changes_summary."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "executing",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.verify_started")
def _handle_step_verify_started(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step verification started — state becomes 'verifying'."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "verifying",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.verify_passed")
def _handle_step_verify_passed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step verification passed — state becomes 'done', stores duration_ms."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "done",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.verify_failed")
def _handle_step_verify_failed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step verification failed — returns to 'executing', stores reason + details."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "executing",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.advanced")
def _handle_step_advanced(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step advanced — state set from data['new_state']."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": data.get("new_state", current.get("state", "") if current else ""),
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.blocked")
def _handle_step_blocked(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step blocked — state becomes 'blocked', stores reason."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "blocked",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.snapshotted")
def _handle_step_snapshotted(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step snapshotted — state unchanged, stores snapshot_hash and tier."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": current.get("state", "") if current else "",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.step.reverted")
def _handle_step_reverted(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Step reverted — state becomes 'reverted', stores snapshot_hash + reason."""
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "reverted",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


# ── Slice handlers (4) ────────────────────────────────────────────────────


@_register_handler("state.slice.planned")
def _handle_slice_planned(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Slice planned — state becomes 'planned'."""
    return {
        "id": current.get("id", "") if current else "",
        "phase_id": data.get("phase_id", current.get("phase_id", "") if current else ""),
        "state": "planned",
        "worktree_dir": current.get("worktree_dir") if current else None,
        "worktree_branch": current.get("worktree_branch") if current else None,
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.slice.worktree_ready")
def _handle_slice_worktree_ready(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Slice worktree ready — state becomes 'in_progress', stores worktree info."""
    return {
        "id": current.get("id", "") if current else "",
        "phase_id": current.get("phase_id", "") if current else "",
        "state": "in_progress",
        "worktree_dir": data.get("dir", current.get("worktree_dir") if current else None),
        "worktree_branch": data.get("branch", current.get("worktree_branch") if current else None),
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.slice.shipped")
def _handle_slice_shipped(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Slice shipped — state becomes 'shipped', stores snapshot_hash."""
    return {
        "id": current.get("id", "") if current else "",
        "phase_id": current.get("phase_id", "") if current else "",
        "state": "shipped",
        "worktree_dir": current.get("worktree_dir") if current else None,
        "worktree_branch": current.get("worktree_branch") if current else None,
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.slice.reverted")
def _handle_slice_reverted(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Slice reverted — state becomes 'reverted', stores reason."""
    return {
        "id": current.get("id", "") if current else "",
        "phase_id": current.get("phase_id", "") if current else "",
        "state": "reverted",
        "worktree_dir": current.get("worktree_dir") if current else None,
        "worktree_branch": current.get("worktree_branch") if current else None,
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }


# ── Concept handlers (5) ──────────────────────────────────────────────────


@_register_handler("state.concept.introduced")
def _handle_concept_introduced(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Concept introduced — state becomes 'introduced', seeds subject info."""
    return {
        "id": current.get("id", "") if current else "",
        "subject_id": data.get("subject_id", current.get("subject_id", "") if current else ""),
        "learner_id": data.get("learner_id", current.get("learner_id", "") if current else ""),
        "mastery_probability": current.get("mastery_probability", 0.0) if current else 0.0,
        "scaffold_level": current.get("scaffold_level", 0) if current else 0,
        "bloom_level": current.get("bloom_level", "remember") if current else "remember",
        "frontmatter": _merge_frontmatter(current, data),
        "last_drilled_at": current.get("last_drilled_at") if current else None,
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.concept.observed")
def _handle_concept_observed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Concept observed — state becomes 'observed', stores observation + classification."""
    return {
        "id": current.get("id", "") if current else "",
        "subject_id": current.get("subject_id", "") if current else "",
        "learner_id": current.get("learner_id", "") if current else "",
        "mastery_probability": current.get("mastery_probability", 0.0) if current else 0.0,
        "scaffold_level": current.get("scaffold_level", 0) if current else 0,
        "bloom_level": current.get("bloom_level", "remember") if current else "remember",
        "frontmatter": _merge_frontmatter(current, data),
        "last_drilled_at": current.get("last_drilled_at") if current else None,
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.concept.drilled")
def _handle_concept_drilled(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Concept drilled — state becomes 'drilled', computes mastery and scaffold level."""
    score = data.get("score", 0.0)
    items_attempted = data.get("items_attempted", 0)
    mastery_probability = min(1.0, score / max(items_attempted, 1))
    scaffold_level = max(0, 5 - items_attempted // 3)
    return {
        "id": current.get("id", "") if current else "",
        "subject_id": current.get("subject_id", "") if current else "",
        "learner_id": current.get("learner_id", "") if current else "",
        "mastery_probability": mastery_probability,
        "scaffold_level": scaffold_level,
        "bloom_level": current.get("bloom_level", "remember") if current else "remember",
        "frontmatter": _merge_frontmatter(current, data),
        "last_drilled_at": current.get("last_drilled_at") if current else None,
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.concept.mastered")
def _handle_concept_mastered(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Concept mastered — state becomes 'mastered', stores explicit mastery_probability."""
    return {
        "id": current.get("id", "") if current else "",
        "subject_id": current.get("subject_id", "") if current else "",
        "learner_id": current.get("learner_id", "") if current else "",
        "mastery_probability": data.get(
            "mastery_probability",
            current.get("mastery_probability", 1.0) if current else 1.0,
        ),
        "scaffold_level": current.get("scaffold_level", 0) if current else 0,
        "bloom_level": current.get("bloom_level", "remember") if current else "remember",
        "frontmatter": _merge_frontmatter(current, data),
        "last_drilled_at": current.get("last_drilled_at") if current else None,
        "updated_at": current.get("updated_at", "") if current else "",
    }


@_register_handler("state.concept.reviewed")
def _handle_concept_reviewed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Concept reviewed — state becomes 'reviewed', applies mastery_delta."""
    mastery_delta = data.get("mastery_delta", 0.0)
    current_mastery = current.get("mastery_probability", 0.5) if current else 0.5
    new_mastery = max(0.0, min(1.0, current_mastery + mastery_delta))
    return {
        "id": current.get("id", "") if current else "",
        "subject_id": current.get("subject_id", "") if current else "",
        "learner_id": current.get("learner_id", "") if current else "",
        "mastery_probability": new_mastery,
        "scaffold_level": current.get("scaffold_level", 0) if current else 0,
        "bloom_level": current.get("bloom_level", "remember") if current else "remember",
        "frontmatter": _merge_frontmatter(current, data),
        "last_drilled_at": current.get("last_drilled_at") if current else None,
        "updated_at": current.get("updated_at", "") if current else "",
    }


# ── Table column definitions ──────────────────────────────────────────────

_STEP_COLUMNS: tuple[str, ...] = (
    "id", "slice_id", "state", "title", "frontmatter", "updated_at",
)
_SLICE_COLUMNS: tuple[str, ...] = (
    "id", "phase_id", "state", "worktree_dir", "worktree_branch",
    "frontmatter", "updated_at",
)
_CONCEPT_COLUMNS: tuple[str, ...] = (
    "id", "subject_id", "learner_id", "mastery_probability", "scaffold_level",
    "bloom_level", "frontmatter", "last_drilled_at", "updated_at",
)


# ── Projector class ───────────────────────────────────────────────────────


class Projector:
    """Orchestrates projection rebuilds and live updates.

    Two modes:
    1. **Rebuild** -- ``rebuild_all()`` truncates cache tables and replays
       ALL events from the ``events`` table in aggregate+seq order.
    2. **Live** -- ``apply_event()`` updates a single projection row after
       an event has been appended (same-transaction call).

    Args:
        db: The event store for reading events.
    """

    def __init__(self, db: SqliteEventStore) -> None:
        self._db = db

    async def rebuild_all(self) -> int:
        """Full rebuild: truncate cache tables, replay all events.

        Opens its OWN connection (not through the EventStore), wraps
        everything in a single ``BEGIN IMMEDIATE``...``COMMIT`` transaction,
        reads events ordered by (aggregate_id, seq), applies handlers, and
        writes the final state for every aggregate into the cache tables.

        Returns:
            Number of events processed.
        """
        async with get_connection() as db:
            await db.execute("PRAGMA synchronous=FULL;")
            await db.execute("BEGIN IMMEDIATE")

            # Truncate all cache tables
            for table in ("steps", "slices", "concepts"):
                _validate_table(table)
                await db.execute(f"DELETE FROM {table}")

            # Read all events ordered by aggregate+seq
            cursor = await db.execute(
                "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
                "FROM events "
                "ORDER BY aggregate_id ASC, seq ASC"
            )
            rows = await cursor.fetchall()

            # Accumulate projected state per aggregate, grouped by table
            steps_state: dict[str, dict[str, Any]] = {}
            slices_state: dict[str, dict[str, Any]] = {}
            concepts_state: dict[str, dict[str, Any]] = {}

            for row in rows:
                d = dict(row)
                aggregate_id = d["aggregate_id"]
                event_type = d["type"]
                aggregate_type = d["aggregate_type"]

                # Route to the right in-memory dict
                if aggregate_type == "step":
                    target = steps_state
                elif aggregate_type == "slice":
                    target = slices_state
                elif aggregate_type == "concept":
                    target = concepts_state
                else:
                    log.debug(
                        "non_cache_aggregate_skipped",
                        aggregate_type=aggregate_type,
                        aggregate_id=aggregate_id,
                    )
                    continue

                # Deserialize the JSON data payload
                raw_data = d.get("data", "{}")
                if isinstance(raw_data, str):
                    try:
                        event_data: dict[str, Any] = json.loads(raw_data)
                    except (json.JSONDecodeError, TypeError):
                        event_data = {}
                else:
                    event_data = raw_data if isinstance(raw_data, dict) else {}

                # Route to handler
                handler = HANDLERS.get(event_type)
                if handler is None:
                    log.debug(
                        "no_handler_for_event",
                        event_type=event_type,
                        aggregate_id=aggregate_id,
                    )
                    continue

                current_state = target.get(aggregate_id)
                new_state = handler(current_state, event_data)
                # Override envelope fields from the event row
                new_state["id"] = aggregate_id
                new_state["updated_at"] = d.get("ts", "")
                target[aggregate_id] = new_state

            events_processed = len(rows)

            # Write steps
            for _agg_id, s in steps_state.items():
                cols = ", ".join(_STEP_COLUMNS)
                placeholders = ", ".join("?" for _ in _STEP_COLUMNS)
                values = tuple(s.get(c, "") for c in _STEP_COLUMNS)
                await db.execute(
                    f"INSERT OR REPLACE INTO steps ({cols}) VALUES ({placeholders})",
                    values,
                )

            # Write slices
            for _agg_id, s in slices_state.items():
                cols = ", ".join(_SLICE_COLUMNS)
                placeholders = ", ".join("?" for _ in _SLICE_COLUMNS)
                values = tuple(s.get(c) for c in _SLICE_COLUMNS)
                await db.execute(
                    f"INSERT OR REPLACE INTO slices ({cols}) VALUES ({placeholders})",
                    values,
                )

            # Write concepts
            for _agg_id, s in concepts_state.items():
                cols = ", ".join(_CONCEPT_COLUMNS)
                placeholders = ", ".join("?" for _ in _CONCEPT_COLUMNS)
                values = tuple(s.get(c) for c in _CONCEPT_COLUMNS)
                await db.execute(
                    f"INSERT OR REPLACE INTO concepts ({cols}) VALUES ({placeholders})",
                    values,
                )

            log.info(
                "rebuild_complete",
                events_processed=events_processed,
                steps=len(steps_state),
                slices=len(slices_state),
                concepts=len(concepts_state),
            )

            await db.commit()

        return events_processed

    async def apply_event(self, event_row: dict[str, Any]) -> None:
        """Live single-event update after the event has been appended.

        Determines the cache table from ``aggregate_type``, reads the
        existing row (if any), calls the registered handler, and writes
        an ``INSERT OR REPLACE`` in its own transaction.

        Args:
            event_row: A dict with keys matching the events table columns,
                       including ``type``, ``aggregate_type``,
                       ``aggregate_id``, ``data``, and ``ts``.
        """
        event_type = event_row.get("type", "")
        handler = HANDLERS.get(event_type)
        if handler is None:
            return  # Silent skip -- no handler for this event type

        aggregate_type = event_row.get("aggregate_type", "")
        aggregate_id = event_row.get("aggregate_id", "")

        # Determine which cache table to update
        if aggregate_type == "step":
            table = "steps"
            columns = _STEP_COLUMNS
        elif aggregate_type == "slice":
            table = "slices"
            columns = _SLICE_COLUMNS
        elif aggregate_type == "concept":
            table = "concepts"
            columns = _CONCEPT_COLUMNS
        else:
            return  # No cache table for arcs, phases, decisions, etc.

        _validate_table(table)
        event_data = event_row.get("data", {})

        async with get_connection() as db:
            await db.execute("PRAGMA synchronous=FULL;")
            await db.execute("BEGIN IMMEDIATE")

            # Read existing row for this aggregate (if any)
            cursor = await db.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (aggregate_id,),
            )
            existing = await cursor.fetchone()

            if existing is not None:
                current: dict[str, Any] | None = dict(existing)
                # Deserialize frontmatter JSON for the handler
                raw_fm = current.get("frontmatter", "{}")
                if isinstance(raw_fm, str):
                    try:
                        current["frontmatter"] = json.loads(raw_fm)
                    except (json.JSONDecodeError, TypeError):
                        current["frontmatter"] = {}
            else:
                current = None

            new_state = handler(current, event_data)

            # Set envelope fields that the handler cannot know
            new_state["id"] = aggregate_id
            new_state["updated_at"] = event_row.get("ts", "")

            # Build the INSERT OR REPLACE
            cols = ", ".join(columns)
            placeholders = ", ".join("?" for _ in columns)
            values = tuple(new_state.get(c) for c in columns)

            await db.execute(
                f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})",
                values,
            )

            await db.commit()

    async def _read_events(self) -> list[dict[str, Any]]:
        """Read all events ordered by (aggregate_id, seq) with data deserialized.

        Returns:
            List of event-row dicts. Each dict's ``data`` field is a
            Python dict (deserialized from the stored JSON string).
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
                "FROM events "
                "ORDER BY aggregate_id ASC, seq ASC"
            )
            rows = await cursor.fetchall()

            result: list[dict[str, Any]] = []
            for row in rows:
                d = dict(row)
                raw_data = d.get("data", "{}")
                if isinstance(raw_data, str):
                    try:
                        d["data"] = json.loads(raw_data)
                    except (json.JSONDecodeError, TypeError):
                        d["data"] = {}
                result.append(d)
            return result
