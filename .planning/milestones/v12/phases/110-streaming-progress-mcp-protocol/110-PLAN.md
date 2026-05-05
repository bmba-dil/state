---
phase: 110
phase_name: streaming-progress-mcp-protocol
wave: 1
depends_on: ["106"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["MCP-B-05"]
autonomous: true
---

## Plan 01: Add MCP Progress Context to Stateful Tools

**Goal:** Long-running tools accept `Context` for `progress` notification support per MCP spec.

### Tasks

#### 01.1 Import Context and add to stateful tool signatures
**Acceptance:** 6 stateful tools accept `ctx: Context` parameter
**Estimated effort:** Small
**Dependencies:** Phase 109 (task_id already added)

<action>
1. Import `Context` from `mcp.server.fastmcp`
2. Add `ctx: Context = None` parameter to the 6 stateful tools: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session`
3. Add comment showing where `ctx.report_progress()` would be called in real implementation

The `ctx` parameter is passed automatically by FastMCP when the tool function signature includes it. When `None`, FastMCP provides the actual context at runtime.

Consumed by: Phase 111 (shared library wiring calls ctx.report_progress during real work), opencode MCP client (receives progress notifications).
</action>

<read_first>
- src/state_build/mcp.py
</read_first>

<acceptance_criteria>
- `grep "from mcp.server.fastmcp import.*Context" src/state_build/mcp.py` returns 1 match
- `grep "ctx.*Context" src/state_build/mcp.py | grep "def "` returns 6 matches
- `ruff check` clean
- Tool count remains 15
</acceptance_criteria>

### Integration Notes
- Non-stateful tools (dag_status, arc_show, etc.) do not need progress — they're instant queries
- Phase 111 will add actual `ctx.report_progress()` calls when real work is implemented
