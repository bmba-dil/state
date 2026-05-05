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

if __name__ == "__main__":
    check_mode_gate(Path.cwd())
    asyncio.run(mcp.run_stdio_async())
