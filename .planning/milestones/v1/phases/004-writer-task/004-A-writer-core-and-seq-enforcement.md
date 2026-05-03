---
phase: "004"
plan: "A"
type: "auto"
autonomous: false
wave: 1
depends_on:
  - "Phase 002 (schema.py event models)"
  - "Phase 003 (database.py, migrations.py, aggregate_seq table)"
files_modified:
  - "src/state_core/events.py"
  - ".state/migrations/0003_add_mode_column.sql"
requirements:
  - "EVT-01"
  - "EVT-02"
  - "EVT-03"
  - "EVT-06"
---

<objective>
Implement `SqliteEventStore.append()` with per-aggregate seq enforcement, deterministic clock injection, and JSON serialization. Deliver the core writer that establishes commit-then-return semantics — SQLite is authoritative, events are durable before any notification. This is the final piece completing the base EventStore contract started in Phase 003.

By the end of this plan, `EventStore.append()` will:
- Accept `aggregate_type`, `aggregate_id`, `event_type`, `data`, and optional `mode`, `ts`, `id_`
- Generate a ULID (or accept one for testing)
- Read/increment aggregate sequence from `aggregate_seq` table
- Serialize data dict to deterministic JSON
- Write event row + upsert aggregate_seq in a single transaction
- Return the event ID string
</objective>

<tasks>

## Task 1 — Create migration 0003 to add mode column to events table

<read_first>
  .state/migrations/0001_init.sql (existing events table schema — note: no mode column)
  .state/migrations/0002_cache.sql (existing cache tables)
  src/state_core/migrations.py (how migrations are discovered and applied)
</read_first>

<action>

Create `.state/migrations/0003_add_mode_column.sql`:

```sql
-- 0003_add_mode_column: Add mode column to events table
-- The mode field ('kernel' | 'build' | 'teach' | 'both') supports
-- mode-scoped event filtering. Default is 'kernel'.
-- This migration is additive (ALTER TABLE ADD COLUMN) and safe to
-- apply on existing databases that already have 0001 and 0002 applied.

ALTER TABLE events ADD COLUMN mode TEXT NOT NULL DEFAULT 'kernel';

-- Update the event-by-aggregate index to include mode
-- (drop + recreate to change the column coverage)
DROP INDEX IF EXISTS idx_events_agg;
CREATE INDEX IF NOT EXISTS idx_events_agg ON events(aggregate_id, seq);
```

Key constraints:
- `mode TEXT NOT NULL DEFAULT 'kernel'` — matches schema.py EventEnvelope default
- `ALTER TABLE ADD COLUMN` is non-destructive — existing rows get `'kernel'` default
- Existing indexes are preserved (DROP + CREATE same index is a no-op for coverage; index already covers seq)
- The migration file is discovered by `migrate()` automatically (sorted glob `[0-9]*.sql`)
- Run `python3 -m pytest tests/test_migrations.py -x -q` after creation to verify no regression
</action>

<acceptance_criteria>
- ✗ `.state/migrations/0003_add_mode_column.sql` exists with the ALTER TABLE statement
- ✗ Migration files sorted order: 0001, 0002, then 0003
- ✗ Running `migrate()` on a fresh database creates `events` with `mode` column
- ✗ Running `migrate()` on an existing database (0001+0002 applied) applies 0003 without error
- ✗ `PRAGMA table_info(events)` after full migration shows `mode` column with type TEXT, notnull=1, default='kernel'
- ✗ No regression in test_migrations.py (checksums of 0001, 0002 remain valid)
</acceptance_criteria>

## Task 2 — Update `EventStore` protocol with optional parameters

<read_first>
  src/state_core/events.py (full file — read the existing EventStore protocol and SqliteEventStore stub)
  src/state_core/schema.py (Mode type, EventEnvelope constraints)
</read_first>

<action>
1. In `src/state_core/events.py`, update the `EventStore` protocol class to extend the `append()` signature:

```python
async def append(
    self,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    data: dict[str, Any],
    *,
    mode: str = "kernel",
    ts: str | None = None,
    id_: str | None = None,
) -> str: ...
```

Key constraints:
- `mode` defaults to `"kernel"` (matching `EventEnvelope` default in schema.py)
- `ts` defaults to `None` — NOT `datetime.now()` (enforces EVT-06 determinism)
- `id_` defaults to `None` — generates ULID when None, uses value when provided (test injection)
- `mode` and `ts` and `id_` are keyword-only (after `*`) — keeps positional interface clean
- Return type is `str` (the event ID)
- Parameters `aggregate_type`, `aggregate_id`, `event_type`, `data` remain positional
</action>

<acceptance_criteria>
- ✗ `EventStore` protocol `append()` signature includes `mode`, `ts`, `id_` keyword-only params
- ✗ All params after `data` are keyword-only
- ✗ `mode` defaults to `"kernel"`
- ✗ `ts` defaults to `None`
- ✗ `id_` defaults to `None`
- ✗ Return type annotation is `-> str`
- ✗ Protocol still passes `mypy --strict` protocol checks (structural subtyping)
</acceptance_criteria>

## Task 3 — Implement `SqliteEventStore.append()` with seq enforcement

<read_first>
  src/state_core/events.py (full file — current stub implementation)
  src/state_core/database.py (get_connection factory)
  src/state_core/migrations.py (schema includes aggregate_seq table)
  src/state_core/schema.py (Mode type for reference)
</read_first>

<action>

Implement the real `append()` method on `SqliteEventStore`. Replace the existing `raise NotImplementedError()` stub.

The implementation follows this flow (all inside a single `async with get_connection() as db:`):

```python
from ulid import ULID
import json

async def append(
    self,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    data: dict[str, Any],
    *,
    mode: str = "kernel",
    ts: str | None = None,
    id_: str | None = None,
) -> str:
    # 1. Generate or use provided ULID
    event_id = id_ if id_ is not None else str(ULID())

    # 2. Serialize data to deterministic JSON
    data_json = json.dumps(data, sort_keys=True, separators=(",", ":"))

    # 3. Determine timestamp: use provided or empty string (not datetime.now!)
    timestamp = ts if ts is not None else ""

    async with get_connection() as db:
        # 4. Read current aggregate sequence
        cursor = await db.execute(
            "SELECT seq FROM aggregate_seq WHERE aggregate_id = ?",
            (aggregate_id,),
        )
        row = await cursor.fetchone()
        current_seq = row[0] if row else 0

        # 5. Increment sequence (first event gets seq 1)
        new_seq = current_seq + 1

        # 6. Insert the event row (mode column exists after 0003 migration)
        await db.execute(
            "INSERT INTO events "
            "(id, seq, aggregate_type, aggregate_id, type, data, ts, mode, synced_to_opencode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (
                event_id,
                new_seq,
                aggregate_type,
                aggregate_id,
                event_type,
                data_json,
                timestamp,
                mode,
            ),
        )

        # 7. Upsert aggregate_seq
        from datetime import datetime, timezone
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        await db.execute(
            "INSERT OR REPLACE INTO aggregate_seq (aggregate_id, seq, updated_at) "
            "VALUES (?, ?, ?)",
            (aggregate_id, new_seq, now_ts),
        )

        # 8. Commit transaction explicitly
        await db.commit()

    # 9. Return event ID
    return event_id
```

**Critical constraints (enforce EVT-06 determinism):**
- `ts` parameter defaults to `""` (empty string) when caller does not provide it — NEVER `datetime.now()`
- The `datetime.now()` call in step 7 for `aggregate_seq.updated_at` is acceptable because: (a) it's metadata, not event data; (b) `aggregate_seq` is a derived cache table, not authoritative event data; (c) the `updated_at` is not part of any projection or replay. **However**, to be safe, use `""` (empty string) for `updated_at` too, since this value is not consumed anywhere. This eliminates the `datetime.now()` call entirely.
- `id_` defaults to `None` — generates new ULID when not provided; `None` is NOT a valid ULID overrride

**Updated step 7 (no datetime):**

```python
await db.execute(
    "INSERT OR REPLACE INTO aggregate_seq (aggregate_id, seq, updated_at) "
    "VALUES (?, ?, ?)",
    (aggregate_id, new_seq, ""),
)
```

**Additional constraints:**
- All imports inside the function body or at top of file
- Use `json.dumps(data, sort_keys=True, separators=(",", ":"))` for deterministic serialization
- `synced_to_opencode` defaults to `0` (Phase 005 handles mirroring)
- No `await db.commit()` between step 6 and step 7 — they share one transaction
- The `async with get_connection()` context manager handles rollback on exception
</action>

<acceptance_criteria>
- ✗ `SqliteEventStore.append()` is implemented (no `NotImplementedError`)
- ✗ Appending a first event to an aggregate yields `seq=1`
- ✗ Appending a second event to the same aggregate yields `seq=2`
- ✗ Appending to different aggregates yields independent seq numbers
- ✗ Passing explicit `id_="01ARZ3NDEKTSV4RRFFQ69G5FAV"` stores that exact ULID
- ✗ Passing explicit `ts="2026-04-23T00:00:00Z"` stores that exact timestamp
- ✗ Not passing `ts` stores `""` (empty string)
- ✗ Data is serialized as sorted-key, compact JSON
- ✗ Return value matches the stored event `id`
- ✗ `aggregate_seq` row exists with correct seq and empty `updated_at` after append
- ✗ No `datetime.now()` call exists in the append path (grep: `datetime.now` returns 0 matches in append)
- ✗ No call to `random` module in `events.py`
- ✗ `synced_to_opencode` is `0` for every appended event
</acceptance_criteria>

## Task 4 — Update `read_stream()` to include mode in SELECT and deserialize JSON data

<read_first>
  src/state_core/events.py (read_stream method)
</read_first>

<action>

Update `read_stream()` to deserialize the `data` column from JSON text back to a dict when yielding rows. Currently it yields raw dicts from `aiosqlite.Row` — the `data` column is TEXT but callers expect `dict`.

Also include `mode` in the SELECT list (it was missing from the Phase 003 stub).

Modify the query and yield inside `read_stream()`:

```python
import json  # already at top of file after Task 3

# Update the SQL to include mode:
cursor = await db.execute(
    "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode, synced_to_opencode "
    "FROM events "
    "WHERE aggregate_id = ? AND seq > ? "
    "ORDER BY seq ASC",
    (aggregate_id, after_seq),
)

# Then deserialize data from JSON text to dict:
for row in rows:
    result = dict(row)
    if isinstance(result.get("data"), str):
        result["data"] = json.loads(result["data"])
    yield result
```

This ensures:
- `mode` column is included in the returned dict
- `data` is deserialized from JSON text back to dict
- Round-trip `append()` → `read_stream()` returns identical data dict
</action>

<acceptance_criteria>
- ✗ `read_stream()` yields dicts where `data` is a Python `dict` (not a JSON string)
- ✗ `read_stream()` yields dicts that include `mode` key
- ✗ A round-trip `append()` → `read_stream()` returns identical `data` dict
- ✗ A round-trip preserves the `mode` value
- ✗ Existing tests for `read_stream()` still pass (no regression)
- ✗ The `data` column in `events` table remains TEXT (the deserialization is at the application layer)
</acceptance_criteria>

## Task 5 — Update module docstring and clean up imports

<read_first>
  src/state_core/events.py (full file)
</read_first>

<action>

1. Update the module-level docstring to reflect that Phase 004 delivers the complete append() implementation with seq enforcement and deterministic clock.

2. Ensure all imports are clean:
   - Add `import json` at top level
   - Add `from ulid import ULID` at top level
   - Remove any unused imports
   - Remove the `from src.state_core.database import get_connection` if it was only imported for the stub — keep it as it's used by `read_stream()` and now `append()`

3. Ensure `from __future__ import annotations` is present at the top.
</action>

<acceptance_criteria>
- ✗ Module docstring references seq enforcement, deterministic clock, and single-transaction commit pattern
- ✗ `from __future__ import annotations` is present
- ✗ All imports are used (no dead imports)
- ✗ `json` and `ULID` imports are present
</acceptance_criteria>

</tasks>

<verification>
How to confirm this plan is complete:

1. Run `python3 -m pytest tests/ -x -q` — all existing tests pass (no regression)
2. Run a manual round-trip check:
   ```python
   import asyncio, json
   from src.state_core.database import get_connection
   from src.state_core.events import SqliteEventStore
   from src.state_core.migrations import migrate
   
   async def check():
       await migrate()
       store = SqliteEventStore()
       eid = await store.append("step", "step-01", "state.step.executed", {"changes_summary": "test"}, mode="build")
       print(f"Event ID: {eid}")
       async for evt in store.read_stream("step-01"):
           print(f"Seq: {evt['seq']}, Data: {json.dumps(evt['data'])}")
       eid2 = await store.append("step", "step-01", "state.step.verify_passed", {"duration_ms": 100}, mode="build")
       print(f"Event ID 2: {eid2}")
       async for evt in store.read_stream("step-01"):
           print(f"Seq: {evt['seq']}, Data: {evt['data']}")
   
   asyncio.run(check())
   ```
   Expected output: first event seq=1, second event seq=2, data fields are dicts not JSON strings.

3. Grep `events.py` for `datetime.now` — must return 0 matches.
4. Grep `events.py` for `raise NotImplementedError` — the `append()` method must not raise.
5. Run `python3 -m pytest tests/test_imports.py -x -q` — import test passes.
</verification>

<must_haves>
- Working `SqliteEventStore.append()` with seq enforcement
- `EventStore` protocol updated with optional `mode`, `ts`, `id_` params
- Deterministic JSON serialization (`sort_keys=True, separators=(",", ":")`)
- No `datetime.now()` or randomness in event-store code
- `read_stream()` returns dict data (not JSON string)
- All existing tests continue to pass
- Single commit per append — no auto-commit reliance
</must_haves>
