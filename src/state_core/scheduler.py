"""Pure-Python DAG scheduler. No networkx dependency."""

from __future__ import annotations

import asyncio
import tomllib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


StepExecutor = Callable[[Node], Awaitable[None]]
"""Async callable that executes a single Step. Injected for testability."""


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


def _slice_key(node_id: str) -> str:
    """Extract Slice prefix from node ID for dispatch grouping.

    Returns the path component up to and including 'slice-N'.
    Falls back to the full node_id if no 'slice-N' component is found
    (e.g., standalone arc/phase nodes group individually).

    >>> _slice_key("arc-1/phase-1/slice-1/step-2")
    'arc-1/phase-1/slice-1'
    >>> _slice_key("arc-1/phase-1/slice-1")
    'arc-1/phase-1/slice-1'
    >>> _slice_key("arc-1/phase-1")
    'arc-1/phase-1'
    """
    parts = node_id.split("/")
    for i, part in enumerate(parts):
        if part.startswith("slice-"):
            return "/".join(parts[: i + 1])
    return node_id


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


# -- Frontier calculator --------------------------------------------------------


def frontier(nodes: list[Node], edges: list[Edge]) -> list[Node]:
    """Return unblocked nodes whose blocks/data predecessors are all DONE.

    - Nodes with status 'done' or 'failed' are excluded.
    - Only 'blocks' and 'data' edges block; 'soft' edges do NOT block.
    - A node is unblocked iff ALL its blocks/data predecessors have status 'done'.

    Args:
        nodes: All nodes in the DAG.
        edges: Directed dependency edges (source_node -> target_node).

    Returns:
        Nodes that are unblocked and not done/failed.

    Raises:
        ValueError: If an edge references a source_node not in the nodes list.
    """
    node_map = {n.id: n for n in nodes}

    result: list[Node] = []
    for node in nodes:
        # Exclude done and failed nodes — they're already resolved
        if node.status in ("done", "failed"):
            continue

        # Find all edges targeting this node that are blocking
        blocking_predecessors = [
            edge for edge in edges
            if edge.target_node == node.id
            and edge.kind in ("blocks", "data")
        ]

        # Validate edge endpoints (matching topo_sort pattern)
        for edge in blocking_predecessors:
            if edge.source_node not in node_map:
                raise ValueError(
                    f"Edge source '{edge.source_node}' not found in node list"
                )

        # Check all blocking predecessors are done
        all_done = all(
            node_map[edge.source_node].status == "done"
            for edge in blocking_predecessors
        )

        if all_done:
            result.append(node)

    return result


# -- Cycle detection -----------------------------------------------------------


def detect_cycles(edges: list[Edge]) -> list[list[str]]:
    """DFS-based cycle detection with 3-color marking (WHITE/GRAY/BLACK).

    Returns a list of cycle paths found in the graph. Each cycle is
    a list[str] of node IDs where the first and last elements are the
    same node (the back-edge closure point). Returns an empty list
    for acyclic DAGs.

    Uses iterative DFS with an explicit path stack to extract cycle
    paths when back edges (GRAY→GRAY) are detected. Nodes are derived
    from edge endpoints only — no separate node list is required.

    Args:
        edges: Directed dependency edges. Nodes are derived from edge
               endpoints — no separate node list is required.

    Returns:
        List of cycles, each a list of node ID strings forming the
        cycle path. Empty list if the graph has no cycles.
    """
    # Derive all unique nodes from edge endpoints
    nodes: set[str] = set()
    for edge in edges:
        nodes.add(edge.source_node)
        nodes.add(edge.target_node)

    if not nodes:
        return []

    # Build adjacency list
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in edges:
        adj[edge.source_node].append(edge.target_node)

    # 3-color marking: 0=WHITE, 1=GRAY, 2=BLACK
    color: dict[str, int] = {n: 0 for n in nodes}
    cycles: list[list[str]] = []

    # Iterative DFS with explicit path — avoids recursion limit issues
    # and makes cycle-path extraction straightforward.
    for start in sorted(nodes):
        if color[start] != 0:
            continue

        # Each entry: (node, neighbor_index). The neighbor_index is the
        # NEXT neighbor to examine (0 means haven't started examining).
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = [start]
        color[start] = 1  # GRAY

        while stack:
            node, ni = stack[-1]
            neighbors = adj.get(node, [])

            if ni >= len(neighbors):
                # All neighbors examined — pop, mark BLACK
                stack.pop()
                path.pop()
                color[node] = 2  # BLACK
                continue

            # Advance the frame's neighbor index for next time
            stack[-1] = (node, ni + 1)

            neighbor = neighbors[ni]
            if color[neighbor] == 0:  # WHITE → descend
                stack.append((neighbor, 0))
                path.append(neighbor)
                color[neighbor] = 1  # GRAY
            elif color[neighbor] == 1:  # GRAY → back edge, cycle found
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
            # BLACK → skip (already fully explored)

    return cycles


# -- DAG Scheduler skeleton (phases 042-049) -----------------------------------


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""

    def __init__(
        self,
        concurrency_cap: int = 4,
        step_executor: StepExecutor | None = None,
    ) -> None:
        self.concurrency_cap = max(1, min(concurrency_cap, 64))
        self._executor: StepExecutor = step_executor or _default_step_executor

    async def tick(self, nodes: list[Node], edges: list[Edge]) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...


async def _default_step_executor(node: Node) -> None:
    """Default no-op step executor — used when none is injected."""
    pass


class SchedulerConfig(BaseModel):
    """Scheduler configuration loaded from .state/config.toml [scheduler] section."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concurrency_cap: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum number of Slices to dispatch concurrently per tick.",
    )


def load_scheduler_config(config_path: Path | None = None) -> SchedulerConfig:
    """Load scheduler config from .state/config.toml, falling back to defaults."""
    defaults = SchedulerConfig()
    path = config_path or Path(".state/config.toml")

    if not path.is_file():
        return defaults

    try:
        raw = path.read_text(encoding="utf-8")
        data = tomllib.loads(raw)
        scheduler_data = data.get("scheduler", {})
        if not isinstance(scheduler_data, dict):
            return defaults
        merged = defaults.model_dump() | {
            k: v for k, v in scheduler_data.items() if k in defaults.model_fields
        }
        return SchedulerConfig(**merged)
    except (tomllib.TOMLDecodeError, OSError, ValueError):
        return defaults
