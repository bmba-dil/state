---
wave: 1
depends_on: []
files_modified:
  - src/state_core/events.py
autonomous: true
---

## Plan C: Startup Repair Wiring
**Goal:** Wire `repair_aggregate_seqs()` into the event store startup so recovery happens before any seq consumer reads and before migration 0004 applies the UNIQUE index.

### Tasks

#### C.1 Add __init__ and lazy repair to SqliteEventStore
<read_first>src/state_core/events.py (full SqliteEventStore class — currently has no __init__)</read_first>
<acceptance_criteria>
`grep "def __init__" src/state_core/events.py` exits 0
`grep "_maybe_repair" src/state_core/events.py` exits 0
`grep "_repair_done" src/state_core/events.py` exits 0
`grep "_maybe_repair.*append\|_maybe_repair.*read_stream" src/state_core/events.py` exits 0
</acceptance_criteria>
<action>
Add explicit `__init__` to `SqliteEventStore` (currently has no `__init__`, uses `object.__init__`):
- Parameter: `run_repair: bool = False`
- Instance flag: `self._repair_done = False`
- Helper `_maybe_repair()`: if not `_repair_done`, call `self.repair_aggregate_seqs()`, set `_repair_done = True`, log via structlog
- Call `_maybe_repair()` at top of `append()` and `read_stream()`
- Create `run_repair_now()` public method for daemon startup to force repair before migrate
- Docstring documenting startup ordering: **repair → migrate → reconciler** (repair must run BEFORE migration 0004 to clean duplicate seq values, otherwise UNIQUE index creation will fail)

**Deployment path:**
- All existing callers use `SqliteEventStore()` with no args → `run_repair=False` → `_maybe_repair` fires on first `append()/read_stream()`
- Daemon startup: `store.run_repair_now()` before `await migrate()` ensures repair runs before migration 0004
- Tests: continue to use `SqliteEventStore()` default — `_maybe_repair` triggers on first access
</action>
**Estimated effort:** Medium
**Dependencies:** None (repair_aggregate_seqs() already exists in events.py)

#### C.2 Add structlog logging to repair actions
<read_first>src/state_core/events.py (repair_aggregate_seqs method)</read_first>
<acceptance_criteria>
`grep "logger\|log\." src/state_core/events.py | grep -i repair` exits 0 (repair actions are logged)
</acceptance_criteria>
<action>
- Add structlog logger to `SqliteEventStore`
- Log every repair action: count of aggregates repaired, stale/future seq corrections, any skipped
- Log at `_maybe_repair()` trigger: "repair_triggered" event with source (append/read_stream/run_repair_now)
</action>
**Estimated effort:** Small
**Dependencies:** C.1

#### C.3 Document Phase 006 integration boundary
<read_first>src/state_core/events.py (SqliteEventStore docstring)</read_first>
<acceptance_criteria>
`grep "Phase 006\|reconciler" src/state_core/events.py` exits 0
</acceptance_criteria>
<action>
- Add integration note to SqliteEventStore docstring:
  "Startup ordering: repair() → migrate() → reconciler(). Phase 006 reconciler MUST NOT read seq values until repair completes. This is enforced by daemon startup calling run_repair_now() before migrate()."
</action>
**Estimated effort:** Small
**Dependencies:** C.1

<threat_model>
- HIGH: Repair runs on every append if `_repair_done` flag never set. Mitigation: flag is set immediately after first repair.
- MEDIUM: Repair runs before migration 0004 — this is CORRECT. Repair cleans duplicate seq values first, then migration 0004 creates UNIQUE index.
- HIGH: Migration 0004 fails on startup because crash left duplicate seqs in events table. Mitigation: run_repair_now() before migrate() — repair fixes duplicates, THEN migration applies UNIQUE index.
</threat_model>

---
