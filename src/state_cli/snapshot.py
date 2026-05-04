"""`state snapshot` CLI commands."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from state_core.snapshot import SnapshotManager, SnapshotTier

app = typer.Typer(name="snapshot", help="Snapshot management commands")
manager = SnapshotManager()


@app.command(name="track")
def snapshot_track(
    tier: str = typer.Option(..., help="Snapshot tier: step or slice"),
    ref: str = typer.Option(..., help="Reference string (e.g. arc-1/phase-2/slice-3)"),
    reason: str = typer.Option("pre_execute", help="Reason: pre_execute, pre_verify, shipped"),
    directory: str | None = typer.Option(None, help="Directory to snapshot (defaults to cwd)"),
) -> None:
    """Capture a content-addressed snapshot of a worktree."""
    worktree_dir = Path(directory) if directory else None

    async def _track() -> None:
        snap_id = await manager.track(
            tier=tier,
            ref=ref,
            reason=reason,
            worktree_dir=worktree_dir,
        )
        entry = manager.get(snap_id)
        if entry:
            result = {
                "snapshot_id": snap_id,
                "tier": entry.tier,
                "ref": entry.ref,
                "reason": entry.reason,
                "digest": entry.hash_digest[:16],
            }
            typer.echo(json.dumps(result, indent=2))

    asyncio.run(_track())


@app.command(name="list")
def snapshot_list() -> None:
    """List all snapshots, most recent first."""
    entries = manager.list()
    if not entries:
        typer.echo("No snapshots recorded.")
        return
    for entry in entries:
        typer.echo(
            f"{entry.snapshot_id:30s}  {entry.tier:6s}  "
            f"{entry.reason:13s}  {entry.ref}"
        )


@app.command(name="diff")
def snapshot_diff(
    a: str = typer.Option(..., help="First snapshot ID"),
    b: str = typer.Option(..., help="Second snapshot ID"),
) -> None:
    """Compare two snapshots by content hash."""
    result = manager.diff(a, b)
    typer.echo(json.dumps(result, indent=2))


@app.command(name="revert")
def snapshot_revert(
    snapshot_id: str = typer.Option(..., help="Snapshot ID to revert toward"),
) -> None:
    """Report the snapshot that would be used for revert.

    Note: Revert requires the worktree service to apply changes.
    This command displays snapshot metadata for manual revert.
    """
    entry = manager.get(snapshot_id)
    if entry is None:
        typer.echo(f"Snapshot not found: {snapshot_id}", err=True)
        raise typer.Exit(code=1)

    result = {
        "snapshot_id": entry.snapshot_id,
        "tier": entry.tier,
        "ref": entry.ref,
        "reason": entry.reason,
        "digest_full": entry.hash_digest,
    }
    typer.echo(json.dumps(result, indent=2))
    typer.echo("\nUse the snapshot digest to identify target state for revert.")
