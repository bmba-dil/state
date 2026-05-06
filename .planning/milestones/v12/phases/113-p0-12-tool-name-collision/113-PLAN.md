---
phase: 113
phase_name: p0-12-tool-name-collision
wave: 1
depends_on: ["112"]
files_modified:
  - tests/test_mcp_collision_regression.py
requirements_addressed: ["P0-12 defence"]
autonomous: true
---

## Plan 01: P0-12 Collision Regression Test Suite

**Goal:** Regression test proving build and teach tool names never collide, and mode-gate blocks cross-mode server starts.

### Tasks

#### 01.1 Create tool-name collision test class
**Acceptance:** 3 tests: build tool count = 15, no build/teach overlap, snake_case naming
**Estimated effort:** Medium
**Dependencies:** Phase 107 (15 tools defined), Phase 112 (mode gate exists)

<action>
Create `tests/test_mcp_collision_regression.py` with `TestToolNameCollisions` class:

**test_build_tool_count**: Import `state_build.mcp`, assert `mcp._tool_manager._tools` has exactly 15 tools matching MCP-B-03 roster.

**test_no_build_teach_overlap**: Compute set intersection of `BUILD_TOOL_NAMES` and `TEACH_TOOL_NAMES`. Assert empty — this is the P0-12 gate. Any overlap means opencode cannot route calls correctly.

**test_tool_naming_convention**: Every tool name must be lowercase, snake_case, no hyphens, no spaces. This ensures the naming contract is uniform.

Tool name sets are `frozenset` to prevent accidental mutation during test runs.

Consumed by: CI pipeline (must pass before merge), Phase v13 (updated when state-teach ships), SECURITY.md (P0 pitfall verification).
</action>

<read_first>
- src/state_build/mcp.py (tool names)
- .planning/milestones/v12/REQUIREMENTS.md (MCP-B-03, MCP-T-02)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_collision_regression.py::TestToolNameCollisions -v` exits 0 with 3 passed
- `BUILD_TOOL_NAMES & TEACH_TOOL_NAMES == set()` (P0-12 invariant)
- All tool names pass snake_case validation
</acceptance_criteria>

#### 01.2 Create mode-gate test class
**Acceptance:** 3 tests: allows build, rejects teach (exit 78), allows both
**Estimated effort:** Medium
**Dependencies:** Phase 112 (_check_mode_gate function exists)

<action>
Add `TestModeGate` class to `tests/test_mcp_collision_regression.py`:

**test_mode_gate_allows_build**: Call `_check_mode_gate()` from project root (where `.state/mode.json` has `mode=build`). Must not raise.

**test_mode_gate_rejects_teach**: Create temp `.state/mode.json` with `{"mode": "teach"}`, chdir to temp dir, assert `_check_mode_gate()` raises `SystemExit` with code 78. Must restore cwd in finally.

**test_mode_gate_allows_both**: Create temp `.state/mode.json` with `{"mode": "both"}`, chdir to temp dir, assert `_check_mode_gate()` does not raise.

Uses `tmp_path` fixture for isolated `.state/mode.json` files. Each test must `os.chdir()` back to original cwd.

Consumed by: CI pipeline, SECURITY.md (mode enforcement verification).
</action>

<read_first>
- src/state_build/mcp.py (_check_mode_gate source)
- .state/mode.json (verify current mode is build)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_collision_regression.py::TestModeGate -v` exits 0 with 3 passed
- teach mode → SystemExit(code=78)
- build mode → no exception
- both mode → no exception
</acceptance_criteria>

#### 01.3 Create SkeletonResponse schema test class
**Acceptance:** 3 tests: defaults, task_id propagation, JSON serialization
**Estimated effort:** Small
**Dependencies:** Phase 109 (task_id on SkeletonResponse)

<action>
Add `TestSkeletonResponse` class:

**test_defaults**: `SkeletonResponse(tool="x")` → `status="not_implemented"`, `task_id=None`.

**test_with_task_id**: `SkeletonResponse(tool="x", task_id="abc")` → `task_id="abc"`.

**test_json_serialization**: `model_dump()` and `model_dump_json()` produce correct JSON with all fields.

Consumed by: downstream consumers that parse SkeletonResponse from MCP JSON-RPC responses.
</action>

<read_first>
- src/state_build/mcp.py (SkeletonResponse class definition)
</read_first>

<acceptance_criteria>
- `pytest tests/test_mcp_collision_regression.py::TestSkeletonResponse -v` exits 0 with 3 passed
- Default values correct
- task_id round-trips
- JSON is valid and complete
</acceptance_criteria>

### Integration Notes
- All 9 tests must pass in < 1 second (no subprocess, no network)
- File must be importable from project root without pytest conftest dependency
- Phase 114 (integration test) builds on this with broader server coverage
