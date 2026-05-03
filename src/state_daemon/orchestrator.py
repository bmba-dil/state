"""Daemon startup orchestrator — enforces redactor → repair → migrate → reconciler ordering."""

from __future__ import annotations

import structlog

from state_core.events import SqliteEventStore
from state_core.migrations import migrate
from state_core.observability import assert_redactor_attached, install
from state_core.reconciler import StartupReconciler
from state_core.sync_mirror import SyncEventMirror

log = structlog.get_logger(__name__)


async def startup() -> None:
    """Run the full startup sequence: redactor → repair → migrate → reconciler.

    Step 0 (Phase 020 / AUTH-10) installs the root-logger token
    redactor and self-checks that it is attached. If the redactor
    is not attached, RedactorNotAttached fires and the daemon
    process exits before any other I/O (P0-14 defense layer 2).

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

    store = SqliteEventStore()

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
    mirror = SyncEventMirror()
    reconciler = StartupReconciler(db=store, mirror=mirror)
    await reconciler.start()

    log.info("startup: complete")
