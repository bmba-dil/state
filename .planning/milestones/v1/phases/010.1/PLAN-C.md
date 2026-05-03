---
phase: "010.1"
plan: "C"
type: "gap_closure"
autonomous: false
wave: 1
depends_on: []
files_modified:
  - "src/state_daemon/orchestrator.py"
  - "__init__.py"
requirements:
  - "EVT-04"
---

<objective>
Create `src/state_daemon/orchestrator.py` — the daemon startup orchestrator that enforces the correct startup order: `repair() → migrate() → reconciler()`. Currently this ordering is only documented in docstrings inside `SqliteEventStore` but no module enforces it at the daemon level. The orchestrator provides a single `startup()` async entry point that the daemon calls on boot, ensuring Phase 006's `StartupReconciler` never reads stale seq values before repair completes, and that migration 0004 (UNIQUE index) never runs before duplicate seq values are cleaned.
</objective>

<tasks>

### Task 1: Create orchestrator.py with `startup()` entry point

<read_first>
- `src/state_core/events.py` (lines 50–104: `run_repair_now()` method and docstrings about startup ordering)
- `src/state_core/migrations.py` (full file: `migrate()` function)
- `src/state_core/reconciler.py` (full file: `StartupReconciler` class — `start()` method)
- `src/state_daemon/__init__.py` (current content — minimal, just a docstring)
</read_first>

<action>
1. Create `src/state_daemon/orchestrator.py` with the following structure:

   ```python
   """Daemon startup orchestrator — enforces repair→migrate→reconciler ordering.
   
   The daemon calls orchestrator.startup() on boot. The orchestrator is
   responsible for:
   1. Running repair_aggregate_seqs() BEFORE migration 0004 (which creates
      the UNIQUE(aggregate_id, seq) index — stale dupes would crash it).
   2. Applying all pending SQL migrations.
   3. Starting the StartupReconciler sweep loop for unsent events.
   
   This module exists because Phase 006 (startup reconciliation) and Phase 007
   (crash recovery) were implemented independently, leaving the ordering
   constraint specified only in docstrings. The orchestrator makes it
   mechanically enforced.
   """
   
   from __future__ import annotations
   
   import structlog
   
   from src.state_core.events import SqliteEventStore
   from src.state_core.migrations import migrate
   from src.state_core.reconciler import StartupReconciler
   from src.state_core.sync_mirror import SyncEventMirror
   
   log = structlog.get_logger(__name__)
   
   
   async def startup(
       store: SqliteEventStore | None = None,
       mirror: SyncEventMirror | None = None,
   ) -> StartupReconciler | None:
       """Run the full daemon startup sequence: repair → migrate → reconciler.
       
       Args:
           store: SqliteEventStore instance. If None, creates a new one.
           mirror: SyncEventMirror instance. If None, reconciler is skipped.
       
       Returns:
           The StartupReconciler instance if mirror was provided, None otherwise.
       """
       if store is None:
           store = SqliteEventStore()
       
       # Step 1: Repair — clean duplicate/gapped seq values BEFORE migration
       # 0004 creates the UNIQUE(aggregate_id, seq) index. If repair is not
       # run first, the index creation will fail on duplicate seq values.
       log.info("startup_repair")
       repairs = await store.run_repair_now()
       if repairs:
           log.info("startup_repair_completed", count=len(repairs))
       else:
           log.info("startup_repair_noop")
       
       # Step 2: Migrate — apply all pending SQL migrations in order.
       # This must run AFTER repair (for migration 0004) and BEFORE the
       # reconciler (so the reconciler sees the full schema).
       log.info("startup_migrate")
       await migrate()
       log.info("startup_migrate_completed")
       
       # Step 3: Reconciler — start the unsent-event replay sweeper.
       # Runs after repair+migrate so it reads consistent data with
       # the full schema in place.
       if mirror is None:
           log.info("startup_skip_reconciler", reason="no mirror provided")
           return None
       
       reconciler = StartupReconciler(db=store, mirror=mirror)
       log.info("startup_reconciler_start")
       await reconciler.start()
       log.info("startup_reconciler_started")
       return reconciler
   ```

2. Run `ruff check src/state_daemon/orchestrator.py --fix` and `mypy src/state_daemon/orchestrator.py` to confirm no issues.

3. Run `pytest tests/ -x` to confirm no regressions (the orchestrator is not yet called by anything — this is purely additive).
</action>

<acceptance_criteria>
- `test -f src/state_daemon/orchestrator.py` returns 0 (file exists)
- `grep -c "async def startup" src/state_daemon/orchestrator.py` returns 1
- `grep -c "run_repair_now" src/state_daemon/orchestrator.py` returns 1
- `grep -c "migrate" src/state_daemon/orchestrator.py` returns 1
- `grep -c "StartupReconciler" src/state_daemon/orchestrator.py` returns 1
- `python3 -c "import ast; ast.parse(open('src/state_daemon/orchestrator.py').read()); print('syntax ok')"` prints "syntax ok"
- `mypy src/state_daemon/orchestrator.py` exits 0
</acceptance_criteria>

</tasks>

### Task 2: Wire orchestrator import into daemon `__init__.py`

<read_first>
- `src/state_daemon/__init__.py` (current content)
</read_first>

<action>
1. Update `src/state_daemon/__init__.py` to re-export the `startup` function so daemon consumers can import from the package:

   ```python
   """Daemon package — always-on user service for state."""
   
   from __future__ import annotations
   
   from src.state_daemon.orchestrator import startup
   
   __all__ = ["startup"]
   ```

2. Run `ruff check src/state_daemon/__init__.py --fix` and `mypy src/state_daemon/__init__.py` to confirm no issues.
</action>

<acceptance_criteria>
- `grep -c "from src.state_daemon.orchestrator import startup" src/state_daemon/__init__.py` returns 1
- `python3 -c "from src.state_daemon import startup; print('ok')"` prints "ok"
- `mypy src/state_daemon/__init__.py` exits 0
</acceptance_criteria>

</tasks>

<verification>
1. Full import test: `python3 -c "from src.state_daemon.orchestrator import startup; print('orchestrator ok')"` succeeds.
2. `mypy src/state_daemon/` exits 0.
3. `ruff check src/state_daemon/` passes.
4. Full test suite: `pytest tests/ -x` passes (no regressions — orchestrator is not yet wired into daemon main).
</verification>

<must_haves>
- `startup()` must call repair BEFORE migrate, and migrate BEFORE reconciler — in that exact order
- `startup()` must accept optional `store` and `mirror` parameters for testability (inject mocks)
- `startup()` must return the `StartupReconciler` instance (or `None`) so callers can manage its lifecycle
- The orchestrator must be importable from `src.state_daemon` via `__init__.py`
- No changes to existing `SqliteEventStore`, `migrate()`, or `StartupReconciler` code
</must_haves>

<threat_model>
**ASVS L1 coverage:**
- **V1.2 (Authentication):** The orchestrator does not handle credentials or authentication. It delegates to `SqliteEventStore` and `StartupReconciler`, which manage their own auth context.
- **V5.1 (Input Validation):** `startup()` accepts optional pre-constructed `store` and `mirror` instances — no untrusted input parsing occurs in the orchestrator.
- **V9.1 (Data Protection):** The orchestrator controls startup order. If an attacker could inject a malicious `mirror` instance, the reconciler would emit events to the attacker's endpoint. This is defended by (a) the `mirror` parameter only being set by the daemon's own main entry point, (b) the existing Project CLAUDE.md requirement for chmod-0600 on `.state/` secrets. No new vector introduced.
- **V12.2 (Secure Deployment):** The orchestrator enforces that repair runs before migration 0004 — this prevents a class of data-loss bugs where a migration fails mid-startup due to un-repaired duplicate seq values. This is an integrity improvement.
</threat_model>
