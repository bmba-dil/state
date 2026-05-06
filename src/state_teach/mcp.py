"""state-teach MCP server entry point — Phase 115. FastMCP stdio; mode-gate check."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import structlog
from mcp.server.fastmcp import Context, FastMCP  # noqa: F401 (Context: Phase 120 wiring)
from pydantic import BaseModel

from state_core.schema import validate_mode_config

# Shared library wiring (Phase 120) — single import surface for all tools
from state_core.auth import load_credentials as _load_credentials  # noqa: F401
from state_core.events import SqliteEventStore as _SqliteEventStore  # noqa: F401

log = structlog.get_logger(__name__)


class SkeletonResponse(BaseModel):
    """Standard not-implemented response for skeleton teach-mode tools."""

    tool: str
    status: str = "not_implemented"


def check_mode_gate(project_root: Path) -> None:
    """Read .state/mode.json and refuse to start if mode is 'build'.

    Args:
        project_root: Project root directory (where .state/ lives).

    Raises:
        SystemExit(1): If mode is 'build' or mode.json is invalid.
    """
    mode_path = project_root / ".state" / "mode.json"
    if not mode_path.exists():
        log.warning("mcp.mode_gate_no_file", path=str(mode_path))
        return

    try:
        raw = mode_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        log.error("mcp.mode_gate_invalid_json", path=str(mode_path), error=str(exc))
        sys.exit(1)

    try:
        cfg = validate_mode_config(data)
    except ValueError as exc:
        log.error("mcp.mode_gate_invalid_config", path=str(mode_path), error=str(exc))
        sys.exit(1)

    if cfg.mode == "build":
        log.error("mcp.mode_gate_blocked", reason="state-teach cannot start in build mode")
        sys.exit(1)

    log.info("mcp.mode_gate_passed", mode=cfg.mode)


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


if __name__ == "__main__":
    check_mode_gate(Path.cwd())
    asyncio.run(mcp.run_stdio_async())
