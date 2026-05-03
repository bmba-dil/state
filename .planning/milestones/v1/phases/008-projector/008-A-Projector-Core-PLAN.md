---
phase: 008
plan: 1 of 3
type: auto
autonomous: true
wave: 1
depends_on: []
files_modified:
  - src/state_core/projector.py
requirements:
  - EVT-02
---

# Plan 1: Projector Core Module

<objective>
Create the `src/state_core/projector.py` module — a CQRS-style projection engine that rebuilds the `steps`, `slices`, and `concepts` cache tables from the authoritative `events` log. Delivers: handler registry with decorator-based registration, 19 pure projection handler functions (10 step + 4 slice + 5 concept), and the `Projector` class with `rebuild_all()` (full rebuild in single transaction) and `apply_event()` (live single-event update).

Follows the exact structural pattern of `src/state_core/reconciler.py`.
</objective>

<threat_model>
| Severity | Threat | Mitigation |
|----------|--------|------------|
| **HIGH** | Non-deterministic handlers violate EVT-06 — handlers calling `datetime.now()`, `random`, `uuid` would break replay idempotency | No imports of `datetime`, `random`, `uuid`, `time`, `secrets` in projector.py. Projection handlers receive only (current_state, event_data) — no access to clocks or RNG. CI-greppable: `grep -rn "datetime\.now\|random\.\|uuid\.\|time\.\|secrets\." src/state_core/projector.py` |
| **MEDIUM** | SQL injection via table name interpolation — `DELETE FROM {table}` with unvalidated input | Table names validated against hardcoded whitelist `_CACHE_TABLES: frozenset = frozenset({"steps", "slices", "concepts"})` before any SQL construction |
| **MEDIUM** | Partial cache state on mid-transaction crash | Single `BEGIN IMMEDIATE` + `COMMIT` wraps the entire rebuild. SQLite rollback on crash restores pre-rebuild state atomically. No two-phase approach needed — the transaction IS the safety net |
| **MEDIUM** | Out-of-order event replay produces inconsistent projections | Rebuild reads events ordered by `(aggregate_id, seq) ASC`. Per-aggregate seq is monotonically increasing (Phase 004/007 invariant). Handlers assume sequential replay |
| **LOW** | Handler registry silently misses new event types added in future phases | `HANDLERS.get(event_type)` returns `None` for unregistered types — silently skipped. This is correct future-proofing. Log a debug message when skipping |
</threat_model>

<tasks>

### Task 1: Module skeleton + handler registry pattern

<read_first>
- src/state_core/reconciler.py (full file — structural analog)
- src/state_core/events.py lines 152-185 (BEGIN IMMEDIATE + COMMIT pattern)
- src/state_core/database.py lines 39-55 (get_connection factory)
</read_first>

<action>
Create `src/state_core/projector.py` with:

1. **Module docstring** (triple-quoted, describes CQRS projection engine, handler registry, live/rebuild modes, three cache tables)

2. **Imports** (in this exact order):
   ```python
   from __future__ import annotations

   import json
   from collections.abc import Callable
   from typing import Any

   import structlog

   from src.state_core.database import get_connection
   from src.state_core.events import SqliteEventStore

   log = structlog.get_logger(__name__)
   ```

3. **Constants:**
   ```python
   _HandlerFn: type = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]
   """Handler signature: (current_state_or_None, event_data_dict) -> new_state_dict."""

   _CACHE_TABLES: frozenset = frozenset({"steps", "slices", "concepts"})
   """Whitelist of cache table names — validated before any SQL interpolation."""

   HANDLERS: dict[str, _HandlerFn] = {}
   """Event-type-to-handler registry. Populated by @_register_handler decorator."""
   ```

4. **`_register_handler(event_type: str)` decorator:**
   ```python
   def _register_handler(event_type: str) -> Callable[[_HandlerFn], _HandlerFn]:
       """Decorator that registers a projection handler for *event_type*."""
       def decorator(fn: _HandlerFn) -> _HandlerFn:
           HANDLERS[event_type] = fn
           return fn
       return decorator
   ```

5. **`_validate_table(name: str) -> str` helper:**
   ```python
   def _validate_table(name: str) -> str:
       """Validate *name* is a known cache table; raise ValueError if not."""
       if name not in _CACHE_TABLES:
           raise ValueError(f"Unknown cache table: {name!r}. Expected one of {_CACHE_TABLES}")
       return name
   ```
</action>

<acceptance_criteria>
- File `src/state_core/projector.py` exists
- `grep -c "HANDLERS" src/state_core/projector.py` returns >= 1
- `grep -c "_HandlerFn" src/state_core/projector.py` returns >= 1
- `grep -c "_register_handler" src/state_core/projector.py` returns >= 1
- `grep -c "_validate_table" src/state_core/projector.py` returns >= 1
- `grep -c "from __future__ import annotations" src/state_core/projector.py` returns 1
- No imports of `datetime`, `random`, `uuid`, `time`, or `secrets` in the file
- `python3 -c "import ast; ast.parse(open('src/state_core/projector.py').read())"` exits 0
</acceptance_criteria>

---

### Task 2: Projection handler functions for steps, slices, and concepts

<read_first>
- src/state_core/projector.py (file created in Task 1 — must read before adding handlers)
- src/state_core/schema.py lines 217-297 (event data payload models — determines what fields each handler can access)
- .state/migrations/0002_cache.sql (cache table schemas — determines what columns each handler must produce)
</read_first>

<action>
Add the following handler functions AFTER the registry pattern and BEFORE the Projector class. Every handler:
- Accepts `(current: dict[str, Any] | None, data: dict[str, Any]) -> dict[str, Any]`
- Returns a complete row dict matching the corresponding cache table schema
- Uses `current` as base when not None (accumulated state from prior events)
- Uses `data` (the event payload) to update relevant fields
- Never calls `datetime.*`, `random.*`, `uuid.*`, `time.*`, or `secrets.*`
- Serializes complex values (e.g. `verify_contract`) with `json.dumps(..., sort_keys=True, separators=(",", ":"))`

**Step handlers** (10 handlers, all registered to `state.step.*` event types):

| Handler | Event Type | State Transition | Key Data Fields |
|---------|-----------|-----------------|-----------------|
| `_handle_step_discussed` | `state.step.discussed` | state → `"discussing"` | `slice_id`, `title` (from `approach_summary`) |
| `_handle_step_planned` | `state.step.planned` | state → `"planning"` | `goal`, `verify_contract` |
| `_handle_step_executed` | `state.step.executed` | state → `"executing"` | `changes_summary` |
| `_handle_step_verify_started` | `state.step.verify_started` | state → `"verifying"` | (none — state only) |
| `_handle_step_verify_passed` | `state.step.verify_passed` | state → `"done"` | `duration_ms` |
| `_handle_step_verify_failed` | `state.step.verify_failed` | state → `"executing"` | `reason`, `details` |
| `_handle_step_advanced` | `state.step.advanced` | state → `data["new_state"]` | `new_state` |
| `_handle_step_blocked` | `state.step.blocked` | state → `"blocked"` | `reason` |
| `_handle_step_snapshotted` | `state.step.snapshotted` | state unchanged | `snapshot_hash`, `tier` |
| `_handle_step_reverted` | `state.step.reverted` | previous state | `snapshot_hash`, `reason` |

Each step handler returns a dict with at least these keys (matching `steps` table schema):
```python
{
    "id": str,           # aggregate_id
    "slice_id": str,     # from data or current
    "state": str,        # new state literal
    "title": str,        # from data or current
    "frontmatter": str,  # JSON — merged data dict on top of current frontmatter
    "updated_at": str,   # ISO 8601 — uses current.get("updated_at", ...)
}
```

The `frontmatter` field is built by accumulating event data payloads: parse `current.get("frontmatter", "{}")` as JSON, merge with new `data` keys, re-serialize deterministically.

**Slice handlers** (4 handlers, registered to `state.slice.*` event types):

| Handler | Event Type | State Transition | Key Data Fields |
|---------|-----------|-----------------|-----------------|
| `_handle_slice_planned` | `state.slice.planned` | state → `"planned"` | `phase_id`, `title`, `goal` |
| `_handle_slice_worktree_ready` | `state.slice.worktree_ready` | state → `"in_progress"` | `worktree_name`, `branch`, `dir` |
| `_handle_slice_shipped` | `state.slice.shipped` | state → `"shipped"` | `snapshot_hash` |
| `_handle_slice_reverted` | `state.slice.reverted` | state → `"reverted"` | `reason` |

Each slice handler returns a dict with keys matching `slices` table:
```python
{
    "id": str,
    "phase_id": str,
    "state": str,
    "worktree_dir": str | None,
    "worktree_branch": str | None,
    "frontmatter": str,  # JSON
    "updated_at": str,
}
```

**Concept handlers** (5 handlers, registered to `state.concept.*` event types):

| Handler | Event Type | State Transition | Key Data Fields |
|---------|-----------|-----------------|-----------------|
| `_handle_concept_introduced` | `state.concept.introduced` | state → `"introduced"` | `subject_id`, `name`, `prerequisites` |
| `_handle_concept_observed` | `state.concept.observed` | state → `"observed"` | `observation`, `classification` |
| `_handle_concept_drilled` | `state.concept.drilled` | state → `"drilled"` | `score`, `items_attempted` → `mastery_probability`, `scaffold_level` |
| `_handle_concept_mastered` | `state.concept.mastered` | state → `"mastered"` | `mastery_probability` |
| `_handle_concept_reviewed` | `state.concept.reviewed` | state → `"reviewed"` | `mastery_delta` |

Each concept handler returns a dict with keys matching `concepts` table:
```python
{
    "id": str,
    "subject_id": str,
    "learner_id": str,
    "mastery_probability": float,
    "scaffold_level": int,
    "bloom_level": str,
    "frontmatter": str,  # JSON
    "last_drilled_at": str | None,
    "updated_at": str,
}
```
</action>

<acceptance_criteria>
- `grep -c "_handle_step_" src/state_core/projector.py` returns 10
- `grep -c "_handle_slice_" src/state_core/projector.py` returns 4
- `grep -c "_handle_concept_" src/state_core/projector.py` returns 5
- `grep -c "@_register_handler" src/state_core/projector.py` returns 19
- `grep -c "state\.step\." src/state_core/projector.py` returns >= 10
- `grep -c "state\.slice\." src/state_core/projector.py` returns 4
- `grep -c "state\.concept\." src/state_core/projector.py` returns 5
- `python3 -c "import ast; ast.parse(open('src/state_core/projector.py').read())"` exits 0
- No imports of `datetime`, `random`, `uuid`, `time`, or `secrets` — confirmed by grep (0 matches)
</acceptance_criteria>

---

### Task 3: Projector class with rebuild_all() and apply_event()

<read_first>
- src/state_core/projector.py (file from Tasks 1-2)
- src/state_core/events.py lines 152-185 (BEGIN IMMEDIATE + COMMIT pattern for rebuild_all)
- src/state_core/events.py lines 274-322 (repair_aggregate_seqs — transaction pattern analog)
- src/state_core/events.py lines 201-225 (read_stream — Row factory + JSON deserialization pattern)
</read_first>

<action>
Add the `Projector` class at the end of `projector.py`.

**Class definition:**
```python
class Projector:
    """Orchestrates projection rebuilds and live updates.

    Two modes:
    1. **Rebuild** — ``rebuild_all()`` truncates cache tables and replays
       ALL events from the ``events`` table in aggregate+seq order.
    2. **Live** — ``apply_event()`` updates a single projection row after
       an event has been appended (same-transaction call).

    Args:
        db: The event store for reading events.
    """

    def __init__(self, db: SqliteEventStore) -> None:
        self._db = db
```

**`async def rebuild_all(self) -> int` method:**
- Opens a connection via `get_connection()` (NOT the EventStore's connection)
- Sets `PRAGMA synchronous=FULL` (belt-and-suspenders)
- Executes `BEGIN IMMEDIATE`
- For each table in `("steps", "slices", "concepts")`: validates via `_validate_table()`, then `DELETE FROM <table>`
- Reads ALL events ordered by `(aggregate_id, seq) ASC` with columns: `id, seq, aggregate_type, aggregate_id, type, data, ts, mode`
- Uses `db.row_factory = aiosqlite.Row`
- Fetches all rows via `cursor.fetchall()`
- Maintains in-memory `state: dict[str, dict[str, Any]]` keyed by aggregate_id
- For each row: deserializes `data` column (JSON string → dict), routes to handler via `HANDLERS.get(type)` (skips unknown types with debug log), accumulates state in the in-memory dict
- After all rows are processed, groups accumulated states by table:
  - Key prefix check: aggregate types `"step"` → `"steps"`, `"slice"` → `"slices"`, `"concept"` → `"concepts"`
  - For each aggregate's final state, builds `INSERT OR REPLACE` SQL with the cache table columns
- Executes all upserts
- Logs summary: `log.info("rebuild_complete", events_processed=N, steps=N, slices=N, concepts=N)`
- Commits via `await db.commit()`
- Returns the number of events processed

**`async def apply_event(self, event_row: dict) -> None` method:**
- Called after `EventStore.append()` to keep projections in sync (live mode)
- Takes a single event row dict (from the event store's read interface)
- Routes to the handler via `HANDLERS.get(event_row["type"])`
- If no handler registered, returns immediately (silent skip)
- Determines the cache table from `event_row["aggregate_type"]`:
  - `"step"` → `"steps"`, `"slice"` → `"slices"`, `"concept"` → `"concepts"`
  - Other aggregate types → silently return (no cache table for arcs, phases, etc.)
- Opens a connection, `BEGIN IMMEDIATE`
- SELECTs the current row for this aggregate_id from the cache table (to get prior state)
- If row exists: parses `frontmatter` JSON, passes as `current` dict to handler
- If row doesn't exist: passes `None` as current state
- Calls handler with `(current_state, event_row["data"])` → `new_state`
- Sets `new_state["id"] = event_row["aggregate_id"]` and `new_state["updated_at"] = event_row.get("ts", ...)`
- Builds and executes `INSERT OR REPLACE` with all columns
- Commits

**`async def _read_events(self) -> list[dict[str, Any]]` helper method** (private, used by rebuild_all):
- Opens a connection, reads all events ordered by `(aggregate_id, seq) ASC`
- Returns list of dicts with `data` field deserialized from JSON

**Transaction isolation rules:**
- `rebuild_all()` opens its OWN connection via `get_connection()`, not through `self._db`
- `apply_event()` opens its own connection too
- Never calls `self._db.append()` — projector is read-only from the event store's perspective
- Never acquires the EventStore's internal connection/lock
</action>

<acceptance_criteria>
- `grep -c "class Projector" src/state_core/projector.py` returns 1
- `grep -c "def rebuild_all" src/state_core/projector.py` returns 1
- `grep -c "def apply_event" src/state_core/projector.py` returns 1
- `grep -c "BEGIN IMMEDIATE" src/state_core/projector.py` returns >= 1
- `grep -c "COMMIT" src/state_core/projector.py` returns >= 1
- `grep -c "INSERT OR REPLACE" src/state_core/projector.py` returns >= 1
- `grep -c "_validate_table" src/state_core/projector.py` returns >= 3 (one per table)
- `python3 -c "from src.state_core.projector import Projector, HANDLERS; print(f'{len(HANDLERS)} handlers')"` outputs "19 handlers"
- `python3 -c "from src.state_core.projector import Projector; print(Projector); print('OK')"` exits 0
- `python3 -c "import ast; ast.parse(open('src/state_core/projector.py').read())"` exits 0
</acceptance_criteria>

</tasks>

<verification>
1. **Import check:** `python3 -c "from src.state_core.projector import Projector, HANDLERS, _register_handler; print(f'OK: {len(HANDLERS)} handlers')"` must print `OK: 19 handlers` and exit 0.
2. **Syntax check:** `python3 -c "import ast; ast.parse(open('src/state_core/projector.py').read())"` exits 0.
3. **Determinism check:** `grep -rn "datetime\.now\|random\.\|uuid\.\|time\.\|secrets\." src/state_core/projector.py` returns 0 matches.
4. **Table whitelist check:** Every SQL table reference goes through `_validate_table` — no raw f-string interpolation of table names without validation.
5. **Transaction discipline:** Both `rebuild_all()` and `apply_event()` use `BEGIN IMMEDIATE` + `COMMIT` wrapping all writes.
</verification>

<must_haves>
- [x] `src/state_core/projector.py` exists with `class Projector`
- [x] `HANDLERS` dict populated with exactly 19 handlers (10 step + 4 slice + 5 concept)
- [x] `_register_handler` decorator pattern works
- [x] `_validate_table` whitelist guards all SQL table name interpolation
- [x] `rebuild_all()`: single `BEGIN IMMEDIATE`...`COMMIT` transaction, DELETE + replay + INSERT OR REPLACE
- [x] `apply_event()`: single event upsert for live post-append updates
- [x] Unknown event types silently ignored (no crash, no error)
- [x] No non-deterministic imports (datetime.now, random, uuid, time, secrets)
- [x] All event payload fields mapped to cache table columns per the event→projection mapping table
</must_haves>
