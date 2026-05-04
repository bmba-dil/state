---
phase: 050-starlette-http-server-unix-socket
plan: 050-1
subsystem: infra
tags: [asyncio, unix-socket, json-rpc, http, structlog]

# Dependency graph
requires:
  - phase: 004
    provides: sqlite-event-store
  - phase: 020
    provides: redactor-install, observability
  - phase: 021
    provides: opencode-auth-importer
  - phase: 023
    provides: shared-httpx-client
provides:
  - HTTP server bound to unix domain socket (DaemonServer)
  - JSON-RPC 2.0 request router with method dispatch (JsonRpcRouter)
  - GET /health endpoint
  - POST routing with Content-Type validation (415 for non-JSON)
  - Signal-handled graceful shutdown (SIGTERM/SIGINT)
  - Server startup wired into orchestrator.startup() sequence
affects: [mode-middleware, sse-bus, auth-endpoints, cli-daemon-start]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pluggable router callable pattern: DaemonServer accepts any (method, path, headers, body) -> bytes callable
    - Async handler registration: JsonRpcRouter.add_method(name, async_handler)
    - JSON-RPC 2.0 error code taxonomy: -32700 Parse, -32600 Invalid, -32601 Method not found, -32603 Internal
    - Module-level server reference for signal handler access from synchronous context
    - Environment-variable-overridable defaults: STATE_DAEMON_SOCKET

key-files:
  created:
    - src/state_daemon/server.py - DaemonServer class (184 lines)
    - src/state_daemon/router.py - JsonRpcRouter class (148 lines)
    - tests/test_daemon_server.py - 19 tests covering server, router, integration (494 lines)
  modified:
    - src/state_daemon/orchestrator.py - Added Step 4 (server startup) + signal handlers (162 lines)

key-decisions:
  - "Raw HTTP/1.1 parsing over asyncio streams instead of a framework dependency — keeps the daemon lean with zero new deps"
  - "Router callable is generic (method, path, headers, body) -> bytes — JsonRpcRouter is one implementation; future phases can add other routers"
  - "Server handles GET /health and Content-Type validation internally — router focuses purely on JSON-RPC semantics"
  - "Socket path defaults to .state/daemon.sock with STATE_DAEMON_SOCKET env override — Phase 052 will finalize"
  - "Signal handlers use asyncio.create_task() for async shutdown — cannot await directly from sync signal context"

patterns-established:
  - "Router callable pattern: DaemonServer(router) where router is async (method, path, headers, body) -> bytes"
  - "Method registration: router.add_method(name, async_handler) — handlers receive parsed params, return JSON-serializable result"
  - "HTTP response building: helper _http_response(status, headers, body) for consistent framing"

requirements-completed: ["DAE-05"]

# Metrics
duration: 7min
completed: 2026-05-04
---

# Phase 050 Plan 050-1: HTTP Server with Unix Socket + JSON-RPC 2.0 Router Summary

**Async HTTP server on a unix domain socket with JSON-RPC 2.0 dispatch, health endpoint, and graceful signal-handled shutdown — the transport layer of the state daemon.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-04T18:43:42-0500
- **Completed:** 2026-05-04T18:50:19-0500
- **Tasks:** 4
- **Files modified:** 4
- **Tests:** 19 (all passing)

## Accomplishments

- DaemonServer binds to unix domain socket via `asyncio.start_unix_server`, parses raw HTTP/1.1, and routes requests through a pluggable callable
- JsonRpcRouter implements full JSON-RPC 2.0 spec: method dispatch, 4 error codes (-32700/-32600/-32601/-32603), notification suppression
- GET /health returns `{"status": "ok"}`; POST with non-JSON Content-Type returns 415
- Server startup wired into orchestrator's `startup()` as Step 4, with SIGTERM/SIGINT graceful shutdown
- 19 unit/integration tests covering server lifecycle, routing, JSON-RPC parsing, error codes, notifications, and full server+router integration

## Task Commits

Each task was committed atomically:

1. **Task 050.1: Server Core — asyncio.start_unix_server** - `ab0eed7` (feat)
2. **Task 050.2: JSON-RPC 2.0 Router** - `f3b08dc` (feat)
3. **Task 050.3: Server-Router Integration** - `470465b` (feat)
4. **Task 050.4: Startup Wiring in Orchestrator** - `e56c159` (feat)

## Files Created/Modified

- `src/state_daemon/server.py` — DaemonServer: HTTP/1.1 over unix socket, health check, Content-Type validation
- `src/state_daemon/router.py` — JsonRpcRouter: JSON-RPC 2.0 parsing, method dispatch, error codes, notifications
- `src/state_daemon/orchestrator.py` — Added Step 4: server startup with signal handlers
- `tests/test_daemon_server.py` — 19 tests: server lifecycle (6), router unit (11), integration (2)

## Decisions Made

- Used raw `asyncio.start_unix_server` + manual HTTP/1.1 parsing instead of a framework — keeps the daemon dependency-free for the transport layer
- Router callable signature is `(method, path, headers, body) -> bytes` — generic enough for non-JSON-RPC routers in future phases
- Server handles GET /health and Content-Type validation internally so the router can focus on JSON-RPC semantics
- JsonRpcRouter handlers are `async` — matches the plan spec and allows I/O in method implementations
- Socket path defaults to `.state/daemon.sock` with `STATE_DAEMON_SOCKET` env override — temporary default until Phase 052 finalizes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Environment discrepancy: system pytest (Python 3.14) vs venv pytest (Python 3.12). Tests require the venv pytest at `.venv/bin/pytest` which has all project dependencies installed. System pytest was missing `pytest-asyncio` and `litellm`.

## Next Phase Readiness

- Socket path ready for Phase 052 (unix-socket-path) to finalize the canonical location
- JsonRpcRouter ready for Phase 053 (mode middleware) and Phase 059 (auth endpoints) to register via `add_method()`
- Server infrastructure ready for Phase 054 (SSE bus) to add streaming endpoints

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: local-socket-surface | src/state_daemon/server.py | Unix domain socket with chmod 0600 — local-only, but auth enforcement arrives in Phase 059 |
| threat_flag: json-parsing | src/state_daemon/router.py | JSON-RPC input parsing — validates structure but no auth on method dispatch yet |

---
## Self-Check: PASSED

- ✅ `src/state_daemon/server.py` exists (184 lines)
- ✅ `src/state_daemon/router.py` exists (148 lines)
- ✅ `tests/test_daemon_server.py` exists (494 lines, 19 tests passing)
- ✅ Commits `ab0eed7`, `f3b08dc`, `470465b`, `e56c159` all present
- ✅ No file deletions in plan commits
- ✅ No stubs, TODOs, or placeholders in implementation files
- ✅ All plan must_haves verified

---
*Phase: 050-starlette-http-server-unix-socket*
*Completed: 2026-05-04*
