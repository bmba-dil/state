# Phase 107: 15-skeleton-tools-80-token — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (tool scaffold phase, discuss skipped)

<domain>
## Phase Boundary

Names per MCP-B-03; skeleton returns "not implemented" with structured error; descriptions tuned for token budget.

Add the remaining 14 skeleton tools to the `state_build/mcp.py` server, completing the full 15-tool roster. Each tool must have a ≤80-token description and return a pydantic model indicating "not implemented" status. The existing `dag_status` tool from Phase 106 must be updated to match the standardized skeleton pattern.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — pure infrastructure phase.

Key technical decisions:
- Standardize all skeleton tools on a common `SkeletonResponse` pydantic model (or per-tool models if semantics differ)
- Tool names exactly match MCP-B-03 list
- Each description ≤80 tokens (use simple heuristic: ≤~80 words)
- Each tool body returns `SkeletonResponse(status="not_implemented")` or equivalent
- Follow existing `@mcp.tool()` decorator pattern from Phase 106
</decisions>

<code_context>
## Existing Code Insights

### Current mcp.py (from Phase 106)
- FastMCP server instantiated with `name="state-build"`
- One tool: `dag_status` returning `DAGStatus` model
- Stdio transport wired via `mcp.run(transport="stdio")`
- Uses pydantic `BaseModel` for tool schemas

### Required tool names (MCP-B-03)
Already implemented: `dag_status`
Remaining 14: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `snapshot_revert`, `arc_show`, `slice_ship`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`

### Token budget (MCP-B-02)
Total 15 tools × ≤80 tokens each = ≤1200 tokens for all descriptions.
</code_context>

<specifics>
## Specific Ideas

All 15 tools (including dag_status refactor) use a shared `SkeletonResponse` model:
```python
class SkeletonResponse(BaseModel):
    status: str = "not_implemented"
    tool: str  # tool name for diagnostics
```

Refactor `dag_status` to also use `SkeletonResponse` for consistency.
</specifics>

<deferred>
## Deferred Ideas

- Phase 108: Tool budget command
- Phase 109: Stateful tool resume
- Phase 111: Shared library wiring (real implementations)
</deferred>
