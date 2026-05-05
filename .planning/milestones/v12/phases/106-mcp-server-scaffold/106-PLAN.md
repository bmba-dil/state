---
phase: 106
phase_name: mcp-server-scaffold
wave: 1
depends_on: ["099"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["MCP-B-01"]
autonomous: true
---

## Plan 01: FastMCP Server Scaffold

**Goal:** Replace the 3-line stub `src/state_build/mcp.py` with a working FastMCP server that registers via stdio transport with at least 1 pydantic-validated skeleton tool.

### Tasks

#### 01.1 Scaffold FastMCP server with stdio transport
**Acceptance:** `python -c "from state_build.mcp import mcp; assert mcp.name == 'state-build'"` passes
**Estimated effort:** Medium
**Dependencies:** None
**Details:**
- Replace contents of `src/state_build/mcp.py`
- Import `FastMCP` from `mcp.server.fastmcp`
- Instantiate with `name="state-build"`, instructions describing build-mode tools
- Wire stdio transport via `if __name__ == "__main__": mcp.run(transport="stdio")`
- Follow existing package conventions: `from __future__ import annotations`, double quotes, 120-char lines

<action>
Create `src/state_build/mcp.py` with a FastMCP instance:

1. Import `FastMCP` from `mcp.server.fastmcp`
2. Create `mcp = FastMCP("state-build", instructions="...")`
3. Add `if __name__ == "__main__": mcp.run(transport="stdio")` entry point
4. The instructions should describe that this server exposes build-mode tools for the state workflow engine

Consumed by: opencode MCP client (registers via stdio), state_build kernel (imports for tool registration in later phases).
</action>

<read_first>
- src/state_build/mcp.py
- src/state_build/__init__.py
- pyproject.toml (for mcp dependency version)
</read_first>

<acceptance_criteria>
- `grep "FastMCP" src/state_build/mcp.py` returns at least 1 match
- `grep "state-build" src/state_build/mcp.py` returns at least 1 match
- `grep "run(transport=\"stdio\")" src/state_build/mcp.py` returns 1 match
- `python3 -c "from state_build.mcp import mcp; assert mcp.name == 'state-build'"` exits 0
</acceptance_criteria>

#### 01.2 Register 1 pydantic-validated skeleton tool as PoC
**Acceptance:** `python3 -c "from state_build.mcp import mcp; tools = mcp._tool_manager._tools; assert len(tools) >= 1"` passes
**Estimated effort:** Small
**Dependencies:** 01.1
**Details:**
- Add one skeleton tool using `@mcp.tool()` decorator
- Tool name: `dag_status` (per MCP-B-03 list)
- Description: ≤80 tokens (per MCP-B-02 budget)
- Return type: Pydantic model with `status` and `nodes` fields
- Tool body: return placeholder data showing "not implemented" status
- This proves the pydantic schema generation pipeline works end-to-end

<action>
Define a pydantic model `DAGStatus` and register a `dag_status` tool:

```python
from pydantic import BaseModel

class DAGStatus(BaseModel):
    status: str = "not_implemented"
    nodes: int = 0

@mcp.tool()
def dag_status() -> DAGStatus:
    """Query the current state of the build-mode DAG scheduler."""
    return DAGStatus()
```

Consumed by: opencode MCP client (enumerates tools, validates schemas), phase 107 (adds real implementations to skeleton tools).
</action>

<read_first>
- src/state_build/mcp.py
- requirements file for MCP-B-02 (80-token description rule), MCP-B-03 (tool name list)
</read_first>

<acceptance_criteria>
- `grep "dag_status" src/state_build/mcp.py` returns at least 1 match
- `grep "@mcp.tool()" src/state_build/mcp.py` returns at least 1 match
- `python3 -c "from state_build.mcp import mcp; tools = mcp._tool_manager._tools; assert len(tools) >= 1"` exits 0
- Tool description is ≤80 tokens (count with approximate tokenizer)
</acceptance_criteria>

#### 01.3 Add `__main__.py` for `python -m` entry point
**Acceptance:** `python3 -m state_build.mcp` starts the server (starts and waits for stdio)
**Estimated effort:** Small
**Dependencies:** 01.1
**Details:**
- Create `src/state_build/__main__.py`
- Import `mcp` from `state_build.mcp` and call `mcp.run(transport="stdio")`
- This enables `python -m state_build.mcp` as the canonical launch command

<action>
Create `src/state_build/__main__.py`:

```python
from __future__ import annotations

from state_build.mcp import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Consumed by: opencode MCP config (command entry), state_cli (may wrap for daemon-managed lifecycle), CI (integration tests).
</action>

<read_first>
- src/state_build/__init__.py
- src/state_teach/ (for parallel pattern — no __main__.py exists there either yet)
</read_first>

<acceptance_criteria>
- `test -f src/state_build/__main__.py` exits 0
- `grep "mcp.run" src/state_build/__main__.py` returns 1 match
- `grep "from __future__ import annotations" src/state_build/__main__.py` returns 1 match
</acceptance_criteria>

### Integration Notes
- This scaffold is the foundation for Phase 107 (15 skeleton tools) and Phase 112 (mode-gate integration)
- The `dag_status` tool is placeholder — real DAG query will be wired in Phase 107
- The `__main__.py` pattern is consistent with standard Python packaging conventions
- Mode gating is deferred to Phase 112; this scaffold does not read `.state/mode.json`
- No state_core imports needed yet — keep the scaffold lean

### Deviation Notes
- None. Following the FastMCP scaffold pattern as specified in the phase goal and CONTEXT.md.
