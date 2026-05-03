# v12 — state-build MCP Server (skeleton)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 106–114 (9 phases)

---

## Phases

#### Phase 106 — MCP server scaffold (FastMCP from `mcp` SDK)
**Goal:** `state_build.mcp` entry with stdio transport; pydantic tool schemas.
**Depends on:** 099
**Requirements:** MCP-B-01
**Parallelizable:** yes

#### Phase 107 — 15 skeleton tools with ≤80-token descriptions
**Goal:** Names per MCP-B-03; skeleton returns "not implemented" with structured error; descriptions tuned for token budget.
**Depends on:** 106
**Requirements:** MCP-B-02, MCP-B-03
**Parallelizable:** yes

#### Phase 108 — `state dev tool-budget` command + CI assertion
**Goal:** Sum tool-description tokens (tiktoken replacement: use provider counts), refuse > budget.
**Depends on:** 107
**Requirements:** MCP-B-06
**Parallelizable:** yes

#### Phase 109 — Stateful tool resume (opencode `task` + `task_id`)
**Goal:** `discuss_step`/`plan_step`/`execute_step`/`verify_step`/`code_review`/`debug_session` use `task` tool; task_id stored in event; resume after compaction.
**Depends on:** 106
**Requirements:** MCP-B-04
**Parallelizable:** yes

#### Phase 110 — Streaming progress via MCP protocol
**Goal:** Long-running tools emit `progress` notifications per MCP spec.
**Depends on:** 106
**Requirements:** MCP-B-05
**Parallelizable:** yes

#### Phase 111 — Shared library wiring (auth, events, provider via `state_core`)
**Goal:** Tool impls call `state_core` helpers; no duplicate auth/provider logic.
**Depends on:** 106
**Requirements:** (infrastructure)
**Parallelizable:** yes

#### Phase 112 — Mode-gate integration (refuse start when mode=teach)
**Goal:** Server checks `.state/mode.json` at boot; exits with clear error if mode mismatch.
**Depends on:** 097
**Requirements:** MCP-B-01, MODE-03
**Parallelizable:** yes

#### Phase 113 — P0-12 tool-name collision regression test
**Goal:** Spawn both servers → assert opencode refuses or mode-gate blocks; name prefix contract.
**Depends on:** 112
**Requirements:** (P0-12 defence)
**Parallelizable:** yes

#### Phase 114 — Integration test against real opencode MCP client
**Goal:** E2E: spawn opencode binary, register state-build, enumerate tools, invoke each skeleton tool.
**Depends on:** 106..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

