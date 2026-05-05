"""state — agentic state-machine workflow engine for opencode."""

from __future__ import annotations

__version__ = "0.1.0"

from src.state_core.scheduler import DAGScheduler, Edge, EdgeKind, Node, NodeRegistry, SchedulerConfig, detect_cycles, frontier, topo_sort

__all__ = [
    "DAGScheduler",
    "detect_cycles",
    "Edge",
    "EdgeKind",
    "frontier",
    "Node",
    "NodeRegistry",
    "SchedulerConfig",
    "topo_sort",
]
