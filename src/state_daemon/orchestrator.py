"""Daemon startup orchestrator — enforces redactor → import → repair → migrate → reconciler ordering.

Step 4 (Phase 050) starts the HTTP server on a unix domain socket,
wiring the JSON-RPC 2.0 router so downstream phases can register handlers.
"""

from __future__ import annotations

import asyncio
import os
import signal

import aiosqlite
import litellm
import structlog

from state_core.auth import import_from_opencode
from state_core.database import get_connection
from state_core.deps import Deps
from state_core.events import SqliteEventStore
from state_core.http_client import build_shared_client
from state_core.migrations import migrate
from state_core.observability import assert_redactor_attached, install
from state_core.projector import Projector
from state_core.reconciler import StartupReconciler
from state_core.sync_mirror import SyncEventMirror

from src.state_daemon.auth_manager import AuthRefreshLoop, AuthStatusHandler
from src.state_daemon.logging import configure_daemon_logging
from src.state_daemon.middleware import ModeMiddleware, load_mode_config, get_current_mode
from src.state_daemon.pid import acquire_pid_file, release_pid_file
from src.state_daemon.recovery import CrashRecovery, InFlightStep
from src.state_daemon.router import JsonRpcRouter
from src.state_daemon.server import DaemonServer
from src.state_daemon.socket import resolve_socket_path, write_socket_path
from src.state_daemon.sse import SseBus, SseClientManager, SseEndpointHandler

log = structlog.get_logger(__name__)

# Module-level server reference for graceful shutdown via signal handlers.
_server: DaemonServer | None = None

# Module-level auth refresh loop reference for graceful shutdown.
_auth_refresh: AuthRefreshLoop | None = None

# Event store reference — set during startup so the SIGHUP handler can emit events.
_event_store: SqliteEventStore | None = None

# Pid file path — set during startup so the shutdown handler can clean it up.
_pid_path: str | None = None

# Project root — set during startup so the SIGHUP handler can reload mode config.
_project_root: str | None = None


async def startup() -> None:
    """Run the full startup sequence: redactor → logging → import → repair → migrate → reconciler → HTTP server.

    Step 0 (Phase 020 / AUTH-10) installs the root-logger token
    redactor and self-checks that it is attached. If the redactor
    is not attached, RedactorNotAttached fires and the daemon
    process exits before any other I/O (P0-14 defense layer 2).

    Step 0.0-logging (Phase 056 / DAE-07) configures structured daemon
    logging with rotation, redaction, and configurable output mode
    (JSON for production, human-readable for dev).  Must run AFTER the
    redactor is attached (so the file handler inherits redaction) and
    BEFORE any I/O-driven steps (so all subsequent log records land in
    .state/logs/daemon.log).

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

    # Step 0.0-logging (Phase 056 / DAE-07): configure daemon structured logging
    # with rotation, redaction, and mode selection.  Must run AFTER redactor install
    # (so the file handler inherits redaction) and BEFORE pid acquisition (so
    # startup messages are captured in the log file).
    configure_daemon_logging()

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
    global _event_store
    _event_store = store
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

    # Step 3.5 (Phase 054): Create SSE broadcast bus and wire post-commit
    # callback so every state.* event appended to the event store is
    # automatically fanned out to all connected SSE subscribers.
    log.info("startup: initializing SSE bus")
    sse_client_manager = SseClientManager()
    sse_bus = SseBus(sse_client_manager)
    store.add_post_commit_callback(sse_bus.on_event)
    sse_handler = SseEndpointHandler(sse_client_manager)
    log.info("startup: SSE bus wired to event store post-commit")

    # Step 3.6 (Phase 057 / DAE-08): Crash recovery — replay event log
    # through the projector to rebuild projections and resume in-flight
    # Steps that were executing/verifying at crash time.  Runs AFTER
    # SSE bus wiring (so recovery events are broadcast) and BEFORE
    # server start (so no connections are accepted until recovered).
    log.info("startup: running crash recovery")
    projector = Projector(store)
    recovery = CrashRecovery(projector)
    recovery_result = await recovery.recover()

    if not recovery_result.projection_valid:
        log.critical(
            "crash_recovery.projection_invalid",
            events_replayed=recovery_result.events_replayed,
        )
        raise SystemExit(1)

    log.info(
        "startup: recovery replay complete",
        events_replayed=recovery_result.events_replayed,
        in_flight_count=len(recovery_result.in_flight_steps),
        last_event_id=recovery_result.last_event_id,
    )

    if recovery_result.in_flight_steps:
        # Build InFlightStep records from the step IDs and resume them.
        # Status is read from the steps cache table (already rebuilt).
        in_flight_steps = await _build_in_flight_steps(
            recovery_result.in_flight_steps,
        )
        resume_actions = await recovery.resume_in_flight(
            store, in_flight_steps,
        )
        log.info(
            "startup: in-flight steps resumed",
            count=len(resume_actions),
        )
    else:
        log.info("startup: no in-flight steps to resume")

    # Step 4 (Phase 050 / 052): Resolve deterministic socket path, start
    # HTTP server, and persist the path for worker/client discovery.
    # The JsonRpcRouter starts empty — downstream phases call add_method().
    log.info("startup: resolving socket path")
    router = JsonRpcRouter()
    project_root = os.environ.get("STATE_PROJECT_ROOT", os.getcwd())
    global _project_root
    _project_root = project_root
    socket_path = os.environ.get("STATE_DAEMON_SOCKET", resolve_socket_path(project_root))

    log.info(
        "daemon.startup.begin",
        pid=os.getpid(),
        project_root=project_root,
        socket_path=socket_path,
    )

    # Step 4.5 (Phase 053): Load mode config and wrap router with
    # ModeMiddleware — the 6th layer of defense-in-depth for mode
    # isolation.  Cross-mode write requests are rejected with 403
    # before they reach any JSON-RPC handler.
    log.info("startup: loading mode config")
    mode_config = load_mode_config(project_root)
    middleware = ModeMiddleware(router, mode_config)
    log.info("startup: mode middleware enabled", active_mode=mode_config.mode)

    _server = DaemonServer(socket_path, middleware, sse_handler=sse_handler)
    try:
        await _server.start()
    except OSError as exc:
        log.critical(
            "daemon.startup.socket_in_use",
            socket_path=socket_path,
            error_type=type(exc).__name__,
            hint="Address already in use — another daemon may be running. "
                 "Check `ps aux | grep state` for a stale process.",
        )
        raise

    # Persist the resolved socket path for worker discovery (Phase 061).
    write_socket_path(socket_path)

    # Step 5 (Phase 059): Wire auth manager — status endpoint + background refresh.
    # Workers query /auth/status over HTTP; they never read auth.json directly.
    log.info("startup: wiring auth manager")
    auth_status = AuthStatusHandler()
    _server.add_get_handler("/auth/status", auth_status.handle)
    log.info("startup: auth status endpoint registered at /auth/status")

    global _auth_refresh
    _auth_refresh = AuthRefreshLoop()
    await _auth_refresh.start()
    log.info("startup: auth refresh loop started")

    # Register signal handlers for graceful shutdown.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _schedule_shutdown)
        except NotImplementedError:
            # Signal handlers not supported on this platform (e.g. Windows
            # without win32 support) — graceful shutdown via other mechanisms.
            pass

    # Register SIGHUP handler for mode hot-reload.
    try:
        loop.add_signal_handler(signal.SIGHUP, _schedule_mode_reload)
        log.info("startup: SIGHUP handler registered for mode hot-reload")
    except (NotImplementedError, AttributeError):
        # SIGHUP not available on this platform (e.g. Windows) —
        # mode changes still work via daemon restart.
        pass

    log.info("startup: complete", socket_path=socket_path)


async def _build_in_flight_steps(step_ids: list[str]) -> list[InFlightStep]:
    """Query the steps cache table for status of each in-flight step ID.

    Called after crash recovery rebuilds the steps projection, so the
    cache table is guaranteed fresh.

    Args:
        step_ids: Step IDs detected as in-flight by CrashRecovery.

    Returns:
        InFlightStep records with status populated from the cache.
    """
    if not step_ids:
        return []

    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        # Build a parameterized IN clause
        placeholders = ", ".join("?" for _ in step_ids)
        cursor = await db.execute(
            f"SELECT id, state, slice_id, title FROM steps "
            f"WHERE id IN ({placeholders}) "
            f"ORDER BY id ASC",
            tuple(step_ids),
        )
        rows = await cursor.fetchall()
        return [
            InFlightStep(
                step_id=row["id"],
                status=row["state"],
                slice_id=row.get("slice_id"),
                title=row.get("title"),
            )
            for row in rows
        ]


def _schedule_mode_reload() -> None:
    """Schedule mode config reload from a SIGHUP signal handler.

    Re-reads .state/mode.json and, if the mode actually changed,
    emits a state.mode.activated event through the event store
    so SSE subscribers (plugin, workers) can hot-reload their
    MCP registrations.  No event is emitted when the mode is
    unchanged (no-op SIGHUP).

    Must be a plain function because asyncio signal handlers are
    called synchronously from the event loop.
    """
    if _project_root is not None:
        log.info("daemon.reload.signal_received", signal="SIGHUP")
        try:
            old_mode = get_current_mode()
            new_config = load_mode_config(_project_root)
            new_mode = new_config.mode
            if old_mode != new_mode:
                log.info(
                    "daemon.reload.mode_changed",
                    old_mode=old_mode,
                    new_mode=new_mode,
                )
                if _event_store is not None:
                    asyncio.create_task(_emit_mode_event(old_mode, new_mode))
                else:
                    log.warning(
                        "daemon.reload.no_event_store",
                        old_mode=old_mode,
                        new_mode=new_mode,
                    )
            else:
                log.debug(
                    "daemon.reload.mode_unchanged",
                    mode=new_mode,
                )
        except Exception as exc:
            log.error("daemon.reload.failed", error=str(exc))
    else:
        log.warning("daemon.reload.no_project_root", signal="SIGHUP")


async def _emit_mode_event(old_mode: str, new_mode: str) -> None:
    """Emit state.mode.activated event through the event store.

    This is called as a background task from the SIGHUP handler
    when the mode changes. SSE fan-out is automatic via the
    post-commit callback wired to SseBus in startup().

    Args:
        old_mode: The mode before the change (from get_current_mode()).
        new_mode: The mode after the change (from the reloaded ModeConfig).
    """
    global _event_store
    if _event_store is None:
        log.warning("daemon.mode_event.no_store")
        return
    from src.state_core.schema import ModeActivatedData
    data = ModeActivatedData(old_mode=old_mode, new_mode=new_mode)
    await _event_store.append(
        aggregate_type="mode",
        aggregate_id=f"mode-{new_mode}",
        event_type="state.mode.activated",
        data=data.model_dump(),
        mode="kernel",
    )
    log.info(
        "daemon.mode_event.emitted",
        old_mode=old_mode,
        new_mode=new_mode,
    )


def _schedule_shutdown() -> None:
    """Schedule graceful server shutdown from a signal handler.

    Must be a plain function (not a coroutine) because asyncio signal
    handlers are called synchronously from the event loop.
    """
    if _server is not None:
        log.info("daemon.shutdown.signal_received")
        asyncio.create_task(_shutdown_server())


async def _shutdown_server() -> None:
    """Stop the HTTP server, auth refresh loop, and clean up."""
    global _server
    global _auth_refresh
    global _pid_path

    # Stop the auth refresh loop first (no-op if not started).
    if _auth_refresh is not None:
        await _auth_refresh.stop()
        _auth_refresh = None
        log.info("daemon.shutdown.auth_refresh_stopped")

    if _server is not None:
        await _server.stop()
        _server = None
        log.info("daemon.shutdown.complete")
    if _pid_path is not None:
        release_pid_file(_pid_path)
        _pid_path = None
