---
phase: 109
phase_name: stateful-tool-resume
wave: 1
depends_on: ["106"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["MCP-B-04"]
autonomous: true
---

## Plan 01: Add task_id to Stateful Tool Signatures

**Goal:** 6 stateful tools accept `task_id` parameter for session-resume support.

### Tasks

#### 01.1 Update SkeletonResponse with optional task_id
**Acceptance:** `SkeletonResponse` has optional `task_id` field
**Estimated effort:** Small
**Dependencies:** Phase 107

<action>
Update `SkeletonResponse`:

```python
class SkeletonResponse(BaseModel):
    tool: str
    status: str = "not_implemented"
    task_id: str | None = None
```

Consumed by: Phase 111 (shared library wiring uses task_id for event storage).
</action>

<read_first>
- src/state_build/mcp.py
</read_first>

<acceptance_criteria>
- `grep "task_id" src/state_build/mcp.py | grep SkeletonResponse` returns 1 match
- `.venv/bin/python3 -c "from state_build.mcp import SkeletonResponse; r = SkeletonResponse(tool='x', task_id='abc'); assert r.task_id == 'abc'"` exits 0
</acceptance_criteria>

#### 01.2 Add task_id parameter to 6 stateful tools
**Acceptance:** `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session` all accept `task_id` parameter
**Estimated effort:** Small
**Dependencies:** 01.1

<action>
Update the 6 stateful tool function signatures to accept `task_id: str | None = None` and pass it to `SkeletonResponse`:

```python
@mcp.tool()
def plan_step(task_id: str | None = None) -> SkeletonResponse:
    return SkeletonResponse(tool="plan_step", task_id=task_id)
```

Apply same pattern to: `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session`.

Non-stateful tools (dag_status, arc_show, etc.) remain unchanged.

Consumed by: Phase 111 (event storage), opencode task tool (uses task_id for resume).
</action>

<read_first>
- src/state_build/mcp.py
</read_first>

<acceptance_criteria>
- `grep "task_id" src/state_build/mcp.py | grep "def "` returns 6 matches
- `.venv/bin/python3 -c "from state_build.mcp import plan_step; r = plan_step(task_id='abc'); assert r.task_id == 'abc'"` exits 0
- `.venv/bin/python3 -c "from state_build.mcp import dag_status; r = dag_status(); assert r.task_id is None"` exits 0
- Tool count remains 15
- `ruff check` clean
</acceptance_criteria>

### Integration Notes
- Non-stateful tools (9 of 15) remain unchanged — dag_status, arc_show, slice_ship, etc.
- The `task_id` is echoed back in the response; event storage deferred to Phase 111
