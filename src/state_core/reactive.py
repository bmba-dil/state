"""ReactiveTrigger — event-driven DAG scheduler activation via post-commit callbacks.

Wires SqliteEventStore post-commit callbacks to DAGScheduler.tick() so that
Step/Slice/Phase completion events immediately unblock successor nodes.
No polling — purely event-driven via add_post_commit_callback.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import structlog

from src.state_core.scheduler import DAGScheduler, Edge, Node

log = structlog.get_logger(__name__)


# Default watched event types — the completion signals that trigger a DAG tick.
_DEFAULT_WATCHED: frozenset[str] = frozenset({
    "state.step.advanced",
    "state.slice.worktree_ready",
    "state.phase.planned",
})


class ReactiveTrigger:
    """Subscribes to event-store post-commit callbacks and calls
    ``DAGScheduler.tick()`` when relevant state-change events occur.

    Follows the same pattern as ``SseBus.on_event()``:
    - sync callback (``on_event``) receives event_row dict
    - filters by event type
    - dispatches ``_tick()`` via ``asyncio.create_task()`` (fire-and-forget)

    The post-commit path must never block on tick execution.
    """

    def __init__(
        self,
        scheduler: DAGScheduler,
        dag_provider: Callable[[], tuple[list[Node], list[Edge]]],
        watched_events: frozenset[str] | None = None,
    ) -> None:
        """Initialise the reactive trigger.

        Args:
            scheduler: The DAG scheduler whose tick() will be called.
            dag_provider: Injectable callable returning current (nodes, edges).
            watched_events: Set of event types that trigger a tick.  Defaults
                to ``{"state.step.advanced", "state.slice.worktree_ready",
                "state.phase.planned"}``.
        """
        self._scheduler = scheduler
        self._dag_provider = dag_provider
        self._watched: frozenset[str] = (
            watched_events if watched_events is not None else _DEFAULT_WATCHED
        )

    @property
    def watched_events(self) -> frozenset[str]:
        """Return the current frozenset of watched event types (immutable)."""
        return self._watched

    def on_event(self, event_row: dict[str, Any]) -> None:
        """Sync callback for ``SqliteEventStore.add_post_commit_callback``.

        Extracts ``event_row["type"]`` and, if it matches a watched type,
        schedules ``_tick()`` via ``asyncio.create_task()``.  Must be called
        from within a running event loop (same constraint as ``SseBus``).

        Never awaits anything — this is a sync callback; the event store's
        post-commit path must not block on tick execution.
        """
        event_type = event_row.get("type")
        if event_type is None or event_type not in self._watched:
            return

        asyncio.create_task(self._tick())

    async def _tick(self) -> None:
        """Internal tick dispatcher — fetch current DAG state and invoke scheduler.

        Wrapped in try/except — a tick failure must not crash the post-commit
        callback chain (T-047-01 mitigation).
        """
        try:
            nodes, edges = self._dag_provider()
            await self._scheduler.tick(nodes, edges)
        except Exception:
            log.exception(
                "reactive.tick_failed",
                watched=str(self._watched),
            )
