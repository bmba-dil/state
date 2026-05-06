"""state-teach MCP server entry point — Phase 115. FastMCP stdio; mode-gate check."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import structlog
from mcp.server.fastmcp import FastMCP

from state_core.schema import validate_mode_config

log = structlog.get_logger(__name__)


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


@mcp.tool(description="Determine the next concept to teach from the learner's position in the subject concept tree.")
async def concept_next() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Prepare a drill session with typing and modification exercises for the current concept.")
async def drill_prepare() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Verify the learner's drill session results and record performance metrics.")
async def drill_verify() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Teach one concept using a mode chosen from PRIMM, Scaffolded, Socratic, or Constructivist.")
async def concept_teach() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Record a structured observation about the learner's behavior during a teaching session.")
async def observation_record() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Display the mental model projection showing the learner's mastery across all taught concepts.")
async def mental_model_show() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Select an active learning subject from the available subject catalog.")
async def subject_pick() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Create or modify a subject definition including its concept tree and prerequisite mappings.")
async def subject_author() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Edit the teaching style including verbosity, pace, hint level, and feedback preferences.")
async def style_edit() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Retrieve or update the learner's current state including progress, session data, and mode.")
async def learner_state() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Conduct a code review session with graduated hints for the learner's submitted code.")
async def review_session() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Guide the learner through creating a project skeleton with structured observations.")
async def mentor_scaffold() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Provide interactive coding mentorship with graduated hints when the learner is stuck.")
async def coding_partner() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Verify learning outcomes by checking the learner's comprehension against concept objectives.")
async def learning_verify() -> dict[str, str]:
    return {"error": "not_implemented"}


@mcp.tool(description="Check the learner's existing knowledge level on a topic with targeted assessment questions.")
async def knowledge_check() -> dict[str, str]:
    return {"error": "not_implemented"}


if __name__ == "__main__":
    check_mode_gate(Path.cwd())
    asyncio.run(mcp.run_stdio_async())
