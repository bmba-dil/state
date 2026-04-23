"""Typer app: `state db init`, `state auth login`, `state mode set`, etc."""

from __future__ import annotations

import asyncio

import typer

from src.state_core.migrations import migrate as _migrate

app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")

db_app = typer.Typer(name="db", help="Database management commands")
app.add_typer(db_app)


@db_app.command(name="init")
def db_init() -> None:
    """Initialize the event store database by applying all pending migrations."""
    asyncio.run(_migrate())
    typer.echo("Database initialized: all migrations applied.")
