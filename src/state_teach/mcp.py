"""state-teach MCP server entry point. FastMCP stdio; mode-gate check."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP  # noqa: F401 (Context: Phase 120 wiring)
from pydantic import BaseModel

# Shared library wiring (Phase 120) — single import surface for all tools
from state_core.auth import load_credentials as _load_credentials  # noqa: F401
from state_core.events import SqliteEventStore as _SqliteEventStore  # noqa: F401


class SkeletonResponse(BaseModel):
    """Standard not-implemented response for skeleton teach-mode tools."""

    tool: str
    status: str = "not_implemented"


def _check_mode_gate(project_root: Path) -> None:
    """Verify mode.json allows state-teach to run.

    Reads .state/mode.json and exits with a clear error if the active
    mode is 'build'.  Called before the server starts.

    Args:
        project_root: Project root directory (where .state/ lives).

    Raises:
        SystemExit(78): If mode is 'build'.
    """
    mode_path = project_root / ".state" / "mode.json"
    if not mode_path.exists():
        return  # No mode file — allow startup (development mode)

    try:
        data = json.loads(mode_path.read_text())
        mode = data.get("mode")
    except (json.JSONDecodeError, OSError):
        return  # Corrupt or unreadable — allow startup

    if mode not in ("teach", "both"):
        sys.stderr.write(
            f"state-teach: mode mismatch — .state/mode.json has mode={mode}, "
            f"but state-teach requires mode=teach or mode=both.\n",
        )
        sys.exit(78)  # EX_CONFIG: configuration error


mcp = FastMCP("state-teach")


# ── Concept and drill tools ───────────────────────────────────


@mcp.tool()
def concept_next() -> SkeletonResponse:
    """Load and display the next concept in the active teach-mode subject sequence"""
    return SkeletonResponse(tool="concept_next")


@mcp.tool()
def drill_prepare() -> SkeletonResponse:
    """Generate a muscle-memory drill for the current concept"""
    return SkeletonResponse(tool="drill_prepare")


@mcp.tool()
def drill_verify() -> SkeletonResponse:
    """Verify learner output against drill expected results"""
    return SkeletonResponse(tool="drill_verify")


@mcp.tool()
def concept_teach() -> SkeletonResponse:
    """Teach one concept using the configured teaching mode"""
    return SkeletonResponse(tool="concept_teach")


# ── Subject and observation tools ─────────────────────────────


@mcp.tool()
def observation_record() -> SkeletonResponse:
    """Record a structured observation about learner behavior"""
    return SkeletonResponse(tool="observation_record")


@mcp.tool()
def mental_model_show() -> SkeletonResponse:
    """Display the current mental model projection for the active learner"""
    return SkeletonResponse(tool="mental_model_show")


@mcp.tool()
def subject_pick() -> SkeletonResponse:
    """Select or switch the active teach-mode subject"""
    return SkeletonResponse(tool="subject_pick")


@mcp.tool()
def subject_author() -> SkeletonResponse:
    """Create or edit a teach-mode subject definition"""
    return SkeletonResponse(tool="subject_author")


@mcp.tool()
def style_edit() -> SkeletonResponse:
    """View or modify the active teaching style configuration"""
    return SkeletonResponse(tool="style_edit")


# ── Session and verification tools ────────────────────────────


@mcp.tool()
def learner_state() -> SkeletonResponse:
    """Show current learner state and session history"""
    return SkeletonResponse(tool="learner_state")


@mcp.tool()
def review_session() -> SkeletonResponse:
    """Run a scheduled review session for concepts approaching their review interval"""
    return SkeletonResponse(tool="review_session")


@mcp.tool()
def mentor_scaffold() -> SkeletonResponse:
    """Guide the learner through creating a project skeleton file-by-file"""
    return SkeletonResponse(tool="mentor_scaffold")


@mcp.tool()
def coding_partner() -> SkeletonResponse:
    """Start an interactive coding partner session"""
    return SkeletonResponse(tool="coding_partner")


@mcp.tool()
def learning_verify() -> SkeletonResponse:
    """Run goal-backward verification on learner concept mastery"""
    return SkeletonResponse(tool="learning_verify")


@mcp.tool()
def knowledge_check() -> SkeletonResponse:
    """Quiz the learner with retrieval-practice questions on the active concept"""
    return SkeletonResponse(tool="knowledge_check")


if __name__ == "__main__":
    _check_mode_gate(Path.cwd())
    asyncio.run(mcp.run_stdio_async())
