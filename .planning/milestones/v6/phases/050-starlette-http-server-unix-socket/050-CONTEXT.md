# Phase 050: Starlette HTTP server + unix socket binding - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`asyncio.start_unix_server`, JSON-RPC 2.0 framing, request router. This is the daemon's transport layer — a minimal async HTTP server bound to a unix domain socket that accepts JSON-RPC 2.0 requests and routes them to handlers.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Use Starlette or bare `asyncio` — both valid; prefer the lighter option consistent with the project's existing HTTP stack (httpx on client side).
- JSON-RPC 2.0 framing: `{"jsonrpc": "2.0", "method": "...", "params": {...}, "id": ...}` with error object `{"code": int, "message": str, "data": ...}`.
- Request router should be pluggable so individual endpoints can be registered by later phases.
- Module location: `src/state_core/state_daemon/` or `src/state_daemon/` — follow existing package conventions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing core package (event store, auth, CLI)
- `state_core` uses httpx for client-side HTTP — daemon is the server side
- v1 event store (004) is a dependency — daemon writes events through the single-writer store

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

Requirements: DAE-05
Depends on: 004 (event store writer)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
