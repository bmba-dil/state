---
phase: 009
plan: A
type: auto
autonomous: true
wave: 1
depends_on: []
files_modified:
  - .state/migrations/0005_add_events_id_index.sql
  - src/state_core/events.py
requirements:
  - EVT-07
  - EVT-08
---

<objective>
Add migration 0005 (index on events.id ASC) and four global-read methods to SqliteEventStore: `read_events()`, `read_events_iter()`, `count_events()`, `get_last_events()`. These are the foundation for the CLI tail/replay/export commands.
</objective>

---

## Task 1: Create migration 0005 — index on events(id ASC)

<read_first>
- .state/migrations/0004_add_unique_agg_seq.sql (existing migration, follow exact header/format pattern)
</read_first>

<action>
Create file `.state/migrations/0005_add_events_id_index.sql` with:

```sql
-- 0005_add_events_id_index: Support ULID-offset queries for CLI tail/replay/export
-- Applied by MigrationRunner after 0004_add_unique_agg_seq.sql.

CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC);
```

The file must:
- Start with `-- 0005_add_events_id_index:` description on line 1
- Include `Applied by MigrationRunner after 0004` comment on line 2
- Use `CREATE INDEX IF NOT EXISTS` (safe for re-runs)
- End with a single trailing newline
- Use lowercase column names matching the existing events table schema
</action>

<acceptance_criteria>
1. File `.state/migrations/0005_add_events_id_index.sql` exists
2. `grep -c "CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC)" .state/migrations/0005_add_events_id_index.sql` returns 1
3. The migration runner (`src/state_core/migrations.py`) can discover and apply the file — confirmed by running `python3 -c "import asyncio; from src.state_core.migrations import migrate; asyncio.run(migrate())"` without error
4. The index exists after migration: `python3 -c "import aiosqlite, asyncio; from src.state_core.database import get_connection; async def check(): async with get_connection() as db: cur=await db.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_events_id'\"); r=await cur.fetchone(); print(r[0] if r else 'MISSING'); asyncio.run(check())"` prints `idx_events_id`
</acceptance_criteria>

---

## Task 2: Add `read_events()` and `read_events_iter()` to SqliteEventStore

<read_first>
- src/state_core/events.py (existing methods: read_stream, get_unsynced_events, count_unsynced_events — follow exact patterns for connection management, row_factory, data deserialization)
- .planning/milestones/v1/phases/009-cli-state-events-tail-replay/009-RESEARCH.md (signatures and SQL patterns)
</read_first>

<action>
Add TWO methods to the `SqliteEventStore` class in `src/state_core/events.py`, inserted after the `count_unsynced_events()` method (line 339) and before any closing:

**Method 1 — `read_events()`:**

```python
async def read_events(
    self,
    *,
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Read events with optional ULID offset, mode filter, and limit.

    Ordered by id ASC (lexicographic = chronological for ULIDs).
    Deserializes the *data* column from JSON text to a Python dict.

    Args:
        from_id: ULID offset (exclusive lower bound). Events with id > from_id.
        to_id: ULID offset (exclusive upper bound). Events with id < to_id.
        mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.
        limit: Max rows. 0 = no limit.

    Returns:
        List of event row dicts with keys: id, seq, aggregate_type,
        aggregate_id, type, data (deserialized), ts, mode.
    """
    await self._maybe_repair(source="read_events")

    clauses: list[str] = [
        "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
        "FROM events WHERE 1=1"
    ]
    params: list[Any] = []

    if from_id is not None:
        clauses.append("AND id > ?")
        params.append(from_id)
    if to_id is not None:
        clauses.append("AND id < ?")
        params.append(to_id)
    if mode is not None:
        clauses.append("AND mode = ?")
        params.append(mode)

    clauses.append("ORDER BY id ASC")

    if limit > 0:
        clauses.append("LIMIT ?")
        params.append(limit)

    sql = " ".join(clauses)

    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                d["data"] = json.loads(d["data"])
            result.append(d)
        return result
```

**Method 2 — `read_events_iter()`:**

```python
async def read_events_iter(
    self,
    *,
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Read events as an async generator — memory-safe for large volumes.

    Ordered by id ASC (lexicographic = chronological for ULIDs).
    Deserializes *data* from JSON text to a Python dict per row.

    Args:
        from_id: ULID offset (exclusive lower bound).
        to_id: ULID offset (exclusive upper bound).
        mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.
    """
    await self._maybe_repair(source="read_events_iter")

    clauses: list[str] = [
        "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
        "FROM events WHERE 1=1"
    ]
    params: list[Any] = []

    if from_id is not None:
        clauses.append("AND id > ?")
        params.append(from_id)
    if to_id is not None:
        clauses.append("AND id < ?")
        params.append(to_id)
    if mode is not None:
        clauses.append("AND mode = ?")
        params.append(mode)

    clauses.append("ORDER BY id ASC")
    sql = " ".join(clauses)

    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        while True:
            row = await cursor.fetchone()
            if row is None:
                break
            d = dict(row)
            if isinstance(d.get("data"), str):
                d["data"] = json.loads(d["data"])
            yield d
```

Key patterns the executor MUST follow:
- Use `await self._maybe_repair(source="method_name")` on entry (matching existing methods)
- Use `get_connection()` context manager (not direct aiosqlite)
- Set `db.row_factory = aiosqlite.Row` before queries
- Deserialize `data` column from JSON string to dict
- Use `" ".join(clauses)` approach for dynamic SQL with parameterized params (NO string interpolation of user values)
- Return type annotation must match `from typing import Any` (already imported) and `from collections.abc import AsyncIterator` (already imported)
</action>

<acceptance_criteria>
1. `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'read_events'); assert hasattr(SqliteEventStore, 'read_events_iter'); print('OK')"` prints `OK`
2. After appending 3 events with ULIDs, `read_events(from_id=first_id)` returns exactly 2 events (the ones after first_id)
3. `read_events(mode="build")` returns only events with mode='build'
4. `read_events(limit=1)` returns exactly 1 event
5. `read_events_iter()` yields all events when iterated with `async for`
6. All data dict values have deserialized `data` field (Python dict, not JSON string)
7. `grep -c "\.execute\(.*%\|\.execute\(f"` on the new methods returns 0 (no string interpolation of SQL) — all queries use parameterized `?` placeholders
</acceptance_criteria>

---

## Task 3: Add `count_events()` and `get_last_events()` to SqliteEventStore

<read_first>
- src/state_core/events.py (read_events from Task 2 will be above — insert these after it)
</read_first>

<action>
Add TWO methods after `read_events_iter()` in `src/state_core/events.py`:

**Method 3 — `count_events()`:**

```python
async def count_events(self, *, mode: str | None = None) -> int:
    """Count events with optional mode filter.

    Args:
        mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.

    Returns:
        Total event count (optionally filtered by mode).
    """
    await self._maybe_repair(source="count_events")

    if mode is not None:
        sql = "SELECT COUNT(*) FROM events WHERE mode = ?"
        params: list[Any] = [mode]
    else:
        sql = "SELECT COUNT(*) FROM events"
        params = []

    async with get_connection() as db:
        cursor = await db.execute(sql, params)
        row = await cursor.fetchone()
        return row[0] if row else 0
```

**Method 4 — `get_last_events()`:**

```python
async def get_last_events(
    self, count: int = 10, *, mode: str | None = None
) -> list[dict[str, Any]]:
    """Return the last N events ordered by id DESC, then reversed to ASC.

    Args:
        count: Number of events to return. Defaults to 10.
        mode: Filter by mode ('build', 'teach', 'kernel'). None = all modes.

    Returns:
        List of up to *count* event dicts in id ASC order (oldest first
        within the window), with keys: id, seq, aggregate_type,
        aggregate_id, type, data (deserialized), ts, mode.
    """
    await self._maybe_repair(source="get_last_events")

    clauses: list[str] = [
        "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
        "FROM events WHERE 1=1"
    ]
    params: list[Any] = []

    if mode is not None:
        clauses.append("AND mode = ?")
        params.append(mode)

    clauses.append("ORDER BY id DESC LIMIT ?")
    params.append(count)

    sql = " ".join(clauses)

    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for row in reversed(rows):  # reverse to chronological order
            d = dict(row)
            if isinstance(d.get("data"), str):
                d["data"] = json.loads(d["data"])
            result.append(d)
        return result
```

Key patterns:
- `count_events()` uses direct SQL instead of the clauses-list pattern (simpler since only one filter)
- `get_last_events()` uses the same clauses-list + params pattern as `read_events()`
- `reversed(rows)` converts DESC order to ASC order so consumers get chronological windows
- All parameters are bound with `?` placeholders — no f-strings or `%` formatting with user input
</action>

<acceptance_criteria>
1. `python3 -c "from src.state_core.events import SqliteEventStore; assert hasattr(SqliteEventStore, 'count_events'); assert hasattr(SqliteEventStore, 'get_last_events'); print('OK')"` prints `OK`
2. After appending 5 events, `count_events()` returns 5 and `count_events(mode="build")` returns count of build-mode events
3. After appending 5 events, `get_last_events(3)` returns exactly 3 events in chronological (ASC) order
4. After appending 5 events with mixed modes, `get_last_events(10, mode="build")` returns only build-mode events in chronological order
5. On empty store, `count_events()` returns 0 and `get_last_events(5)` returns `[]`
6. No raw-string SQL interpolation in any new method — confirmed by `grep -n 'execute(f\|execute(%' src/state_core/events.py` for lines in new methods
</acceptance_criteria>

---

<verification>
1. Run the 0005 migration against a fresh database and confirm the index is created: `python3 -c "import asyncio, aiosqlite; from src.state_core.database import get_connection; from src.state_core.migrations import migrate; async def v(): await migrate(); async with get_connection() as db: cur=await db.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_events_id'\"); r=await cur.fetchone(); assert r and r[0]=='idx_events_id', 'Index missing'; print('Index OK'); asyncio.run(v())"`
2. Functional test: Append 5 events, then call each new method and assert correct results. Use a pytest or inline script.
3. Run `ruff check src/state_core/events.py` to confirm no linting issues.
4. Run `python3 -c "from src.state_core.events import SqliteEventStore"` to confirm no import errors.
</verification>

<must_haves>
1. Migration 0005 file at `.state/migrations/0005_add_events_id_index.sql` with `CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC)`
2. `read_events()` method with all 4 parameters (from_id, to_id, mode, limit), all parameterized
3. `read_events_iter()` async generator variant with same filter params
4. `count_events()` with optional mode filter
5. `get_last_events(count, mode)` returning chronologically-ordered window
6. Zero SQL injection vectors — all user input via `?` placeholders only
</must_haves>

<threat_model>
**ASVS L1 analysis for Plan A:**

| Threat | Vector | Mitigation |
|--------|--------|------------|
| SQL injection | `from_id`, `to_id`, `mode` could contain SQL fragment | All user values bound via `?` placeholders in parameterized queries. The `" ".join(clauses)` pattern only concatenates fixed SQL fragments, never user input. |
| Data corruption | Read-only methods accidentally issue writes | All methods use `get_connection()` context manager with no explicit write operations. Read-only SELECT queries only. |
| Information disclosure via error messages | Exception may reveal SQL schema | Errors bubble to caller; at the CLI layer (Plan B), they'll be caught and surfaced as safe messages. |
| Large result set memory exhaustion | Unlimited fetchall() | `read_events()` has `limit` parameter (default 0=unlimited but caller can set). `read_events_iter()` yields one row at a time. `get_last_events()` is bounded by `count` param. |
</threat_model>
