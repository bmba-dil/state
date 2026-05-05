"""`state daemon start/stop/status/install/uninstall/logs` CLI commands.

Task 055.3: ``state daemon install`` and ``state daemon uninstall`` wired to the
OS service definition generator.

Task 058.1: ``state daemon start``, ``stop``, ``restart`` — daemon lifecycle.
Task 058.2: ``state daemon status`` — running daemon health snapshot.
Task 058.3: ``state daemon logs`` — log file tailing with --follow.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from src.state_daemon.pid import (
    is_pid_alive,
    read_pid_file,
    release_pid_file,
)
from src.state_daemon.service import (
    _service_file_path as _svc_def_path,
    current_platform_name,
    install_service,
    uninstall_service,
)
from src.state_daemon.socket import read_socket_path

app = typer.Typer(
    name="daemon",
    help="Manage the state daemon service (install, uninstall, start, stop, status, logs).",
)

console = Console()

# ————————————————————————————————————————————————
# Shared helpers
# ————————————————————————————————————————————————

_PID_PATH = ".state/daemon.pid"
_LOG_PATH = ".state/logs/daemon.log"
_MODE_PATH = ".state/mode.json"


def _is_service_installed() -> bool:
    """Return True if the OS service definition file exists on disk."""
    return os.path.isfile(_svc_def_path())


def _service_start() -> None:
    """Start the daemon via the OS service manager (launchctl / systemctl --user)."""
    if sys.platform == "darwin":
        subprocess.run(
            ["launchctl", "start", "com.state.daemon"],
            check=True,
            capture_output=False,
        )
    else:
        subprocess.run(
            ["systemctl", "--user", "start", "state-daemon.service"],
            check=True,
            capture_output=False,
        )


def _service_stop() -> None:
    """Stop the daemon via the OS service manager."""
    if sys.platform == "darwin":
        subprocess.run(
            ["launchctl", "stop", "com.state.daemon"],
            capture_output=False,
        )
    else:
        subprocess.run(
            ["systemctl", "--user", "stop", "state-daemon.service"],
            capture_output=False,
        )


def _spawn_daemon(project_root: str, socket_path: str | None = None) -> subprocess.Popen[bytes]:
    """Launch the daemon as a background subprocess.

    Uses ``python -m state_daemon``, passing --project-root and optionally
    --socket as environment overrides.
    """
    env = os.environ.copy()
    env["STATE_PROJECT_ROOT"] = project_root
    if socket_path:
        env["STATE_DAEMON_SOCKET"] = socket_path

    return subprocess.Popen(
        [sys.executable, "-m", "state_daemon", "--project-root", project_root],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # detach from the CLI process
    )


def _wait_for_pid_file(
    path: str = _PID_PATH,
    timeout: float = 15.0,
    interval: float = 0.2,
) -> dict[str, int] | None:
    """Poll for the pid file to appear and return its parsed contents.

    Returns None if the file does not appear within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = read_pid_file(path)
        if data is not None:
            return data
        time.sleep(interval)
    return None


def _sigkill_fallback(pid: int, timeout: float = 10.0) -> bool:
    """Send SIGTERM, wait *timeout* s, then SIGKILL if still alive.

    Returns True if the process exits during the SIGTERM grace period.
    """
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return True  # already gone

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True  # exited
        time.sleep(0.5)

    # Still alive — force kill
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    return False


def _resolve_daemon_socket_path() -> str | None:
    """Read the daemon socket path from .state/daemon.sock."""
    return read_socket_path()


def _read_mode() -> str | None:
    """Read the active mode from .state/mode.json."""
    try:
        with open(_MODE_PATH, "r", encoding="utf-8") as f:
            import json as _json

            raw = _json.load(f)
            return raw.get("mode")
    except (FileNotFoundError, OSError, ValueError):
        return None


def _format_uptime(start_time_ns: int) -> str:
    """Convert a monotonic start time (ns) to a human-readable uptime string."""
    elapsed_s = (time.monotonic_ns() - start_time_ns) / 1_000_000_000
    if elapsed_s < 0:
        return "0s"

    days, rem = divmod(int(elapsed_s), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return "".join(parts)


# ————————————————————————————————————————————————
# Task 058.1 — start / stop / restart
# ————————————————————————————————————————————————


@app.command(name="start")
def daemon_start() -> None:
    """Start the state daemon.

    If installed as an OS service (via ``state daemon install``), delegates
    to ``launchctl start`` (macOS) or ``systemctl --user start`` (Linux).

    Otherwise, spawns the daemon as a background subprocess and waits for
    the pid file to appear, verifying the process is alive.
    """
    try:
        if _is_service_installed():
            _service_start()
            typer.echo("✅ Daemon started via OS service manager.")
        else:
            project_root = os.getcwd()
            _spawn_daemon(project_root)
            typer.echo("Starting daemon...")

            pid_data = _wait_for_pid_file()
            if pid_data is None:
                typer.echo(
                    "❌ Daemon did not start within the expected time. "
                    "Check .state/logs/daemon.log for errors.",
                    err=True,
                )
                raise typer.Exit(code=1)

            pid = pid_data["pid"]
            if not is_pid_alive(pid, pid_data["start_time_ns"]):
                typer.echo(
                    f"❌ Daemon process (pid={pid}) exited immediately. "
                    "Check .state/logs/daemon.log for errors.",
                    err=True,
                )
                raise typer.Exit(code=1)

            socket_path = _resolve_daemon_socket_path() or "(unknown)"
            typer.echo(
                f"✅ Daemon started (pid={pid}, socket={socket_path})"
            )
    except subprocess.CalledProcessError as exc:
        typer.echo(f"❌ Failed to start daemon: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"❌ Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="stop")
def daemon_stop(*, _timeout: float = 10.0) -> None:
    """Stop the state daemon gracefully.

    Reads the pid file, sends SIGTERM, waits up to 10 s for graceful
    shutdown, then sends SIGKILL if the process is still alive.

    If no pid file is found, reports that the daemon is not running.
    """
    try:
        pid_data = read_pid_file(_PID_PATH)
        if pid_data is None:
            typer.echo("Daemon is not running (no pid file found).")
            return

        pid = pid_data["pid"]
        start_ns = pid_data["start_time_ns"]

        if not is_pid_alive(pid, start_ns):
            typer.echo("Daemon is not running (stale pid file cleaned).")
            release_pid_file(_PID_PATH)
            return

        # Attempt graceful stop via OS service manager first
        if _is_service_installed():
            try:
                _service_stop()
            except subprocess.CalledProcessError:
                pass  # fall through to direct signal

        graceful = _sigkill_fallback(pid, timeout=_timeout)
        release_pid_file(_PID_PATH)

        if graceful:
            typer.echo(f"✅ Daemon stopped (pid={pid}).")
        else:
            typer.echo(f"⚠  Daemon force-killed (pid={pid}).")
    except Exception as exc:
        typer.echo(f"❌ Error stopping daemon: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="restart")
def daemon_restart() -> None:
    """Restart the state daemon: stop + 1 s delay + start."""
    # We call the stop logic inline then re-invoke start.
    # Reading pid file
    pid_data = read_pid_file(_PID_PATH)
    if pid_data is not None:
        pid = pid_data["pid"]
        start_ns = pid_data["start_time_ns"]
        if is_pid_alive(pid, start_ns):
            if _is_service_installed():
                try:
                    _service_stop()
                except subprocess.CalledProcessError:
                    pass
            _sigkill_fallback(pid, timeout=10.0)
            release_pid_file(_PID_PATH)
            typer.echo(f"Stopped daemon (pid={pid}). Waiting 1 s...")
            time.sleep(1)
        else:
            release_pid_file(_PID_PATH)

    # Re-use start logic
    daemon_start()


# ————————————————————————————————————————————————
# Task 058.2 — status
# ————————————————————————————————————————————————


@app.command(name="status")
def daemon_status() -> None:
    """Display daemon health: pid, uptime, events count, active mode, socket path.

    Queries the pid file, .state/daemon.sock, .state/mode.json, and the
    event store.  If the daemon is not running, shows a clear message.
    """
    pid_data = read_pid_file(_PID_PATH)

    if pid_data is None:
        typer.echo("Daemon is not running (no pid file found).")
        return

    pid = pid_data["pid"]
    start_ns = pid_data["start_time_ns"]

    alive = is_pid_alive(pid, start_ns)

    table = Table(title="Daemon Status")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("pid", str(pid) if alive else f"{pid} (stale)")
    table.add_row("running", "✅ yes" if alive else "❌ no")

    if alive:
        table.add_row("uptime", _format_uptime(start_ns))
    else:
        table.add_row("uptime", "—")

    socket_path = _resolve_daemon_socket_path()
    table.add_row("socket", socket_path or "(unknown)")

    mode = _read_mode()
    table.add_row("mode", mode or "(unknown)")

    # Query event count from the event store
    try:
        from src.state_core.events import SqliteEventStore

        store = SqliteEventStore()
        count = asyncio.run(store.count_events())
        table.add_row("events", str(count))
    except Exception:
        table.add_row("events", "(unavailable)")

    console.print(table)

    if not alive:
        typer.echo(
            "\n💡 The daemon pid file exists but the process is not alive. "
            "Run `state daemon start` to launch it.",
        )


# ————————————————————————————————————————————————
# Task 058.3 — logs
# ————————————————————————————————————————————————


@app.command(name="logs")
def daemon_logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Follow mode — watch the log file for new lines (like tail -f).",
    ),
    lines: int = typer.Option(
        20,
        "--lines",
        "-n",
        help="Number of lines to show from the end of the log (default: 20).",
        min=0,
    ),
) -> None:
    """Tail the daemon log file.

    Reads ``.state/logs/daemon.log``.  If the file does not exist or is
    empty, prints an informative message.
    """
    log_path = Path(_LOG_PATH)

    if not log_path.is_file():
        typer.echo(
            f"No log file found at {_LOG_PATH} — "
            "the daemon may not have started yet."
        )
        return

    try:
        with open(log_path, "r", encoding="utf-8") as fh:
            all_lines = fh.readlines()
    except OSError as exc:
        typer.echo(f"❌ Cannot read log file: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not all_lines:
        typer.echo("Log file is empty.")
        return

    # Print last N lines
    tail_lines = all_lines[-lines:] if lines > 0 else all_lines
    for line in tail_lines:
        typer.echo(line.rstrip("\n"))

    if not follow:
        return

    # Follow mode — poll for new lines every 500 ms
    try:
        _follow_log(log_path, len(all_lines))
    except KeyboardInterrupt:
        pass  # clean exit on Ctrl+C


def _follow_log(log_path: Path, start_offset: int) -> NoReturn:
    """Poll the log file for new lines every 500 ms; print new lines as they appear."""
    last_size = log_path.stat().st_size

    with open(log_path, "r", encoding="utf-8") as fh:
        fh.seek(0, os.SEEK_END)  # start at end of what was already printed

        while True:
            line = fh.readline()
            if line:
                typer.echo(line.rstrip("\n"))
            else:
                time.sleep(0.5)
                # Check if file was truncated (rotated)
                current_size = log_path.stat().st_size
                if current_size < last_size:
                    fh.seek(0)
                last_size = current_size


# ————————————————————————————————————————————————
# Task 055.3 — install / uninstall
# ————————————————————————————————————————————————


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
