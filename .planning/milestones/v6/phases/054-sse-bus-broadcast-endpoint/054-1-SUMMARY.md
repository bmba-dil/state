---
phase: 054-sse-bus-broadcast-endpoint
plan: 1
subsystem: infra
tags: [sse, server-sent-events, event-store, broadcast, heartbeat, asyncio, unix-socket]

# Dependency graph
requires:
  - phase: 050
    provides: HTTP server on unix domain socket (DaemonServer)
  - phase: 004
    provides: SqliteEventStore with append() and event schema
  - phase: 053
    provides: ModeMiddleware wrapping the JSON-RPC router
provides:
  - SSE broadcast bus fanning event-store domain events to connected clients
  - GET /events/subscribe endpoint with mode and ULID filtering
  - Post-commit callback hook on SqliteEventStore
  - SseClientManager for multi-client fan-out with mode-aware filtering
  - Heartbeat keepalives every 30s to prevent proxy timeouts
affects: [061-workers, 081-tui, 009-cli-tail]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pluggable SSE handler on DaemonServer: sse_handler parameter receives (reader, writer, path, headers)"
    - "Post-commit callback pattern: SqliteEventStore.add_post_commit_callback() invoked after db.commit()"
    - "Fire-and-forget broadcast: SseBus.on_event() dispatches via asyncio.create_task"
    - "Poll-loop with writer.is_closing()/reader.at_eof() for SSE disconnect detection"

key-files:
  created:
    - src/state_daemon/sse.py — SseClient, SseClientManager, SseBus, SseEndpointHandler, SSE format helpers
    - tests/test_daemon_sse.py — 22 tests covering client lifecycle, endpoint integration, store wiring
  modified:
    - src/state_daemon/server.py — added SseHandler type and sse_handler parameter; GET /events/subscribe routing
    - src/state_daemon/orchestrator.py — wired SseClientManager, SseBus, SseEndpointHandler into startup()
    - src/state_core/events.py — added add_post_commit_callback() hook; callbacks invoked after commit

key-decisions:
  - "SSE handler receives raw reader/writer (not request/response) to own the stream lifecycle"
  - "Heartbeat interval decoupled from queue poll interval: heartbeat task runs every 30s; queue polls every 1s for writer-closed detection"
  - "Post-commit callbacks are synchronous (not awaitable) — async work dispatched via asyncio.create_task internally"
  - "Mode filtering applied in broadcast() before queue.put_nowait() — no filtered events fill queues"
  - "DaemonServer.sse_handler is optional — if None, /events/subscribe returns 501 Not Implemented"

patterns-established:
  - "SSE subscription pattern: GET /events/subscribe?mode=build|teach|kernel&from=<ulid>"
  - "Event store callback chain: append() → commit → callbacks → mirror — callbacks run before mirror"
  - "Disconnect detection: writer.is_closing() or reader.at_eof() checked each poll iteration"

requirements-completed: [DAE-06]

# Metrics
duration: 29 min
completed: 2026-05-04
---

# Phase 054 Plan 1: SSE Bus Broadcast Endpoint Summary

**SSE fan-out bus with multi-client broadcast, mode/ULID filtering, heartbeat keepalives, and event-store post-commit integration**

## Performance

- **Duration:** 29 min
- **Started:** 2026-05-05T00:45:04Z
- **Completed:** 2026-05-05T01:14:20Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments
- SseClientManager tracks connected SSE subscribers with mode-aware fan-out broadcasting
- GET /events/subscribe endpoint streams events in real-time with query-param filtering (mode, from ULID)
- SseBus bridges SqliteEventStore post-commit to SSE broadcast via fire-and-forget tasks
- Full orchestrator wiring: daemon startup creates SSE bus, registers callback, attaches endpoint to server

## Task Commits

Each task was committed atomically:

1. **Task 054.1: SSE Stream Format + Client Manager** - `a1a023a` (feat)
2. **Task 054.2: SSE HTTP Endpoint** - `8367893` (feat)
3. **Task 054.3: Event Store Integration** - `119106b` (feat)
4. **Task 054.4: Orchestrator Wiring** - `a63c1df` (feat)

## Files Created/Modified
- `src/state_daemon/sse.py` — SseClient (hashable dataclass), SseClientManager (add/remove/broadcast), SseBus (event store bridge), SseEndpointHandler (stream lifecycle), SSE format helpers
- `src/state_daemon/server.py` — Pluggable SseHandler type, sse_handler parameter on DaemonServer, GET /events/subscribe routing
- `src/state_daemon/orchestrator.py` — Step 3.5: creates SseClientManager, SseBus, SseEndpointHandler; wires post-commit callback; passes sse_handler to DaemonServer
- `src/state_core/events.py` — add_post_commit_callback() method; append() invokes callbacks after commit before mirror
- `tests/test_daemon_sse.py` — 22 tests across 4 test classes (SseClientManager, SseFormat, SseEndpoint, SseBus, SseOrchestratorWiring)

## Decisions Made
- SSE handler owns the writer lifecycle entirely — server delegates and returns after handler completes
- Queue poll interval is 1s (not tied to heartbeat interval) so disconnect detection is fast in tests
- Post-commit callbacks are synchronous callables; SseBus.on_event() dispatches async broadcast via create_task internally
- Mode filtering happens in broadcast() before queue insertion — filtered events never reach client queues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unhashable SseClient for set-based client manager**
- **Found during:** Task 054.1
- **Issue:** Dataclass default `eq=True` sets `__hash__` to `None`, making SseClient unhashable and preventing `set.add(client)`
- **Fix:** Added `eq=False` to `@dataclasses.dataclass(eq=False)` for identity-based hashing
- **Files modified:** `src/state_daemon/sse.py`
- **Committed in:** `a1a023a`

**2. [Rule 1 - Bug] Fixed missing disconnect detection in SSE handler poll loop**
- **Found during:** Task 054.2
- **Issue:** Handler used 30s queue timeout; after client disconnect, handler took 30s to detect and exit, causing tests to time out
- **Fix:** Reduced queue poll timeout to 1s and added `reader.at_eof()` check alongside `writer.is_closing()`
- **Files modified:** `src/state_daemon/sse.py`
- **Committed in:** `8367893`

**3. [Rule 3 - Blocking] Installed pytest-asyncio in project venv**
- **Found during:** Task 054.1
- **Issue:** Async test functions failed with "async def functions are not natively supported" — pytest-asyncio was missing from venv
- **Fix:** Identified project venv at `.venv/` and ran tests with `.venv/bin/python3 -m pytest` which has pytest-asyncio installed
- **Verification:** All async tests pass against venv Python

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness and testability. No scope creep.

## Issues Encountered
- Venv discovery: homebrew `python3` on PATH lacked litellm and pytest-asyncio; resolved by using project `.venv/bin/python3` which has all deps installed.
- `init_db` function does not exist in `database.py`; resolved by using `migrate()` from `migrations.py` for test database setup, consistent with existing `test_events.py` pattern.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SSE bus is operational and ready for consumption by:
  - Phase 061 (Workers) — subscribe to event stream for real-time updates
  - Phase 009 (CLI tail) — stream events to terminal
  - Phase 081-084 (TUI) — live status updates
- All 22 SSE tests + 112 existing tests pass with no regressions.

---

*Phase: 054-sse-bus-broadcast-endpoint*
*Completed: 2026-05-04*

## Self-Check: PASSED

- [x] `src/state_daemon/sse.py` exists on disk
- [x] `tests/test_daemon_sse.py` exists on disk
- [x] Commit `a1a023a` (Task 054.1) present in git log
- [x] Commit `8367893` (Task 054.2) present in git log
- [x] Commit `119106b` (Task 054.3) present in git log
- [x] Commit `a63c1df` (Task 054.4) present in git log
- [x] 22 SSE tests pass + 112 existing tests pass (0 regressions)
- [x] v6 STATE.md updated (Phase 054 → Complete, 5/10 phases done)
- [x] v6 ROADMAP.md updated (Phase 054 → Complete)
- [x] v6 REQUIREMENTS.md updated (DAE-06 → checked)
- [x] No stubs, no TODO/FIXME/placeholder markers in new code
