---
phase: 008-projector
reviewed: 2026-04-24T15:30:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/state_core/projector.py
  - src/state_cli/main.py
  - tests/test_projector.py
findings:
  critical: 0
  warning: 8
  info: 5
  total: 13
status: issues_found
---

# Phase 008: Code Review Report — Projection Engine

**Reviewed:** 2026-04-24T15:30:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the CQRS projection engine (663 LOC), CLI entry point (46 LOC), and test suite (895 LOC). The core projection logic is sound — handlers are pure functions, the rebuild/live-update duality is cleanly separated, transaction boundaries (BEGIN IMMEDIATE / COMMIT) are correct, and the crash-atomicity rollback works by design (SQLite auto-rollback on connection close).

Key concerns: the `Projector` stores a `SqliteEventStore` reference but never uses it (both methods bypass the EventStore entirely), `apply_event()` has a fragile data-type contract that would crash if called with a raw database row, and there's dead code (`_read_events`) and dead env var writes in the test suite. No CRITICAL/blocker issues found, but 8 WARNING-level issues should be addressed.

---

## Warnings

### WR-01: `Projector.__init__` stores `SqliteEventStore` but never uses it

**File:** `src/state_core/projector.py:433-434`
**Issue:** Both `rebuild_all()` (line 447) and `apply_event()` (line 597) open their own database connections via `get_connection()` and issue raw SQL directly against the `events` table. The `self._db` field is assigned in `__init__` but never read by any method. This means the `SqliteEventStore` constructor parameter is purely decorative.

This has two consequences:
1. The Projector is tightly coupled to the raw SQLite schema — if `SqliteEventStore` ever changes its storage layer (e.g., migrates to a different schema, adds caching, partitions tables), the Projector will silently go out of sync because it bypasses the EventStore entirely.
2. The `__init__` API is misleading — callers must provide an `SqliteEventStore` object for no reason.

**Fix:** Either (a) refactor `rebuild_all()` and `apply_event()` to query events through `self._db.read_stream()` or similar EventStore methods, or (b) remove the parameter entirely and make the Projector a stateless utility that always opens its own connection. Option (a) is preferred for abstraction integrity.

### WR-02: `apply_event()` doesn't deserialize the `data` field — fragile contract

**File:** `src/state_core/projector.py:595`
**Issue:** `apply_event()` extracts event data with `event_row.get("data", {})` and passes it directly to handler functions. But `rebuild_all()` (line 491-498) explicitly handles both JSON string and dict for the `data` field:

```python
raw_data = d.get("data", "{}")
if isinstance(raw_data, str):
    try:
        event_data: dict[str, Any] = json.loads(raw_data)
    except (json.JSONDecodeError, TypeError):
        event_data = {}
else:
    event_data = raw_data if isinstance(raw_data, dict) else {}
```

`apply_event()` omits this deserialization entirely. If a caller passes an event row directly from the database (where `data` is a JSON text column), the handlers would receive a string and crash with `AttributeError` on `data.get(...)`.

The docstring says "keys matching the events table columns" — but the `data` column in events tables stores JSON text, not a Python dict. The current callers (tests) always pass events from `store.read_stream()` which pre-deserializes the field, so this doesn't crash today. But it's a landmine for future callers.

**Fix:**
```python
# In apply_event(), replace line 595 with:
raw_data = event_row.get("data", {})
if isinstance(raw_data, str):
    try:
        event_data = json.loads(raw_data)
    except (json.JSONDecodeError, TypeError):
        event_data = {}
else:
    event_data = raw_data if isinstance(raw_data, dict) else {}
```

### WR-03: `_read_events()` is dead code

**File:** `src/state_core/projector.py:638-663`
**Issue:** The `_read_events()` method is defined but never called anywhere in the codebase (confirmed via grep). It duplicates the event-reading + data-deserialization logic already embedded in `rebuild_all()`. This is dead code that adds maintenance burden.

**Fix:** Either remove the method, or call it from `rebuild_all()` to deduplicate the event-reading logic. If retained for future use, document its intended caller.

### WR-04: Handlers are called synchronously — no `await` — async handlers would fail silently

**File:** `src/state_core/projector.py:28, 511, 620`
**Issue:** The `_HandlerFn` type alias and handler registry (`HANDLERS`) define handlers as synchronous callables:
```python
_HandlerFn: type = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]
```
Both call sites (line 511 in `rebuild_all()` and line 620 in `apply_event()`) invoke handlers without `await`:
```python
new_state = handler(current_state, event_data)
```

If an async handler were registered (returning a coroutine instead of a dict), this would silently return a coroutine object rather than executing the handler. The coroutine would then be used as a dict, likely causing attribute errors later, but the error would be confusing and far from the root cause. The type system provides no protection against this.

**Fix:** Either:
- Add an explicit assert/type guard before calling the handler:
  ```python
  result = handler(current_state, event_data)
  if hasattr(result, "__await__"):
      raise TypeError(f"Handler {event_type!r} must be synchronous, not async")
  new_state = result
  ```
- Or make the Projector support both sync and async handlers with `handler = HANDLERS.get(event_type); result = handler(current, data); if asyncio.iscoroutine(result): result = await result`.

### WR-05: `test_rebuild_deterministic` — dead env var write, no try/finally cleanup

**File:** `tests/test_projector.py:592-613`
**Issue:** Two problems in the same test:

1. **Line 592:** `os.environ["STATE_DB_PATH_B"] = str(db_path_b)` — the `_B` suffix env var is **never read**. It's set on line 592 and deleted on line 613, but no code ever reads `os.environ.get("STATE_DB_PATH_B")`. This is a debugging leftover.

2. **Lines 594-614:** The `STATE_DB_PATH` override and restore are not wrapped in `try/finally`. If any statement between line 594 (`os.environ["STATE_DB_PATH"] = ...`) and line 612 (`os.environ["STATE_DB_PATH"] = old_path`) raises an exception, the environment variable is left pointing to a temporary directory that `pytest` will clean up. Subsequent tests that use `get_connection()` would fail with opaque database errors.

**Fix:** Wrap the temp directory and env-var manipulation in `try/finally`:
```python
old_path = os.environ.get("STATE_DB_PATH", "")
try:
    os.environ["STATE_DB_PATH"] = str(db_path_b)
    # ... test body ...
finally:
    if old_path:
        os.environ["STATE_DB_PATH"] = old_path
    else:
        os.environ.pop("STATE_DB_PATH", None)
```
Also remove the dead `STATE_DB_PATH_B` write (lines 592, 613).

### WR-06: Hypothesis property test modifies `STATE_DB_PATH` without restoration

**File:** `tests/test_projector.py:798-840`
**Issue:** The `test_property_rebuild_no_side_effects` Hypothesis test overrides `STATE_DB_PATH` at line 809 but never restores the original value. Although `_isolate_db` (autouse, function-scoped) resets it before the next test, the stale value persists during the teardown window. If `_isolate_db` were ever removed or changed to session scope, this test would silently corrupt the database path for all subsequent tests.

Additionally, the `_isolate_db` fixture (autouse, function-scoped) runs once per Hypothesis-driven test function (not once per example), so the override persists across all 50 examples run by `@given`. This means all examples share the same database file, which violates test isolation — concurrent examples could race on the database.

**Fix:** Restore the original env var in a `try/finally` block within the test body, or better, use an `_isolate_db`-style fixture pattern that yields and cleans up:
```python
old_path = os.environ.get("STATE_DB_PATH", "")
os.environ["STATE_DB_PATH"] = str(db_path)
try:
    # ... test body ...
finally:
    if old_path:
        os.environ["STATE_DB_PATH"] = old_path
    else:
        os.environ.pop("STATE_DB_PATH", None)
```

### WR-07: `main.py` — Redundant local import of `SqliteEventStore`

**File:** `src/state_cli/main.py:40`
**Issue:** `SqliteEventStore` is imported locally inside `_do_rebuild_projections()`:
```python
async def _do_rebuild_projections() -> None:
    from src.state_core.events import SqliteEventStore
```

But `SqliteEventStore` is already imported transitively via the module-level `from src.state_core.projector import Projector as _Projector` (line 10), which itself imports `SqliteEventStore` at `projector.py:24`. (The `from __future__ import annotations` in `projector.py` does not suppress regular imports — only annotations.)

**Fix:** Move the import to module level for clarity:
```python
from src.state_core.events import SqliteEventStore
...
async def _do_rebuild_projections() -> None:
    await _migrate()
    store = SqliteEventStore()
    ...
```

### WR-08: `_HandlerFn` type alias is semantically incorrect

**File:** `src/state_core/projector.py:28`
**Issue:** `_HandlerFn: type = Callable[...]` declares a module variable `_HandlerFn` with type annotation `type` (i.e., `Type[Any]`). The value `Callable[...]` happens to be a `type` at runtime, so this doesn't crash. But type checkers (mypy, pyright) will treat `_HandlerFn` as `type` rather than as the specific callable signature `Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]`.

This means `HANDLERS: dict[str, _HandlerFn]` on line 34 is effectively `dict[str, type]` to type checkers, losing all value type information.

**Fix:**
```python
from collections.abc import Callable
from typing import TypeAlias

_HandlerFn: TypeAlias = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]
```

---

## Info

### IN-01: Handler field lookups use redundant defaults

**File:** `src/state_core/projector.py:88-94` (and all 19 handlers)
**Issue:** All handlers use the pattern `current.get("field", "") if current else ""`. When `current` is not None, the `""` default is never reached because the Projector always sets every field on lines 513 and 623 before writing to the database. The defaults are meaningless. This is harmless but adds noise to every handler.

### IN-02: `_CACHE_TABLES` lacks element type

**File:** `src/state_core/projector.py:31`
**Issue:** The type annotation `frozenset` would benefit from `frozenset[str]` for element-level type precision (Python 3.9+ syntax is available since the project targets 3.12+).

### IN-03: Step advanced handler returns empty string state when no `new_state`

**File:** `src/state_core/projector.py:180`
**Issue:** If `current` is None and `data` has no `new_state` key, the `state` field defaults to `""`:
```python
"state": data.get("new_state", current.get("state", "") if current else ""),
```
No crash, but an empty-string state is an invalid domain value. Consider raising a `ValueError` when `new_state` is required but absent.

### IN-04: `test_rebuild_multi_aggregate` — asymmetric assertion coverage

**File:** `tests/test_projector.py:492-519`
**Issue:** The test verifies `steps` state values and `slices` state but doesn't assert anything about the `concepts` row beyond existence (line 519: `assert len(concepts) == 1`). For completeness, consider asserting the state of the concept row as well.

### IN-05: `typer.Exit` chained with `from exc` prints confusing traceback

**File:** `src/state_cli/main.py:35`
**Issue:** `raise typer.Exit(code=1) from exc` chains the original exception, causing Python to print "During handling of the above exception, another exception occurred" in the traceback. For a CLI tool, the original exception details are useful for debugging but the traceback chain may confuse end users. Consider logging the original exception and raising `typer.Exit` without the `from` chain.

---

_Reviewed: 2026-04-24T15:30:00Z_
_Reviewer: AI (gsd-code-reviewer)_
_Depth: standard_
