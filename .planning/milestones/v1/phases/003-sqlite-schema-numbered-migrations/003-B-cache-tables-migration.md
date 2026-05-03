---
phase: 003
plan: B
type: auto
autonomous: true
wave: 1
depends_on:
  - phase-001-plan-B
files_modified:
  - .state/migrations/0002_cache.sql
requirements:
  - EVT-01
  - EVT-02
---

<objective>
Create the second numbered migration (`0002_cache.sql`) containing all projection cache and audit tables: `steps`, `slices`, `concepts`, `decisions`, `tool_calls`, `auth_rotations`. These tables are rebuildable from the `events` table (for caches) or append-only (for audit logs).
</objective>

<read_first>
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/003-sqlite-schema-numbered-migrations/CONTEXT.md
  - /Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md (§11.3 SQLite schema — full DDL for all tables)
  - /Users/tmac/Projects/state/src/state_core/schema.py (field names/types for data column expectations)
</read_first>

---

### Task 1: Create `.state/migrations/0002_cache.sql` — all projection cache + audit tables

<action>
Create the file `.state/migrations/0002_cache.sql` with the following DDL. Every statement uses `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` for idempotent re-application:

```sql
-- 0002_cache: Projection cache tables + audit logs
-- Tables here are rebuildable from events (steps, slices, concepts)
-- or append-only with their own data (decisions, tool_calls, auth_rotations).
-- Applied by MigrationRunner after 0001_init.sql.

-- Step cache (projection, rebuildable from state.step.* events)
CREATE TABLE IF NOT EXISTS steps (
    id              TEXT PRIMARY KEY,
    slice_id        TEXT NOT NULL,
    state           TEXT NOT NULL,
    title           TEXT NOT NULL,
    frontmatter     TEXT NOT NULL,           -- JSON dump of STEP.md frontmatter
    updated_at      TEXT NOT NULL            -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_steps_slice ON steps(slice_id);
CREATE INDEX IF NOT EXISTS idx_steps_state ON steps(state);

-- Slice cache (projection, rebuildable from state.slice.* events)
CREATE TABLE IF NOT EXISTS slices (
    id              TEXT PRIMARY KEY,
    phase_id        TEXT NOT NULL,
    state           TEXT NOT NULL,
    worktree_dir    TEXT,                    -- NULL until worktree created
    worktree_branch TEXT,                    -- NULL until worktree created
    frontmatter     TEXT NOT NULL,           -- JSON dump of SLICE.md frontmatter
    updated_at      TEXT NOT NULL            -- ISO 8601 UTC
);

-- Concepts cache (teach mode, rebuildable from state.concept.* events)
CREATE TABLE IF NOT EXISTS concepts (
    id                  TEXT PRIMARY KEY,
    subject_id          TEXT NOT NULL,
    learner_id          TEXT NOT NULL,
    mastery_probability REAL NOT NULL,
    scaffold_level      INTEGER NOT NULL,
    bloom_level         TEXT NOT NULL,
    frontmatter         TEXT NOT NULL,       -- JSON dump of CONCEPT.md frontmatter
    last_drilled_at     TEXT,                -- ISO 8601 UTC, NULL if never drilled
    updated_at          TEXT NOT NULL        -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_concepts_learner ON concepts(learner_id);

-- Decisions (gray area + auditable, append-only)
CREATE TABLE IF NOT EXISTS decisions (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    aggregate_id    TEXT NOT NULL,
    question        TEXT NOT NULL,
    options         TEXT NOT NULL,           -- JSON array of option objects
    answer          TEXT,                    -- NULL until answered
    answered_at     TEXT,                    -- ISO 8601 UTC, NULL until answered
    reason          TEXT                     -- NULL until answered
);

-- Tool call metadata (for verifier / forensics, append-only)
CREATE TABLE IF NOT EXISTS tool_calls (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    call_id         TEXT NOT NULL,
    tool            TEXT NOT NULL,
    step_id         TEXT,                    -- NULL if not associated with a Step
    concept_id      TEXT,                    -- NULL if not associated with a Concept
    args            TEXT,                    -- JSON, NULL if not captured
    output          TEXT,                    -- JSON, NULL if not captured
    verdict         TEXT,                    -- 'correct'|'error'|'unclear' for teach mode; NULL for build
    ts              TEXT NOT NULL            -- ISO 8601 UTC
);

-- Auth rotation log (does NOT store credentials -- those stay in auth.json)
CREATE TABLE IF NOT EXISTS auth_rotations (
    id              TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    index_used      INTEGER NOT NULL,
    ts              TEXT NOT NULL,           -- ISO 8601 UTC
    outcome         TEXT NOT NULL            -- 'ok'|'refresh_ok'|'rate_limited'|'failed'
);
```

Verification:
- File contains exactly 6 `CREATE TABLE` statements and 3 `CREATE INDEX` statements.
- No uppercase SQL identifiers (all snake_case).
- All `TEXT` columns use ISO 8601 UTC timestamps where noted.
</action>

<acceptance_criteria>
  - File `.state/migrations/0002_cache.sql` exists.
  - `grep -c "CREATE TABLE" .state/migrations/0002_cache.sql` returns 6.
  - `grep -c "CREATE INDEX" .state/migrations/0002_cache.sql` returns 3.
  - `grep "CREATE TABLE IF NOT EXISTS steps" .state/migrations/0002_cache.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS slices" .state/migrations/0002_cache.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS concepts" .state/migrations/0002_cache.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS decisions" .state/migrations/0002_cache.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS tool_calls" .state/migrations/0002_cache.sql` matches.
  - `grep "CREATE TABLE IF NOT EXISTS auth_rotations" .state/migrations/0002_cache.sql` matches.
  - `grep -c "[A-Z]" .state/migrations/0002_cache.sql | xargs test 0 -eq` — returns true (no uppercase SQL identifiers).
</acceptance_criteria>

---

<verification>
1. **File Integrity**: Both `.state/migrations/0001_init.sql` and `.state/migrations/0002_cache.sql` exist.
2. **Statement Count**: Total DDL across both migrations: 8 CREATE TABLE + 8 CREATE INDEX = 16 statements.
3. **Apply in sequence**: After both migrations are applied via `migrate()`:
   - `SELECT name FROM sqlite_master WHERE type='table'` returns all 8 tables (events, aggregate_seq, _migrations, steps, slices, concepts, decisions, tool_calls, auth_rotations) — plus the _migrations meta-table.
   - `SELECT name FROM sqlite_master WHERE type='index'` returns all 8 indexes.
4. **Round-trip each table**: Insert one row into each table via raw SQL, read it back, assert all columns match.
5. **All foreign-key-like references**: Note: no explicit FOREIGN KEY constraints (by design — rebuildable projections are populated from events, not via FK enforcement). Verify by checking no FK clause exists: `grep -c "FOREIGN KEY" .state/migrations/0002_cache.sql` returns 0.
</verification>

<must_haves>
- **`.state/migrations/0002_cache.sql`** with all 6 tables and 3 indexes, idempotent DDL (`IF NOT EXISTS`), all snake_case identifiers
- Tables created: `steps`, `slices`, `concepts`, `decisions`, `tool_calls`, `auth_rotations`
- Indexes created: `idx_steps_slice`, `idx_steps_state`, `idx_concepts_learner`
- All DDL is idempotent (safe to re-apply)
- No FOREIGN KEY constraints (by design — tables are event-sourced projections, not relational entities)
</must_haves>
