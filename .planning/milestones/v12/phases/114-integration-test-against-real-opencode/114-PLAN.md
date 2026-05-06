---
phase: 114
phase_name: integration-test-against-real-opencode
wave: 1
depends_on: ["106", "107", "108", "109", "110", "111", "112"]
files_modified:
  - tests/test_mcp_integration.py
requirements_addressed: ["verifier"]
autonomous: true
---

## Plan 01: MCP Server Integration Test Suite

**Goal:** E2E integration test proving the state-build MCP server contract: registration, schemas, invocation, and mode-gate.

### Tasks

#### 01.1 Create server registration test class
**Acceptance:** 3 tests: server name, tool count, tool descriptions ≤80 tokens
**Estimated effort:** Medium
**Dependencies:** Phase 107 (15 tools defined)

<action>
Create `tests/test_mcp_integration.py` with `TestMCPServerRegistration` class:

**test_server_name**: `mcp.name == "state-build"`

**test_tool_count**: `len(mcp._tool_manager._tools) == 15`

**test_all_tools_have_descriptions**: Every tool has a non-empty `description` attribute, and every description is ≤80 tokens (word-count heuristic). This validates MCP-B-02 compliance.

Uses `pytest.fixture(autouse=True)` to `os.chdir()` to project root before each test.

Consumed by: CI pipeline (post-commit), SECURITY.md (tool contract verification).
</action>

<read_first>
- src/state_build/mcp.py
- .planning/milestones/v12/REQUIREMENTS.md (MCP-B-02 token budget)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_integration.py::TestMCPServerRegistration -v` exits 0 with 3 passed
- Server name assertion holds
- Tool count = 15
- All descriptions present and ≤80 tokens
</acceptance_criteria>

#### 01.2 Create tool schema validation test class
**Acceptance:** 2 tests: stateful tools have task_id, non-stateful tools lack task_id
**Estimated effort:** Small
**Dependencies:** Phase 109 (task_id parameter), Phase 110 (ctx parameter)

<action>
Add `TestToolSchemas` class:

**test_stateful_tool_signatures_accept_task_id**: Use `inspect.signature()` on each of the 6 stateful tool functions (`plan_step`, `execute_step`, `verify_step`, `discuss_step`, `code_review`, `debug_session`). Assert `"task_id"` is in the parameter list.

**test_non_stateful_tools_lack_task_id**: Same check for the 9 non-stateful tools. Assert `"task_id"` is NOT in the parameter list.

Uses `inspect.signature()` instead of raw `inputSchema` introspection because FastMCP builds schemas lazily.

Consumed by: Phase v14 (real StepMachine implementations must maintain same signatures).
</action>

<read_first>
- src/state_build/mcp.py (tool function signatures)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_integration.py::TestToolSchemas -v` exits 0 with 2 passed
- All 6 stateful tools have task_id in signature
- All 9 non-stateful tools lack task_id in signature
</acceptance_criteria>

#### 01.3 Create tool invocation test class
**Acceptance:** 4 tests: dag_status struct, plan_step with/without task_id, all 15 tools callable
**Estimated effort:** Medium
**Dependencies:** Phase 111 (dag_status wired to DAGScheduler)

<action>
Add `TestToolInvocation` class:

**test_dag_status_returns_struct**: Assert response has `tool="dag_status"`, `status` contains `"scheduler_ready"`, `task_id=None`.

**test_plan_step_with_task_id**: Call `plan_step(task_id="session-001")`, assert `task_id == "session-001"`.

**test_plan_step_without_task_id**: Call `plan_step()` with no args, assert `task_id is None`.

**test_all_15_tools_invocable**: Iterate over all 15 tool names in `mcp._tool_manager._tools`. For each, `getattr()` from the module and call with no args. Assert response `tool` field matches name and response is valid (status contains "not_implemented" or "scheduler_ready").

Uses `import state_build.mcp as mcp_mod` to avoid shadowing the `mcp` FastMCP instance.

Consumed by: CI pipeline (smoke test), opencode MCP client (tool enumeration contract).
</action>

<read_first>
- src/state_build/mcp.py (all 15 tool functions)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_integration.py::TestToolInvocation -v` exits 0 with 4 passed
- dag_status returns scheduler_ready
- plan_step propagates task_id
- All 15 tools callable without errors
</acceptance_criteria>

#### 01.4 Create mode-gate integration test class
**Acceptance:** 2 tests: gate allows when file missing, gate allows when mode=build
**Estimated effort:** Small
**Dependencies:** Phase 112 (_check_mode_gate function)

<action>
Add `TestModeGateIntegration` class:

**test_mode_gate_no_file_allows**: Use `pytest.MonkeyPatch` to make `Path.exists()` return `False`. Assert `_check_mode_gate()` does not raise.

**test_mode_gate_build_allows**: In project root (where mode=build), assert `_check_mode_gate()` does not raise.

Complementary to Phase 113's mode-gate tests — these validate the integration-level behavior from the server module's perspective.

Consumed by: CI pipeline (integration gate).
</action>

<read_first>
- src/state_build/mcp.py (_check_mode_gate)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_integration.py::TestModeGateIntegration -v` exits 0 with 2 passed
- No exception when mode.json missing
- No exception when mode=build
</acceptance_criteria>

### Integration Notes
- All 11 tests must pass in < 1 second
- File must be importable from project root without conftest dependency
- Subprocess-based E2E (spawning `python -m state_build.mcp` over stdio) is deferred — opencode binary test infrastructure needed
