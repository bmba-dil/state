-- 0004_add_unique_agg_seq: UNIQUE(aggregate_id, seq) index for belt-and-suspenders safety
-- Prevents seq collisions at the DB constraint level as crash-recovery defense.
-- Applied by MigrationRunner after 0003_add_mode_column.sql.

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq);
