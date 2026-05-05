"""Typer app: `state db init`, `state auth login`, `state mode set`, etc."""

from __future__ import annotations

import asyncio
import json
import os
import typing
from pathlib import Path

import typer

from src.state_core.migrations import migrate as _migrate
from src.state_core.projector import Projector as _Projector
from src.state_core.schema import BUILD_SUBTREE, RUNTIME_MODES, TEACH_SUBTREE

app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")

db_app = typer.Typer(name="db", help="Database management commands")
app.add_typer(db_app)

events_app = typer.Typer(name="events", help="Event store management commands")
app.add_typer(events_app)

# Phase 022 — auth sub-app
from src.state_cli.auth import auth_app  # noqa: E402
app.add_typer(auth_app)

# Phase 040 — snapshot sub-app
from src.state_cli.snapshot import app as snapshot_app  # noqa: E402
app.add_typer(snapshot_app)

# Phase 049 — dag sub-app
from src.state_cli.dag import app as dag_app  # noqa: E402
app.add_typer(dag_app)

# Phase 055 — daemon sub-app
from src.state_daemon.cli import app as daemon_app  # noqa: E402
app.add_typer(daemon_app)

# Phase 097 — mode sub-app
mode_app = typer.Typer(name="mode", help="Mode management commands")
app.add_typer(mode_app)


@db_app.command(name="init")
def db_init() -> None:
    """Initialize the event store database by applying all pending migrations."""
    asyncio.run(_migrate())
    typer.echo("Database initialized: all migrations applied.")


@events_app.command(name="rebuild-projections")
def rebuild_projections() -> None:
    """Rebuild steps/slices/concepts cache tables from events."""
    try:
        asyncio.run(_do_rebuild_projections())
    except Exception as exc:
        typer.echo(f"Error rebuilding projections: {exc}", err=True)
        raise typer.Exit(code=1) from exc


async def _do_rebuild_projections() -> None:
    """Async implementation of rebuild-projections."""
    from src.state_core.events import SqliteEventStore

    await _migrate()
    store = SqliteEventStore()
    projector = _Projector(db=store)
    count = await projector.rebuild_all()
    typer.echo(f"Projections rebuilt: {count} events processed.")


# Re-exported from schema.py for backwards compatibility within this module.
VALID_MODES = RUNTIME_MODES


def _validate_mode(value: str | None) -> str | None:
    """Validate --mode argument against allowed values."""
    if value is not None and value not in VALID_MODES:
        raise typer.BadParameter(
            f"Invalid mode '{value}'. Must be one of: {', '.join(sorted(VALID_MODES))}"
        )
    return value


def _print_event_line(ev: dict) -> None:
    """Print a single event as a compact single-line summary."""
    typer.echo(
        f"{ev['id'][-13:]}  {ev['type']:<40s} {ev['aggregate_id'][:20]:<20s} "
        f"{ev['mode']:<8s} {ev['ts']}"
    )


@events_app.command(name="tail")
def tail(
    from_id: str = typer.Option(None, "--from", help="ULID offset to start from"),
    mode: str | None = typer.Option(None, "--mode", callback=_validate_mode, help="Filter by mode (build, teach, kernel)"),
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


@events_app.command(name="replay")
def replay(
    from_id: str = typer.Option(..., "--from", help="ULID offset to start from (required)"),
    to_id: str = typer.Option(None, "--to", help="ULID offset to stop at"),
    mode: str | None = typer.Option(None, "--mode", callback=_validate_mode, help="Filter by mode (build, teach, kernel)"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max events to replay (0 = unlimited)"),
) -> None:
    """Replay events from a ULID offset."""
    try:
        asyncio.run(_do_replay(from_id=from_id, to_id=to_id, mode=mode, limit=limit))
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


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


@events_app.command(name="export")
def export(
    from_id: str = typer.Option(None, "--from", help="ULID offset to start from"),
    to_id: str = typer.Option(None, "--to", help="ULID offset to stop at"),
    mode: str | None = typer.Option(None, "--mode", callback=_validate_mode, help="Filter by mode (build, teach, kernel)"),
    output_format: str = typer.Option("jsonl", "--format", help="Export format (jsonl only)"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
) -> None:
    """Export events in JSONL format."""
    if output_format != "jsonl":
        raise typer.BadParameter("Only --format=jsonl is supported in this version")
    try:
        asyncio.run(_do_export(
            from_id=from_id, to_id=to_id, mode=mode, output=output,
        ))
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


async def _do_export(
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
    output: str | None = None,
) -> None:
    """Export events in JSONL format."""
    import sys

    from src.state_core.events import SqliteEventStore

    store = SqliteEventStore()
    count = 0

    if output is not None:
        with open(output, "w", encoding="utf-8") as fh:
            async for ev in store.read_events_iter(from_id=from_id, to_id=to_id, mode=mode):
                line = json.dumps(ev, sort_keys=True, separators=(",", ":"))
                fh.write(line + "\n")
                count += 1
        typer.echo(f"Exported {count} events to {output}")
    else:
        async for ev in store.read_events_iter(from_id=from_id, to_id=to_id, mode=mode):
            line = json.dumps(ev, sort_keys=True, separators=(",", ":"))
            sys.stdout.write(line + "\n")
            count += 1


# ── Mode management ────────────────────────────────────────────────────────


@mode_app.command(name="init")
def mode_init(
    mode: str = typer.Argument(..., help="Mode to initialise: build, teach, or both"),
) -> None:
    """Create .state/mode.json with the specified mode.

    This is a first-time setup command. It creates the .state/ directory
    if needed and writes a mode.json file with strict 0600 permissions.

    Valid modes: build, teach, both
    Internal-only mode "kernel" is NOT accepted by this command.
    """
    from src.state_core.schema import validate_mode_config

    # Validate the mode before touching the filesystem.
    # validate_mode_config raises ValueError on invalid input,
    # which is caught and surfaced as a user-facing error.
    try:
        cfg = validate_mode_config({"mode": mode})
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Determine project root: walk up from cwd to find .state/ directory.
    # If .state/ doesn't exist anywhere upward, use cwd.
    project_root = Path.cwd()
    current = project_root
    while current != current.parent:
        if (current / ".state").is_dir():
            project_root = current
            break
        current = current.parent

    # Create .state/ directory and mode.json with 0600 permissions
    state_dir = project_root / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    mode_path = state_dir / "mode.json"
    with open(mode_path, "w", encoding="utf-8") as f:
        json.dump({"mode": cfg.mode}, f)
    os.chmod(mode_path, 0o600)

    # Create mode-specific subtrees — the 2nd layer of 6-layer defense-in-depth.
    # These directories serve as a physical, non-bypassable signal of the
    # active mode.  Later layers (daemon middleware, import-graph lint) use
    # their presence as an enforcement gate.
    if cfg.mode in ("build", "both"):
        (state_dir / BUILD_SUBTREE.removeprefix(".state/")).mkdir(parents=True, exist_ok=True)
    if cfg.mode in ("teach", "both"):
        (state_dir / TEACH_SUBTREE.removeprefix(".state/")).mkdir(parents=True, exist_ok=True)

    typer.echo(f"Mode initialised to '{cfg.mode}' ({mode_path})")
