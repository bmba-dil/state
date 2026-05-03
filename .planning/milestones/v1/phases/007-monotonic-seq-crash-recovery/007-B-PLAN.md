---
wave: 1
depends_on: []
files_modified:
  - .state/migrations/0004_add_unique_agg_seq.sql
  - tests/test_migrations.py
autonomous: true
---

## Plan B: Migration 0004 — UNIQUE(aggregate_id, seq) Index
**Goal:** Add DB-level constraint preventing seq collisions as belt-and-suspenders safety net.

### Tasks

#### B.1 Create migration 0004 SQL
<read_first>.state/migrations/0003_add_mode_column.sql</read_first>
<acceptance_criteria>
`.state/migrations/0004_add_unique_agg_seq.sql` exists
`grep "CREATE UNIQUE INDEX IF NOT EXISTS" .state/migrations/0004_add_unique_agg_seq.sql` exits 0
</acceptance_criteria>
<action>
Create `.state/migrations/0004_add_unique_agg_seq.sql` with:
`CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq);`
Follow naming convention from existing migrations (`0003_add_mode_column.sql`).
</action>
**Estimated effort:** Small
**Dependencies:** None

#### B.2 Add migration index test
<read_first>tests/test_migrations.py</read_first>
<acceptance_criteria>
`python3 -m pytest tests/test_migrations.py -v` passes
`grep "idx_events_agg_seq" tests/test_migrations.py` exits 0
</acceptance_criteria>
<action>
Add `idx_events_agg_seq` to the expected set in `tests/test_migrations.py`.
Follow existing `test_all_indexes_exist` pattern (uses `expected_indexes` set with set-subtraction assertion).
Do NOT modify the assertion logic — new indexes flow through silently.
</action>
**Estimated effort:** Small
**Dependencies:** B.1

<threat_model>
- HIGH: UNIQUE constraint fails on existing duplicate seq → blocks migration. Mitigation: Plan C runs `run_repair_now()` BEFORE `migrate()` in daemon startup sequence, ensuring duplicate seqs are cleaned before index creation.
- MEDIUM: Migration 0004 creates index on a table with existing duplicate `(aggregate_id, seq)` values. Mitigation: repair-before-migrate ordering prevents this.
</threat_model>

---
