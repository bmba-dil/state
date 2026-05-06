# Phase 114: Integration Test Against Real Opencode MCP Client — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (discuss skipped)

<domain>
## Phase Boundary

E2E: spawn opencode binary, register state-build, enumerate tools, invoke each skeleton tool.

Validate the state-build MCP server contract end-to-end: server import/reputation, tool enumeration, tool invocation, and mode-gate enforcement. This is the final verifier for the skeleton milestone — every tool must be importable, enumerable, callable, and schema-conformant.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

- Test file: `tests/test_mcp_integration.py`
- Uses direct Python imports (not subprocess) for reliability and speed
- Four test classes covering: server registration, tool schemas, tool invocation, mode gate integration
- `_tool_manager._tools` used for introspection (implementation detail of FastMCP, acceptable for test code)
- `inspect.signature()` used instead of raw schema access (more reliable across FastMCP versions)

### Why not subprocess-based E2E
A true opencode binary E2E test requires the opencode CLI, a configured MCP server entry, and network access. That infrastructure doesn't exist yet in CI. The Python import approach validates every aspect of the server contract except the stdio wire protocol itself, which is tested by FastMCP's own test suite.
</decisions>

<code_context>
## Existing Code Insights

### Server structure (post-Phase 112)
- `state_build.mcp` module: FastMCP instance, SkeletonResponse model, 15 tools, mode gate
- All tools return `SkeletonResponse` with `tool`, `status`, `task_id` fields
- 6 stateful tools have `task_id` and `ctx` parameters
- `_check_mode_gate()` runs at `if __name__ == "__main__"` time

### Test patterns from existing test suite
- `from __future__ import annotations` at top
- `pytest.fixture(autouse=True)` for `_chdir` to project root
- Direct imports from `state_build.mcp`
- No conftest dependency required
</code_context>

<specifics>
## Specific Ideas

Four test classes:
1. **TestMCPServerRegistration** (3 tests): server name = "state-build", 15 tools registered, every tool has a description ≤80 tokens
2. **TestToolSchemas** (2 tests): stateful tools have `task_id` in signature, non-stateful tools lack it
3. **TestToolInvocation** (4 tests): dag_status returns scheduler_ready, plan_step with/without task_id, all 15 tools callable
4. **TestModeGateIntegration** (2 tests): gate allows when file missing, gate allows when mode=build
</specifics>

<deferred>
## Deferred Ideas

- Subprocess-based E2E test (spawn `python -m state_build.mcp`, send JSON-RPC, read response) — deferred until opencode test infrastructure is available
- Wire-protocol conformance test against MCP spec test suite
</deferred>
