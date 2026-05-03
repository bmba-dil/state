# CONTEXT: Phase 006 — Startup Reconciliation (Unsent-Event Replay to Opencode)

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

On daemon start, find rows with `synced_to_opencode=0` and emit them to opencode's `POST /sync/replay` endpoint. Also handle opencode-unreachable with exponential backoff, covering events that arrive while opencode is down. This is the "catch-up" layer of the dual-write architecture: Phase 005 handles real-time emission at append time; Phase 006 ensures eventual consistency for any events that missed their window.

Phase 006 covers both **startup reconciliation** (daemon boot) and **periodic retry** (events that Phase 005's fire-and-forget task couldn't deliver). The periodic retry runs as a lightweight background sweep.

## Requirements

- **EVT-04**: Startup reconciliation replays unsent events to opencode's SyncEvent when opencode reconnects

## Locked Decisions

### Reconciliation Trigger

- **Dual trigger:**
  1. **Startup:** On daemon start, immediately attempt to reconcile all `synced_to_opencode=0` events. This is the primary reconciliation opportunity — most events that Phase 005 couldn't deliver should be caught here.
  2. **Periodic:** A background sweep runs every 60 seconds (configurable via class init param) to catch any events that accumulated since startup. This handles the case where opencode comes back mid-session.
- **No SSE/subscription-based trigger:** Phase 006 does not subscribe to opencode's SSE stream for reconnect detection. The periodic sweep is simpler and equally effective. If a subscription-based trigger is needed later, it can be added as an optimization.
- **Idle suppression:** The periodic sweep skips if no opencode-unreachable events exist (check `SELECT COUNT(*) FROM events WHERE synced_to_opencode = 0` first). No unnecessary HTTP calls.

### Backoff & Retry Strategy

- **Exponential backoff per sweep:** The periodic sweep retries on failure with exponential backoff:
  - Initial delay: 1 second
  - Multiplier: 2x
  - Max delay: 60 seconds
  - Max consecutive failures before warning: 10 (emits structlog warning at 10, then continues)
- **No cap on total retries:** Never give up on events. Opencode might return after hours of downtime. The event data is safe in SQLite.
- **Per-event independence:** Each event's `synced_to_opencode` is set to 1 individually on success. Partial success (some events delivered, some failed) is handled cleanly — only successfully delivered events are marked.
- **Backoff state:** The backoff timer resets on any successful delivery (even 1 event out of a batch).

### Phase 005 Integration

- **Reuse `SyncEventMirror`:** Phase 006 uses `SyncEventMirror.emit()` for individual event delivery. The same class handles both real-time (Phase 005) and reconciliation (Phase 006) emission.
- **Same HTTP client:** `SyncEventMirror` already owns a shared `httpx.AsyncClient`. Phase 006 uses the same instance.
- **Same config discovery:** Phase 006 reuses the opencode config discovery function (`find_opencode_config`) from Phase 005's `sync_mirror.py`. URL resolution is identical.
- **Dependency injection:** The `StartupReconciler` class receives `SyncEventMirror` via constructor injection, keeping it testable without HTTP mocking:
  ```python
  class StartupReconciler:
      def __init__(
          self,
          db: SqliteEventStore,
          mirror: SyncEventMirror,
          sweep_interval: float = 60.0,
      ) -> None: ...
  ```
- **New module:** `src/state_core/reconciler.py` — `StartupReconciler` class. This keeps reconciliation logic separate from the mirror emission logic in `sync_mirror.py`.

### Batch vs Single Emission

- **Batch query, single emission:** Query all unsent events in one SQL query (`SELECT * FROM events WHERE synced_to_opencode = 0 ORDER BY seq ASC`), then emit them **one at a time** via `SyncEventMirror.emit()`.
- **Rationale against batching:** The opencode `POST /sync/replay` API accepts an array of events. However, emitting one at a time is simpler, matches Phase 005's pattern, and avoids partial-batch failures. If batch performance becomes an issue, it can be added as an optimization.
- **Ordering:** Events are emitted in `seq` order (oldest first). This preserves chronological order for the receiver.
- **Batch sizes:** No artificial limit on events-per-sweep. A single sweep may emit 10,000 events sequentially. This is acceptable because:
  - Each emission is a fire-and-forget call via the shared httpx client
  - The sweep is non-blocking (runs as an asyncio task)
  - Startup is a one-time cost; the user expects some latency on first boot after a long offline period

### Opencode Reachability Detection

- **Passive detection:** Phase 006 does NOT actively poll opencode for health. Reachability is determined by the success/failure of the actual `POST /sync/replay` call.
- **How it works:**
  1. On startup, try to reconcile all unsent events
  2. If ALL succeed, stop (no periodic sweep needed)
  3. If ANY fail, start the periodic sweep
  4. On each sweep tick, attempt to deliver remaining unsent events
  5. When ALL succeed, stop the periodic sweep
- **Sweep lifecycle:** The background task starts when unsent events exist and opencode is unreachable. It stops when all events are delivered. It does NOT run indefinitely when the queue is empty.
- **Edge case:** If opencode is reachable at startup but goes down later, Phase 005's fire-and-forget tasks will fail and leave events unsent. The periodic sweep (already running) will continue retrying. If the sweep was stopped (all events delivered), it restarts when new unsent events appear — but this restart is triggered by the next periodic check. See "Scope Boundaries" for the limitation.

### Scope Boundaries

| In Scope | Out of Scope |
|----------|-------------|
| Startup reconciliation of unsent events | Rebuilding projections (Phase 008) |
| Periodic retry for events Phase 005 couldn't deliver | Monitoring/dead-letter queue for permanently undeliverable events |
| Exponential backoff for opencode unreachable | SSE subscription for reconnect detection |
| Reuse of `SyncEventMirror` for individual event emission | Creating a new opencode config format or discovery mechanism |
| Structlog warnings after 10 consecutive failures | CLI commands for manual retry (`state events retry` — Phase 010 candidate) |
| Clean shutdown (cancel sweep task on daemon stop) | Per-event TTL or expiry |

**Important runtime gap:** If all unsent events are delivered and the sweep stops, but new events arrive while opencode is unreachable, Phase 005's fire-and-forget will try (once + retry once) and leave them as `synced_to_opencode=0`. The sweep won't restart until the next periodic tick (up to 60s later). This is acceptable — Phase 006 prioritizes simplicity over real-time catch-up. The 60s max gap for mid-session downtime is documented and acceptable per EVT-04 (which requires "when opencode reconnects", not "immediately").

### Projection Impact

- **No projection rebuild:** Phase 006 does not trigger projection rebuilding. Projections (`steps`, `slices`, `concepts` cache tables) are Phase 008's responsibility.
- **Emission-only:** Phase 006 only emits events to opencode. It does not touch any table except `events` (reading and updating `synced_to_opencode`).

### Code Architecture

- **New module:** `src/state_core/reconciler.py`
- **Class:**
  ```python
  class StartupReconciler:
      def __init__(
          self,
          db: SqliteEventStore,
          mirror: SyncEventMirror,
          sweep_interval: float = 60.0,
      ) -> None:
          self._db = db
          self._mirror = mirror
          self._sweep_interval = sweep_interval
          self._task: asyncio.Task | None = None
          self._consecutive_failures = 0

      async def start(self) -> None:
          """Called on daemon start. Runs immediate reconciliation,
          then starts periodic sweep if needed."""

      async def stop(self) -> None:
          """Cancels periodic sweep task."""

      async def _reconcile_once(self) -> int:
          """Single reconciliation pass. Returns number of events emitted."""

      async def _sweep_loop(self) -> None:
          """Periodic sweep with exponential backoff."""
  ```
- **Integration point:** The daemon calls `startup_reconciler.start()` after the event store is ready and `startup_reconciler.stop()` on graceful shutdown.
- **Query for unsent events:**
  ```sql
  SELECT id, aggregate_id, seq, event_type, data, mode, ts
  FROM events
  WHERE synced_to_opencode = 0
  ORDER BY seq ASC
  ```
- **Update on success:**
  ```sql
  UPDATE events SET synced_to_opencode = 1 WHERE id = ?
  ```

### Plan Split (2 plans)

| Plan | Wave | Focus | Depends on |
|------|------|-------|------------|
| **A** | 1 | `StartupReconciler` class + startup reconciliation + periodic sweep loop + exponential backoff | Phase 004 (writer), Phase 005 (SyncEventMirror) |
| **B** | 2 | Comprehensive test suite: startup scenarios, periodic sweep, backoff behavior, failure modes, determinism | Plan A |

### Code Conventions

- Every `.py` file: `from __future__ import annotations` at top
- All SQL identifiers: `snake_case`
- `async with get_connection()` for all DB access
- Structlog for logging: `log = structlog.get_logger(__name__)`
- Docstrings on all public methods
- No `datetime.now()` or randomness in the reconciler (use injected timestamps for testability)
- Per-file module-level `__all__` if more than one public symbol

### Testing Approach

- Use `pytest-httpx` to mock `POST /sync/replay` endpoint
- Use `tmp_path` fixture + monkeypatch `STATE_DB_PATH` for isolated databases (same pattern as Phase 003/004/005 tests)
- Use `monkeypatch` to inject a fake `SyncEventMirror` for unit-testing the reconciler logic
- Test startup reconciliation: create events with `synced_to_opencode=0` → call `start()` → verify all events emitted and marked as synced
- Test periodic sweep: create events, make opencode unreachable, start reconciler, then make opencode reachable → verify events delivered
- Test backoff: mock successive failures → verify warning at 10 consecutive failures
- Test empty queue: no unsent events → `start()` does nothing, no periodic sweep begins
- Test partial success: batch of 5 events, first 3 succeed, last 2 fail → verify first 3 marked synced, last 2 remain unsent
- Test stop/cancellation: start reconciler, cancel task → verify clean exit
- Test determinism: same set of unsent events + reachable opencode → same emission order and HTTP request bodies
- Hypothesis property test: for any set of unsent events with mixed success/failure, reconciler always terminates with every event either synced or still `synced_to_opencode=0` (never partially updated)

### P0 Pitfalls Owned

- **EVT-04 (startup reconciliation):** Phase 006 ensures eventual consistency. Every event that Phase 005 couldn't deliver gets retried on daemon start and periodically thereafter. The invariant is: *every event will eventually be delivered to opencode, assuming opencode comes back at least once per session.*
- **No data loss:** Unsent events are never deleted or modified except to set `synced_to_opencode=1` on successful delivery. If the daemon crashes mid-reconciliation, the next startup will re-attempt all still-unsent events (idempotent emission — opencode deduplicates by event ID).

## Research Sources Used

- `.planning/milestones/v1/ROADMAP.md` — Phase 006 scope, dependency on Phase 004, EVT-04 requirement
- `.planning/milestones/v1/phases/005-syncevent-mirror-emitter/CONTEXT.md` — `SyncEventMirror` class design, opencode URL discovery, fire-and-forget pattern, retry-once-then-delegate contract
- `.planning/milestones/v1/phases/004-writer-task/CONTEXT.md` — writer task patterns, `synced_to_opencode` column, `SqliteEventStore.append()` integration
- `.planning/milestones/v1/REQUIREMENTS.md` — EVT-04 requirement text
- `.planning/milestones/v1/STATE.md` — phase status tracking
- `src/state_core/events.py` — existing `SqliteEventStore`, `read_stream()` with `synced_to_opencode` column
- `src/state_core/sync_mirror.py` — existing `SyncEventMirror` class (Phase 005 deliverable)
