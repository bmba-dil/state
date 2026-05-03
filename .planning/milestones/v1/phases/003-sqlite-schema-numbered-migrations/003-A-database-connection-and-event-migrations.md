---
phase: 003
plan: A
type: auto
autonomous: true
wave: 1
depends_on:
  - phase-001-plan-B
files_modified:
  - src/state_core/database.py
  - src/state_core/migrations.py
  - src/state_core/events.py
  - .state/migrations/0001_init.sql
  - src/state_cli/main.py
requirements:
  - EVT-01
  - EVT-02
---

<objective>
Create the database connection layer (`database.py`), the migration runner (`migrations.py`), and the initial schema migration (`0001_init.sql`) for the `events` (authoritative event log) and `aggregate_seq` (per-aggregate sequence tracker) tables. Update the existing `EventStore` protocol in `events.py` to use the new connection factory. Provide a `state db init` Typer command stub in `state_cli.main.py`.
</objective>

<read_first>
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/CONTEXT.md
  - /Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md (§11.3 SQLite schema, §5.2 dual-write contract)
  - /Users/tmac/Projects/state/src/state_core/events.py (existing EventStore protocol stub)
  - /Users/tmac/Projects/state/src/state_core/schema.py (EventEnvelope field names/types — drives column names)
  - /Users/tmac/Projects/state/src/state_cli/main.py (existing Typer app for adding commands)
  - /Users/tmac/Projects/state/pyproject.toml (current dependency list — aiosqlite already present at line 13)
</read_first>

---

### Task 1: Create `src/state_core/database.py` — async connection factory with WAL + synchronous=NORMAL

<action>
Create the file `src/state_core/database.py` with the following content:

```python
"""Async SQLite connection factory with WAL mode, synchronous=NORMAL, path resolution.

Every daemon connection goes through this module to enforce:
- WAL journal mode (PRAGMA journal_mode=WAL)
- synchronous = NORMAL (balance safety vs throughput)
- Configurable path via STATE_DB_PATH env var, defaulting to .state/events.sqlite
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


def _resolve_db_path() -> Path:
    """Resolve the database file path.

    Priority:
    1. STATE_DB_PATH environment variable
    2. `.state/events.sqlite` relative to project root
    """
    env_path = os.environ.get("STATE_DB_PATH")
    if env_path:
        return Path(env_path).resolve()
    return Path.cwd() / ".state" / "events.sqlite"


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection to the event store with WAL + synchronous=NORMAL.

    Ensures the parent directory exists, then opens the database
    and applies the required pragmas on every connection open.

    Yields:
        An aiosqlite.Connection with WAL mode and synchronous=NORMAL.
    """
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        yield db


def get_db_path() -> Path:
    """Return the resolved database path without opening a connection."""
    return _resolve_db_path()
```

Verification:
- `uv run python3 -c "from src.state_core.database import get_connection, get_db_path; print('OK')"` succeeds.
- `uv run python3 -c "from src.state_core.database import get_db_path; p = get_db_path(); assert p.name == 'events.sqlite'; print(f'Path: {p}')"` prints the resolved path.
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.database import get_connection, get_db_path"` exits 0.
  - `uv run python3 -c "from src.state_core.database import get_db_path; assert get_db_path().name == 'events.sqlite'"` passes.
  - `ruff check src/state_core/database.py --no-cache` exits 0.
  - `uv run mypy src/state_core/database.py --strict` exits 0 (may need `# type: ignore[attr-defined]` on `aiosqlite.connect` if stubs incomplete).
</acceptance_criteria>

---

### Task 2: Create `.state/migrations/0001_init.sql` — events + aggregate_seq tables

<action>
Create the file `.state/migrations/0001_init.sql` with the authoritative event log and aggregate sequence tracker:

```sql
-- 0001_init: Events table + aggregate sequence tracker
-- Applied by MigrationRunner on daemon startup.
-- WAL mode and synchronous=NORMAL are set by database.py at connection time.

CREATE TABLE IF NOT EXISTS events (
    id              TEXT PRIMARY KEY,          -- ULID
    seq             INTEGER NOT NULL,          -- per-aggregate sequence
    aggregate_type  TEXT NOT NULL,             -- 'arc' | 'phase' | 'slice' | 'step' | 'concept' | 'drill' | 'decision' | 'auth' | 'mode'
    aggregate_id    TEXT NOT NULL,
    type            TEXT NOT NULL,             -- 'state.step.verify_passed' etc.
    data            TEXT NOT NULL,             -- JSON payload
    ts              TEXT NOT NULL,             -- ISO 8601 UTC
    synced_to_opencode INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_agg ON events(aggregate_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_unsynced ON events(synced_to_opencode) WHERE synced_to_opencode = 0;

CREATE TABLE IF NOT EXISTS aggregate_seq (
    aggregate_id    TEXT PRIMARY KEY,
    seq             INTEGER NOT NULL,
    updated_at      TEXT NOT NULL             -- ISO 8601 UTC
);
```

Verification steps after Task 3's migration runner is complete:
- `uv run python3 -c "
import aiosqlite, asyncio
from src.state_core.database import get_db_path
async def test():
    p = get_db_path()
    await asyncio.sleep(0)  # noop to use aiosqlite
    print('Schema file OK:', p.parent / 'migrations/0001_init.sql')
asyncio.run(test())
"` — file exists and readable (applied in Task 3).

This file must have:
- Exactly 8 CREATE TABLE/INDEX statements (2 tables + 3 indexes on events + 0 on aggregate_seq + 0 elsewhere)
- All SQL identifiers in snake_case
- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` for idempotency
- ISO 8601 UTC timestamps with `T` separator (matching `schema.py` convention)
</action>

<acceptance_criteria>
  - File `.state/migrations/0001_init.sql` exists.
  - `grep -c "CREATE TABLE\|CREATE INDEX" .state/migrations/0001_init.sql` returns 5.
  - `grep "CREATE TABLE IF NOT EXISTS events" .state/migrations/0001_init.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS aggregate_seq" .state/migrations/0001_init.sql` matches.
  - `grep "synced_to_opencode" .state/migrations/0001_init.sql` matches (the critical dual-write field).
  - All SQL uses snake_case identifiers — `grep -c "[A-Z]" .state/migrations/0001_init.sql` returns 0 (no upper-case SQL identifiers in DDL).
</acceptance_criteria>

---

### Task 3: Create `src/state_core/migrations.py` — numbered migration runner

<action>
Create the file `src/state_core/migrations.py` with the following content. The runner reads `.state/migrations/` for `.sql` files, tracks applied migrations in a `_migrations` meta-table, and applies any unapplied migrations in filename order:

```python
"""Numbered SQL migration runner.

Scans .state/migrations/ for 0001_*.sql, 0002_*.sql, etc.
Tracks applied migrations in the _migrations meta-table.
Applies unapplied migrations in filename order on each call to migrate().
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


def _migrations_dir() -> Path:
    """Return the migrations directory path relative to the database."""
    from src.state_core.database import get_db_path

    return get_db_path().parent / "migrations"


async def ensure_meta_table(db: aiosqlite.Connection) -> None:
    """Create the _migrations tracking table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            filename    TEXT PRIMARY KEY,
            checksum    TEXT NOT NULL,
            applied_at  TEXT NOT NULL  -- ISO 8601 UTC
        )
    """)


async def applied_migrations(db: aiosqlite.Connection) -> set[str]:
    """Return the set of already-applied migration filenames."""
    cursor = await db.execute("SELECT filename FROM _migrations ORDER BY filename")
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def _checksum(path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def migrate() -> None:
    """Apply all unapplied migrations in filename order.

    Safe to call multiple times -- already-applied migrations are skipped.
    Raises RuntimeError if a previously-applied migration's checksum changes.
    """
    from src.state_core.database import get_connection

    migrations_dir = _migrations_dir()
    migrations_dir.mkdir(parents=True, exist_ok=True)

    migration_files = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))

    async with get_connection() as db:
        await ensure_meta_table(db)
        applied = await applied_migrations(db)

        for mf in migration_files:
            cs = await _checksum(mf)

            if mf.name in applied:
                # Verify checksum hasn't changed (tamper / accidental edit detection)
                cursor = await db.execute(
                    "SELECT checksum FROM _migrations WHERE filename = ?", (mf.name,)
                )
                row = await cursor.fetchone()
                if row and row[0] != cs:
                    raise RuntimeError(
                        f"Migration {mf.name} checksum changed: "
                        f"expected {row[0]}, got {cs}. "
                        f"Already-applied migrations must not be modified."
                    )
                continue

            sql = mf.read_text()
            await db.executescript(sql)
            await db.execute(
                "INSERT INTO _migrations (filename, checksum, applied_at) "
                "VALUES (?, ?, datetime('now'))",
                (mf.name, cs),
            )
            await db.commit()
            logger.info("Applied migration: %s", mf.name)
```

Verification (after test file created in Plan C):
- Module imports cleanly.
- `ruff check src/state_core/migrations.py --no-cache` exits 0.
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.migrations import migrate; print('OK')"` succeeds.
  - `ruff check src/state_core/migrations.py --no-cache` exits 0.
  - `uv run mypy src/state_core/migrations.py --strict` exits 0 (or minimal type: ignore).
  - `grep "CREATE TABLE IF NOT EXISTS _migrations" .state/migrations/0001_init.sql || true` — note: `_migrations` is created at runtime by `ensure_meta_table()`, not by `0001_init.sql`.
</acceptance_criteria>

---

### Task 4: Update `src/state_core/events.py` — wire EventStore protocol to database.py

<action>
Edit `src/state_core/events.py` to replace the bare Protocol stub with a concrete implementation that uses `database.py`. Replace the current file content:

```python
"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture.

Uses database.py for connection factory (WAL mode, synchronous=NORMAL).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from src.state_core.database import get_connection


class EventStore(Protocol):
    """Protocol for writing and reading domain events."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> str: ...

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]: ...


class SqliteEventStore:
    """Concrete EventStore backed by events.sqlite via database.py."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> str:
        """Append an event row and return its id.

        NOTE: This is a stub for Phase 003. Per-aggregate seq enforcement,
        ULID generation, and commit-then-emit logic will be added in Phase 004.
        """
        raise NotImplementedError("append() is implemented in Phase 004")

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]:
        """Read events for an aggregate, ordered by seq, starting after_seq.

        Yields event rows as dicts.
        """
        async with get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, synced_to_opencode "
                "FROM events "
                "WHERE aggregate_id = ? AND seq > ? "
                "ORDER BY seq ASC",
                (aggregate_id, after_seq),
            )
            rows = await cursor.fetchall()
            for row in rows:
                yield dict(row)
```

Note: Add `import aiosqlite` at the top of the file.
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.events import SqliteEventStore; print('OK')"` succeeds.
  - `uv run python3 -c "from src.state_core.events import EventStore; print('OK')"` succeeds (protocol still exported).
  - `ruff check src/state_core/events.py --no-cache` exits 0.
  - `uv run mypy src/state_core/events.py --strict` exits 0.
</acceptance_criteria>

---

### Task 5: Add `state db init` Typer command stub in `src/state_cli/main.py`

<action>
Edit `src/state_cli/main.py` to add a `db` command group with an `init` subcommand that calls `migrate()`:

Read the current file first, then add:

```python
import typer
from src.state_core.migrations import migrate as _migrate

# Add after the existing app creation
db_app = typer.Typer(name="db", help="Database management commands")
app.add_typer(db_app)


@db_app.command(name="init")
def db_init() -> None:
    """Initialize the event store database by applying all pending migrations."""
    import asyncio

    asyncio.run(_migrate())
    typer.echo("Database initialized: all migrations applied.")
```

Find the existing `app = typer.Typer(...)` line and insert the `db_app` creation and `app.add_typer(db_app)` call after it.
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_cli.main import app; print('OK')"` succeeds.
  - `grep "db_app" src/state_cli/main.py` matches.
  - `grep "db_init" src/state_cli/main.py` matches.
  - `ruff check src/state_cli/main.py --no-cache` exits 0.
  - `uv run mypy src/state_cli/main.py --strict` exits 0.
</acceptance_criteria>

---

<verification>
1. **Module import chain**: `uv run python3 -c "from src.state_core.database import get_connection; from src.state_core.migrations import migrate; from src.state_core.events import SqliteEventStore; print('All imports OK')"` succeeds.
2. **Migration idempotency**: Create a temp dir, copy `.state/migrations/0001_init.sql`, run `migrate()` twice, assert second call is a no-op (no error, no new `_migrations` row).
3. **Schema correctness**: After migration, connect to the DB and assert:
   - `PRAGMA journal_mode` returns `wal`
   - `SELECT name FROM sqlite_master WHERE type='table' AND name='events'` returns `events`
   - `SELECT name FROM sqlite_master WHERE type='table' AND name='aggregate_seq'` returns `aggregate_seq`
   - All 5 indexes exist in `sqlite_master`
4. **Round-trip insert/select**: Insert a row into `events` via raw SQL, read it back via `read_stream`, assert all fields match.
5. **CLI stub**: `uv run python3 -m src.state_cli.main db init --help` exits 0 and shows the help text.
6. **ruff clean**: `ruff check src/state_core/database.py src/state_core/migrations.py src/state_core/events.py src/state_cli/main.py --no-cache` exits 0.
7. **mypy clean**: `uv run mypy src/state_core/ --strict` exits 0.
</verification>

<must_haves>
- **`src/state_core/database.py`** — async connection factory with WAL + synchronous=NORMAL + path resolution via `STATE_DB_PATH` env var, defaulting to `.state/events.sqlite`
- **`src/state_core/migrations.py`** — `migrate()` function that scans `.state/migrations/`, applies unapplied `0001_*.sql` in filename order, tracks via `_migrations` meta-table with checksum tamper detection
- **`.state/migrations/0001_init.sql`** — `events` table (8 columns including `synced_to_opencode`) + `aggregate_seq` table + full index set (3 on events)
- **`src/state_core/events.py`** — updated with `SqliteEventStore` concrete class implementing `EventStore` protocol, using `database.py` connection factory, with `read_stream()` implemented (returns events as dicts)
- **`src/state_cli/main.py`** — `state db init` Typer command that invokes `migrate()`
- All files pass `ruff` and `mypy --strict`
</must_haves>
