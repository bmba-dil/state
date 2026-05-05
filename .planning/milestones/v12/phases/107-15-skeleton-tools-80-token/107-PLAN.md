---
phase: 107
phase_name: 15-skeleton-tools-80-token
wave: 1
depends_on: ["106"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["MCP-B-02", "MCP-B-03"]
autonomous: true
---

## Plan 01: Complete 15-Tool Roster with Token Budget

**Goal:** Add 14 remaining skeleton tools to `state_build/mcp.py`, refactor `dag_status` to standardized pattern, verify ≤80-token descriptions and ≤15 total tools.

### Tasks

#### 01.1 Standardize skeleton response pattern and refactor dag_status
**Acceptance:** `dag_status` returns a `SkeletonResponse` model (not `DAGStatus`)
**Estimated effort:** Small
**Dependencies:** Phase 106
**Details:**
- Define a shared `SkeletonResponse` pydantic model with `tool: str` and `status: str = "not_implemented"` fields
- Refactor `dag_status` to return `SkeletonResponse`
- Remove `DAGStatus` model

<action>
Add `SkeletonResponse` model and update `dag_status`:

1. Define `class SkeletonResponse(BaseModel)` with `tool: str` and `status: str = "not_implemented"`
2. Change `dag_status` return type to `SkeletonResponse` 
3. Update body to `return SkeletonResponse(tool="dag_status")`
4. Remove `DAGStatus` class

Consumed by: Phase 108 (tool-budget command parses return types), Phase 109 (stateful tool resume uses tool field).
</action>

<read_first>
- src/state_build/mcp.py
</read_first>

<acceptance_criteria>
- `grep "class SkeletonResponse" src/state_build/mcp.py` returns 1 match
- `grep "class DAGStatus" src/state_build/mcp.py` returns 0 matches
- `.venv/bin/python3 -c "from state_build.mcp import dag_status; r = dag_status(); assert r.tool == 'dag_status'; assert r.status == 'not_implemented'"` exits 0
</acceptance_criteria>

#### 01.2 Add 14 remaining skeleton tools with ≤80-token descriptions
**Acceptance:** 15 total tools registered, all descriptions ≤80 tokens
**Estimated effort:** Medium
**Dependencies:** 01.1
**Details:**
- Add tools: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `snapshot_revert`, `arc_show`, `slice_ship`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`
- Each tool: `@mcp.tool()` decorated function, returns `SkeletonResponse`, ≤80-token description
- Descriptions should be terse but meaningful per MCP-B-02 budget
- Group tools logically (planning tools, verification tools, utility tools)

<action>
Add 14 skeleton tools to `state_build/mcp.py`. Every tool follows this pattern:

```python
@mcp.tool()
def plan_step() -> SkeletonResponse:
    """Brief description under 80 tokens."""
    return SkeletonResponse(tool="plan_step")
```

Tool descriptions (terse, ≤80 tokens each):
- `plan_step`: Create step plan from discuss context. Returns structured task list.
- `execute_step`: Execute planned step tasks. Reports progress per task.
- `verify_step`: Goal-backward verification of step outputs. Returns pass/gap status.
- `discuss_step`: Surface implementation decisions for a step. Returns grey-area table.
- `research_step`: Research technical approach for a step. Returns findings doc.
- `snapshot_revert`: Revert working tree to named snapshot. Returns reverted ref.
- `arc_show`: Display current arc status and phase progression.
- `slice_ship`: Ship completed slice with PR and verification. Returns ship status.
- `code_review`: Review staged changes for bugs and quality. Returns REVIEW.md.
- `debug_session`: Start or resume a persistent debug session. Returns session ID.
- `forensics`: Post-mortem failed workflow analysis. Returns forensic report.
- `intel_refresh`: Refresh codebase intelligence files. Returns updated intel paths.
- `pause_work`: Create context handoff for pausing. Returns handoff path.
- `resume_work`: Resume from saved context handoff. Returns restored state.

Consumed by: Phase 108 (tool-budget CI assertion), Phase 109 (stateful tool resume wiring), Phase 111 (shared library wiring for real implementations).
</action>

<read_first>
- src/state_build/mcp.py
- .planning/milestones/v12/REQUIREMENTS.md (MCP-B-02, MCP-B-03)
</read_first>

<acceptance_criteria>
- `grep -c "@mcp.tool()" src/state_build/mcp.py` returns 15
- `grep -c "def " src/state_build/mcp.py` returns >= 15 (tool functions)
- `.venv/bin/python3 -c "from state_build.mcp import mcp; assert len(mcp._tool_manager._tools) == 15"` exits 0
- All 15 tool names match MCP-B-03 list exactly
- No description exceeds ~80 words (manual spot-check)
</acceptance_criteria>

### Integration Notes
- Phase 108 (tool-budget command) asserts total descriptions fit ≤1200 tokens
- Phase 109 (stateful tool resume) wires `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session` to opencode `task` tool
- Phase 111 (shared library wiring) replaces skeleton bodies with real implementations
- The `SkeletonResponse.model_json_schema()` output is consumed by opencode MCP client for tool enumeration

### Deviation Notes
- None. Following the standardized skeleton pattern established in Phase 106.
