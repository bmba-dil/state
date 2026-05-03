# v12 — state-build MCP Server (skeleton) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### MCP: state-build server (A12)

- [ ] **MCP-B-01**: Server registered as `state-build` in opencode MCP config
- [ ] **MCP-B-02**: ≤15 tools with ≤80-token descriptions each
- [ ] **MCP-B-03**: Tools include: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `snapshot_revert`, `dag_status`, `arc_show`, `slice_ship`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`
- [ ] **MCP-B-04**: Stateful tools (discuss/plan/execute/verify/review/debug) use opencode `task` tool + `task_id` resume; survive context compaction
- [ ] **MCP-B-05**: Streaming progress via MCP protocol for long-running tools
- [ ] **MCP-B-06**: `state dev tool-budget` command asserts total tool descriptions fit in the ≤15 × 80-token budget
