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


# -- Topological sort -----------------------------------------------------------


def _parse_sort_key(node_id: str) -> tuple[str, str]:
    """Derive (slice_id, step_id) from node.id for stable topological ordering.

    Splits node_id on '/' and extracts 'slice-N' and 'step-N' components.
    For IDs without slice/step components, returns ('', node_id) as fallback
    so non-step nodes sort before steps.

    >>> _parse_sort_key("arc-1")
    ('', 'arc-1')
    >>> _parse_sort_key("arc-1/phase-1/slice-1/step-2")
    ('slice-1', 'step-2')
    >>> _parse_sort_key("arc-1/phase-1/slice-1")
    ('slice-1', '')
    """
    parts = node_id.split("/")
    slice_part = ""
    step_part = ""
    for part in parts:
        if part.startswith("slice-"):
            slice_part = part
        elif part.startswith("step-"):
            step_part = part
    if not slice_part and not step_part:
        return ("", node_id)
    return (slice_part, step_part)


def topo_sort(edges: list[Edge], nodes: list[Node]) -> list[Node]:
    """Kahn's algorithm topological sort with stable ordering.

    Returns nodes in dependency order (dependencies before dependents).
    Within the frontier (in-degree=0 nodes), ties are broken by
    (slice_id, step_id) derived from node.id for deterministic output.

    Args:
        edges: Directed dependency edges (source_node -> target_node).
        nodes: All nodes in the DAG.

    Returns:
        Nodes in topological order.

    Raises:
        ValueError: If an edge references a node not in the nodes list,
                    or if the DAG contains a cycle.
    """
    # Validate: all edge endpoints exist in node list
    node_ids = {n.id for n in nodes}
    for edge in edges:
        if edge.source_node not in node_ids:
            raise ValueError(
                f"Edge source '{edge.source_node}' not found in node list"
            )
        if edge.target_node not in node_ids:
            raise ValueError(
                f"Edge target '{edge.target_node}' not found in node list"
            )

    # Build adjacency list and in-degree map
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}
    node_map: dict[str, Node] = {n.id: n for n in nodes}

    for edge in edges:
        adj[edge.source_node].append(edge.target_node)
        in_degree[edge.target_node] += 1

    # Kahn's algorithm with stable frontier ordering
    frontier = sorted(
        [nid for nid, deg in in_degree.items() if deg == 0],
        key=_parse_sort_key,
    )

    result: list[Node] = []

    while frontier:
        current = frontier.pop(0)
        result.append(node_map[current])

        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                frontier.append(neighbor)

        # Re-sort frontier for stability after adding new elements
        if frontier:
            frontier.sort(key=_parse_sort_key)

    if len(result) != len(nodes):
        remaining_ids = sorted(node_ids - {n.id for n in result})
        raise ValueError(
            f"Cycle detected in DAG: {len(remaining_ids)} node(s) "
            f"not reachable: {remaining_ids}"
        )

    return result


# -- DAG Scheduler skeleton (phases 042-049) -----------------------------------


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""

    async def tick(self, arc_id: str) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...
