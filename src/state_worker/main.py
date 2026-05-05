"""Per-session worker spawned by the plugin shim.

The worker is a session-scoped process that:
1.  Resolves its session identity (060.1)
2.  Discovers the daemon socket via ``.state/daemon.sock``
3.  Health-checks the daemon before registering
4.  Registers SIGTERM/SIGINT handlers for graceful shutdown
5.  Provides the ``attach_to_daemon()`` bridge (extended by Phase 061)
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import tempfile
from pathlib import Path

import structlog

from state_worker.bridge import SseBridge
from state_worker.hooks import HookQueue
from state_worker.hot_state import HotState
from state_worker.logging import configure_worker_logging
from state_worker.session import SessionIdentity, resolve_session_id

from state_core.version import PLUGIN_VERSION
from state_daemon.socket import read_socket_path

log = structlog.get_logger(__name__)

_WORKER_PID_DIR = ".state"


# ---------------------------------------------------------------------------
# Task 060.2 — Daemon health-check + attach
# ---------------------------------------------------------------------------


async def attach_to_daemon(session: SessionIdentity, timeout: float = 2.0) -> bool:
    """Discover the daemon socket and health-check it.

    Returns ``True`` if the daemon is reachable and returns a valid
    ``GET /health`` response, ``False`` otherwise.

    Args:
        session: The current :class:`SessionIdentity`.
        timeout: Connection timeout in seconds.
    """
    socket_path = read_socket_path()
    if socket_path is None:
        log.warning("worker.daemon.not_found", reason="no_socket_marker")
        return False

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(socket_path),
            timeout=timeout,
        )
    except (ConnectionRefusedError, FileNotFoundError):
        log.warning("worker.daemon.connection_refused", socket_path=socket_path)
        return False
    except asyncio.TimeoutError:
        log.warning("worker.daemon.timeout", socket_path=socket_path, timeout=timeout)
        return False
    except OSError as exc:
        log.warning("worker.daemon.os_error", socket_path=socket_path, error=str(exc))
        return False

    try:
        request = (
            f"GET /health HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"X-State-Session-Id: {session.session_id}\r\n"
            f"X-State-Plugin-Version: {PLUGIN_VERSION}\r\n"
            f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        # Read status line.
        response_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not response_line:
            log.warning("worker.daemon.empty_response")
            return False

        decoded = response_line.decode().strip()
        if decoded.startswith("HTTP/1.1 426"):
            log.warning(
                "worker.daemon.version_incompatible",
                response=decoded,
            )
            return False
        if not decoded.startswith("HTTP/1.1 200"):
            log.warning("worker.daemon.unexpected_status", response=decoded)
            return False

        # Skip headers.
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if line in (b"\r\n", b"\n", b""):
                break

        # Read body.
        body_bytes = await asyncio.wait_for(reader.readexactly(23), timeout=timeout)
        body_text = body_bytes.decode()
        if '"status": "ok"' not in body_text:
            log.warning("worker.daemon.unexpected_body", body=body_text)
            return False

    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
        log.warning("worker.daemon.read_error")
        return False
    except Exception:
        log.exception("worker.daemon.unexpected_error")
        return False
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    log.info("worker.daemon.health_ok", session_id=session.session_id)
    return True


# ---------------------------------------------------------------------------
# Task 060.3 — Worker main entry point + signal handling
# ---------------------------------------------------------------------------


_shutdown_event: asyncio.Event = asyncio.Event()


def _handle_shutdown_signal(signum: int) -> None:
    """Set the shutdown event so the main loop exits gracefully."""
    sig_name = signal.Signals(signum).name
    log.info("worker.signal.received", signal=sig_name, signum=signum)
    _shutdown_event.set()


def _write_pid_file(session_id: str, pid: int) -> str:
    """Atomically write the worker PID file to ``.state/worker-{session_id}.pid``."""
    os.makedirs(_WORKER_PID_DIR, exist_ok=True)

    pid_path = os.path.join(_WORKER_PID_DIR, f"worker-{session_id}.pid")

    fd, tmp_path = tempfile.mkstemp(
        dir=_WORKER_PID_DIR, prefix=".worker_pid_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(pid))
        os.replace(tmp_path, pid_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return pid_path


def _cleanup_pid_file(pid_path: str) -> None:
    """Remove the worker PID file."""
    try:
        os.unlink(pid_path)
    except FileNotFoundError:
        pass


async def main() -> None:
    """Worker main entry point — bootstrap, attach to daemon, wait for shutdown.

    Command-line usage::

        python -m state_worker [--session-id STATE-xyz]
    """
    # --- Parse CLI args ---
    session_id_arg: str | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--session-id" and i + 1 < len(args):
            session_id_arg = args[i + 1]
            i += 2
        else:
            i += 1

    # --- Resolve session identity ---
    session = resolve_session_id(session_id_arg)
    log.info(
        "worker.startup",
        session_id=session.session_id,
        pid=session.pid,
        project_root=session.project_root,
    )

    # --- Write PID file ---
    pid_path = _write_pid_file(session.session_id, session.pid)
    log.info("worker.pid_file", path=pid_path)

    # --- Configure per-worker logging (Phase 066) ---
    configure_worker_logging(
        session_id=session.session_id,
        project_root=session.project_root,
    )

    # --- Register signal handlers ---
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_shutdown_signal, sig)

    # --- Attach to daemon ---
    daemon_ok = await attach_to_daemon(session)
    bridge: SseBridge | None = None
    bridge_task: asyncio.Task[None] | None = None
    hot_state = HotState()
    hook_queue = HookQueue()

    if not daemon_ok:
        log.warning(
            "worker.daemon.unavailable",
            session_id=session.session_id,
        )
    else:
        log.info(
            "worker.daemon.attached",
            session_id=session.session_id,
        )

        socket_path = read_socket_path()
        if socket_path is not None:
            bridge = SseBridge(session)
            bridge.on_event = hot_state.apply_event
            bridge_task = asyncio.create_task(bridge.connect(socket_path))
            log.info("worker.bridge.started", session_id=session.session_id)

    # --- Wait for shutdown signal ---
    await _shutdown_event.wait()

    # --- Teardown ---
    log.info("worker.shutdown", session_id=session.session_id)

    # Flush pending hook events before disconnecting from daemon.
    socket_path = read_socket_path()
    if socket_path is not None and hook_queue.flush_count > 0:
        await hook_queue.flush_pending(socket_path)

    if bridge is not None:
        await bridge.disconnect()
        if bridge_task is not None:
            bridge_task.cancel()
            try:
                await bridge_task
            except asyncio.CancelledError:
                pass

    _cleanup_pid_file(pid_path)


if __name__ == "__main__":
    asyncio.run(main())
