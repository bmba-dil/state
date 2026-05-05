# Phase 106: mcp-server-scaffold — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (scaffold phase, discuss skipped)

<domain>
## Phase Boundary

`state_build.mcp` entry with stdio transport; pydantic tool schemas.

Create the MCP server scaffold using `mcp.server.fastmcp.FastMCP` from the `mcp>=1.27.0` SDK. The server runs via stdio transport and exposes build-mode tools to opencode. This phase establishes the physical `state_build/mcp.py` entry point with a FastMCP instance, stdio transport wiring, and at least one pydantic-validated tool schema as proof-of-concept.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — pure infrastructure phase. Use the existing package structure (`src/state_build/`), the `mcp>=1.27.0` SDK, and codebase conventions to guide decisions.

Key technical decisions:
- Use `mcp.server.fastmcp.FastMCP` (not low-level `mcp.server.Server`)
- Server name: `"state-build"`
- Transport: `stdio` via `FastMCP.run(transport="stdio")`
- Tool schemas: pydantic models via type hints on `@mcp.tool()` decorated functions
- Follow existing `state_build/` package conventions (`from __future__ import annotations`, double quotes, 120-char lines)
</decisions>

<code_context>
## Existing Code Insights

### Current state of `src/state_build/`
- `__init__.py`: Package docstring only
- `kernel.py`: `StepMachine` class stub
- `commands/__init__.py`: Docstring only
- `verifiers/__init__.py`: Docstring only
- `mcp.py`: Only 3 lines — `from __future__ import annotations` and docstring

### MCP SDK (v1.27.0)
- `FastMCP` class in `mcp.server.fastmcp`
- `.tool()` decorator for tool registration
- `.run(transport="stdio")` for stdio transport
- Tool functions use type hints for pydantic schema generation

### Shared library
- `state_core.schema` — event payloads, mode config, subtree validation
- `state_core.events` — `SqliteEventStore` and `EventStore` protocol
- `state_core.providers` — LLM provider routing
- `state_core.config` — project configuration from `.state/`

### Patterns
- All packages use `from __future__ import annotations`
- Double-quote style, 120-char line length (ruff)
- Tests in `tests/` with `pythonpath = ["src"]`
- Mode isolation: `state_build.*` MUST NOT import `state_teach.*`
</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the phase goal — infrastructure scaffold phase.
</specifics>

<deferred>
## Deferred Ideas

- Phase 107: 15 skeleton tools (deferred from Phase 106 which only needs 1 proof-of-concept tool)
- Phase 108: Tool budget command
- Phase 112: Mode-gate integration at server boot
</deferred>
