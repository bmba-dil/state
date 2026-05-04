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


# -- Node registry -----------------------------------------------------------


class NodeRegistry:
    """In-memory registry of all DAG nodes keyed by node ID.

    Provides O(1) lookup, upsert, and removal.  Raises ValueError on duplicate
    registration to prevent accidental overwrites — later phases can add explicit
    update methods when status transitions are needed.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}

    def register(self, node: Node) -> None:
        """Register a node. Raises ValueError if node.id already present."""
        if node.id in self._nodes:
            raise ValueError(f"Node '{node.id}' already registered")
        self._nodes[node.id] = node

    def get(self, node_id: str) -> Node:
        """Retrieve a node by ID. Raises KeyError if not found."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def contains(self, node_id: str) -> bool:
        """Return True if node_id is registered."""
        return node_id in self._nodes

    def remove(self, node_id: str) -> None:
        """Remove a node by ID. Raises KeyError if not found."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        del self._nodes[node_id]

    def all_nodes(self) -> list[Node]:
        """Return a list of all registered nodes."""
        return list(self._nodes.values())

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes


# -- DAG Scheduler skeleton (phases 042-049) -----------------------------------


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""

    async def tick(self, arc_id: str) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...
