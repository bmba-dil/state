"""Daemon startup orchestrator — enforces redactor → import → repair → migrate → reconciler ordering."""

from __future__ import annotations

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

log = structlog.get_logger(__name__)


async def startup() -> None:
    """Run the full startup sequence: redactor → import → repair → migrate → reconciler.

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
    """
    # Step 0 (Phase 020 / AUTH-10): install + verify redactor BEFORE any other I/O.
    # Failure raises RedactorNotAttached which is fatal — the daemon process
    # exits with a non-zero status. P0-14 secret-leak prevention (defense layer 2).
    install()
    assert_redactor_attached()

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

    log.info("startup: complete")
