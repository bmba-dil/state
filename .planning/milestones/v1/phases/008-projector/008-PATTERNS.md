# Phase 008: Projector — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 3 (1 new module, 1 new test file, 1 modified CLI)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/state_core/projector.py` | service | event-driven + CRUD | `src/state_core/reconciler.py` | exact |
| `src/state_cli/main.py` (modified) | controller | request-response (CLI) | `.state_cli/main.py` — `db_app` sub-app pattern | exact |
| `tests/test_projector.py` | test | event-driven + CRUD | `tests/test_reconciler.py` | exact |

## Pattern Assignments

### `src/state_core/projector.py` (service, event-driven + CRUD)

**Analog:** `src/state_core/reconciler.py` (136 lines — service that reads events from store and processes them)

**Imports pattern** (lines 1-18):
```python
"""Event-sourced projection engine — rebuilds cache tables from events.

Projection handlers map event types to cache-table upserts. The Projector
class supports two modes:
1. Live update: called after append() to update projections in same txn
2. Rebuild: truncates cache tables, replays all events, materializes state
"""

from __future__ import annotations

import structlog
from typing import Any

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore

log = structlog.get_logger(__name__)
```

**Source:** `src/state_core/reconciler.py` lines 1-18 — use same `from __future__ import annotations`, `from src.state_core.events import SqliteEventStore`, `from src.state_core.database import get_connection`, and `log = structlog.get_logger(__name__)`.

**Core class pattern** (lines 25-44):
```python
class Projector:
    """Orchestrates projection rebuilds and live updates.

    Args:
        db: The event store for reading events.
    """

    def __init__(self, db: SqliteEventStore) -> None:
        self._db = db

    async def rebuild_all(self) -> int:
        """Truncate and rebuild all projections from events.

        Returns:
            Number of events processed.
        """
        ...
```

**Source:** `src/state_core/reconciler.py` lines 26-44 — same constructor pattern with SqliteEventStore argument, same Google-style docstrings with `Args:` / `Returns:` sections.

**Database transaction pattern** (for rebuild_all — modeled after `events.py` lines 152-185):
```python
async with get_connection() as db:
    await db.execute("PRAGMA synchronous=FULL;")
    await db.execute("BEGIN IMMEDIATE")

    # Truncate cache tables
    for table in ("steps", "slices", "concepts"):
        await db.execute(f"DELETE FROM {table}")

    # Read all events ordered by (aggregate_id, seq)
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode "
        "FROM events "
        "ORDER BY aggregate_id, seq ASC"
    )
    rows = await cursor.fetchall()

    for row in rows:
        row_dict = dict(row)
        if isinstance(row_dict.get("data"), str):
            row_dict["data"] = json.loads(row_dict["data"])
        projected = await self._apply_event(row_dict)
        ...

    await db.commit()
```

**Source:** `src/state_core/events.py` lines 152-185 (BEGIN IMMEDIATE + commit pattern) and lines 211-225 (Row factory + JSON deserialization). Also `src/state_core/events.py` lines 274-322 (repair method's BEGIN IMMEDIATE + commit + pragma pattern).

**Deterministic JSON serialization** (for any JSON round-trips — lines 173-174):
```python
json.dumps(data, sort_keys=True, separators=(",", ":"))
```

**Source:** `src/state_core/events.py` line 173 — deterministic serialization must be used everywhere data is written as JSON.

**Handler registry pattern** (decorator-based, to route event types to handlers):
```python
_HandlerFn: TypeAlias = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]

HANDLERS: dict[str, _HandlerFn] = {}

def _register_handler(event_type: str):
    """Decorator that registers a projection handler for *event_type*."""
    def decorator(fn: _HandlerFn) -> _HandlerFn:
        HANDLERS[event_type] = fn
        return fn
    return decorator

@_register_handler("state.step.discussed")
def _handle_step_discussed(state: dict[str, Any] | None, data: dict[str, Any]) -> dict[str, Any]:
    """Step enters DISCUSSING state."""
    return {
        "aggregate_id": ..., "state": "discussing",
        "title": data.get("approach_summary", ""),
        "approach_summary": data.get("approach_summary", ""),
    }
```

**Source:** No direct analog in current codebase — this is new. The pattern follows the RESEARCH.md design (lines 267-285). The `HANDLERS` dict + decorator is a standard Python registry pattern matching the codebase's convention of module-level constants (e.g., `reconciler.py` lines 20-23 module constants).

---

### `src/state_cli/main.py` (modified — controller, request-response CLI)

**Analog:** The existing file itself — specifically the `db_app` Typer sub-app pattern (lines 13-21)

**Current pattern for Typer sub-apps** (lines 11-14):
```python
app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")

db_app = typer.Typer(name="db", help="Database management commands")
app.add_typer(db_app)
```

**Source:** `src/state_cli/main.py` lines 11-14 — the canonical pattern for adding a new sub-app (like `events`).

**Current pattern for async CLI commands** (lines 17-21):
```python
@db_app.command(name="init")
def db_init() -> None:
    """Initialize the event store database by applying all pending migrations."""
    asyncio.run(_migrate())
    typer.echo("Database initialized: all migrations applied.")
```

**Source:** `src/state_cli/main.py` lines 17-21 — the canonical pattern for a command that runs an async function and echoes a completion message.

**New `events` sub-app + command** (following the exact db_app pattern):
```python
events_app = typer.Typer(name="events", help="Event store management commands")
app.add_typer(events_app)


@events_app.command(name="rebuild-projections")
def rebuild_projections() -> None:
    """Rebuild steps/slices/concepts cache tables from events."""
    asyncio.run(_do_rebuild_projections())
    typer.echo("Projections rebuilt.")


async def _do_rebuild_projections() -> None:
    from src.state_core.events import SqliteEventStore
    from src.state_core.migrations import migrate
    from src.state_core.projector import Projector

    await migrate()
    store = SqliteEventStore()
    projector = Projector(db=store)
    count = await projector.rebuild_all()
    typer.echo(f"Projections rebuilt: {count} events processed.")
```

**Source:** The `db init` command pattern from `main.py` lines 17-21 combined with the RESEARCH.md recommended implementation (lines 327-348).

---

### `tests/test_projector.py` (test, event-driven + CRUD)

**Analog:** `tests/test_reconciler.py` (441 lines — same DB isolation fixtures, same SqliteEventStore + migrate setup)

**DB isolation fixture** (lines 23-33):
```python
@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)
```

**Source:** `tests/test_reconciler.py` lines 38-48 AND `tests/test_events.py` lines 23-32 — identical pattern used in every test file.

**Store fixture** (lines 50-54):
```python
@pytest.fixture
async def store() -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()
```

**Source:** `tests/test_reconciler.py` lines 50-54 — exact same pattern used by all event store tests.

**Test class structure** (lines 93-95, 141-142):
```python
@pytest.mark.asyncio
class TestStepProjection:
    """Each state.step.* event produces correct step cache row."""
    ...
```

**Source:** `tests/test_reconciler.py` lines 93-94 and `tests/test_events.py` lines 53-54 — all tests use `@pytest.mark.asyncio` + class grouping with descriptive class docstrings.

**Event append helper** (lines 65-79):
```python
async def _append_events(
    store: SqliteEventStore,
    events: list[tuple[str, str, dict[str, Any]]],
) -> list[str]:
    """Append multiple events and return their IDs."""
    ids: list[str] = []
    for aggregate_id, event_type, data in events:
        id_ = await store.append("step", aggregate_id, event_type, data)
        ids.append(id_)
    return ids
```

**Source:** `tests/test_reconciler.py` lines 65-79 — same helper pattern pattern for populating test data.

**Hypothesis property test pattern** (lines 281-296):
```python
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.one_of(st.integers(min_value=0, max_value=100), st.text(max_size=20)),
        min_size=0,
        max_size=5,
    ),
)
async def test_property_rebuild_determinism(
    tmp_path: Path,
    data: dict,
) -> None:
    """Hypothesis property: identical events produce identical projections."""
    import uuid
    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    db_path = unique / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    ...
```

**Source:** `tests/test_events.py` lines 281-312 — the property-based test pattern with per-example DB isolation (uuid in tmp_path). Also `tests/test_reconciler.py` for the general fixture structure.

## Shared Patterns

### Deterministic JSON Serialization
**Source:** `src/state_core/events.py` line 173
**Apply to:** `projector.py` — any JSON serialization of event data must use:
```python
json.dumps(data, sort_keys=True, separators=(",", ":"))
```

### Database Connection + Transaction Pattern
**Source:** `src/state_core/events.py` lines 152-185 (append), lines 274-322 (repair)
**Apply to:** `projector.py` — all database writes must follow the `BEGIN IMMEDIATE` + single `COMMIT` pattern:
```python
async with get_connection() as db:
    await db.execute("PRAGMA synchronous=FULL;")
    await db.execute("BEGIN IMMEDIATE")
    # ... work ...
    await db.commit()
```

### DB Row Deserialization Pattern
**Source:** `src/state_core/events.py` lines 211-225
**Apply to:** `projector.py` — reading events with JSON data columns:
```python
db.row_factory = aiosqlite.Row
cursor = await db.execute(...)
rows = await cursor.fetchall()
for row in rows:
    d = dict(row)
    if isinstance(d.get("data"), str):
        d["data"] = json.loads(d["data"])
    yield d
```

### Structlog Setup
**Source:** Every module in `src/state_core/`
**Apply to:** `projector.py`
```python
import structlog
log = structlog.get_logger(__name__)
```

### Test DB Isolation
**Source:** `tests/test_reconciler.py` lines 38-48, `tests/test_events.py` lines 23-32
**Apply to:** `tests/test_projector.py`
- Use `tmp_path` + `monkeypatch.setenv("STATE_DB_PATH", ...)` for every test
- Use `autouse=True` fixture for isolation
- Copy migrations from `Path.cwd() / ".state" / "migrations"` to the temp dir
- Accept `_isolate_db: None` as a fixture dependency on `store`

### CLI Sub-app Pattern
**Source:** `src/state_cli/main.py` lines 13-21
**Apply to:** Adding `events_app` with `rebuild-projections` command
- Create `events_app = typer.Typer(name="events", help="...")`
- Register with `app.add_typer(events_app)`
- Each command is a sync function that calls `asyncio.run(...)`
- Echo completion messages with `typer.echo()`

## No Analog Found

None — all files have strong existing analogs in the codebase.

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (none) | | | All three files have exact analogs |

## Metadata

**Analog search scope:** `src/state_core/`, `src/state_cli/`, `tests/`
**Files scanned:** 11 (5 production, 6 test)
**Pattern extraction date:** 2026-04-24
