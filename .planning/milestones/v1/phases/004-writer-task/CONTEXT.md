# CONTEXT: Phase 004 — Writer task (single-writer aiosqlite + commit-then-emit)

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

Implement `EventStore.append()` with per-aggregate seq enforcement, monotonic guarantee, deterministic clock injection. The commit-then-emit pattern (writing to SQLite before any SyncEvent mirror) is established here; the mirror emission itself is Phase 005.

## Requirements

- **EVT-01**: Daemon writes every domain event to `.state/events.sqlite` (WAL, synchronous=NORMAL) before mirroring to opencode `SyncEvent`
- **EVT-02**: SQLite is the authoritative event source; daemon reads history from SQLite only
- **EVT-03**: Event sequence is monotonic per stream (Arc / Phase / Slice / Step / concept / learner); crash-recovery reconciles gaps
- **EVT-06**: Event payloads are deterministic (no `datetime.now()` / randomness in handlers); replay is bit-identical

## Locked Decisions

### Append Interface (`EventStore` protocol + `SqliteEventStore`)

- **Extended protocol:** Add `mode: Mode = "kernel"` and `ts: str | None = None` parameters to `append()`. These are optional for backward compat with callers that don't need mode filtering or deterministic injection.
- **Return value:** `append()` returns the event ID string (ULID) — enables caller to reference the event immediately.
- **ULID generation:** Use `python-ulid` library `ULID()` constructor (already a dependency from Phase 002). No ID collision detection — ULID's 122-bit randomness makes collision probability negligible.
- **`id_` override:** Add optional `id_: str | None = None` parameter for test injection. When set, use the provided ULID instead of generating one. This enables deterministic test assertions.
- **`ts` semantics:** When `ts` is `None`, do NOT call `datetime.now()`. Use a deterministic fallback (empty string `""` or `None` stored as NULL) — caller MUST provide a timestamp in production. This guarantees replay determinism.

### Seq Enforcement

- **Source of truth:** `aggregate_seq` table (already created by Phase 003 migration).
- **Pattern:** Within `append()`:
  1. `SELECT seq FROM aggregate_seq WHERE aggregate_id = ?` — returns current seq or 0 if no row.
  2. New seq = current + 1 (first event for an aggregate gets seq 1).
  3. Write event row with new seq.
  4. `INSERT OR REPLACE INTO aggregate_seq (aggregate_id, seq, updated_at) VALUES (?, ?, ?)`.
- **Atomicity:** All four operations happen in a single transaction. If any step fails, the entire append is rolled back.
- **Seq starts at 1:** First event for any aggregate always gets `seq=1`. This differs from `EventEnvelope` default of `seq=0` — the writer overrides the seq at write time.
- **No seq gap detection:** Gap detection is Phase 007's responsibility (P0-9). Phase 004 ensures monotonicity (seq never decreases) but not gap-free continuity.

### Data Serialization

- **JSON serialization:** `data` dict is serialized via `json.dumps(data)` at append time. The `events` table stores it as TEXT.
- **JSON deserialization:** `read_stream()` deserializes via `json.loads()` when yielding rows.
- **Serializer consistency:** Use `orjson` if already in deps, otherwise stdlib `json`. The key invariant is deterministic serialization — use `json.dumps(data, sort_keys=True, separators=(",", ":"))` to ensure bit-identical JSON for identical data dicts.

### Transaction Pattern

- **Explicit commit:** `await db.commit()` after all writes. No reliance on context manager auto-commit.
- **Async safety:** `aiosqlite` uses a single thread for all operations, so no concurrent write races within the same connection. External race prevention (across daemon restarts, multiple processes) is handled by `filelock` in later phases — Phase 004 assumes single-writer process.
- **Rollback on error:** If any step in `append()` raises, the context manager's `__aexit__` rolls back the transaction automatically (aiosqlite behavior).

### Mode Handling

- **Mode stored as-is:** The `mode` parameter is written to the `events` table's column. No validation against the Mode literal at the store layer — validation is the schema/domain layer's concern.
- **Default mode:** `"kernel"` — matching `EventEnvelope` default in `schema.py`.

### Error Handling

- **Let constraint violations propagate:** SQLite UNIQUE/PRIMARY KEY constraints on `aggregate_seq.aggregate_id` and `events.id` will raise `aiosqlite.IntegrityError` on violation. Let them propagate — the caller handles the exception.
- **No custom error hierarchy in Phase 004:** Custom `EventStoreError` types can be added in a later phase if callers need typed error handling. Phase 004 keeps it simple.

### Code Location

- **Primary file:** `src/state_core/events.py` — the `SqliteEventStore` class.
- **EventStore protocol update:** Same file, add `mode` and `ts` parameters to `append()` signature.
- **Migration:** `.state/migrations/0003_add_mode_column.sql` — adds `mode` column to `events` table (Phase 003 schema didn't include it).
- **New test file:** `tests/test_events.py` — comprehensive async tests for the writer.

### Plan Split (2 plans)

| Plan | Wave | Focus | Depends on |
|------|------|-------|------------|
| **A** | 1 | `SqliteEventStore.append()` core implementation + seq enforcement + deterministic clock | Phase 002, Phase 003 |
| **B** | 2 | Comprehensive test suite: monotonicity, seq enforcement, determinism, mode filtering, protocol conformance | A |

### Code Conventions

- Every `.py` file: `from __future__ import annotations` at top
- All SQL identifiers: `snake_case`
- Timestamps as ISO 8601 text in UTC (`T` separator, `Z` suffix)
- JSON stored as text via `json.dumps(data, sort_keys=True, separators=(",", ":"))`
- `async with get_connection()` for all DB access
- Docstrings on all public methods
- No `datetime.now()` or `random` in event-store code (Phase 004 is the enforcement point for EVT-06)

### Testing Approach

- Use `tmp_path` fixture + monkeypatch `STATE_DB_PATH` for isolated databases (same pattern as Phase 003 tests)
- Apply migrations before each test via `migrate()` to ensure schema exists
- Test basic append → read_stream round trip
- Test seq enforcement across multiple appends to same aggregate
- Test seq independence across different aggregates
- Test determinism: two appends with same `id_`, `ts`, and data produce same DB row
- Test mode field is written and filterable
- Test read_stream after_seq filtering
- Hypothesis property test: for any valid aggregate_id + event_type + data, append succeeds and seq is monotonic

### P0 Pitfalls Owned

- **P0-9**: SQLite event-sequence non-monotonic under crash. Phase 004 prevents monotonicity violation within a single process (seq always increases). Full crash-recovery (gap detection + repair) is Phase 007. Phase 004's contribution: seq is always written inside the same transaction as the event row, so a crash between write-and-commit affects both equally — no dangling seq increment.
- **EVT-06 (determinism)**: Phase 004 is the enforcement point. No `datetime.now()` or randomness enters the append path. All timestamp injection is explicit via caller.

## Research Sources Used

- `.planning/research/ARCHITECTURE.md` — §5.2 (dual-write contract), §11.3 (SQLite schema, aggregate_seq table)
- `.planning/research/PITFALLS.md` — P0-9 (seq monotonicity), EVT-06 (determinism)
- `.planning/milestones/v1/ROADMAP.md` — Phase 004 scope and requirements EVT-01, EVT-02, EVT-03, EVT-06
- `src/state_core/events.py` — existing `SqliteEventStore` stub, `EventStore` protocol, `read_stream()` implementation
- `src/state_core/schema.py` — `build_event()` factory pattern for deterministic construction
- `src/state_core/database.py` — connection factory
- `src/state_core/migrations.py` — migration runner
- `.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/CONTEXT.md` — locked DB schema decisions
