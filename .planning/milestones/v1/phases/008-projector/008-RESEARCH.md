# RESEARCH: Phase 008 — Projector (Steps/Slices/Concepts Cache Rebuild from Events)

<summary>
Phase 008 delivers a CQRS-style projection engine that rebuilds the `steps`, `slices`, and `concepts` cache tables from the authoritative `events` log. The projector reads events in seq order, applies pure projection handlers to derive current state, and writes the result through the existing single-writer pattern. A `state events rebuild-projections` Typer command orchestrates a full replay: truncate cache tables, replay all events, and materialize the projections. The projector also supports a "live" mode where it updates projections as a post-append side effect inside the same transaction, keeping caches always consistent with the event log.
</summary>

<tech_stack>
| Component | Detail | Confidence |
|-----------|--------|------------|
| **Language** | Python 3.12+ (async/await) | [VERIFIED: pyproject.toml line 4] |
| **Event store** | `SqliteEventStore` in `src/state_core/events.py` with `append()`, `read_stream()`, `get_unsynced_events()` | [VERIFIED: src/state_core/events.py] |
| **DB driver** | `aiosqlite>=0.22.1` — async, single-thread, WAL mode | [VERIFIED: pyproject.toml line 13] |
| **Projection cache tables** | `steps`, `slices`, `concepts` defined in migration `0002_cache.sql` | [VERIFIED: CONTEXT.md from Phase 003-B] |
| **Audit tables (not rebuildable)** | `decisions`, `tool_calls`, `auth_rotations` — append-only, kept as-is during rebuild | [VERIFIED: ARCHITECTURE.md §11.3 line 934] |
| **CLI framework** | `typer>=0.15` in `src/state_cli/main.py` — `state db init` already exists as pattern | [VERIFIED: src/state_cli/main.py] |
| **Pattern for migration files** | Numbered `.sql` files in `.state/migrations/`, pattern `0001_init.sql`, `0002_cache.sql`, `0003_add_mode_column.sql`, `0004_uniq_agg_seq.sql` | [VERIFIED: src/state_core/migrations.py line 60] |
| **Deterministic JSON** | `json.dumps(data, sort_keys=True, separators=(",", ":"))` | [VERIFIED: src/state_core/events.py line 173] |
| **Structlog** | `log = structlog.get_logger(__name__)` throughout codebase | [VERIFIED: src/state_core/reconciler.py line 13] |
| **Existing test pattern** | `tmp_path` + `monkeypatch.setenv("STATE_DB_PATH", ...)` for DB isolation | [VERIFIED: tests/test_events.py lines 23-32] |
</tech_stack>

<patterns>

### Pattern 1: CQRS Projection Engine

The projector follows the classic CQRS pattern:

```
events table (source of truth)
    │
    ├──► projection handlers (pure functions: state × event → new_state)
    │       ├── step_projection_handler(state, event) → new_state
    │       ├── slice_projection_handler(state, event) → new_state
    │       └── concept_projection_handler(state, event) → new_state
    │
    └──► materialized cache tables (steps, slices, concepts)
```

Key rules:
- **Events are the only source of truth.** Projections are derived views. [VERIFIED: ARCHITECTURE.md §11.3 line 934: "Rebuilding from events: steps, slices, concepts, tool_calls are all rebuildable by replaying events table"]
- **Handlers are pure functions.** Given the same (state, event) input, they always produce the same output. No side effects — no I/O, no datetime, no randomness. This is required by EVT-06. [VERIFIED: REQUIREMENTS.md EVT-06]
- **No event is ever deleted or modified.** Projections are rebuilt by replaying, not by patching history.

### Pattern 2: Event→Projection Mapping Per Aggregate

| Projection Table | Source Events | Projection Logic |
|---|---|---|
| `steps` | `state.step.discussed` | Step enters DISCUSSING state; store title, approach_summary |
| `steps` | `state.step.planned` | Update state to PLANNING; store goal, verify_contract |
| `steps` | `state.step.executed` | Update state to EXECUTING; store changes_summary |
| `steps` | `state.step.verify_started` | Update state to VERIFYING |
| `steps` | `state.step.verify_passed` | Update state to DONE; store duration_ms |
| `steps` | `state.step.verify_failed` | Update state back to EXECUTING; store failure reason |
| `steps` | `state.step.advanced` | Update state to next lifecycle stage |
| `steps` | `state.step.blocked` | Update state to BLOCKED |
| `steps` | `state.step.snapshotted` | Update snapshot_hash; no state change |
| `steps` | `state.step.reverted` | Update state to previous; store revert reason |
| `slices` | `state.slice.planned` | Create slice row; store title, goal |
| `slices` | `state.slice.worktree_ready` | Update worktree_dir, worktree_branch |
| `slices` | `state.slice.shipped` | Update state to SHIPPED; store snapshot_hash |
| `slices` | `state.slice.reverted` | Update state; store revert reason |
| `concepts` | `state.concept.introduced` | Create concept row; store subject_id, prerequisites |
| `concepts` | `state.concept.observed` | Update observation/classification data |
| `concepts` | `state.concept.drilled` | Update mastery_probability, scaffold_level, last_drilled_at |
| `concepts` | `state.concept.mastered` | Update mastery_probability |
| `concepts` | `state.concept.reviewed` | Update mastery_delta |

[VERIFIED: src/state_core/schema.py event types + Phase 003 CONTEXT.md table schemas]

### Pattern 3: Two-Mode Projection Strategy

The projector operates in two modes:

**Mode A: Live projection (post-append side effect)**
- After `EventStore.append()` commits the event, update the corresponding projection table
- Uses the same `get_connection()` factory (but a separate connection — the append's connection is closed after commit)
- Updates are best-effort and must never block the append path
- Can be synchronous in same transaction (if projection table is upserted in the append transaction) or fire-and-forget after commit

**Mode B: Full rebuild (state events rebuild-projections)**
1. Truncate all projection cache tables (`steps`, `slices`, `concepts`)
2. Read ALL events from `events` table ordered by `id ASC` (ULID = time order) or `seq ASC`
3. For each event, route to the appropriate projection handler
4. `INSERT OR REPLACE` into the corresponding cache table
5. Audit/apppend-only tables (`decisions`, `tool_calls`, `auth_rotations`) are NOT touched during rebuild

**Critical design question:** Should live projections update in the same transaction as the event append, or as a separate post-commit step? The single-writer constraint suggests same-transaction for consistency, but this adds latency to `append()`. The `commit-then-emit` pattern from Phase 004 suggests post-commit updates are the preferred pattern for non-critical side effects.

### Pattern 4: Single-Writer Constraint

The "single writer" means:
- **The EventStore (`SqliteEventStore.append()`) is the only code that creates event rows** [VERIFIED: ARCHITECTURE.md line 76: "The daemon is the only writer to planning tables"]
- Projection tables can be written by the projector (they are caches, not primary data)
- But projection writes must go through the same database connection factory and respect the same transactional discipline
- During rebuild, the projector reads events via `read_stream()` / direct SQL and writes to cache tables directly (not through `append()` — that would create new events, which is wrong)
- The key invariant: never write a projection row without having read the events that justify it

[VERIFIED: ROADMAP.md line 53: "Rebuildable projections written through the single writer"]

### Pattern 5: Rebuild Idempotency and Determinism

- `DROP` + replay must produce the same projection regardless of how many times it runs
- Handlers are deterministic: same events → same projection state → same upserted rows
- The rebuild command must complete within a single transaction if possible (or use explicit `BEGIN IMMEDIATE` + `COMMIT`)
- If the rebuild crashes mid-way, the next rebuild starts from scratch (DROP + replay again)
- No cleanup of half-written state needed — the DROP at the start handles this

[VERIFIED: REQUIREMENTS.md EVT-06: "Event payloads are deterministic; replay is bit-identical"]

### Pattern 6: Module Structure (patterned after reconciler.py)

Following the existing module pattern in `src/state_core/reconciler.py`:

```python
"""Event-sourced projection engine — rebuilds cache tables from events.

Three projection handlers (step, slice, concept) map event types to
cache-table upserts. The Projector class orchestrates full rebuilds.
"""

from __future__ import annotations

import structlog

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore

log = structlog.get_logger(__name__)
```

This follows the exact pattern of `src/state_core/reconciler.py` (lines 1-18): module docstring, `from __future__ import annotations`, structlog setup, imports from `state_core.database` and `state_core.events`.

[VERIFIED: src/state_core/reconciler.py lines 1-18]

</patterns>

<pitfalls>

### P0-9 (Crash During Rebuild)
**Risk:** If the rebuild process crashes after dropping cache tables but before replaying all events, the cache tables are empty or partially populated.
**Mitigation:** Use a two-phase approach: (1) `BEGIN IMMEDIATE`, (2) DELETE FROM cache tables, (3) replay events and INSERT/REPLACE, (4) COMMIT. A crash during step 2-3 causes a rollback — the old cache state is preserved. On retry, the user calls `rebuild-projections` again. The initial DROP+replay has no partial-write problem because SQLite's transaction ensures atomicity.
**Alternatively:** Create temp tables, rebuild into them, then RENAME-swap with the originals. This avoids any window where cache tables are empty. However, temp tables add complexity and the transactional approach is sufficient since the rebuild is a CLI command, not a hot-path operation.

### Determinism Violation in Projection Handlers
**Risk:** A projection handler accidentally calls `datetime.now()` or `random` to generate a value, breaking replay determinism (EVT-06).
**Mitigation:** Projection handlers MUST NOT call any non-deterministic function. They derive all values from the event payload and the existing projection state. Code review must enforce: no `datetime`, `random`, `uuid`, `time`, `secrets` imports in projection handler code. **Belt-and-suspenders:** Add a grep check in CI: `grep -rn "datetime\.now\|random\." src/state_core/projector.py`.

### Event Ordering During Rebuild
**Risk:** Events replayed in wrong order produce inconsistent projections (e.g., `state.step.verify_passed` replayed before `state.step.executed`).
**Mitigation:** Rebuild reads events ordered by `id ASC` (ULID = time-ordered) or `(aggregate_id, seq) ASC`. The `seq` field within an aggregate is monotonically increasing (enforced by Phase 004/007). For cross-aggregate ordering, use ULID ordering which is timestamp-ordered.

### Projection Table Schema Drift
**Risk:** As the project evolves, new event types may require new columns in projection tables. The current schema only covers known event types from the Phase 002 event taxonomy.
**Mitigation:** Projection handlers should silently ignore unknown event types (future-proofing). Add a new migration (0005+) when projection table schemas need to change. The rebuild process always replays ALL events, so new columns automatically get populated by the handlers.

### Phase 009 CLI Overlap
**Risk:** Phase 008's CLI (`state events rebuild-projections`) and Phase 009's CLI (`state events tail`, `state events replay`, `state events export`) share the `state events` namespace. They need to be compatible and share the same Typer sub-app.
**Mitigation:** Phase 008 should create the `events` Typer sub-app in `state_cli/main.py` and add `rebuild-projections` as a subcommand. Phase 009 will add more subcommands to the same app. Alternatively, Phase 008 creates a minimal stub that Phase 009 extends. Coordinate with Phase 009's planned structure.

### Event Type Prefix Assumptions
**Risk:** The projector routes events by type string (e.g., `state.step.executed`). If new event types are added later that don't follow the `state.<aggregate>.<action>` pattern, the routing could miss them.
**Mitigation:** Use the `aggregate_type` field from the event row (not the type string prefix) for routing decisions. The `aggregate_type` is a controlled vocabulary: `"arc"`, `"phase"`, `"slice"`, `"step"`, `"concept"`, `"drill"`, `"decision"`, `"auth"`, `"mode"`. [VERIFIED: src/state_core/schema.py lines 20-31]

</pitfalls>

<dependencies>

| Dependency | Current Version | Usage in Phase 008 | Confidence |
|-------------|-----------------|-------------------|------------|
| `python3` stdlib | 3.12+ | Core language — async/await, `sqlite3` | [VERIFIED: pyproject.toml line 4] |
| `aiosqlite>=0.22.1` | in pyproject.toml | Database access for read/replay | [VERIFIED: pyproject.toml line 13] |
| `structlog>=25.1` | in pyproject.toml | Logging rebuild progress | [VERIFIED: pyproject.toml line 23] |
| `typer>=0.15` | in pyproject.toml | CLI command: `state events rebuild-projections` | [VERIFIED: pyproject.toml line 24] |
| `pytest>=8.4.0` | dev dep | Testing | [VERIFIED: pyproject.toml line 29] |
| `pytest-asyncio>=1.3.0` | dev dep | Async test support | [VERIFIED: pyproject.toml line 30] |
| `hypothesis>=6.120` | dev dep | Property-based tests for replay determinism | [VERIFIED: pyproject.toml line 32] |

**No new external dependencies required.** The Phase 008 projector uses only tools already in the stack. [ASSUMED]

</dependencies>

<alternatives>

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Same-transaction projection update** — Projection tables updated inside the same `BEGIN IMMEDIATE` as the event append | Strong consistency; projections always reflect latest event | Slower append latency; projection logic in the hot path | **Adopt for live mode** — but make projection handlers injectable so they can be skipped (e.g., during bulk rebuilds) |
| **Post-commit async projection** — Append commits, then fire-and-forget a task to update projections | Minimal append latency; projection errors don't affect event durability | Eventual consistency; window where projections lag behind events | **Reject for v1** — same-transaction is simpler and the single-writer constraint favors it. Can switch to async if latency becomes an issue |
| **Separate projection writer process** — A dedicated process reads events from SQLite and updates projections | Clean separation of concerns; can be scaled independently | Complexity; adds inter-process coordination; violates the "single writer" pattern for projections | **Reject** — the entire architecture avoids multi-process for projections; the projector is a module in state_core used by the daemon |
| **JSON-file projections** (like MENTAL-MODEL.json) — Write projections as JSON files instead of SQLite tables | Portable; human-readable; easy to diff | No query capability; no JOINs; already have SQLite tables designed for this | **Reject** — Phase 003 already created the SQLite cache tables. Use them. JSON file projections are future milestones (v18+) |
| **Trigger-based projection** — Use SQLite triggers on the `events` table to auto-maintain projection tables | Zero application code; always consistent | Triggers are opaque; hard to test; not portable; cannot do "rebuild from scratch" without dropping/creating triggers | **Reject** — application-layer handlers are testable and debuggable |
| **Single SQL VIEW for each projection** — Define `CREATE VIEW steps_view AS SELECT ... FROM events ...` | Zero data duplication; always fresh | Complex SQL; no indexing on derived columns; event data is JSON so extracting fields is painful | **Reject** — pre-materialized cache tables are the right choice for query performance |

</alternatives>

<open_questions>

1. **Should the projection update happen inside the same transaction as `append()` or as a post-commit hook?** [MEDIUM]
   - Same-transaction: stronger consistency, but adds latency to `append()`
   - Post-commit (same pattern as `SyncEventMirror.emit`): async, eventual consistency, but simpler
   - The single-writer constraint plus the existing `commit-then-emit` pattern (Phase 004 CONTEXT.md) suggests post-commit is the preferred approach for non-critical side effects. But projections being materially consistent with events is arguably critical.
   - **Recommendation:** Start with same-transaction by passing projection handlers into `append()` as optional callbacks. This gives the best consistency. If latency is a problem, switch to async.

2. **Does `state events rebuild-projections` need a `--dry-run` flag?** [LOW]
   - Dry-run would replay events without writing, showing what would change
   - Useful for debugging projection logic, but adds complexity
   - **Recommendation:** Skip for v1. The rebuild is fast and safe (idempotent). Add dry-run if users need debugging support.

3. **How to handle projection of `tool_calls` table?** [MEDIUM]
   - ARCHITECTURE.md line 934 says `tool_calls` is "rebuildable by replaying events table"
   - But `tool_calls` stores data not present in event payloads (call_id, args, output, verdict)
   - Some `tool_calls` data might only exist in the live tool execution context, not in events
   - **Clarification needed:** Are `tool_calls` projections fed by dedicated `state.tool_call.*` events, or are they populated by side-channel data?
   - **Recommendation:** Exclude `tool_calls` from Phase 008 scope. Focus only on `steps`, `slices`, `concepts` per the ROADMAP.md description.

4. **Should the projector also handle the `arc` and `phase` aggregate projections?** [LOW]
   - The ROADMAP.md only mentions `steps`, `slices`, `concepts`
   - `arc` and `phase` have simpler lifecycles (planned → in_progress → shipped/changed)
   - Their data is primarily in markdown files, not SQLite cache tables
   - **Recommendation:** Exclude arcs and phases from Phase 008. They're handled by the build kernel directly (Phase 016+).

5. **What event ordering should the rebuild use?** [MEDIUM]
   - Option A: `ORDER BY id ASC` (ULID time ordering) — gives global ordering
   - Option B: `ORDER BY seq ASC` (per-aggregate seq, but what global order?)
   - Option C: `ORDER BY aggregate_id, seq ASC` (grouped by aggregate)
   - Since projections are per-aggregate (each step, slice, or concept is an independent state machine), grouping by aggregate simplifies handler logic
   - **Recommendation:** Option C — events grouped by `(aggregate_id, seq) ASC`. Each aggregate's events are replayed in order, and aggregates are independent so ordering between them doesn't matter.

6. **Rebuild performance target — 10,000 events in < 1 second?** [LOW]
   - Each event handler is a simple dict read + optional upsert
   - SQLite handles 10k inserts easily within a single transaction
   - **Recommendation:** No special optimization needed for v1. Test with 10k events as a verification step (Phase 010).

7. **Should migration 0005 create any new tables or indexes for the projector?** [LOW]
   - The cache tables already exist (0002_cache.sql)
   - No new tables needed unless the projector needs a tracking table (e.g., `projector_checkpoint` for incremental rebuilds)
   - **Recommendation:** No migration needed for Phase 008 unless the projector adds metadata tracking. Keep it schema-change-free.

</open_questions>

## Recommended Implementation Strategy

### Module: `src/state_core/projector.py` (NEW)

Follow the exact pattern of `src/state_core/reconciler.py`:

```python
"""Event-sourced projection engine — rebuilds cache tables from events.

Projection handlers map event types to cache-table upserts. The Projector
class supports two modes:
1. Live update: called after append() to update projections in same txn
2. Rebuild: truncates cache tables, replays all events, materializes state
"""

from __future__ import annotations

import structlog
from typing import Any

from src.state_core.database import get_connection
from src.state_core.events import SqliteEventStore

log = structlog.get_logger(__name__)

# ── Projection handler registry ──────────────────────────────────────────

HANDLERS: dict[str, _HandlerFn] = {}  # event_type → handler


def _register_handler(event_type: str):
    """Decorator that registers a projection handler for *event_type*."""
    def decorator(fn: _HandlerFn) -> _HandlerFn:
        HANDLERS[event_type] = fn
        return fn
    return decorator


# ── Step projection handlers ─────────────────────────────────────────────

@_register_handler("state.step.discussed")
def _handle_step_discussed(state: dict | None, data: dict) -> dict:
    # ... map event data to step cache row fields ...
    pass

# ... more handlers ...

# ── Projector class ──────────────────────────────────────────────────────

class Projector:
    """Orchestrates projection rebuilds and live updates.

    Args:
        db: The event store for reading events.
    """

    def __init__(self, db: SqliteEventStore) -> None:
        self._db = db

    async def rebuild_all(self) -> int:
        """Truncate and rebuild all projections from events.

        Returns:
            Number of events processed.
        """
        # 1. BEGIN IMMEDIATE
        # 2. DELETE FROM steps, slices, concepts
        # 3. SELECT * FROM events ORDER BY aggregate_id, seq ASC
        # 4. For each event, route to handler and INSERT OR REPLACE
        # 5. COMMIT
        ...

    async def apply_event(self, event_row: dict) -> None:
        """Apply a single event to the projection tables (live mode).
        
        Called after append() to keep projections in sync.
        """
        # Route event_row["type"] to its handler
        # UPSERT into the appropriate cache table
        ...
```

### CLI: Extend `state_cli/main.py`

Add an `events` Typer sub-app and `rebuild-projections` command — following the exact `state db init` pattern from Phase 003:

```python
events_app = typer.Typer(name="events", help="Event store management commands")
app.add_typer(events_app)


@events_app.command(name="rebuild-projections")
def rebuild_projections() -> None:
    """Rebuild steps/slices/concepts cache tables from events."""
    import asyncio
    from src.state_core.events import SqliteEventStore
    from src.state_core.projector import Projector
    from src.state_core.migrations import migrate

    asyncio.run(_do_rebuild())


async def _do_rebuild() -> None:
    await migrate()
    store = SqliteEventStore()
    projector = Projector(db=store)
    count = await projector.rebuild_all()
    typer.echo(f"Projections rebuilt: {count} events processed.")
```

[VERIFIED: src/state_cli/main.py lines 1-21 for the pattern]

### Migration Impact

- **No new migration needed** for Phase 008. The cache tables already exist from migration `0002_cache.sql`.
- If Phase 008 adds checkpoint tracking for incremental rebuilds, a `0005_projector_checkpoint.sql` migration would be needed:
  ```sql
  CREATE TABLE IF NOT EXISTS projector_checkpoint (
      projection_name TEXT PRIMARY KEY,
      last_event_id   TEXT NOT NULL,
      updated_at      TEXT NOT NULL
  );
  ```

### Test Strategy (patterned after tests/test_reconciler.py)

| Test Class | Focus | Pattern |
|-----------|-------|---------|
| `TestStepProjection` | Each `state.step.*` event produces correct step cache row | Isolated DB, append event, verify step row fields |
| `TestSliceProjection` | Each `state.slice.*` event produces correct slice cache row | Same pattern |
| `TestConceptProjection` | Each `state.concept.*` event produces correct concept cache row | Same pattern |
| `TestFullRebuild` | 10 events → rebuild_all → all 3 cache tables are correct | Append events to store, call rebuild_all, verify all rows |
| `TestRebuildIdempotency` | rebuild_all twice produces identical results | Run twice, assert rows are byte-identical |
| `TestRebuildAfterCrash` | Simulate crash mid-rebuild → no partial state | Use monkeypatch on connection, verify rollback |
| `TestDeterminism` | Identical event sequences produce identical projections | Two identical sequences → byte-identical cache tables |
| `TestHypothesisProperty` | Randomized event sequences → invariant checks | property-based: all handlers are pure |
| `TestCLI` | `state events rebuild-projections --help` | Subprocess or import check |

[VERIFIED: tests/test_reconciler.py lines 1-50 for fixture patterns; tests/test_events.py lines 23-39 for DB isolation pattern]

### Key Risk Checklist

- [ ] Projection handlers are pure (no datetime, random, I/O) — EVT-06
- [ ] Rebuild uses a single transaction for atomicity — P0-9 mitigation
- [ ] Unknown event types are silently ignored (future-proof)
- [ ] CLI command follows the existing `state db init` pattern
- [ ] Tests cover: single-event projection, multi-event replay, rebuild idempotency, crash recovery
- [ ] No new external dependencies
- [ ] The `aggregate_type` field is used for routing, not string prefix parsing
</recommended_implementation>
</projector>
</content>
