"""Entry point for ``python -m state_build.mcp``.

Launches the state-build MCP server with stdio transport.
"""

from __future__ import annotations

from state_build.mcp import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
