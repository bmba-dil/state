"""Pure-Python DAG scheduler. No networkx dependency."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# -- Type literals -------------------------------------------------------------

EdgeKind = Literal["blocks", "soft", "data"]
"""Edge dependency kind:
- blocks: hard prerequisite — target cannot start until source completes.
- soft: advisory — scheduler may override (e.g. for critical-path promotion).
- data: data-flow dependency — target needs source's output artifacts."""


# -- DAG node types ------------------------------------------------------------


class Edge(BaseModel):
    """A directed dependency edge between two DAG nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_node: str
    target_node: str
    kind: EdgeKind


class Node(BaseModel):
    """A node in the scheduler DAG — represents a unit of work (Arc/Phase/Slice/Step).

    Status lifecycle: idle → pending → in_progress → done (or blocked/failed).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: Literal["arc", "phase", "slice", "step"]
    status: Literal["idle", "pending", "in_progress", "done", "blocked", "failed"] = "idle"


# -- DAG Scheduler skeleton (phases 042-049) -----------------------------------


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""

    async def tick(self, arc_id: str) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...
