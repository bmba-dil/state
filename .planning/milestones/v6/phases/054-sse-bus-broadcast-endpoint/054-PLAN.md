---
wave: 1
depends_on: ["050", "009"]
files_modified:
  - src/state_daemon/sse.py
  - src/state_daemon/server.py
  - tests/test_daemon_sse.py
autonomous: true
---

# Plan 054-1: SSE Bus Broadcast Endpoint

**Goal:** Implement Server-Sent Events broadcast endpoint that fans out event-store domain events to all connected clients with heartbeat keepalives.

**Requirements:** DAE-06

### Tasks

#### 054.1 SSE Stream Format + Client Manager

**Acceptance:** `SseClientManager` tracks connected clients; `broadcast(event)` sends to all; clients can subscribe/unsubscribe cleanly.
**Estimated effort:** Medium
**Dependencies:** none

**Details:**
- `SseClient` dataclass with `queue: asyncio.Queue`, `mode_filter: str | None`, `from_ulid: str | None`.
- `SseClientManager` class:
  - `add_client(mode_filter, from_ulid) -> SseClient`: registers new client, returns client object.
  - `remove_client(client)`: removes client from fan-out set.
  - `broadcast(event_json: str, event_type: str, event_id: str, mode: str)`: iterates all clients, checks mode filter (if client has mode_filter, only send matching events), puts event on each client's queue.
- Handle client disconnect: catch `BrokenPipeError`/`ConnectionResetError` and remove client.
- Test: unit tests for client add/remove, broadcast filtering by mode, queue behavior.

**Files:**
- `src/state_daemon/sse.py` — new file

#### 054.2 SSE HTTP Endpoint

**Acceptance:** `GET /events/subscribe?mode=<filter>&from=<ulid>` returns SSE stream; clients receive events in real-time as they're broadcast.
**Estimated effort:** Medium
**Dependencies:** 054.1, 050.3

**Details:**
- Register `GET /events/subscribe` as a raw HTTP handler (not JSON-RPC — SSE is its own protocol).
- Query params: `?mode=build|teach|kernel` (optional filter), `?from=<ulid>` (optional start position).
- On connect: register client with `SseClientManager`, set response headers (`Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`).
- Stream loop: `async for event in client.queue`: format as SSE (`id: <ulid>\nevent: <type>\ndata: <json>\n\n`), flush after each event.
- Heartbeat: every 30s send `: heartbeat\n\n` comment line.
- On client disconnect (or stream error): clean up client from manager.
- Test: integration test with `httpx` streaming client that connects, receives broadcast events, and verifies format.

**Files:**
- `src/state_daemon/sse.py` — extend with endpoint handler
- `src/state_daemon/server.py` — add SSE endpoint routing (raw HTTP, bypasses JSON-RPC router)

#### 054.3 Event Store Integration — Post-Commit Broadcast

**Acceptance:** Every `state.*` event appended to the event store is automatically broadcast to SSE subscribers.
**Estimated effort:** Small
**Dependencies:** 054.2, 004

**Details:**
- `SseBus` class: holds reference to `SseClientManager` and provides `on_event(event_row: dict)` callback.
- Wire into `SqliteEventStore.append()` or use a post-commit hook pattern — after successful commit, call `sse_bus.on_event(row)` with the event data.
- The callback serializes the event row as JSON and calls `client_manager.broadcast()`.
- Ensure broadcast is non-blocking (fire-and-forget via `asyncio.create_task`).
- Test: integration test that writes an event via the event store and verifies it arrives at an SSE client.

**Files:**
- `src/state_daemon/sse.py` — extend with SseBus
- `src/state_core/events.py` — add post-commit callback hook (minimal change)

#### 054.4 Orchestrator Wiring

**Acceptance:** SSE bus starts with the daemon; clients can connect before any events are written.
**Estimated effort:** Small
**Dependencies:** 054.3, 053.3

**Details:**
- In `orchestrator.startup()`, create `SseBus` and `SseClientManager` after server starts.
- Pass `SseBus` to the event store so post-commit callbacks fire.
- Register SSE endpoint with the server/router.
- Test: integration test that starts the full daemon, subscribes to SSE, writes an event, receives it.

**Files:**
- `src/state_daemon/orchestrator.py` — wire SSE bus

### Integration Notes

- SSE is raw HTTP (not JSON-RPC) — requires extending the server to handle non-JSON-RPC routes.
- Mode filtering on SSE clients respects the `X-State-Mode` middleware but SSE connections are long-lived GET requests.
- The heartbeat prevents proxy/load-balancer timeouts.
- This SSE bus will be consumed by workers (Phase 061), TUI (Phase 081-084), and CLI tail (Phase 009).

### must_haves

1. Multiple clients can subscribe to the SSE stream concurrently.
2. Events are broadcast to all connected subscribers in real-time.
3. Mode filtering: clients can subscribe to only build/teach/kernel events.
4. Heartbeat keeps connections alive (every 30s).
5. Client disconnect is handled cleanly without affecting other subscribers.
