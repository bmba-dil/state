---
phase: 009
plan: B
type: auto
autonomous: true
wave: 2
depends_on:
  - PLAN-A (EventStore query methods + migration 0005)
files_modified:
  - src/state_cli/main.py
requirements:
  - EVT-07
  - EVT-08
---

<objective>
Add three CLI commands to the existing `events` Typer sub-app: `state events tail` (polling-based follow mode), `state events replay --from <ulid>` (event history playback), and `state events export --format jsonl` (bulk export). Each command supports `--mode build|teach|kernel` filtering. All commands are read-only.
</objective>

---

## Task 1: Add `state events tail` command

<read_first>
- src/state_cli/main.py (existing pattern: events_app commands, async runner, late imports — follow exactly)
- .planning/milestones/v1/phases/009-cli-state-events-tail-replay/009-RESEARCH.md (patterns section: polling tail, format, --count, --follow)
</read_first>

<action>
Add the `tail` command and its async runner `_do_tail()` to `src/state_cli/main.py`. Insert after the `_do_rebuild_projections()` function (line 46).

**Sync command function:**

```python
@events_app.command(name="tail")
def tail(
    from_id: str = typer.Option(None, "--from", help="ULID offset to start from"),
    mode: str = typer.Option(None, "--mode", help="Filter by mode (build|teach|kernel)"),
    count: int = typer.Option(10, "--count", "-n", help="Number of past events to show"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f", help="Follow mode (poll for new events)"),
) -> None:
    """Tail events from the event store (polling-based)."""
    try:
        asyncio.run(_do_tail(from_id=from_id, mode=mode, count=count, follow=follow))
    except asyncio.CancelledError:
        pass  # clean exit on Ctrl+C
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
```

**Async runner function:**

```python
async def _do_tail(
    from_id: str | None = None,
    mode: str | None = None,
    count: int = 10,
    follow: bool = True,
) -> None:
    """Tail events with polling loop."""
    from src.state_core.events import SqliteEventStore

    store = SqliteEventStore()
    last_id = from_id

    # If no explicit --from, show last N events first
    if last_id is None:
        recent = await store.get_last_events(count, mode=mode)
        for ev in recent:
            _print_event_line(ev)
            last_id = ev["id"]
    elif count > 0:
        events = await store.read_events(from_id=last_id, mode=mode, limit=count)
        for ev in events:
            _print_event_line(ev)
            last_id = ev["id"]

    if not follow:
        return

    # Polling loop
    try:
        while True:
            events = await store.read_events(from_id=last_id, mode=mode)
            for ev in events:
                _print_event_line(ev)
                last_id = ev["id"]
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Clean shutdown on Ctrl+C
        pass
```

**Helper function `_print_event_line()` — added at module level:**

```python
def _print_event_line(ev: dict) -> None:
    """Print a single event as a compact single-line summary."""
    typer.echo(
        f"{ev['id'][-13:]}  {ev['type']:<40s} {ev['aggregate_id'][:20]:<20s} "
        f"{ev['mode']:<8s} {ev['ts']}"
    )
```

Key implementation requirements:
- `--from` maps to parameter name `from_id` (Python keyword workaround)
- `--count / -n` defaults to 10
- `--follow` defaults to True (like `tail -f`)
- Polling interval: exactly 1 second (`await asyncio.sleep(1)`)
- `asyncio.CancelledError` caught for clean Ctrl+C exit
- `typer.Exit(code=1)` on other exceptions
- `_print_event_line` must use `typer.echo()`, not `print()`
</action>

<acceptance_criteria>
1. `python3 -c "from src.state_cli.main import app; cmds=[c.name for c in app.registered_groups[0].typer_instance.registered_commands] if app.registered_groups else []; print('tail' in cmds)"` prints `True`
2. `python3 -m typer src/state_cli/main.py --help 2>&1 | grep -A2 'tail'` shows the tail command
3. Running `python3 -c "from src.state_cli.main import _do_tail; import inspect; assert asyncio.iscoroutinefunction(_do_tail); print('async OK')"` succeeds (confirm async runner is a coroutine)
4. Running `python3 -c "from src.state_cli.main import _print_event_line; print('helper OK')"` succeeds
5. `python3 -c "import ast; tree=ast.parse(open('src/state_cli/main.py').read()); funcs=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert 'tail' in funcs; assert '_do_tail' in funcs; print('defs OK')"` prints `defs OK`
</acceptance_criteria>

---

## Task 2: Add `state events replay --from <ulid>` command

<read_first>
- src/state_cli/main.py (now has tail from Task 1 — follow the same pattern)
- .planning/milestones/v1/phases/009-cli-state-events-tail-replay/009-RESEARCH.md (replay patterns section)
</read_first>

<action>
Add the `replay` command and its async runner `_do_replay()` to `src/state_cli/main.py`. Insert after the `_do_tail()` function.

**Sync command function:**

```python
@events_app.command(name="replay")
def replay(
    from_id: str = typer.Option(..., "--from", help="ULID offset to start from (required)"),
    to_id: str = typer.Option(None, "--to", help="ULID offset to stop at"),
    mode: str = typer.Option(None, "--mode", help="Filter by mode (build|teach|kernel)"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max events to replay (0 = unlimited)"),
) -> None:
    """Replay events from a ULID offset."""
    try:
        asyncio.run(_do_replay(from_id=from_id, to_id=to_id, mode=mode, limit=limit))
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
```

**Async runner function:**

```python
async def _do_replay(
    from_id: str,
    to_id: str | None = None,
    mode: str | None = None,
    limit: int = 0,
) -> None:
    """Replay events from a ULID offset."""
    from src.state_core.events import SqliteEventStore

    store = SqliteEventStore()
    events = await store.read_events(from_id=from_id, to_id=to_id, mode=mode, limit=limit)

    for ev in events:
        _print_event_line(ev)
```

Key requirements:
- `--from` is REQUIRED (`...` as default, which Typer renders as required positional-option)
- `--to` is optional (exclusive upper bound)
- `--limit / -n` defaults to 0 (unlimited)
- Replay uses `_print_event_line()` helper from Task 1 (same compact format)
- Uses `store.read_events()` which already handles data deserialization
</action>

<acceptance_criteria>
1. `python3 -c "from src.state_cli.main import app; cmds=[c.name for c in app.registered_groups[0].typer_instance.registered_commands if app.registered_groups else []] if app.registered_groups else [c.name for c in app.registered_commands]; print([c for c in cmds if 'replay' in c])"` — confirm `replay` is in the list
2. `grep -c 'typer\.Option(\.\.\.' src/state_cli/main.py` is >= 1 (--from is required)
3. `python3 -c "import ast; tree=ast.parse(open('src/state_cli/main.py').read()); funcs=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert 'replay' in funcs; assert '_do_replay' in funcs; print('defs OK')"` prints `defs OK`
4. `python3 -c "from src.state_cli.main import _do_replay; import asyncio; assert asyncio.iscoroutinefunction(_do_replay); print('async OK')"` prints `async OK`
</acceptance_criteria>

---

## Task 3: Add `state events export --format jsonl` command

<read_first>
- src/state_cli/main.py (now has tail + replay from Tasks 1-2 — follow the same pattern)
- .planning/milestones/v1/phases/009-cli-state-events-tail-replay/009-RESEARCH.md (export patterns: JSONL format, orjson, streaming)
</read_first>

<action>
Add the `export` command and its async runner `_do_export()` to `src/state_cli/main.py`. Insert after the `_do_replay()` function.

**Sync command function:**

```python
@events_app.command(name="export")
def export(
    from_id: str = typer.Option(None, "--from", help="ULID offset to start from"),
    to_id: str = typer.Option(None, "--to", help="ULID offset to stop at"),
    mode: str = typer.Option(None, "--mode", help="Filter by mode (build|teach|kernel)"),
    output_format: str = typer.Option("jsonl", "--format", help="Export format (jsonl only)"),
    if output_format != "jsonl":
        raise typer.BadParameter("Only --format=jsonl is supported in this version")
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
) -> None:
    """Export events in JSONL format."""
    try:
        asyncio.run(_do_export(from_id=from_id, to_id=to_id, mode=mode, output=output, output_format=output_format))
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
```

**Async runner function:**

```python
async def _do_export(
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
    output: str | None = None,
    output_format: str = "jsonl",
) -> None:
    """Export events in JSONL format."""
    import sys
    from src.state_core.events import SqliteEventStore

    store = SqliteEventStore()

    # Determine output target
    fh: Any
    if output is not None:
        fh = open(output, "w")
    else:
        fh = sys.stdout

    try:
        count = 0
        async for ev in store.read_events_iter(from_id=from_id, to_id=to_id, mode=mode):
            line = json.dumps(ev, sort_keys=True, separators=(",", ":"))
            fh.write(line + "\n")
            count += 1

        if output is not None:
            typer.echo(f"Exported {count} events to {output}")
    finally:
        if output is not None:
            fh.close()
```

Key requirements:
- Uses `read_events_iter()` for streaming (memory-safe for large exports)
- JSONL format: one compact JSON object per line (no outer array, no trailing comma)
- Uses `json.dumps(sort_keys=True, separators=(",", ":"))` for deterministic serialization (NOT `orjson` — stdlib `json` is already imported at top of main.py)
- `--output <file>` writes to file; default writes to stdout
- When writing to file, print count summary to stdout on completion
- `import json` must be added at the top of `main.py` if not already present (it is not — the JSON serialization is done inside events.py). Add `import json` to the existing stdlib import block in main.py.
</action>

<acceptance_criteria>
1. `python3 -c "from src.state_cli.main import app; cmds=[c.name for c in app.registered_groups[0].typer_instance.registered_commands if app.registered_groups else []] if app.registered_groups else [c.name for c in app.registered_commands]; assert 'export' in cmds; print('cmd OK')"` prints `cmd OK`
2. `python3 -c "import ast; tree=ast.parse(open('src/state_cli/main.py').read()); funcs=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert 'export' in funcs; assert '_do_export' in funcs; print('defs OK')"` prints `defs OK`
3. `grep -c 'read_events_iter' src/state_cli/main.py` is >= 1 (export uses streaming)
4. `grep -c 'import json' src/state_cli/main.py` is >= 1 (json import present)
5. The `--format` option is accepted but only `jsonl` is valid (future extensibility)
</acceptance_criteria>

---

<verification>
1. Import integrity: `python3 -c "from src.state_cli.main import app, _do_tail, _do_replay, _do_export, _print_event_line"` prints nothing (no ImportError)
2. CLI help verification: `python3 -c "from typer.testing import CliRunner; from src.state_cli.main import app; r=CliRunner().invoke(app, ['events', '--help']); assert 'tail' in r.stdout; assert 'replay' in r.stdout; assert 'export' in r.stdout; print('All 3 commands in help: OK')"` prints success message
3. Ruff lint: `ruff check src/state_cli/main.py` passes with no errors
4. No SQL in CLI module: `grep -c '\.execute' src/state_cli/main.py` returns 0 (all SQL lives in events.py)
</verification>

<must_haves>
1. `state events tail` command with --from, --mode, --count/-n, --follow/--no-follow
2. `state events replay --from <ulid>` command with --from (required), --to, --mode, --limit/-n
3. `state events export --format jsonl` command with --from, --to, --mode, --output/-o
4. `_print_event_line()` helper showing truncated ULID, type, aggregate_id, mode, timestamp
5. All commands use parameterized queries via EventStore methods (no direct SQL in CLI layer)
6. Zero mutation of events table — all commands are read-only
</must_haves>

<threat_model>
**ASVS L1 analysis for Plan B:**

| Threat | Vector | Mitigation |
|--------|--------|------------|
| SQL injection | --from, --to, --mode could contain SQL | CLI never constructs SQL — delegates to EventStore methods which use parameterized `?` placeholders exclusively |
| Data corruption | CLI command modifies events | All three commands are read-only. No INSERT/UPDATE/DELETE paths exist in any command function or its async runner. `grep` for write operations in new code confirms safety. |
| Path traversal | --output filename | File write for export: path is resolved relative to CWD. If path contains `../`, writes to parent directory. This is acceptable for a CLI tool (user's own filesystem). No privilege escalation risk. |
| Denial of service | Large export with no limit | Uses `read_events_iter()` streaming — never loads all events into memory. Each event is written to output as it arrives. |
| Information disclosure | Unhandled exception traceback | All sync commands wrap async calls in try/except: `typer.echo(f"Error: {exc}", err=True)` then `raise typer.Exit(code=1)`. No raw tracebacks leak to user. |
| Ctrl+C handling | Stale resources on cancellation | `tail` catches `asyncio.CancelledError` for clean exit. `export` uses try/finally to close file handles. |
</threat_model>
