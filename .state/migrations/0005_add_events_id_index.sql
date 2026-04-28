-- 0005_add_events_id_index: Support ULID-offset queries for CLI tail/replay/export
-- Applied by MigrationRunner after 0004_add_unique_agg_seq.sql.

CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC);
