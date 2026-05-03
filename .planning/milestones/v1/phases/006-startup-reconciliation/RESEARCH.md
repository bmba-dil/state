# RESEARCH: Phase 006 — Startup Reconciliation

## Summary

Phase 006 delivers the catch-up layer of the dual-write architecture: on daemon start (and periodically every 60s), query all unsent events (`synced_to_opencode=0`) and deliver them one-by-one via the existing `SyncEventMirror.emit()` to opencode's `/sync/replay` endpoint. The reconciler class in a new `src/state_core/reconciler.py` module manages exponential backoff (1s → 2s → 4s … 60s max) and clean lifecycle (start/stop). A critical gap identified: `SyncEventMirror.emit()` does not communicate success/failure to its caller, which the reconciler needs for backoff tracking. Two safe remediation paths exist.

---

## Tech Stack Assessment

### Python & asyncio

- **Runtime**: Python 3.14.3 (note: not 3.12 as stated in project docs — though `requires-python = ">=3.12"` covers this). [VERIFIED: python3 --version]
- **`asyncio.TaskGroup`**: Available since 3.11, but the reconciler uses single-task management (start/stop via `_task: asyncio.Task | None`). No `TaskGroup` needed. [VERIFIED: python3 -c "import asyncio; print(hasattr(asyncio, 'TaskGroup'))"]
- **Task cancellation in 3.14**: `asyncio.CancelledError` is a `BaseException` subclass (unchanged since 3.8). Since `SyncEventMirror.emit()` catches `except Exception`, `CancelledError` will correctly propagate through `emit()` to the sweep loop. Standard pattern: `try: … except asyncio.CancelledError: log.info("…"); raise` for clean shutdown. [ASSUMED]
- **`asyncio.ensure_future` vs `asyncio.create_task`**: Both work in 3.14. Phase 005 uses `asyncio.ensure_future`; the reconciler may use `asyncio.create_task` (preferred, more explicit). **No behavioral difference for this use case.** [ASSUMED]
- **`asyncio.get_event_loop_policy()` deprecation**: Deprecated since 3.14, slated for removal in 3.16. The project's test code calls `asyncio.get_event_loop().time()` — this still works in 3.14 but should be migrated to `time.monotonic()` for forward compatibility. Not blocking. [VERIFIED: python3 deprecation warning on get_event_loop_policy]

### pytest-httpx (v0.36.2)

- Compatible with httpx 0.28.x. Already used extensively in `test_sync_mirror.py`. [VERIFIED: installed via venv pip list]
- **Callback FIFO consumption**: When multiple callbacks are registered for the same URL, they are consumed in registration order. Each call consumes one callback. This means an accurate count of expected HTTP calls must be registered. [ASSUMED based on pytest-httpx docs behavior]
- **Global interception**: pytest-httpx intercepts ALL `httpx` traffic. The `url=` parameter restricts matching. Without it, ALL requests match. Since the reconciler only calls opencode's `/sync/replay`, this isn't an issue. [ASSUMED]
- **No mixing real + mock**: pytest-httpx does NOT allow some requests to pass through to real servers while mocking others (by design). All HTTP traffic must be mocked or none. This is fine — all reconciler HTTP traffic goes to the mock. [ASSUMED]
- **`add_exception` for connection failures**: Already tested in Phase 005 — use `httpx.ConnectError` for "opencode unreachable" scenarios. [VERIFIED: test_sync_mirror.py lines 161-176]

### pytest-asyncio (v1.3.0)

- `asyncio_mode = "auto"` is configured in `pyproject.toml` — tests are auto-detected as async if they are `async def`. [VERIFIED: pyproject.toml line 71]
- Existing tests use `@pytest.mark.asyncio` explicitly (redundant but harmless). New tests should follow the existing pattern for consistency. [VERIFIED: test_sync_mirror.py, test_events.py]

### Structlog

- Version 25.1+. Used throughout the codebase. Reconciler will use `log = structlog.get_logger(__name__)`. No issues. [ASSUMED]

---

## Integration Points (Mapped)

### SqliteEventStore — Methods Needed

The current `SqliteEventStore` exposes only `append()` and `read_stream()`. For the reconciler, the following are needed:

| Method | Purpose | Current Status | Recommendation |
|--------|---------|---------------|----------------|
| Query unsent events | `SELECT * FROM events WHERE synced_to_opencode = 0 ORDER BY seq ASC` | **Missing** — add to `SqliteEventStore` or use raw `get_connection()` in reconciler | **Add `get_unsynced_events() -> list[dict]` to `SqliteEventStore`** — keeps DB abstraction clean |
| Count unsynced events | `SELECT COUNT(*) FROM events WHERE synced_to_opencode = 0` | **Missing** — needed for idle suppression guard | **Add `count_unsynced_events() -> int`** — or inline in reconciler, but encapsulated is better |
| Mark event synced | Already done via `SyncEventMirror._mark_synced()` | Reused via `emit()` — no change needed | No new method needed |

**Note on the current `read_stream()` method**: It queries by `aggregate_id` and deserializes `data` from JSON. The reconciler needs ALL unsent events regardless of aggregate, as raw dicts. A separate method or direct SQL is cleaner than trying to adapt `read_stream()`.

### SyncEventMirror — Methods Reused

| Method | Usage in Reconciler | Issue |
|--------|---------------------|-------|
| `emit(event_row)` | Called per-event for delivery | **Returns `None`** — reconciler cannot know if delivery succeeded |
| `_mark_synced(event_id)` | Called internally by `emit()` on success | Not exposed to reconciler (and shouldn't be — it's mirror's responsibility) |
| `close()` | Not called by reconciler — daemon owns lifecycle | N/A |
| `_client` (httpx.AsyncClient) | Shared via `emit()` — reconciler doesn't access directly | N/A |

### Configuration Dependency Chain

```
StartupReconciler
  └─ SyncEventMirror.emit()
       ├─ resolve_opencode_url()           [config.py]
       │    ├─ STATE_OPENCODE_URL env var  [env]
       │    ├─ find_opencode_config()       [config.py — walks up from CWD]
       │    └─ DEFAULT_OPENCODE_HOST:PORT  [config.py — fallback]
       ├─ httpx.AsyncClient().post()       [shared via mirror._client]
       └─ _mark_synced(event_id)           [DB: sync_mirror.py]
            └─ get_connection()            [database.py]
```

The reconciler does NOT need to call `resolve_opencode_url()` directly — it's behind `emit()`. **Zero new config surface needed.**

---

## Risk Areas

### Critical: `emit()` Returns No Success/Failure Status

`SyncEventMirror.emit()` is **fire-and-forget** — it catches all exceptions internally and returns `None` regardless of outcome. The reconciler needs per-event success/failure to:

1. Track `_consecutive_failures` for exponential backoff
2. Return accurate emission count from `_reconcile_once()`
3. Decide whether to stop or continue the sweep loop

**Two remediation paths:**

| Option | Impact | Complexity | Recommendation |
|--------|--------|-----------|----------------|
| **A: Modify `emit()` to return `bool`** | Backward compatible — existing callers via `asyncio.ensure_future` ignore return value. `True` = delivered+marked, `False` = permanent failure | Low (change return + docstring) | **Preferred** — cleanest, no extra DB queries |
| **B: Post-emit DB check** | After `emit()`, query `SELECT synced_to_opencode FROM events WHERE id = ?`. Adds 1 DB query per event on success path. | Low code complexity, but 2x DB round-trips per event (emit's `_mark_synced` + reconciler's check) | Acceptable fallback if Option A is rejected |

**Recommendation: Option A.** Existing callers `asyncio.ensure_future(mirror.emit(...))` do not use the return value. The change is additive and non-breaking.

### Task Lifecycle Risks

| Scenario | Risk | Mitigation |
|----------|------|------------|
| `start()` called twice | Two sweep tasks running concurrently, double emissions | **Guard with early return** if `self._task is not None` |
| `stop()` during startup reconciliation | Startup `_reconcile_once()` interrupted mid-flight | **Shield startup** with `asyncio.shield()` OR let it drain naturally — remaining unsent events will be picked up on next daemon start |
| `stop()` during `_mark_synced` | If `CancelledError` hits during `_mark_synced`, event may be delivered to opencode but NOT marked synced | **Acceptable**: duplicate re-delivery on next sweep. Opencode deduplicates by event ID. |
| Concurrent `_reconcile_once()` calls | Double counting, race on DB updates | **Prevent by design**: `_sweep_loop` is a sequential loop. `start()` performs one `_reconcile_once()` before starting the task. |

**Recommendation on `stop()` semantics:**
```python
async def stop(self) -> None:
    if self._task is not None:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass  # expected
```

No `asyncio.shield()` needed — the sweep loop can be interrupted safely. Unsent events remain in DB and will be retried on next startup.

### Race Conditions

| Race | Happens When | Impact | Acceptable? |
|------|-------------|--------|-------------|
| Phase 005 emits event between reconciler's query and emit | Event `synced_to_opencode=0` at query time, Phase 005's `emit()` succeeds before reconciler's `emit()` | Reconciler re-emits already-synced event. `_mark_synced` sets `synced_to_opencode=1` again (no-op). | **Yes** — harmless duplicate POST to opencode (idempotent dedup by event ID) |
| Phase 005's `emit()` in-flight during reconciler query | `synced_to_opencode=0` at query time, Phase 005's `emit()` hasn't completed yet | Both emit. If both succeed, double mark_synced (harmless). If Phase 005 fails and reconciler succeeds, correct. If both fail, next sweep catches it. | **Yes** — always eventually consistent |
| Event appended between startup reconciliation and sweep start | Reconciler finished startup, starts sweep. Meanwhile Phase 005 appended a new event that failed to deliver. | First sweep iteration picks it up (up to 60s gap). | **Yes** — documented in CONTEXT.md as acceptable runtime gap |
| Daemon crashes mid-reconciliation | Reconciler completed some `emit()` calls but not all | Next startup re-queries `synced_to_opencode=0` events. Already-delivered events are re-sent (idempotent). Not-yet-delivered events are sent fresh. | **Yes** — crash recovery is fully idempotent |

**Verdict:** No race conditions result in data loss or inconsistency.

### Memory

- **10,000 unsent events** loaded at once via `get_unsynced_events()`. Each row is a dict with ULID (26 chars), int, text fields, and a JSON `data` payload. Estimated ~2KB per row → **~20MB** for 10k events.
- If `data` payloads are large (e.g., embedded files in tool_call output), could spike higher.
- **Recommendation:** Document the memory ceiling in the method docstring. No mitigation needed for v1 — if memory proves problematic, add `LIMIT 1000 OFFSET ?` pagination as a future optimization. The partial index `idx_events_unsynced` makes the query fast regardless.

### SQL Injection

- Query template uses `?` placeholders: `WHERE synced_to_opencode = 0`. No user-supplied values are interpolated. **No risk.** [VERIFIED: CONTEXT.md SQL templates]

### Database Connection Contention

- The reconciler opens its own connection via `get_connection()` for the unsent-events query. This is separate from `SyncEventMirror._mark_synced()` which also calls `get_connection()`. Two concurrent connections is fine (WAL mode allows concurrent readers + a writer).
- If both the reconciler and Phase 005's `append()` call `_mark_synced()` for the same event, they'll contend on the same row. SQLite handles this via its internal serialization. No deadlock risk because:
  1. `_mark_synced` is a simple `UPDATE WHERE id = ?` — no multi-table transaction
  2. WAL mode allows concurrent reads
  3. The writer (Phase 005 `append()`) uses `BEGIN IMMEDIATE`; reconciler uses simple auto-commit

---

## Testing Strategy

### Fixture Design

Based on existing patterns in `test_sync_mirror.py` and `test_events.py`:

```python
# ---- Unit-test fixtures (mock mirror) ----

@pytest.fixture(autouse=True)
def _patch_env(tmp_path, monkeypatch):
    """Standard isolation: isolated DB + pinned opencode URL."""
    monkeypatch.setenv("STATE_DB_PATH", str(tmp_path / ".state" / "events.sqlite"))
    monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:0")
    # Copy migrations
    shutil.copytree(Path.cwd() / ".state" / "migrations",
                    tmp_path / ".state" / "migrations",
                    dirs_exist_ok=True)

@pytest.fixture
async def store():
    """Ready-to-use SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()

@pytest.fixture
def mock_mirror(mocker):
    """Mocked SyncEventMirror that tracks calls and returns configurable success."""
    mirror = mocker.AsyncMock(spec=SyncEventMirror)
    mirror.emit.return_value = True  # default: success
    return mirror

@pytest.fixture
def reconciler(store, mock_mirror):
    return StartupReconciler(db=store, mirror=mock_mirror, sweep_interval=0.1)
```

### Test Plan

| Test Class | Focus | Mock Strategy | Key Assertions |
|-----------|-------|---------------|----------------|
| **TestStartupReconciliation** | `start()` behavior | Mock mirror | Unsent events emitted in seq order. Mirror called for each. Synced flag set. |
| **TestIdleOnEmpty** | No unsent events | Mock mirror | `start()` returns quickly. No HTTP calls. Sweep task NOT created. |
| **TestPeriodicSweep** | Background sweep loop | Mock mirror | Sweep retries remaining events. Backoff increases. Resets on success. |
| **TestBackoffBehavior** | Exponential backoff | Mock mirror (all fail) | After 10 consecutive failures, structlog warning emitted. Delays: 1, 2, 4, 8, 16, 32, 60, 60, 60… |
| **TestPartialSuccess** | Mixed success/failure | Mock mirror (first N succeed, rest fail) | First N marked synced. Remaining unsent. `_consecutive_failures` resets (at least 1 success). |
| **TestStopCancellation** | `stop()` mid-sweep | Mock mirror (slow emit) | Task cancelled. Clean exit. Events remain unsent. |
| **TestDoubleStart** | Guard against double-start | Mock mirror | Second `start()` is no-op (or raises). |
| **TestDeterminism** | Same input → same output | Mock mirror | Two identical reconcilers with same events produce same emission order and count. |
| **TestIntegration** | End-to-end with real mirror | pytest-httpx | HTTP body matches expected shape. Synced flag set after successful POST. |
| **TestManyEvents** | 10,000 events at once | pytest-httpx | Smoke test: completes without OOM. All events emitted. |
| **HypothesisProperty** | Randomized success/failure | Mock mirror | For any sequence of events with random success/failure pattern, eventually all events are either synced or still `synced_to_opencode=0` (never half-marked or corrupted). |

### Edge Cases to Cover in Property Tests

- Empty event set
- Single event
- All fail permanently (opencode never comes back)
- All succeed immediately
- Success → failure → success pattern (backoff reset)
- Random interleaving of success/failure per event
- Concurrent calls to `start()`/`stop()` (guard verification only — not true concurrency, since tests are single-threaded)

### pyteset-httpx Mock Patterns (Integration Tests)

Reuse existing helpers from `test_sync_mirror.py`:

```python
def _sync_replay_ok(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200)

def _sync_replay_500(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(500)

def _sync_replay_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.TimeoutException("timed out", request=request)

def _sync_replay_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)
```

For multi-call scenarios (sweep with multiple events), register N callbacks:
```python
httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")   # event 1
httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")  # event 2 (fails)
```

**Important**: pytest-httpx callbacks are consumed FIFO. Each `emit()` call consumes one callback. Ensure the number of callbacks matches the expected number of `emit()` calls.

### Hypothesis Property Test Design

```python
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_events=st.integers(min_value=0, max_value=20),
    success_pattern=st.lists(st.booleans(), min_size=0, max_size=20),
)
async def test_property_reconciler_eventual_consistency(
    tmp_path, monkeypatch, n_events, success_pattern
):
    """
    Property: Starting the reconciler with any mix of events and any
    per-event success pattern always terminates with every event either
    synced (synced_to_opencode=1) or still unsynced (synced_to_opencode=0).
    No event is ever partially updated or corrupted.
    """
    # Setup isolated DB
    # Insert n_events with synced_to_opencode=0
    # Create mock mirror that returns success_pattern[i]
    # Run reconciler.start()
    # Verify: all events have synced_to_opencode in {0, 1}
    # Verify: total synced + total unsynced = n_events
```

---

## Performance Analysis

| Scenario | Events | DB Queries | HTTP Calls | Expected Duration |
|----------|--------|------------|------------|-------------------|
| Startup, no unsent events | 0 | 1 (COUNT) | 0 | < 10ms |
| Startup, 1 unsent event | 1 | 1 (SELECT) + 1 (UPDATE via `_mark_synced`) | 1 (+ 1 retry if fails) | ~100ms (ok) |
| Startup, 1k unsent events | 1,000 | 1 (SELECT) + 1k (UPDATE) | 1k-2k | ~1-2s (acceptable) |
| Startup, 10k unsent events | 10,000 | 1 (SELECT) + 10k (UPDATE) | 10k-20k | ~10-20s (notable but acceptable — first boot after long offline) |
| Periodic sweep, opencode down | N | 1 (SELECT) + 0 | 0 (idle suppression check) | < 10ms |
| Periodic sweep, opencode back | N | 1 (SELECT) + N (UPDATE) | N | Proportional to N |

**Key observation**: With `emit()` returning `bool` (Option A), the reconciler needs 0 extra DB queries beyond what `emit()` already does internally. The DB load is 1 SELECT + N UPDATEs, which is optimal.

**If Option B** (post-emit DB check) is chosen instead: add N extra SELECT queries (one per event after `emit()`), doubling the DB load on the success path. Still acceptable but suboptimal.

---

## Alternative Approaches Evaluated

### Alternative 1: Batch Emission (Multiple Events Per POST)

**Description**: Query all unsent events, then POST them all at once to `/sync/replay` with an event array.

**Pros:**
- Single HTTP call for all events (vs N calls with single emission)
- Lower overhead when opencode is reachable

**Cons:**
- Partial failure is complex: which events in the batch succeeded? Need per-event status codes or rely on opencode's idempotency
- Breaks the Phase 005 pattern (which emits one-at-a-time)
- Requires the opencode API to accept event arrays (already does, but single-event matches the XRPC pattern better)
- A single large POST could timeout on the server for very large event sets

**Verdict**: Rejected by CONTEXT.md. Correct decision — single emission is simpler, more consistent with Phase 005, and cleanly handles partial failures.

### Alternative 2: SSE Subscription for Reconnect Detection

**Description**: Subscribe to opencode's SSE stream to receive a "reconnected" event, triggering immediate reconciliation.

**Pros:**
- Instant notification when opencode returns (vs up to 60s sweep gap)
- More elegant than polling

**Cons:**
- Requires an SSE client library or custom implementation
- Additional opencode API dependency
- Connection management complexity (reconnect the SSE stream itself)
- The 60s max gap is explicitly documented as acceptable

**Verdict**: Rejected by CONTEXT.md. Correct decision — periodic sweep is simpler, equally effective for "eventual consistency" requirements, and doesn't add a new protocol dependency.

### Alternative 3: Active Health Polling

**Description**: Poll opencode's health endpoint (e.g., `GET /health`) every N seconds to detect when it comes back.

**Pros:**
- Can start reconciling immediately when opencode returns

**Cons:**
- Wasted HTTP calls during downtime
- Need to define/implement a health endpoint
- Adds complexity (health check logic, different from real POSTs)
- The passive approach (success/failure of real POSTs) is strictly simpler

**Verdict**: Rejected by CONTEXT.md. Correct decision — passive detection via POST success/failure is the most reliable "health check" (it directly measures what matters).

### Alternative 4: Separate Retry Queue Table

**Description**: Instead of re-scanning the `events` table, maintain a dedicated `retry_queue` table for events that failed to sync.

**Pros:**
- Faster queries (smaller table)
- Cleaner separation of concerns
- Can add metadata (retry count, last error, etc.)

**Cons:**
- Additional schema and migration
- Must keep retry_queue in sync with events (dual-write complexity)
- The partial index `idx_events_unsynced` already optimizes the unsent-events query
- The events table already has all the data needed

**Verdict**: Premature optimization. The partial index makes the query fast enough for all expected event volumes. If monitoring metadata is needed, add a `sync_audit` table later, not a retry queue.

### Alternative 5: Event-Scoped Retry (Per-Event Backoff)

**Description**: Instead of per-sweep backoff, each event gets its own retry schedule (e.g., event 1 retries in 1s, event 2 in 2s, etc.).

**Pros:**
- Smoother retry distribution (could avoid thundering herd when opencode comes back)

**Cons:**
- Much more complex (per-event timers, state tracking)
- Need to manage 10,000 concurrent retry timers
- The thundering herd concern is overstated — opencode handles bulk POSTs fine
- Per-sweep backoff is well-understood and simple

**Verdict**: Not considered in CONTEXT.md, but worth documenting as a known pattern. Reject because complexity outweighs benefit.

---

## Recommendations Summary

1. **Modify `SyncEventMirror.emit()` to return `bool`** [HIGH confidence]: This is the single most important change. It's backward-compatible (existing callers discard the return value) and enables clean backoff tracking without extra DB queries.

2. **Add `SqliteEventStore.get_unsynced_events()`** [HIGH confidence]: Keep DB access behind a clean abstraction. Returns `list[dict[str, Any]]` ordered by `seq ASC`.

3. **Add `SqliteEventStore.count_unsynced_events()`** [MEDIUM confidence]: For the idle suppression guard. Could also be inlined, but encapsulation is better for testability.

4. **Guard `start()` against double-invocation** [HIGH confidence]: Early return or assert `self._task is None`.

5. **No changes to daemon files needed** [HIGH confidence]: Daemon stub files exist but are empty. The reconciler's `start()`/`stop()` will be wired by the daemon implementation (future phase or daemon server work).

6. **Use `time.monotonic()` not `asyncio.get_event_loop().time()`** [MEDIUM confidence]: Future-proofing against 3.16 deprecation. Not urgent but worth adopting now in new code.

7. **Document the ~20MB memory ceiling for 10k events** [MEDIUM confidence]: In the method docstring of `get_unsynced_events()`.

8. **No concurrency protection needed beyond the task guard** [HIGH confidence]: Python's GIL and asyncio's single-threaded event loop prevent true concurrent `_reconcile_once()` execution. The task guard prevents accidental double-start.

---

## Open Questions

1. **Should `emit()` return `True` or `False`?** Clear semantics: `True` = event was successfully delivered to opencode AND `_mark_synced` completed. `False` = both attempts failed (opencode unreachable, non-2xx response, or _mark_synced DB error).

2. **Should `StartupReconciler` accept an optional callable for monitoring callbacks?** E.g., `on_sweep_complete(emitted: int, remaining: int)` for future observability. Not needed for v1 but worth considering the API shape now.

3. **Handler for `resolve_opencode_url()` failures?** `emit()` calls this per-event. If config is missing, every event will fail. Should the reconciler detect this once upfront and log a clear error? Phase 005's `emit()` already handles this gracefully (logs warning, returns False), so the reconciler will see consecutive failures and eventually log a structlog warning. This is adequate.

4. **Migration path for existing events**: The `synced_to_opencode` column already exists and defaults to 0. No migration needed for Phase 006.

5. **Should `_sweep_loop` use `asyncio.sleep()` for the backoff delay, or `asyncio.create_task()` with a delayed start?** `asyncio.sleep()` is simpler and correct — the sweep loop is not a critical path. When `stop()` cancels the task during `asyncio.sleep()`, the sleep is interrupted immediately.
