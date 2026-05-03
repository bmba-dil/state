---
phase: 006
plan: A + B
type: auto
autonomous: true
wave: 1
depends_on:
  - "Phase 004 — SqliteEventStore append + synced_to_opencode column"
  - "Phase 005 — SyncEventMirror emit() + opencode config discovery"
files_modified:
  - "src/state_core/sync_mirror.py"          # MODIFY: emit() returns bool
  - "src/state_core/events.py"               # MODIFY: add get_unsynced_events(), count_unsynced_events()
  - "src/state_core/reconciler.py"           # CREATE: StartupReconciler class
  - "tests/test_reconciler.py"               # CREATE: comprehensive test suite
requirements:
  - "EVT-04: Startup reconciliation replays unsent events to opencode's SyncEvent when opencode reconnects"
---

<objective>
Deliver the catch-up layer of the dual-write architecture. On daemon start (and periodically every 60s), query all unsent events (synced_to_opencode=0) and deliver them one-by-one via SyncEventMirror.emit() to opencode's /sync/replay endpoint. Exponential backoff (1s → 2s → 4s … 60s max) handles opencode-unreachable. This ensures eventual consistency for events Phase 005's fire-and-forget couldn't deliver.

Two-plan split:
- Plan A (Wave 1): SyncEventMirror.emit() return-type fix + SqliteEventStore query methods + StartupReconciler class
- Plan B (Wave 2): Comprehensive test suite (unit, integration, hypothesis property)
</objective>

---

## Plan A — StartupReconciler Implementation (Wave 1)

### Task A1 — Modify SyncEventMirror.emit() to return bool

<read_first>
- src/state_core/sync_mirror.py — entire file (124 lines)
</read_first>

<action>
Change the return type annotation of emit() from None to bool:

1. Signature change (line 49):
   Change `async def emit(self, event_row: dict[str, Any]) -> None:` to `async def emit(self, event_row: dict[str, Any]) -> bool:`

2. Success return (lines 83-87):
   Change `return` (bare) inside `if response.is_success:` block to `return True`

3. Failure return (lines 102-103):
   Add `return False` after `log.warning("sync permanently failed", ...)`

4. Update docstring (lines 50-57):
   - Change first paragraph: "POST a single event ... It catches all exceptions internally — never propagates to the caller." → "POST a single event ... Returns True if delivered+marked, False after both attempts fail."
   - Add: `Returns: True if the event was successfully delivered to opencode and marked synced. False if both attempts failed.`

5. No other changes to SyncEventMirror — do NOT touch __init__, _mark_synced, close, or any other method.

Backward compatibility: Existing callers via asyncio.ensure_future(mirror.emit(...)) (events.py line 134) ignore the return value. No call-site changes needed.
</action>

<acceptance_criteria>
- `python3 -c "from src.state_core.sync_mirror import SyncEventMirror; import inspect; assert 'bool' in inspect.signature(SyncEventMirror.emit).return_annotation"` — return type annotation is bool
- `python3 -m pytest tests/test_sync_mirror.py -v` — all existing tests pass unchanged
- grep for `-> None` on `def emit(` in sync_mirror.py returns no match
- `grep -c "return True" src/state_core/sync_mirror.py` >= 1 AND `grep -c "return False" src/state_core/sync_mirror.py` >= 1
</acceptance_criteria>

---

### Task A2 — Add SqliteEventStore.get_unsynced_events() method

<read_first>
- src/state_core/events.py — entire file (160 lines). Focus on read_stream() pattern for deserialization.
- src/state_core/schema.py — Mode type for reference
</read_first>

<action>
Add get_unsynced_events() to SqliteEventStore in events.py. Insert after read_stream() (after line 160):

```python
async def get_unsynced_events(self) -> list[dict[str, Any]]:
    """Return all events not yet synced to opencode, ordered by seq ASC.

    Loaded entirely into memory. At ~2KB per row, 10k events consume
    ~20MB. If memory proves problematic, add pagination (LIMIT/OFFSET).

    Returns:
        List of event row dicts with keys: id, aggregate_id, seq,
        type, data (deserialized from JSON), mode, ts.
    """
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, aggregate_id, seq, type, data, mode, ts "
            "FROM events "
            "WHERE synced_to_opencode = 0 "
            "ORDER BY seq ASC"
        )
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                d["data"] = json.loads(d["data"])
            result.append(d)
        return result
```

SQL columns: id, aggregate_id, seq, type, data, mode, ts — all match the keys SyncEventMirror.emit() reads (event_row["type"], event_row["id"], event_row["aggregate_id"]).

Imports json and aiosqlite already exist at lines 11 and 15.
</action>

<acceptance_criteria>
- `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'get_unsynced_events')"` — method exists
- `python3 -c "from src.state_core.events import SqliteEventStore; import inspect; assert 'list' in inspect.signature(SqliteEventStore.get_unsynced_events).return_annotation"` — return type annotated
- grep for `row_factory = aiosqlite.Row` in the new method in events.py
- `grep -c "synced_to_opencode = 0" src/state_core/events.py` returns exactly 2 matches
</acceptance_criteria>

---

### Task A3 — Add SqliteEventStore.count_unsynced_events() method

<read_first>
- src/state_core/events.py — same file, adjacent to where get_unsynced_events() was added
</read_first>

<action>
Insert right after get_unsynced_events():

```python
async def count_unsynced_events(self) -> int:
    """Return the count of events where synced_to_opencode = 0.

    Used as an idle suppression guard: if this returns 0, the sweep
    loop skips its work cycle entirely.
    """
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM events WHERE synced_to_opencode = 0"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
```
</action>

<acceptance_criteria>
- `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'count_unsynced_events')"` — method exists
- `python3 -c "from src.state_core.events import SqliteEventStore; import inspect; assert 'int' in inspect.signature(SqliteEventStore.count_unsynced_events).return_annotation"` — return int
- `grep -c "SELECT COUNT" src/state_core/events.py` returns exactly 1 match
</acceptance_criteria>

---

### Task A4 — Create src/state_core/reconciler.py — StartupReconciler class

<read_first>
- src/state_core/sync_mirror.py — SyncEventMirror.emit() contract (now returns bool)
- src/state_core/events.py — SqliteEventStore.get_unsynced_events(), .count_unsynced_events()
- CONTEXT.md — locked decisions on backoff constants, lifecycle, injection
- RESEARCH.md — risk areas: task lifecycle, race conditions, memory ceiling
</read_first>

<action>
Create src/state_core/reconciler.py with the full content below.

This module contains the StartupReconciler class with:
- Constructor: db, mirror, sweep_interval DI
- start(): immediate reconcile + periodic sweep loop
- stop(): cancel sweep task, clean exit
- _reconcile_once(): emit all unsent events, track failures
- _sweep_loop(): periodic retry with exponential backoff
- _compute_backoff_delay(): formula min(1.0 * 2.0^failures, 60.0)

**Sweep lifecycle (CLARIFIED):** After start(), the sweep loop runs INDEFINITELY with idle suppression:
- On each tick: query `count_unsynced_events()`
- If 0: `asyncio.sleep(sweep_interval)` and loop (no backoff, no warnings, no HTTP)
- If > 0: reconcile with exponential backoff
- stop() cancels the task regardless of state

This means new events arriving mid-session via Phase 005 are picked up within `sweep_interval` (default 60s). The sweep NEVER exits on its own — only start()/stop() control the lifecycle. This resolves the ambiguity in CONTEXT.md between "stop when all delivered" and "restarts on next periodic check."

Module-level constants: BACKOFF_INITIAL=1.0, BACKOFF_MULTIPLIER=2.0, BACKOFF_MAX=60.0, CONSECUTIVE_FAILURES_WARN_THRESHOLD=10

See the plan below for the exact source to write into the file.
</action>

<acceptance_criteria>
- `python3 -c "from src.state_core.reconciler import StartupReconciler, BACKOFF_INITIAL, BACKOFF_MULTIPLIER, BACKOFF_MAX, CONSECUTIVE_FAILURES_WARN_THRESHOLD"` — all exports import cleanly
- `python3 -c "from src.state_core.reconciler import StartupReconciler; import inspect; sig = inspect.signature(StartupReconciler.__init__); assert 'db' in sig.parameters and 'mirror' in sig.parameters and 'sweep_interval' in sig.parameters"`
- `python3 -c "from src.state_core.reconciler import StartupReconciler; assert hasattr(StartupReconciler, 'start') and hasattr(StartupReconciler, 'stop') and hasattr(StartupReconciler, '_reconcile_once') and hasattr(StartupReconciler, '_sweep_loop') and hasattr(StartupReconciler, '_compute_backoff_delay')"`
- No datetime.now() or random calls in reconciler.py (grep returns no match)
- ruff check src/state_core/reconciler.py passes
</acceptance_criteria>

---

## Plan B — Test Suite (Wave 2)

### Task B1 — Create tests/test_reconciler.py with comprehensive tests

<read_first>
- tests/test_sync_mirror.py — Existing test patterns: pytest fixtures, httpx_mock usage, MonkeyPatch pattern, _patch_opencode_url autouse fixture, _sync_replay_ok / _sync_replay_500 helpers
- src/state_core/migrations.py — migrate() function
- CONTEXT.md — locked decisions on lifecycle, backoff, guard behavior
</read_first>

<action>
Create tests/test_reconciler.py with the following test classes:

1. TestStartupReconciliation — happy path: emits all unsent events in seq order, sweep stops cleanly
2. TestIdleOnEmpty — no unsent events. start() creates sweep task but first idle check returns 0, no HTTP calls made. Sweep task stays alive (idle loop).
3. TestPeriodicSweep — opencode unreachable at startup, comes back, sweep delivers remaining
4. TestBackoffBehavior — validate exponential backoff formula, max cap, warning at 10 consecutive failures
5. TestPartialSuccess — mixed success/failure: first 3 succeed, last 2 fail. Assert first 3 are synced, last 2 remain unsent, AND `_consecutive_failures` resets to 0 after first batch succeeds (the partial success resets the backoff timer)
6. TestStopCancellation — stop() cancels sweep, events remain unsent, stop is idempotent
7. TestDoubleStart — second start() is no-op, same task reference
8. TestDeterminism — same events produce same emission order (seq 1, 2, 3)
9. TestIntegration — real mirror + pytest-httpx: HTTP body matches expected shape, synced flag set
10. TestManyEvents — 1000 events complete without error (functional check — memory ceiling verified at design-time in RESEARCH.md)
11. TestHypothesisReconciler — property-based: all events eventually synced or unsynced (never corrupted)

Fixtures:
- _patch_env (autouse): isolated DB path + pinned opencode URL + migration copy
- store: SqliteEventStore with migrations applied
- mirror: SyncEventMirror with isolated tmp_path directory
- _seed_events(): helper to insert N unsent events

See the plan below for the exact source to write into the file.
</action>

<acceptance_criteria>
- `python3 -m pytest tests/test_reconciler.py -v --tb=short` — all tests pass
- `python3 -m pytest tests/test_sync_mirror.py -v --tb=short` — existing tests still pass
- `python3 -m pytest tests/ -v --tb=short -x` — no regressions
- ruff check tests/test_reconciler.py passes
</acceptance_criteria>

---

## Verification

```bash
# 1. Run reconciler tests
python3 -m pytest tests/test_reconciler.py -v --tb=short

# 2. Run existing sync_mirror tests (backward compatibility of emit() return type)
python3 -m pytest tests/test_sync_mirror.py -v --tb=short

# 3. Run full test suite (no regressions)
python3 -m pytest tests/ -v --tb=short -x

# 4. Verify imports work
python3 -c "
from src.state_core.reconciler import StartupReconciler;
from src.state_core.events import SqliteEventStore;
from src.state_core.sync_mirror import SyncEventMirror;
print('All imports OK')
"

# 5. Lint
python3 -m ruff check src/state_core/reconciler.py src/state_core/sync_mirror.py src/state_core/events.py tests/test_reconciler.py

# 6. Verify emit() returns bool
python3 -c "
import inspect
from src.state_core.sync_mirror import SyncEventMirror
src = inspect.getsource(SyncEventMirror.emit)
assert 'return True' in src
assert 'return False' in src
print('emit() returns bool - verified')
"

# 7. Verify no datetime.now() or random in reconciler.py
python3 -c "
import ast
with open('src/state_core/reconciler.py') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
        if node.func.attr in ('now', 'utcnow', 'random'):
            raise AssertionError('Found non-deterministic call')
print('No non-deterministic calls - verified')
"
```

## Must-Haves

| # | Deliverable | Verification |
|---|-------------|--------------|
| 1 | SyncEventMirror.emit() returns bool | `grep -c "return True" src/state_core/sync_mirror.py` >= 1 AND `grep -c "return False" src/state_core/sync_mirror.py` >= 1 |
| 2 | SqliteEventStore.get_unsynced_events() method | `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'get_unsynced_events')"` |
| 3 | SqliteEventStore.count_unsynced_events() method | `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'count_unsynced_events')"` |
| 4 | src/state_core/reconciler.py exists | `test -f src/state_core/reconciler.py` |
| 5 | StartupReconciler has start()/stop() | `python3 -c "from src.state_core.reconciler import StartupReconciler; assert hasattr(StartupReconciler, 'start') and hasattr(StartupReconciler, 'stop')"` |
| 6 | Backoff: 1s initial, 2x multiplier, 60s max | Constants match in reconciler.py |
| 7 | Warning at 10 consecutive failures | Test `test_backoff_emits_warning_at_threshold` passes |
| 8 | Double-start guard | Test `test_double_start_is_noop` passes |
| 9 | Clean stop (events remain unsent) | Test `test_stop_cancels_sweep` passes |
| 10 | No datetime.now() or random in reconciler | `grep -c "datetime.now" src/state_core/reconciler.py` returns 0 AND `grep -c "random" src/state_core/reconciler.py` returns 0 |
| 11 | Existing tests still pass | `python3 -m pytest tests/ -x --tb=short` passes |
| 12 | Lint passes | `ruff check src/state_core/ tests/test_reconciler.py` passes |
