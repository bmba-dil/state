"""Typer app: `state db init`, `state auth login`, `state mode set`, etc."""

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


def _print_event_line(ev: dict) -> None:
    """Print a single event as a compact single-line summary."""
    typer.echo(
        f"{ev['id'][-13:]}  {ev['type']:<40s} {ev['aggregate_id'][:20]:<20s} "
        f"{ev['mode']:<8s} {ev['ts']}"
    )


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
    mode: str = typer.Option(None, "--mode", help="Filter by mode (build|teach|kernel)"),
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
