# Phase 061: Daemon ↔ Worker Bridge (HTTP+SSE client) — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Worker connects to daemon Unix socket; subscribes to SSE for session-scoped events.

Requirements: WRK-10 (attach/teardown), WRK-12 (forward hook events to daemon)
Depends on: 060 (worker main), 054 (SSE bus)
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion. Key references:
- Daemon SSE: `state_daemon/sse.py` — SseClient, SseClientManager, SseBus, SseEndpointHandler, GET /events/subscribe
- Daemon HTTP server: `state_daemon/server.py` — Unix socket HTTP/1.1
- Daemon socket discovery: `state_daemon/socket.py` — read_socket_path()
- Worker session: `state_worker/session.py` — SessionIdentity
- Worker main: `state_worker/main.py` — attach_to_daemon()
</decisions>

<code_context>
## Existing Code Insights

- `state_worker/bridge.py` exists as a stub file
- Worker already has `attach_to_daemon()` (health check + socket discovery)
- Daemon SSE sends events formatted as `id: ULID\ndata: JSON\n\n`
- SSE subscribe endpoint: `GET /events/subscribe?mode=build&from=01XYZ`
- Heartbeat every 30s from daemon
</code_context>

<specifics>
## Specific Ideas

- Bridge connects to SSE after successful health check
- Bridge parses SSE event stream (id: / data: / event: lines)
- Bridge filters events by session mode
- Bridge provides event callbacks for downstream consumers (hook forwarding, hot state)
- Phase 063 will use POST to forward hook events to daemon
- Connection retry with backoff on SSE disconnect
</specifics>

<deferred>
## Deferred Ideas

- Hook event forwarding (POST /hook/<name>) — Phase 063
- Version handshake header — Phase 064
</deferred>
