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
"""Event-type-to-handler registry. Populated by @_register_handler decorator."""


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
