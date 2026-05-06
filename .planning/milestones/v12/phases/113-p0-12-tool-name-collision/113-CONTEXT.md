# Phase 113: P0-12 Tool-Name Collision Regression Test — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (discuss skipped)

<domain>
## Phase Boundary

Spawn both servers → assert opencode refuses or mode-gate blocks; name prefix contract.

P0-12 is a cardinal pitfall: if `state-build` and `state-teach` share any tool name, opencode cannot distinguish them and would route calls to the wrong server. This phase creates a regression test suite that prevents that collision from ever shipping.

The test suite also validates the naming contract (snake_case, no hyphens), confirms the 15-tool roster matches MCP-B-03, and exercises the mode gate (Layer 3) end-to-end.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

- Test file: `tests/test_mcp_collision_regression.py`
- Test classes: `TestToolNameCollisions` (naming), `TestModeGate` (mode enforcement), `TestSkeletonResponse` (schema)
- Uses `frozenset` for build/teach tool name sets to prevent accidental mutation
- Uses `tmp_path` fixture for mode-gate tests to isolate `.state/mode.json` mutations
- No subprocess needed — all tests use direct Python imports

### Why hardcode the teach tool names
`state-teach` MCP server (v13) doesn't exist yet, so we cannot import its tools. The teach tool names are hardcoded from MCP-T-02/T-03 in the requirements. When v13 ships, this test should be updated to import dynamically.
</decisions>

<code_context>
## Existing Code Insights

### Tool name sets from MCP-B-03
Build: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `dag_status`, `arc_show`, `slice_ship`, `snapshot_revert`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`

### Planned teach tool names (MCP-T-02)
Teach: `concept_next`, `drill_prepare`, `drill_verify`, `concept_teach`, `observation_record`, `mental_model_show`, `subject_pick`, `subject_author`, `style_edit`, `learner_state`, `review_session`, `mentor_scaffold`, `coding_partner`, `learning_verify`

### Mode-gate test pattern
Uses `tmp_path` fixture + `os.chdir()` to simulate different `.state/mode.json` files. Must restore `os.chdir()` in `finally` block to not break subsequent tests.
</code_context>

<specifics>
## Specific Ideas

Three test classes:
1. **TestToolNameCollisions** (3 tests): build tool count, no build/teach overlap (P0-12), naming conventions
2. **TestModeGate** (3 tests): allows build, rejects teach, allows both
3. **TestSkeletonResponse** (3 tests): defaults, task_id propagation, JSON serialization
</specifics>

<deferred>
## Deferred Ideas

- Dynamic teach-tool import when v13 ships (replace hardcoded `TEACH_TOOL_NAMES` set)
- MCP wire-protocol collision test (spawn both servers, verify opencode routing)
</deferred>
