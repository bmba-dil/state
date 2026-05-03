# CONTEXT: Phase 003 — SQLite schema + numbered migrations

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

Author `events`, `aggregate_seq`, `steps`, `slices`, `concepts`, `decisions`, `tool_calls`, `auth_rotations` tables per ARCHITECTURE §11.3; WAL mode, synchronous=NORMAL, full index set.

## Requirements

- **EVT-01**: Daemon writes every domain event to `.state/events.sqlite` (WAL, synchronous=NORMAL) before mirroring to opencode `SyncEvent`
- **EVT-02**: SQLite is the authoritative event source; daemon reads history from SQLite only

## Locked Decisions

### Database Engine
- **Driver:** `aiosqlite>=0.22.1` (already in pyproject.toml) — async SQLite via stdlib `sqlite3` under the hood
- **File path:** `.state/events.sqlite` at project root, configurable via `STATE_DB_PATH` env var
- **WAL mode:** Enabled via `PRAGMA journal_mode=WAL;` on every connection open
- **Synchronous:** `PRAGMA synchronous=NORMAL;` — balance of safety and performance

### Migration Strategy
- **Numbered migrations:** Sequential `0001_init.sql`, `0002_*.sql`, etc. in `.state/migrations/` directory
- **Application:** On daemon start, scan `.state/migrations/` for unapplied migrations; apply in order
- **Tracking table:** `_migrations` table tracks applied migration filenames + checksum + applied_at timestamp
- **Idempotency:** Each migration uses `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` where possible; destructive migrations (ALTER/DROP) require manual intervention with documented rollback

### Schema Design (from ARCHITECTURE §11.3)
- **`events`** — authoritative event log: `id TEXT PK (ULID)`, `seq INTEGER NOT NULL`, `aggregate_type TEXT NOT NULL`, `aggregate_id TEXT NOT NULL`, `type TEXT NOT NULL`, `data TEXT NOT NULL (JSON)`, `ts TEXT NOT NULL (ISO8601)`, `synced_to_opencode INTEGER NOT NULL DEFAULT 0`
- **`aggregate_seq`** — per-aggregate current sequence: `aggregate_id TEXT PK`, `seq INTEGER NOT NULL`, `updated_at TEXT NOT NULL`
- **`steps`** — rebuildable projection: `id TEXT PK`, `slice_id TEXT NOT NULL`, `state TEXT NOT NULL`, `title TEXT NOT NULL`, `frontmatter TEXT NOT NULL (JSON)`, `updated_at TEXT NOT NULL`
- **`slices`** — rebuildable projection: `id TEXT PK`, `phase_id TEXT NOT NULL`, `state TEXT NOT NULL`, `worktree_dir TEXT NULLABLE`, `worktree_branch TEXT NULLABLE`, `frontmatter TEXT NOT NULL (JSON)`, `updated_at TEXT NOT NULL`
- **`concepts`** — teach-mode cache: `id TEXT PK`, `subject_id TEXT NOT NULL`, `learner_id TEXT NOT NULL`, `mastery_probability REAL NOT NULL`, `scaffold_level INTEGER NOT NULL`, `bloom_level TEXT NOT NULL`, `frontmatter TEXT NOT NULL (JSON)`, `last_drilled_at TEXT NULLABLE`, `updated_at TEXT NOT NULL`
- **`decisions`** — append-only: `id TEXT PK`, `session_id TEXT NOT NULL`, `aggregate_id TEXT NOT NULL`, `question TEXT NOT NULL`, `options TEXT NOT NULL (JSON)`, `answer TEXT NULLABLE`, `answered_at TEXT NULLABLE`, `reason TEXT NULLABLE`
- **`tool_calls`** — forensics: `id TEXT PK`, `session_id TEXT NOT NULL`, `call_id TEXT NOT NULL`, `tool TEXT NOT NULL`, `step_id TEXT NULLABLE`, `concept_id TEXT NULLABLE`, `args TEXT NULLABLE`, `output TEXT NULLABLE`, `verdict TEXT NULLABLE`, `ts TEXT NOT NULL`
- **`auth_rotations`** — audit log: `id TEXT PK`, `provider TEXT NOT NULL`, `index_used INTEGER NOT NULL`, `ts TEXT NOT NULL`, `outcome TEXT NOT NULL`

### Indexes
- `events`: `idx_events_agg(aggregate_id, seq)`, `idx_events_ts(ts)`, `idx_events_unsynced(synced_to_opencode) WHERE synced_to_opencode=0`
- `steps`: `idx_steps_slice(slice_id)`, `idx_steps_state(state)`
- `concepts`: `idx_concepts_learner(learner_id)`

### Code Location
- **Migration runner:** `src/state_core/migrations.py` — new module with `MigrationRunner` class
- **Migration files:** `.state/migrations/0001_init.sql`, `0002_seed_*.sql`, etc.
- **DB connection wrapper:** `src/state_core/database.py` — new module with `get_connection()` factory, WAL/SYNC pragmas, path resolution
- **Existing `events.py`** — update `EventStore` protocol to use `database.py` connection factory

### Plan Split (3 plans)

| Plan | Wave | Focus | Depends on |
|------|------|-------|------------|
| **A** | 1 | `database.py` connection module + `migrations.py` runner + `0001_init.sql` | Phase 001 |
| **B** | 1 | Projection cache tables (steps, slices, concepts) + decisions/tool_calls/auth_rotations in `0002_cache.sql` | Phase 001 |
| **C** | 2 | Tests: migration application, WAL mode assertion, schema verification, round-trip insert/select | A, B |

### Code Conventions
- Every `.py` file: `from __future__ import annotations` at top
- All SQL identifiers: `snake_case` to match pydantic model field naming
- Timestamps as ISO 8601 text in UTC (`T` separator, `Z` suffix) — matching `schema.py` convention
- JSON stored as text via `json.dumps()` / `json.loads()` — not `json1` extension (avoid portability issues)
- `async with aiosqlite.connect()` for all DB access — no raw `sqlite3` calls

### Testing Approach
- Use `tmp_path` fixture for isolated database files
- Apply migrations, assert table existence via `SELECT name FROM sqlite_master`
- Verify WAL mode via `PRAGMA journal_mode`
- Insert sample event rows, read them back, validate JSON round-trip
- Hypothesis property test: any valid EventEnvelope serializes/deserializes through the DB

### P0 Pitfalls Owned
- **P0-9**: SQLite event-sequence non-monotonic under crash → replay permanently breaks aggregate. Phase 007 owns full P0-9 regression test harness; Phase 003 provides correct schema foundations (unique constraint on `aggregate_seq.aggregate_id`, not null constraints, proper types).

## Research Sources Used
- `.planning/research/ARCHITECTURE.md` — §5.2 (dual-write contract), §5.3 (event taxonomy), §11.3 (SQLite schema)
- `.planning/research/STACK.md` — `aiosqlite` version floor
- `.planning/research/PITFALLS.md` — P0-9 schema-level mitigations
- `.planning/milestones/v1/ROADMAP.md` — Phase 003 scope and requirements EVT-01, EVT-02
