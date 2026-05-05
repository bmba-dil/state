"""state-build MCP server entry point.

Mode-gated MCP server for build-mode tools. Registered as ``state-build``
in opencode MCP config. Tool schemas are pydantic-validated via type hints.

Provides 15 skeleton tools (MCP-B-03). Real implementations deferred to
Phase 111 (shared library wiring).
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


class SkeletonResponse(BaseModel):
    """Standard not-implemented response for skeleton tools."""

    tool: str
    status: str = "not_implemented"
    task_id: str | None = None


# ── Planning tools ────────────────────────────────────────────


@mcp.tool()
def plan_step(task_id: str | None = None) -> SkeletonResponse:
    """Create step plan from discuss context. Returns structured task list."""
    return SkeletonResponse(tool="plan_step", task_id=task_id)


@mcp.tool()
def execute_step(task_id: str | None = None) -> SkeletonResponse:
    """Execute planned step tasks. Reports progress per task."""
    return SkeletonResponse(tool="execute_step", task_id=task_id)


@mcp.tool()
def verify_step(task_id: str | None = None) -> SkeletonResponse:
    """Goal-backward verification of step outputs. Returns pass/gap status."""
    return SkeletonResponse(tool="verify_step", task_id=task_id)


@mcp.tool()
def discuss_step(task_id: str | None = None) -> SkeletonResponse:
    """Surface implementation decisions for a step. Returns grey-area table."""
    return SkeletonResponse(tool="discuss_step", task_id=task_id)


@mcp.tool()
def research_step() -> SkeletonResponse:
    """Research technical approach for a step. Returns findings document."""
    return SkeletonResponse(tool="research_step")


# ── DAG and arc tools ────────────────────────────────────────


@mcp.tool()
def dag_status() -> SkeletonResponse:
    """Query build-mode DAG scheduler state. Returns node and edge counts."""
    return SkeletonResponse(tool="dag_status")


@mcp.tool()
def arc_show() -> SkeletonResponse:
    """Display current arc status and phase progression."""
    return SkeletonResponse(tool="arc_show")


# ── Ship and snapshot tools ───────────────────────────────────


@mcp.tool()
def slice_ship() -> SkeletonResponse:
    """Ship completed slice with PR and verification. Returns ship status."""
    return SkeletonResponse(tool="slice_ship")


@mcp.tool()
def snapshot_revert() -> SkeletonResponse:
    """Revert working tree to named snapshot. Returns reverted ref."""
    return SkeletonResponse(tool="snapshot_revert")


# ── Quality tools ─────────────────────────────────────────────


@mcp.tool()
def code_review(task_id: str | None = None) -> SkeletonResponse:
    """Review staged changes for bugs and quality. Returns structured findings."""
    return SkeletonResponse(tool="code_review", task_id=task_id)


# ── Session and debugging tools ───────────────────────────────


@mcp.tool()
def debug_session(task_id: str | None = None) -> SkeletonResponse:
    """Start or resume a persistent debug session. Returns session ID."""
    return SkeletonResponse(tool="debug_session", task_id=task_id)


@mcp.tool()
def forensics() -> SkeletonResponse:
    """Post-mortem failed workflow analysis. Returns forensic report."""
    return SkeletonResponse(tool="forensics")


# ── Utility tools ─────────────────────────────────────────────


@mcp.tool()
def intel_refresh() -> SkeletonResponse:
    """Refresh codebase intelligence files. Returns updated intel paths."""
    return SkeletonResponse(tool="intel_refresh")


@mcp.tool()
def pause_work() -> SkeletonResponse:
    """Create context handoff for pausing. Returns handoff path."""
    return SkeletonResponse(tool="pause_work")


@mcp.tool()
def resume_work() -> SkeletonResponse:
    """Resume from saved context handoff. Returns restored state."""
    return SkeletonResponse(tool="resume_work")


if __name__ == "__main__":
    mcp.run(transport="stdio")
