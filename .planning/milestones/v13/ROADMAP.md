# v13 — state-teach MCP Server (skeleton)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 115–123 (9 phases)

---

## Phases

#### Phase 115 — MCP server scaffold (`state_teach.mcp`)
**Goal:** FastMCP stdio; mode-gate check.
**Depends on:** 099
**Requirements:** MCP-T-01
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [x] 115-01-PLAN.md — FastMCP stdio entry point with mode-gate check + comprehensive tests

#### Phase 116 — 15 skeleton tools with ≤80-token descriptions
**Goal:** Names per MCP-T-03; "not implemented" skeletons.
**Depends on:** 115
**Requirements:** MCP-T-02, MCP-T-03
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [x] 116-01-PLAN.md — Register 15 skeleton @mcp.tool() functions with ≤80-token descriptions + tiktoken budget verification tests

#### Phase 117 — Opencode `question` tool binding wrapper
**Goal:** `ask_structured(questions: list[Question])` → typed answers via `client.question.ask(...)`.
**Depends on:** 115
**Requirements:** MCP-T-04
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [x] 117-01-PLAN.md — Question binding module with Pydantic Question/Option/Answer models and skeleton `ask_structured()` function

#### Phase 118 — Observation schema (structured-only, reject freeform)
**Goal:** Pydantic `Observation` with discriminator `kind`; `extra = "forbid"`.
**Depends on:** 002
**Requirements:** MCP-T-05
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [x] 118-01-PLAN.md — Pydantic Observation model with 5 structured kinds, kind discriminator, extra="forbid"

#### Phase 119 — Drill prompt token cap (≤3000 tokens)
**Goal:** Helper to count + cap; Hypothesis property test.
**Depends on:** 115
**Requirements:** MCP-T-06
**Parallelizable:** yes

#### Phase 120 — Shared library wiring (auth, events via `state_core`)
**Goal:** As 111.
**Depends on:** 115
**Requirements:** (infrastructure)
**Parallelizable:** yes

#### Phase 121 — Mode-gate integration (refuse start when mode=build)
**Goal:** As 112.
**Depends on:** 097
**Requirements:** MCP-T-01, MODE-03
**Parallelizable:** yes

#### Phase 122 — Tool-budget CI assertion (shared helper w/ v12)
**Goal:** `state dev tool-budget --server state-teach` green.
**Depends on:** 116
**Requirements:** (shares MCP-B-06 infra)
**Parallelizable:** yes

#### Phase 123 — Integration test against real opencode MCP client
**Goal:** As 114.
**Depends on:** 115..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

