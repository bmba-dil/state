# Phase 054: SSE bus broadcast endpoint - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`/events/subscribe` SSE stream fan-out of event-store updates; multi-client support; heartbeats. The daemon broadcasts domain events to all connected SSE clients. This is the push mechanism that keeps workers, TUI, and CLI consumers in sync.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- SSE endpoint: `GET /events/subscribe` with optional `?mode=build|teach|kernel&from=<ulid>` query params.
- Multi-client fan-out: maintain a set of connected clients; on each `state.*` event write, broadcast to all subscribed clients.
- Heartbeat: send `: heartbeat\n\n` every 30s to prevent connection timeouts.
- Client disconnect: remove from fan-out set; no lingering subscriptions.
- Event format: `id: <ulid>\nevent: state.<type>\ndata: <json>\n\n` (standard SSE).
- Integration: hook into event store's post-commit callback (Phase 004/005).

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing event store with post-commit hooks
- Phase 005: SyncEvent mirror emitter (post-commit pattern to follow)
- Phase 009: CLI tail command (consumer of SSE)
- Depends on: Phase 050 (HTTP server), Phase 009 (event tail — consumer)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-06
Depends on: 050 (HTTP server), 009 (event tail CLI)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
