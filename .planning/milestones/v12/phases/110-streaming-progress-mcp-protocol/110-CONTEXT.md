# Phase 110: streaming-progress-mcp-protocol — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (discuss skipped)

<domain>
## Phase Boundary

Long-running tools emit `progress` notifications per MCP spec.

Add `Context` parameter to stateful tools so they can report progress via `ctx.report_progress()`. Skeleton tools accept the context but don't do real progress reporting yet — the contract is established for Phase 111 wiring.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
- Import `Context` from `mcp.server.fastmcp`
- 6 stateful tools accept `ctx: Context` parameter
- FastMCP passes context automatically when tool signature includes it
- Skeleton tools don't call `ctx.report_progress()` yet (no real work to report)
</decisions>

<code_context>
## Existing Code

### Current tool pattern
```python
@mcp.tool()
def plan_step(task_id: str | None = None) -> SkeletonResponse:
    return SkeletonResponse(tool="plan_step", task_id=task_id)
```
</code_context>

<specifics>
## Specific Ideas

```python
@mcp.tool()
def plan_step(
    task_id: str | None = None,
    ctx: Context = None,
) -> SkeletonResponse:
    """..."""
    # ctx.report_progress(progress=0.5, total=1.0)  # Phase 111 wiring
    return SkeletonResponse(tool="plan_step", task_id=task_id)
```

FastMCP's `Context` provides:
- `ctx.report_progress(progress: float, total: float | None = None)`
- `ctx.read_resource(uri: str)`
- `ctx.elicit(message: str, schema: dict)`
</specifics>

<deferred>
## Deferred Ideas

- Actual progress reporting in Phase 111 (shared library wiring)
</deferred>
