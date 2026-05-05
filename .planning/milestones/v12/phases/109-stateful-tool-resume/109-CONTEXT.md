# Phase 109: stateful-tool-resume — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (tool signature phase, discuss skipped)

<domain>
## Phase Boundary

`discuss_step`/`plan_step`/`execute_step`/`verify_step`/`code_review`/`debug_session` use `task` tool; task_id stored in event; resume after compaction.

Add `task_id` parameter to the 6 stateful tools. The skeleton tools accept the task_id for stateful resume; actual event storage and resume logic is deferred to Phase 111 (shared library wiring).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

- 6 stateful tools: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session`
- Add `task_id: str | None = None` parameter to each
- Update `SkeletonResponse` to include optional `task_id` field
- Non-stateful tools (dag_status, arc_show, etc.) remain unchanged
</decisions>

<code_context>
## Existing Code

### Current tool signatures (Phase 107)
All 15 tools use `def tool_name() -> SkeletonResponse:` with no parameters.

### SkeletonResponse
```python
class SkeletonResponse(BaseModel):
    tool: str
    status: str = "not_implemented"
```
</code_context>

<specifics>
## Specific Ideas

Stateful tools will echo back the task_id in the response:
```python
@mcp.tool()
def plan_step(task_id: str | None = None) -> SkeletonResponse:
    return SkeletonResponse(tool="plan_step", task_id=task_id)
```
</specifics>

<deferred>
## Deferred Ideas

- Phase 111: Store task_id in event store and wire real resume logic
</deferred>
