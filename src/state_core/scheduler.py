"""Pure-Python DAG scheduler. No networkx dependency."""

from __future__ import annotations


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""

    async def tick(self, arc_id: str) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...
