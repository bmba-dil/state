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
