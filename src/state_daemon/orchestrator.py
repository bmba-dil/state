"""Daemon startup orchestrator — enforces redactor → import → repair → migrate → reconciler ordering.

Step 4 (Phase 050) starts the HTTP server on a unix domain socket,
wiring the JSON-RPC 2.0 router so downstream phases can register handlers.
"""

from __future__ import annotations

import asyncio
import os
import signal

import litellm
import structlog

from state_core.auth import import_from_opencode
from state_core.deps import Deps
from state_core.events import SqliteEventStore
from state_core.http_client import build_shared_client
from state_core.migrations import migrate
from state_core.observability import assert_redactor_attached, install
from state_core.reconciler import StartupReconciler
from state_core.sync_mirror import SyncEventMirror

from src.state_daemon.pid import acquire_pid_file, release_pid_file
from src.state_daemon.router import JsonRpcRouter
from src.state_daemon.server import DaemonServer

log = structlog.get_logger(__name__)

# Phase 050 default socket path — finalized in Phase 052.
# In the project root (where .state/ lives).
_DEFAULT_SOCKET_PATH = ".state/daemon.sock"

# Module-level server reference for graceful shutdown via signal handlers.
_server: DaemonServer | None = None

# Pid file path — set during startup so the shutdown handler can clean it up.
_pid_path: str | None = None


async def startup() -> None:
    """Run the full startup sequence: redactor → import → repair → migrate → reconciler → HTTP server.

    Step 0 (Phase 020 / AUTH-10) installs the root-logger token
    redactor and self-checks that it is attached. If the redactor
    is not attached, RedactorNotAttached fires and the daemon
    process exits before any other I/O (P0-14 defense layer 2).

    Step 0.5 (Phase 021 / AUTH-11) runs the opencode auth.json
    importer. It MUST run AFTER the redactor is attached (so any
    structlog calls during import are filtered) and BEFORE store-
    driven steps (so its auth.imported events flow through the same
    SqliteEventStore + SyncEventMirror dual-write path as runtime
    events). Importer failure is non-fatal — wrapped in try/except;
    daemon boot continues with a WARN log. Foreign data tolerance:
    opencode is read-only from state's perspective, and a corrupt
    opencode auth.json must never block our daemon.

    Each subsequent step is gated on the previous step completing
    without error.

    Step 1 (repair) uses ``run_repair_now()`` instead of lazy repair to
    ensure aggregate_seq consistency BEFORE migration 0004 creates the
    UNIQUE(aggregate_id, seq) index. Step 2 runs all pending SQL migrations.
    Step 3 creates a ``StartupReconciler`` and calls ``start()``, which
    performs an immediate reconciliation sweep of unsent events before
    starting the periodic background sweep loop.

    Step 4 (Phase 050) boots the HTTP server on a unix domain socket and
    registers SIGTERM/SIGINT handlers for graceful shutdown.  The server
    runs as a background task — startup() returns after binding so the
    caller can keep the event loop alive.
    """
    global _server
    global _pid_path

    # Step 0 (Phase 020 / AUTH-10): install + verify redactor BEFORE any other I/O.
    # Failure raises RedactorNotAttached which is fatal — the daemon process
    # exits with a non-zero status. P0-14 secret-leak prevention (defense layer 2).
    install()
    assert_redactor_attached()

    # Step 0.0 (Phase 051 / DAE-03): acquire pid file BEFORE any network bind.
    # P0-15 defense: stale pid detection prevents a zombie pid-file from blocking
    # daemon restart.  Returns False if another instance is already running.
    _pid_path = os.environ.get("STATE_DAEMON_PID", ".state/daemon.pid")
    if not acquire_pid_file(_pid_path):
        log.critical("startup.pid_file_denied", path=_pid_path)
        raise SystemExit(1)

    # Step 0.1 (Phase 023 / PRV-06): build shared HTTP client + Deps container.
    # Must be created inside an async function (not at module level) to avoid
    # asyncio event loop binding issues.  Available to all subsequent steps.
    deps = Deps(http_client=build_shared_client())
    litellm.aclient_session = deps.http_client  # best-effort; works for non-Anthropic providers
    log.info("startup: shared httpx client created", max_connections=100)

    store = SqliteEventStore()
    mirror = SyncEventMirror()

    # Step 0.5 (Phase 021 / AUTH-11): first-run import from opencode auth.json.
    # Runs AFTER redactor attach (logs filtered) and BEFORE repair (importer's
    # auth.imported events dual-write through the same path). Non-fatal: any
    # exception is logged and boot continues.
    try:
        imported = await import_from_opencode(store=store, mirror=mirror)
        if imported:
            log.info("startup: opencode importer added credentials", count=len(imported))
        else:
            log.info("startup: opencode importer no-op")
    except Exception as e:
        # Defensive WARN — error_type only; never log the exception payload (could leak bytes).
        log.warning(
            "daemon.startup.importer_failed",
            error_type=type(e).__name__,
        )

    # Step 1: Repair aggregate seq
    log.info("startup: repairing aggregate sequences")
    repairs = await store.run_repair_now()
    if repairs:
        log.info("startup: repairs applied", count=len(repairs))
    else:
        log.info("startup: no repairs needed")

    # Step 2: Apply pending migrations
    log.info("startup: applying migrations")
    await migrate()

    # Step 3: Reconcile unsent events
    log.info("startup: reconciling unsent events")
    reconciler = StartupReconciler(db=store, mirror=mirror)
    await reconciler.start()

    # Step 4 (Phase 050): Start HTTP server on unix domain socket.
    # Socket path is a temporary default; Phase 052 will finalize it.
    # The JsonRpcRouter starts empty — downstream phases call add_method().
    log.info("startup: starting HTTP server")
    router = JsonRpcRouter()
    socket_path = os.environ.get("STATE_DAEMON_SOCKET", _DEFAULT_SOCKET_PATH)
    _server = DaemonServer(socket_path, router)
    await _server.start()

    # Register signal handlers for graceful shutdown.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _schedule_shutdown)
        except NotImplementedError:
            # Signal handlers not supported on this platform (e.g. Windows
            # without win32 support) — graceful shutdown via other mechanisms.
            pass

    log.info("startup: complete", socket_path=socket_path)


def _schedule_shutdown() -> None:
    """Schedule graceful server shutdown from a signal handler.

    Must be a plain function (not a coroutine) because asyncio signal
    handlers are called synchronously from the event loop.
    """
    if _server is not None:
        log.info("daemon.shutdown.signal_received")
        asyncio.create_task(_shutdown_server())


async def _shutdown_server() -> None:
    """Stop the HTTP server and clean up."""
    global _server
    global _pid_path
    if _server is not None:
        await _server.stop()
        _server = None
        log.info("daemon.shutdown.complete")
    if _pid_path is not None:
        release_pid_file(_pid_path)
        _pid_path = None
