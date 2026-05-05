---
wave: 1
depends_on: ["004"]
files_modified:
  - src/state_daemon/server.py
  - src/state_daemon/router.py
  - tests/test_daemon_server.py
autonomous: true
---

# Plan 050-1: HTTP Server with Unix Socket + JSON-RPC 2.0 Router

**Goal:** Implement an async HTTP server bound to a unix domain socket with JSON-RPC 2.0 request framing and a pluggable request router — the transport layer of the state daemon.

**Requirements:** DAE-05

### Tasks

#### 050.1 Server Core — asyncio.start_unix_server

**Acceptance:** Server starts and accepts connections on a unix socket; `curl --unix-socket` can reach it.
**Estimated effort:** Medium
**Dependencies:** none

**Details:**
- Implement `DaemonServer` class in `src/state_daemon/server.py` that binds to a unix domain socket using `asyncio.start_unix_server`.
- Accepts `socket_path: str` and `router` (callable) on construction.
- The protocol handler reads the HTTP request line + headers, parses Content-Length, reads the body, passes it to the router, and writes the HTTP response back.
- Handle connection errors gracefully — log and close, don't crash.
- Use `structlog` for logging (consistent with the rest of the codebase).
- Graceful shutdown: `server.close()` waits for in-flight requests to complete.
- Test: unit test with `pytest-asyncio` that starts server on a temp socket, sends a raw HTTP request over a unix socket, and asserts the response.

**Files:**
- `src/state_daemon/server.py` — rewrite from stub to full implementation
- `src/state_daemon/__init__.py` — export `DaemonServer`

#### 050.2 JSON-RPC 2.0 Router

**Acceptance:** Valid JSON-RPC 2.0 requests are routed; invalid ones return proper error codes (-32600, -32700, -32601).
**Estimated effort:** Medium
**Dependencies:** 050.1

**Details:**
- Implement `JsonRpcRouter` in `src/state_daemon/router.py`.
- Accepts `POST` requests with `Content-Type: application/json` and JSON body `{"jsonrpc": "2.0", "method": "...", "params": {...}, "id": ...}`.
- Method dispatch: register handlers via `router.add_method(name, handler)` where handler is `async def handler(params) -> Any`.
- Returns JSON response `{"jsonrpc": "2.0", "result": ..., "id": ...}` or error `{"jsonrpc": "2.0", "error": {"code": ..., "message": ...}, "id": ...}`.
- Error codes: -32700 Parse error, -32600 Invalid Request, -32601 Method not found, -32603 Internal error.
- Notification support: if `id` is null/omitted, no response sent (JSON-RPC notification).
- Handle malformed JSON with -32700; handle unknown method with -32601.
- Test: parameterized unit tests for each error code, valid request routing, notification suppression.

**Files:**
- `src/state_daemon/router.py` — new file

#### 050.3 Server-Router Integration + Request Routing

**Acceptance:** Server routes HTTP POST requests through the JSON-RPC router; GET health check returns 200.
**Estimated effort:** Small
**Dependencies:** 050.1, 050.2

**Details:**
- Wire `DaemonServer` with `JsonRpcRouter` — HTTP server calls router for POST, returns router's response.
- Add `GET /health` endpoint returning `{"status": "ok"}` (not JSON-RPC — plain HTTP health check).
- Content-Type validation: reject non-JSON POST with 415.
- Test: integration test that starts the server, sends a POST with a registered JSON-RPC method, and asserts correct response.

**Files:**
- `src/state_daemon/server.py` — integrate router

#### 050.4 Startup Wiring in Orchestrator

**Acceptance:** `startup()` function creates and starts the HTTP server; daemon can be launched from CLI.
**Estimated effort:** Small
**Dependencies:** 050.3, 051.2 (socket path)

**Details:**
- Update `src/state_daemon/orchestrator.py` `startup()` to create a `DaemonServer` after Step 3 (reconciler).
- Pass socket path from Phase 052 (initially use a temporary default path for this phase).
- Server runs as an asyncio background task; `startup()` awaits it.
- Signal handlers: catch SIGTERM/SIGINT to shut down gracefully.
- Test: integration test that calls `startup()` (with limited scope) and verifies server is running.

**Files:**
- `src/state_daemon/orchestrator.py` — add server startup

### Integration Notes

- This phase creates the transport layer only — no mode middleware (Phase 053), no SSE (Phase 054), no auth endpoints (Phase 059).
- The router is designed to be extended by downstream phases via `add_method()`.
- Socket path will be finalized in Phase 052; this phase uses a temporary default.

### must_haves

1. Server binds to a unix domain socket and accepts HTTP connections.
2. JSON-RPC 2.0 requests with valid framing are parsed and routed correctly.
3. Invalid requests produce proper JSON-RPC error responses.
4. Server starts as part of the daemon `startup()` sequence.
5. Unit tests cover: server accept/response, JSON-RPC parsing/errors, router dispatch.
