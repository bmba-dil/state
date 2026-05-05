"""state-build MCP server entry point.

Mode-gated MCP server for build-mode tools. Registered as ``state-build``
in opencode MCP config. Tool schemas are pydantic-validated via type hints.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP(
    "state-build",
    instructions="Build-mode tools for the state workflow engine. "
    "Provides plan_step, execute_step, verify_step, discuss_step, "
    "dag_status, arc_show, slice_ship, code_review, debug_session, "
    "forensics, intel_refresh, pause_work, resume_work, "
    "research_step, and snapshot_revert tools.",
)


class DAGStatus(BaseModel):
    """DAG scheduler status response."""

    status: str = "not_implemented"
    nodes: int = 0
    edges: int = 0


@mcp.tool()
def dag_status() -> DAGStatus:
    """Query the current state of the build-mode DAG scheduler.

    Returns node and edge counts plus overall scheduler status.
    Full implementation deferred to Phase 107 (shared library wiring).
    """
    return DAGStatus()


if __name__ == "__main__":
    mcp.run(transport="stdio")
