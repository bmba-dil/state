---
phase: 006
name: startup-reconciliation
milestone: v1
subsystem: state-core
tags: [reconciler, sync-mirror, event-store, startup, backoff]
dependency-graph: 004 -> 005 -> 006
key-files:
  - src/state_core/reconciler.py
  - src/state_core/events.py (get_unsynced_events, count_unsynced_events)
  - src/state_core/sync_mirror.py (emit returns bool)
  - tests/test_reconciler.py
metrics:
  new-tests: 22
  total-tests: 212
  lint-errors: 0
  total-phases-complete: 6
decisions:
  - StartupReconciler._compute_backoff_delay is an instance method reading self._consecutive_failures directly
  - EventStore protocol NOT updated — reconciler depends on SqliteEventStore directly
  - Sweep loop uses dedicated _reconcile_once() call rather than duplicating logic
  - Backoff formula: min(BACKOFF_INITIAL * (BACKOFF_MULTIPLIER ** (failures - 1)), BACKOFF_MAX)
  - CONSECUTIVE_FAILURES_WARN_THRESHOLD = 10 triggers log.warning
  - httpx_mock uses add_callback for deterministic test counts; is_optional=True for timing-sensitive sweep loop tests
---

## Phase 006 Summary: Startup Reconciliation

### What was built

- **`StartupReconciler` class** (`src/state_core/reconciler.py`):
  - `start()` — immediate `_reconcile_once()` call, then spawns background sweep loop
  - `stop()` — cancels sweep task with `contextlib.suppress(asyncio.CancelledError)`
  - `_reconcile_once()` — fetches all unsynced events and emits via mirror, returns count
  - `_sweep_loop()` — periodic sweep with idle suppression (0 count = sleep) and exponential backoff on failure
  - `_compute_backoff_delay()` — 1.0s initial, 2.0x multiplier, 60s cap
  - Safe double-start / double-stop / stop-without-start

- **`SqliteEventStore.get_unsynced_events()`** — returns all events with `synced_to_opencode=0`, ordered by seq ASC, data deserialized from JSON

- **`SqliteEventStore.count_unsynced_events()`** — COUNT(*) query for idle suppression

- **`SyncEventMirror.emit()` returns bool** — `True` on success, `False` after all retries fail. Docstring updated with Returns section.

### Deviations from plan

None.

### Auth gates encountered

None — no credential manipulation in this phase.

### Known stubs / Threat flags

- `get_unsynced_events()` loads all unsynced events into memory. ~2KB per row = ~20MB for 10k events. Add pagination if this becomes problematic.
- Sweep loop tests use `is_optional=True` for httpx_mock responses to handle timing variability. This is acceptable for integration tests but means unused responses don't fail the test.
- `EventStore` protocol not updated — reconciler couples to `SqliteEventStore` directly.
