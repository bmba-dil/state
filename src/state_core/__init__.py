"""state — agentic state-machine workflow engine for opencode."""

from __future__ import annotations

__version__ = "0.1.0"

from src.state_core.scheduler import Edge, EdgeKind, Node, NodeRegistry, frontier, topo_sort

__all__ = [
    "Edge",
    "EdgeKind",
    "frontier",
    "Node",
    "NodeRegistry",
    "topo_sort",
]
