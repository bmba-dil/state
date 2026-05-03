# Plan 006-A: Startup reconciler

## Goal
Create `StartupReconciler` that queries unsent events on daemon start and periodically, emitting them via `SyncEventMirror.emit()`.

## Tasks

| ID | File | Change |
|----|------|--------|
| A1 | `src/state_core/sync_mirror.py` | `emit()` returns `bool` instead of `None` |
| A2 | `src/state_core/events.py` | Add `get_unsynced_events()` |
| A3 | `src/state_core/events.py` | Add `count_unsynced_events()` |
| A4 | `src/state_core/reconciler.py` | New `StartupReconciler` class |
| B | `tests/test_reconciler.py` | 22 test cases across 5 classes |

## Verification
- 22 tests pass in `tests/test_reconciler.py`
- Full test suite passes (212 total)
- ruff lint clean on all changed files
