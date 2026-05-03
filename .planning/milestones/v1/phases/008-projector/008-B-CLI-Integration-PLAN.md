---
phase: 008
plan: 2 of 3
type: auto
autonomous: true
wave: 2
depends_on:
  - PLAN-001-Projector-Core
files_modified:
  - src/state_cli/main.py
requirements:
  - EVT-02
---

# Plan 2: CLI Integration

<objective>
Add the `state events rebuild-projections` CLI command to `src/state_cli/main.py`. Creates a new `events` Typer sub-app following the exact pattern of the existing `db` sub-app. The command orchestrates a full projection rebuild: applies migrations, creates a `SqliteEventStore`, instantiates the `Projector`, calls `rebuild_all()`, and reports results.

Pattern follows `src/state_cli/main.py` lines 13-21 (`db_app` → `db init`).
</objective>

<threat_model>
| Severity | Threat | Mitigation |
|----------|--------|------------|
| **LOW** | Unhandled exception during rebuild causes Python traceback dump to terminal | Wrap the async runner in a try/except that prints a user-friendly error via `typer.echo("Error: ...", err=True)` and `raise typer.Exit(code=1)` |
| **LOW** | Concurrency — two rebuild commands run simultaneously | SQLite WAL mode handles concurrent readers. The rebuild's `BEGIN IMMEDIATE` blocks a second writer. Acceptable for v1. No additional locking needed |
| **LOW** | Module import errors if projector.py syntax is wrong | The function-level imports inside `_do_rebuild_projections()` (not top-level) ensure errors surface immediately at command invocation, not at module load time |
</threat_model>

<tasks>

### Task 1: Add `events` Typer sub-app + import block

<read_first>
- src/state_cli/main.py (full file — existing db_app pattern)
- src/state_core/projector.py (Plan 1 deliverable — Projector class and HANDLERS)
</read_first>

<action>
Modify `src/state_cli/main.py` to add the `events` sub-app and import.

**Step 1:** Add these lines AFTER the existing `from src.state_core.migrations import migrate as _migrate` import (line 9) and BEFORE the `app = typer.Typer(...)` definition (line 11):
```python
from src.state_core.projector import Projector as _Projector
```

**Step 2:** Add the `events_app` definition AFTER the `app.add_typer(db_app)` line (line 14):
```python
events_app = typer.Typer(name="events", help="Event store management commands")
app.add_typer(events_app)
```

The final file structure should be:
```python
"""Typer app: ..."""

from __future__ import annotations

import asyncio

import typer

from src.state_core.migrations import migrate as _migrate
from src.state_core.projector import Projector as _Projector

app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")

db_app = typer.Typer(name="db", help="Database management commands")
app.add_typer(db_app)

events_app = typer.Typer(name="events", help="Event store management commands")
app.add_typer(events_app)


@db_app.command(name="init")
def db_init() -> None:
    """Initialize the event store database by applying all pending migrations."""
    asyncio.run(_migrate())
    typer.echo("Database initialized: all migrations applied.")
```

**Note:** The `asyncio.run()` calls in CLI commands each open and close their own connection. This is safe because SQLite in WAL mode supports concurrent connections for reads, and the singleton-writer pattern is handled at the daemon level, not the CLI level.
</action>

<acceptance_criteria>
- `grep -c "events_app" src/state_cli/main.py` returns >= 1
- `grep -c "Projector as _Projector" src/state_cli/main.py` returns 1
- `grep -c 'name="events"' src/state_cli/main.py` returns 1
- `grep -c "add_typer(events_app)" src/state_cli/main.py` returns 1
- `python3 -c "import ast; ast.parse(open('src/state_cli/main.py').read())"` exits 0
</acceptance_criteria>

---

### Task 2: Add `rebuild-projections` command

<read_first>
- src/state_cli/main.py (file from Task 1)
- src/state_core/projector.py (Projector class API)
- src/state_core/events.py (SqliteEventStore class)
- src/state_core/migrations.py (migrate function)
</read_first>

<action>
Add the `rebuild-projections` command as a method on `events_app`, placed after the `@db_app.command` block. Follow the exact pattern of `db_init` (sync function → `asyncio.run()` → typer.echo).

**Command function:**
```python
@events_app.command(name="rebuild-projections")
def rebuild_projections() -> None:
    """Rebuild steps/slices/concepts cache tables from events."""
    try:
        asyncio.run(_do_rebuild_projections())
    except Exception as exc:
        typer.echo(f"Error rebuilding projections: {exc}", err=True)
        raise typer.Exit(code=1) from exc
```

**Async runner function:**
```python
async def _do_rebuild_projections() -> None:
    """Async implementation of rebuild-projections."""
    from src.state_core.events import SqliteEventStore

    await _migrate()
    store = SqliteEventStore()
    projector = _Projector(db=store)
    count = await projector.rebuild_all()
    typer.echo(f"Projections rebuilt: {count} events processed.")
```

**Design notes:**
- Uses late (function-level) imports for `SqliteEventStore` to avoid circular imports at module level
- Calls `_migrate()` first to ensure all migrations (including cache table creation) are applied
- Creates a fresh `SqliteEventStore` — no mirror needed since projections don't emit SyncEvents
- The `_Projector` import is module-level (aliased to avoid confusion with any future Projector variants)
- Error handling wraps the full async operation: exceptions produce a user-friendly message and non-zero exit code

**Placement in file:**
Insert AFTER the `db_init` function (after line 21), BEFORE any future commands. The final file should end with the `_do_rebuild_projections` function definition.
</action>

<acceptance_criteria>
- `grep -c "rebuild-projections" src/state_cli/main.py` returns 1
- `grep -c "_do_rebuild_projections" src/state_cli/main.py` returns 2 (definition + call)
- `grep -c "SqliteEventStore" src/state_cli/main.py` returns 1
- `grep -c "typer.Exit(code=1)" src/state_cli/main.py` returns 1
- `python3 -c "import ast; ast.parse(open('src/state_cli/main.py').read())"` exits 0
- `python3 -c "from src.state_cli.main import app; print(len(app.registered_groups))"` exits 0 and prints >= 2 (db + events groups)
</acceptance_criteria>

</tasks>

<verification>
1. **Import check:** `python3 -c "from src.state_cli.main import app; print('OK')"` exits 0.
2. **Help output:** `python3 -m src.state_cli.main events --help` prints help text mentioning `rebuild-projections`.
3. **Syntax:** `python3 -c "import ast; ast.parse(open('src/state_cli/main.py').read())"` exits 0.
4. **App structure:** `python3 -c "from src.state_cli.main import app; groups = {g.name for g in app.registered_groups}; assert 'events' in groups; print('OK')"` exits 0.
</verification>

<must_haves>
- [x] `state events rebuild-projections` CLI command exists and is invocable
- [x] Follows the exact `db_app` → `db init` sub-app pattern from `src/state_cli/main.py`
- [x] Calls `_migrate()` before rebuild to ensure schema is current
- [x] Instantiates `SqliteEventStore` + `Projector` and calls `rebuild_all()`
- [x] Reports event count on success: `"Projections rebuilt: {count} events processed."`
- [x] Error handling: try/except wraps async operation, prints error, exits with code 1
- [x] Late import of `SqliteEventStore` inside the async function (avoids circular imports at module level)
</must_haves>
