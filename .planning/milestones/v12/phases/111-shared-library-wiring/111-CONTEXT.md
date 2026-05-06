# Phase 111: shared-library-wiring — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (discuss skipped)

<domain>
## Phase Boundary

Tool impls call `state_core` helpers; no duplicate auth/provider logic.

Wire the skeleton MCP tools to import and use the shared `state_core` library so that all auth, event-store, and scheduling logic flows through a single import surface. This eliminates duplicate code paths and ensures the mode-silo import-graph lint stays clean.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion — infrastructure phase.

Key decisions:
- Import from `state_core.auth` (`load_credentials`), `state_core.events` (`SqliteEventStore`), `state_core.scheduler` (`DAGScheduler`)
- Use underscore-prefixed aliases (`_load_credentials`, etc.) to signal they're wired but not yet fully utilized by skeleton tools
- `dag_status` instantiates a real `DAGScheduler` and reports its `concurrency_cap` as proof the import works
- Other tools reference the imports via comments but keep skeleton bodies — real wiring deferred to v14 (Build Kernel)

### Why not all tools wired now
Real implementations require the Step FSM (v14), DAG data population (v14), and auth-flow wiring (v15). The skeleton phase establishes the import contract; real calls land in Tier 3a.
</decisions>

<code_context>
## Existing Code Insights

### state_core public API (verified at import time)
- `state_core.auth.load_credentials` — loads auth vault from `.state/auth.json`
- `state_core.events.SqliteEventStore` — WAL-mode SQLite event store
- `state_core.scheduler.DAGScheduler` — reactive DAG scheduler with `concurrency_cap` property

### Current mcp.py (post-Phase 110)
- 15 skeleton tools, all returning `SkeletonResponse`
- 6 stateful tools accept `task_id` and `ctx: Context`
- No state_core imports yet — tools are fully self-contained
</code_context>

<specifics>
## Specific Ideas

- Import block with `# noqa: F401` on each import to suppress unused-import warnings until real wiring
- `dag_status` is the demo tool — shows `scheduler_ready (cap=4)` to prove the import chain works
- Pattern for future: each tool imports what it needs; the top-level block provides discoverability
</specifics>

<deferred>
## Deferred Ideas

- Phase v14 (Build Kernel): Wire `plan_step`/`execute_step`/`verify_step` to StepMachine FSM
- Phase v15 (Build Core Commands): Wire real event persistence via `SqliteEventStore`
- Auth-wired tools (e.g., provider-dependent operations) deferred to v15
</deferred>
