"""`state daemon start/stop/status/install/uninstall` CLI commands.

Task 055.3: ``state daemon install`` and ``state daemon uninstall`` wired to the
OS service definition generator.
"""

from __future__ import annotations

import sys

import typer

from src.state_daemon.service import (
    current_platform_name,
    install_service,
    uninstall_service,
)

app = typer.Typer(
    name="daemon",
    help="Manage the state daemon service (install, uninstall, start, stop, status).",
)


@app.command(name="install")
def daemon_install() -> None:
    """Install the state daemon as an OS-level user service.

    macOS: writes ``~/Library/LaunchAgents/com.state.daemon.plist`` and calls
    ``launchctl load``.

    Linux: writes ``~/.config/systemd/user/state-daemon.service``, then runs
    ``systemctl --user enable && systemctl --user start``.

    The daemon will start automatically at login and survive user logout.
    """
    try:
        install_service()
        platform = current_platform_name()
        typer.echo(
            f"✅ State daemon installed on {platform}. "
            "The daemon will start automatically at login."
        )
    except FileNotFoundError as exc:
        typer.echo(
            f"❌ Required command not found: {exc}. "
            "Is launchctl (macOS) or systemctl (Linux) available?",
            err=True,
        )
        raise typer.Exit(code=1)
    except PermissionError as exc:
        typer.echo(f"❌ Permission denied: {exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"❌ Failed to install service: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command(name="uninstall")
def daemon_uninstall() -> None:
    """Remove the state daemon OS service definition.

    macOS: ``launchctl unload`` + remove plist.
    Linux: ``systemctl --user stop && systemctl --user disable`` + remove unit file.
    """
    try:
        uninstall_service()
        platform = current_platform_name()
        typer.echo(
            f"🗑  State daemon uninstalled from {platform}. "
            "The daemon will no longer start at login."
        )
    except Exception as exc:
        typer.echo(f"❌ Failed to uninstall service: {exc}", err=True)
        raise typer.Exit(code=1)
