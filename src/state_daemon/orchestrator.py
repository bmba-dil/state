"""Daemon startup orchestrator — enforces repair → migrate → reconciler ordering."""

from __future__ import annotations

import structlog

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.reconciler import StartupReconciler
from src.state_core.sync_mirror import SyncEventMirror

log = structlog.get_logger(__name__)


async def startup() -> None:
    """Run the full startup sequence: repair → migrate → reconciler.

    Each step is gated on the previous step completing without error.

    Step 1 (repair) uses ``run_repair_now()`` instead of lazy repair to
    ensure aggregate_seq consistency BEFORE migration 0004 creates the
    UNIQUE(aggregate_id, seq) index. Step 2 runs all pending SQL migrations.
    Step 3 creates a ``StartupReconciler`` and calls ``start()``, which
    performs an immediate reconciliation sweep of unsent events before
    starting the periodic background sweep loop.
    """
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
