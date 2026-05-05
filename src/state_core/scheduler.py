"""Pure-Python DAG scheduler. No networkx dependency."""

from __future__ import annotations

import asyncio
import tomllib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

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


# -- P0-16 Watchdog -------------------------------------------------------------


class SwallowedCancelledError(Exception):
    """Raised by the scheduler watchdog when a swallowed CancelledError
    is detected in a TaskGroup exception group (P0-16 defence).

    The __cause__ chain preserves the original CancelledError for forensics.
    """


def _inspect_for_cancelled(exc: BaseException) -> None:
    """Recursively inspect exception group tree for swallowed CancelledError.

    Python's asyncio.TaskGroup can silently drop CancelledError from
    ExceptionGroup contents when other exceptions are present
    (CPython #116720). This inspector walks the entire exception group
    tree and raises SwallowedCancelledError if ANY CancelledError is
    found — failing loud instead of silently deadlocking the scheduler.

    Args:
        exc: The exception to inspect (may be a leaf exception or group).

    Raises:
        SwallowedCancelledError: If a CancelledError is found anywhere
            in the exception tree.
    """
    if isinstance(exc, asyncio.CancelledError):
        raise SwallowedCancelledError(
            "Watchdog detected swallowed CancelledError in "
            "asyncio.TaskGroup exception group"
        ) from exc
    if isinstance(exc, (ExceptionGroup, BaseExceptionGroup)):
        for sub_exc in exc.exceptions:
            _inspect_for_cancelled(sub_exc)


# -- Critical Path Method (CPM) ---------------------------------------------


def _critical_path_nodes(
    nodes: list[Node],
    edges: list[Edge],
    *,
    edge_kinds: set[EdgeKind] | None = None,
) -> set[str]:
    """Compute nodes on the critical path using CPM with DP on topological order.

    Soft edges are excluded by default; only ``blocks`` and ``data`` edges
    contribute to path length.

    Algorithm:
      1. Filter edges to allowed kinds.
      2. Topological sort.
      3. Forward pass (DP): longest distance from any root to each node.
      4. Backward pass (DP): longest distance from each node to any sink.
      5. Node is critical iff forward[node] + backward[node] == max_forward + 1.

    Complexity: O(V + E).

    Args:
        nodes: All DAG nodes.
        edges: All DAG edges.
        edge_kinds: Edge kinds to include.  Defaults to ``{"blocks", "data"}``.

    Returns:
        Set of node IDs on the critical path.
    """
    if edge_kinds is None:
        edge_kinds = {"blocks", "data"}

    if not nodes:
        return set()

    node_ids = {n.id for n in nodes}
    node_map = {n.id: n for n in nodes}

    # Build adjacency and in-degree restricted to allowed kinds
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    in_deg: dict[str, int] = {n.id: 0 for n in nodes}
    rev_adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    out_deg: dict[str, int] = {n.id: 0 for n in nodes}

    for edge in edges:
        if edge.kind not in edge_kinds:
            continue
        if edge.source_node not in node_ids or edge.target_node not in node_ids:
            continue  # edge references unknown node — skip gracefully
        adj[edge.source_node].append(edge.target_node)
        in_deg[edge.target_node] += 1
        rev_adj[edge.target_node].append(edge.source_node)
        out_deg[edge.source_node] += 1

    # Topological sort (Kahn's, but we need deterministic order — use topo_sort)
    try:
        sorted_nodes = topo_sort(
            [e for e in edges if e.kind in edge_kinds], nodes
        )
    except ValueError:
        # Cycle in edge-kind-filtered subgraph — fallback: treat all as critical
        return node_ids

    order = [n.id for n in sorted_nodes]

    # Forward DP: longest distance from any root to each node
    forward: dict[str, int] = {nid: 0 for nid in node_ids}
    for nid in order:
        for neighbor in adj.get(nid, []):
            if forward[nid] + 1 > forward[neighbor]:
                forward[neighbor] = forward[nid] + 1

    max_forward = max(forward.values()) if forward else 0

    # Backward DP: longest distance from each node to any sink
    backward: dict[str, int] = {nid: 0 for nid in node_ids}
    for nid in reversed(order):
        for pred in rev_adj.get(nid, []):
            if backward[nid] + 1 > backward[pred]:
                backward[pred] = backward[nid] + 1

    # Critical path: forward + backward == max_forward
    # (forward/backward count edges, not nodes — the node itself sits
    # at the midpoint and is not double-counted.)
    critical: set[str] = set()
    for nid in node_ids:
        if forward[nid] + backward[nid] == max_forward:
            critical.add(nid)

    # Ensure single-node / no-edge graphs still return something
    if not critical:
        critical = node_ids

    return critical


def detect_priority_inversion(
    nodes: list[Node], edges: list[Edge]
) -> list[dict[str, Any]]:
    """Detect frontier nodes blocked only by soft edges on the critical path.

    Algorithm:
      1. Compute frontier via the existing ``frontier()`` function.
      2. Compute critical path nodes via ``_critical_path_nodes()``.
      3. For each frontier node, find unfulfilled soft edges (source NOT done).
      4. Flag only nodes that are on the critical path AND have such soft edges.

    Args:
        nodes: All DAG nodes.
        edges: All DAG edges.

    Returns:
        List of dicts with keys ``node_id``, ``soft_edges``, ``critical_path``.
        Empty list if no priority inversion detected.
    """
    # Edge case: empty input
    if not nodes:
        return []

    node_map = {n.id: n for n in nodes}

    # Compute frontier (ignores soft edges)
    frontier_nodes = frontier(nodes, edges)

    # Compute critical path (excludes soft edges)
    critical = _critical_path_nodes(nodes, edges)

    results: list[dict[str, Any]] = []
    for node in frontier_nodes:
        # Find soft edges targeting this node where source is NOT done
        soft_blocking: list[str] = []
        for edge in edges:
            if edge.target_node != node.id:
                continue
            if edge.kind != "soft":
                continue
            source = node_map.get(edge.source_node)
            if source is None:
                continue  # unknown source — skip gracefully
            if source.status != "done":
                soft_blocking.append(edge.source_node)

        # Only flag if on critical path AND has unfulfilled soft edges
        if soft_blocking and node.id in critical:
            results.append({
                "node_id": node.id,
                "soft_edges": soft_blocking,
                "critical_path": True,
            })

    return results


def detect_silent_deadlock(
    nodes: list[Node], edges: list[Edge]
) -> dict[str, Any] | None:
    """Detect when frontier is empty and ALL in-progress nodes are stuck.

    A deadlock occurs when:
      - The frontier is empty (no dispatchable work).
      - At least one node is in_progress.
      - EVERY in_progress node is blocked on missing or descoped predecessors
        (i.e., has no reachable predecessor that could still complete).

    Algorithm:
      1. Compute frontier.  Non-empty → return None.
      2. Find nodes with status ``"in_progress"``.  None → return None.
      3. Build set of known node IDs for membership testing.
      4. For each in_progress node, examine its blocking (blocks, data) edges.
      5. If ALL in_progress nodes are stuck (no reachable non-done predecessor),
         return deadlock payload.  Otherwise return None.

    Args:
        nodes: All DAG nodes.
        edges: All DAG edges.

    Returns:
        Dict with keys ``deadlocked_nodes``, ``missing_predecessors``,
        ``descoped_predecessors`` if deadlock detected; ``None`` otherwise.
    """
    # Edge case: empty
    if not nodes:
        return None

    # 1. Frontier must be empty.  Add shadow "failed" nodes for edges
    #    with missing source nodes so frontier() sees them as blocking
    #    predecessors (missing sources can never complete).
    node_map = {n.id: n for n in nodes}
    node_id_set = set(node_map.keys())

    # Collect missing source IDs referenced by edges
    missing_sources: set[str] = set()
    for edge in edges:
        if edge.source_node not in node_id_set:
            missing_sources.add(edge.source_node)

    # Build extended node list with shadow failed nodes for missing sources
    shadow_nodes = list(nodes)
    for ms in missing_sources:
        shadow_nodes.append(Node(id=ms, kind="step", status="failed"))

    f = frontier(shadow_nodes, edges)
    # Exclude shadow nodes from frontier result (they're synthetic)
    f = [n for n in f if n.id not in missing_sources and n.status != "blocked"]
    if f:
        return None

    # 2. Must have in_progress nodes
    in_progress = [n for n in nodes if n.status == "in_progress"]
    if not in_progress:
        return None

    # 3. Determine if ALL in_progress nodes are stuck
    deadlocked: list[str] = []
    missing_all: list[str] = []
    descoped_all: list[str] = []

    for node in in_progress:
        # Find blocking edges (blocks, data) targeting this node
        blocking_edges = [
            e for e in edges
            if e.target_node == node.id and e.kind in ("blocks", "data")
        ]

        if not blocking_edges:
            # No blocking edges → node is not stuck on predecessors
            # (it's in progress and doesn't need anything)
            return None  # not ALL stuck

        has_reachable = False
        node_missing: list[str] = []
        node_descoped: list[str] = []

        for edge in blocking_edges:
            src_id = edge.source_node

            if src_id not in node_id_set:
                # Source not in node list → missing
                node_missing.append(src_id)
                continue

            src_status = node_map[src_id].status

            if src_status in ("failed", "blocked"):
                # Descoped (terminal failure states)
                node_descoped.append(src_id)
            elif src_status == "done":
                # Done — satisfied, not a problem
                continue
            else:
                # idle, pending, in_progress — reachable, could still complete
                has_reachable = True

        # This node is stuck iff it has at least one missing/descoped
        # predecessor AND no reachable predecessor could satisfy it.
        if (node_missing or node_descoped) and not has_reachable:
            deadlocked.append(node.id)
            missing_all.extend(node_missing)
            descoped_all.extend(node_descoped)
        else:
            # At least one in_progress node is NOT stuck → no deadlock
            return None

    # 4. ALL in_progress nodes are stuck → deadlock
    if not deadlocked:
        return None

    # Deduplicate predecessor lists while preserving order
    seen_missing: set[str] = set()
    uniq_missing: list[str] = []
    for m in missing_all:
        if m not in seen_missing:
            seen_missing.add(m)
            uniq_missing.append(m)

    seen_descoped: set[str] = set()
    uniq_descoped: list[str] = []
    for d in descoped_all:
        if d not in seen_descoped:
            seen_descoped.add(d)
            uniq_descoped.append(d)

    return {
        "deadlocked_nodes": deadlocked,
        "missing_predecessors": uniq_missing,
        "descoped_predecessors": uniq_descoped,
    }


# -- DAG Scheduler skeleton (phases 042-049) -----------------------------------


class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change.

    On each tick:
    1. Compute frontier() — all unblocked nodes
    2. Group by Slice (via _slice_key)
    3. Sort steps within each Slice (via _parse_sort_key)
     4. Dispatch up to concurrency_cap Slices concurrently (via asyncio.TaskGroup)
    5. Steps within a Slice execute sequentially
    6. Return dispatched node IDs
    """

    def __init__(
        self,
        concurrency_cap: int = 4,
        step_executor: StepExecutor | None = None,
        on_scheduler_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.concurrency_cap = max(1, min(concurrency_cap, 64))
        self._executor: StepExecutor = step_executor or _default_step_executor
        self._on_scheduler_event = on_scheduler_event

    async def tick(self, nodes: list[Node], edges: list[Edge]) -> list[str]:
        """Compute frontier, group by Slice, dispatch up to cap.

        Args:
            nodes: All DAG nodes (any status — frontier filters to unblocked).
            edges: All DAG edges (blocks/data/soft).

        Returns:
            Node IDs that were dispatched in this tick.
        """
        ready = frontier(nodes, edges)

        # Group by Slice
        by_slice: dict[str, list[Node]] = {}
        for node in ready:
            key = _slice_key(node.id)
            if key not in by_slice:
                by_slice[key] = []
            by_slice[key].append(node)

        # Sort steps within each Slice for serial execution
        for key in by_slice:
            by_slice[key].sort(key=lambda n: _parse_sort_key(n.id))

        # Select up to concurrency_cap Slices
        slice_entries = list(by_slice.items())[: self.concurrency_cap]

        dispatched: list[str] = []

        # ── Post-tick diagnostics (DAG-05, DAG-06) ──────────────────────
        # Run diagnostics before dispatch so silent deadlock (which
        # requires an empty frontier) is always detected.  Wrap in
        # try/except so diagnostics failure never blocks the scheduler.
        try:
            if self._on_scheduler_event is not None:
                # Priority inversion: nodes in frontier blocked only by soft edges
                inversions = detect_priority_inversion(nodes, edges)
                for inv in inversions:
                    await self._on_scheduler_event(
                        "state.scheduler.priority_inversion",
                        {"node_id": inv["node_id"],
                         "soft_edges": inv["soft_edges"],
                         "critical_path": inv["critical_path"]},
                    )

                # Silent deadlock: all in-progress stuck on missing/descoped
                deadlock = detect_silent_deadlock(nodes, edges)
                if deadlock is not None:
                    await self._on_scheduler_event(
                        "state.scheduler.deadlock",
                        {
                            "deadlocked_nodes": deadlock["deadlocked_nodes"],
                            "missing_predecessors": deadlock["missing_predecessors"],
                            "descoped_predecessors": deadlock["descoped_predecessors"],
                        },
                    )
        except Exception:
            # Diagnostics failure must never abort a tick.  No log here to
            # avoid coupling scheduler to structlog — caller instruments.
            pass

        if not slice_entries:
            return dispatched

        async def _run_slice(slice_nodes: list[Node]) -> None:
            """Execute steps within a Slice sequentially."""
            for node in slice_nodes:
                dispatched.append(node.id)
                await self._executor(node)

        # Concurrent dispatch across Slices — uses TaskGroup for
        # exception-group awareness (P0-16 defence).
        try:
            async with asyncio.TaskGroup() as tg:
                for _, slice_nodes in slice_entries:
                    tg.create_task(_run_slice(slice_nodes))
        except BaseExceptionGroup as eg:
            _inspect_for_cancelled(eg)
            raise

        return dispatched


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
            k: v for k, v in scheduler_data.items() if k in SchedulerConfig.model_fields
        }
        return SchedulerConfig(**merged)
    except (tomllib.TOMLDecodeError, OSError, ValueError):
        return defaults
