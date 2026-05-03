---
phase: 006-startup-reconciliation
reviewed: 2026-04-23T23:59:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/state_core/sync_mirror.py
  - src/state_core/events.py
  - src/state_core/reconciler.py
  - tests/test_reconciler.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 006: Code Review Report — Startup Reconciliation

**Reviewed:** 2026-04-23T23:59:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed 4 files (3 source + 1 test) implementing the startup reconciliation loop for unsent SyncEvent replay. The architecture is sound — separate reconciler loop, exponential backoff, fire-and-forget mirror — and the SQL queries are properly parameterized (no injection risk). The test suite covers the main paths well with 22 test cases.

However, there are four WARNING-level issues:

1. **Ordering bug in `get_unsynced_events()`** — uses `ORDER BY seq` which is per-aggregate, not global chronological order
2. **Sweep loop conflates "new events arrived" with "delivery failed"** — the return value of `_reconcile_once()` is discarded, causing false backoff inflation under load
3. **Missing `mirror.close()` lifecycle** — HTTP client pool leaks on every stop/start cycle
4. **Unvalidated dict access in `emit()`** — missing keys get swallowed by broad `except Exception`

No critical/blocker issues found. No SQL injection vectors. No asyncio task leaks under normal operation.

---

## Warnings

### WR-01: `get_unsynced_events()` orders by per-aggregate sequence number, not global time

**File:** `src/state_core/events.py:178`
**Issue:** `ORDER BY seq ASC` sorts by per-aggregate sequence number, which is meaningless across different aggregates. Two events from different aggregates can both have `seq=1` — their relative order is determined by the sort, not by their actual chronological occurrence. For example:

| Event | aggregate_id | seq | ts |
|-------|-------------|-----|-----|
| A     | step-01     | 1   | 00:00:01 |
| B     | arc-01      | 1   | 00:00:03 |
| C     | step-01     | 2   | 00:00:02 |

`ORDER BY seq` produces: A, B, C. Chronological order is: A, C, B. If opencode's replay endpoint processes events in the delivered order and expects chronological ordering, this produces incorrect results.

**Fix:** Change to `ORDER BY id` (ULIDs encode a 48-bit timestamp prefix and are lexicographically sortable) or `ORDER BY rowid`:

```python
# In get_unsynced_events(), line 178:
"ORDER BY id ASC"
```

Note: `read_stream()` (line 152) also uses `ORDER BY seq ASC` — but that query is filtered by `aggregate_id = ?`, so all seq values are within the same aggregate. That usage is correct.

---

### WR-02: Sweep loop discards `_reconcile_once()` return value — false backoff inflation

**File:** `src/state_core/reconciler.py:99-115`
**Issue:** The sweep loop at line 99 calls `await self._reconcile_once()` but discards its return value. Then it uses `remaining_after > 0` (line 102-107) to decide whether to increment consecutive failures. This conflates two distinct situations:

1. **Delivery actually failed** — `_reconcile_once()` returned 0, remaining > 0 (correct to back off)
2. **New events arrived during reconciliation** — `_reconcile_once()` returned N > 0, but remaining > 0 because new events were appended (incorrect to back off)

Furthermore, `_reconcile_once()` internally resets `self._consecutive_failures = 0` at line 87 when any event succeeds. But then the sweep loop immediately re-increments it at line 107 (`self._consecutive_failures += 1`) because `remaining_after > 0` due to new arrivals. The counter reset is undone within the same iteration.

**Concrete failure path:**
1. `_consecutive_failures = 3` (currently backing off 4s)
2. Sweep wakes, calls `_reconcile_once()` → 1 event succeeds → resets failures to 0
3. Meanwhile, 1 new event was appended by another coroutine
4. `count_unsynced_events()` → 1 (the new event)
5. `remaining_after > 0` → `consecutive_failures = 1` (INCORRECT — was just reset to 0)

In a busy system where events are appended steadily, the backoff counter ratchets up indefinitely even when all deliveries succeed, eventually reaching the 60s cap and suppressing reconciliation.

**Fix:** Only increment failures when `_reconcile_once()` returns 0, indicating no events succeeded:

```python
# In _sweep_loop(), replace lines 99-107:
result = await self._reconcile_once()

remaining_after = await self._db.count_unsynced_events()
if remaining_after == 0:
    self._consecutive_failures = 0
    await asyncio.sleep(self._sweep_interval)
    continue

# Only increment failures if NOTHING was delivered this cycle
if result == 0:
    self._consecutive_failures += 1
    if self._consecutive_failures >= CONSECUTIVE_FAILURES_WARN_THRESHOLD:
        log.warning(...)

    delay = self._compute_backoff_delay()
    await asyncio.sleep(delay)
# else: events succeeded but more remain — new arrivals or partial failure
# Don't back off — loop will retry remaining events on next iteration
```

Note: `_reconcile_once()` also resets `_consecutive_failures` internally when any event succeeds. This can be removed if the sweep loop takes over all failure-count management, avoiding dual responsibility.

---

### WR-03: `SyncEventMirror.close()` never called — HTTP client pool leak

**File:** `src/state_core/reconciler.py:58-68`
**Issue:** The `StartupReconciler` holds a reference to `SyncEventMirror` but never calls `mirror.close()` during `stop()`. The `SyncEventMirror` creates an `httpx.AsyncClient` in its constructor (sync_mirror.py:47) which maintains a connection pool. On every reconciler stop (e.g., daemon restart, mode switch), the pool is leaked.

The lifecycle dependency is implicit: someone must remember to call `mirror.close()` separately after stopping the reconciler. This is easy to miss.

**Fix:** Either have the reconciler manage the mirror's lifecycle, or document clearly who owns the close:

Option A — Reconciler takes ownership:
```python
async def stop(self) -> None:
    if self._task is not None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
    await self._mirror.close()   # <-- add this
    log.debug("reconciler stopped")
```

Option B — Wrap in `AsyncExitStack` at the call site:
```python
# Caller's responsibility:
async with AsyncExitStack() as stack:
    mirror = SyncEventMirror(directory=...)
    stack.push_async_callback(mirror.close)
    reconciler = StartupReconciler(store, mirror)
    stack.push_async_callback(reconciler.stop)
    await reconciler.start()
    ...
```

---

### WR-04: `emit()` uses bare dict key access — missing keys swallowed by broad `except`

**File:** `src/state_core/sync_mirror.py:67-78`
**Issue:** Lines 71-76 access `event_row` dict with bare bracket notation (`event_row["id"]`, `event_row["aggregate_id"]`, etc.). If any key is missing or the dict has unexpected structure, a `KeyError` is raised. This gets caught by the broad `except Exception` at line 103, logged as "sync unexpected error", and the event silently returns False. The error message doesn't indicate it was a dict shape issue vs. an HTTP transport failure.

**Fix:** Add validation early in `emit()`, or use `.get()` with explicit handling:

```python
async def emit(self, event_row: dict[str, Any]) -> bool:
    # Validate required keys early
    required_keys = {"id", "aggregate_id", "seq", "type", "data"}
    missing = required_keys - event_row.keys()
    if missing:
        log.error("sync event_row missing keys", missing=missing)
        return False

    url = resolve_opencode_url()
    replay_url = f"{url}{SYNC_REPLAY_PATH}"

    body: dict[str, Any] = {
        "directory": str(self._directory),
        "events": [
            {
                "id": event_row["id"],
                "aggregate_id": event_row["aggregate_id"],
                "seq": event_row["seq"],
                "type": event_row["type"],
                "data": event_row["data"] if isinstance(event_row["data"], dict)
                        else json.loads(event_row["data"]),
            }
        ],
    }
    ...
```

---

## Info

### IN-01: Race condition — `stop()` during `start()`'s initial reconcile is silently lost

**File:** `src/state_core/reconciler.py:47-68`
**Issue:** `start()` calls `_reconcile_once()` synchronously (line 55) BEFORE creating the sweep task (line 56). If `stop()` is called while this initial reconcile is in progress, `stop()` sees `self._task is None` and returns immediately as a no-op. After `_reconcile_once()` completes, `start()` creates the sweep task — the reconciler is now running even though `stop()` was called.

In a well-designed daemon, `start()` and `stop()` are called sequentially during init/shutdown, so this race is unlikely in practice. But in async systems with concurrent lifecycle management (e.g., signal handlers), it could manifest.

**Fix:** Add a `_stopped` flag:

```python
def __init__(self, ...):
    ...
    self._stopped = False

async def stop(self) -> None:
    self._stopped = True
    if self._task is not None:
        self._task.cancel()
        ...

async def start(self) -> None:
    if self._task is not None:
        return
    self._stopped = False
    await self._reconcile_once()
    if self._stopped:          # <-- check if stop() was called during reconcile
        return
    self._task = asyncio.create_task(self._sweep_loop())
```

---

### IN-02: White-box test coupling to private attributes

**File:** `tests/test_reconciler.py` (multiple locations)
**Issue:** Tests directly access private attributes (`reconciler._consecutive_failures`, `reconciler._task`, `reconciler._task.done()`). This creates tight coupling to implementation details:

- Line 101: `assert reconciler._task is not None`
- Line 102: `assert not reconciler._task.done()`
- Line 200: `reconciler._consecutive_failures = 5`
- Line 218: `reconciler._consecutive_failures = 3`
- Line 237: `reconciler._consecutive_failures = 3`
- Line 271: `reconciler._consecutive_failures = 1`
- Line 385: `assert reconciler._consecutive_failures > 0`

If these attributes are renamed or the internal logic is restructured, the tests silently break. Consider using public interfaces where possible (e.g., `is_running()` method for task state), or call `_reconcile_once()` directly and verify behavior through side effects (DB state, HTTP requests).

---

### IN-03: Test fixture depends on `Path.cwd()` — fragile outside project root

**File:** `tests/test_reconciler.py:44`
**Issue:** The `_isolate_db` fixture copies migration files from `Path.cwd() / ".state" / "migrations"`. If tests are run from a different working directory (e.g., `python3 -m pytest tests/` from a symlinked location), the path may not resolve correctly. The migrations won't be copied, `migrate()` will silently find nothing to apply, the events table won't exist, and `store.append()` will fail with opaque errors.

**Fix:** Resolve migrations relative to the test file, not CWD:

```python
_HERE = Path(__file__).resolve().parent.parent.parent
_MIGRATIONS_SRC = _HERE / ".state" / "migrations"
```

Or use `git rev-parse --show-toplevel` if running from within the repo.

---

### IN-04: No test coverage for `mirror.close()` during reconciler lifecycle

**File:** `tests/test_reconciler.py` (entire file)
**Issue:** The test suite never exercises what happens when `mirror.close()` is called while the reconciler is active. Since `SyncEventMirror` and `StartupReconciler` have an implicit lifecycle dependency (the mirror's client must outlive the reconciler's usage), this is a coverage gap. If `mirror.close()` is called while the reconciler is running, subsequent `emit()` calls will raise `httpx.ConnectError` on a closed client.

---

_Reviewed: 2026-04-23T23:59:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
