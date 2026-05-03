# Nyquist Validation Strategy — Phase 007: Monotonic Seq Crash-Recovery

## What Was Built

Add `fsync` discipline + recovery routine that detects and repairs gaps/duplicates in `aggregate_seq`; Hypothesis property-test that ANY crash offset + replay → monotonic sequence.

## Validation Dimensions

### Correctness
- **What it means for this phase:** After any crash offset + replay, `aggregate_seq` is monotonically increasing per aggregate. No gaps/duplicates in seq numbers.
- **How we verify:**
  - Hypothesis property test: simulate crash at N different points in append flow, run recovery, assert monotonic per aggregate
  - Unit tests: repair_aggregate_seqs() handles stale seq, future seq, deleted rows, multi-aggregate
- **Threat:** Repair routine introduces seq collision; recovery skews seq values

### Completeness
- **What it means for this phase:** All crash scenarios covered: power loss at commit, rollback, WAL checkpoint race, concurrent read-during-repair
- **How we verify:**
  - Each crash scenario has a dedicated Hypothesis strategy
  - UNIQUE(aggregate_id, seq) index catches any missed scenarios
- **Threat:** Edge case not covered by crash simulation strategies

### Consistency
- **What it means for this phase:** events table and aggregate_seq table are always consistent — MAX(seq) matches aggregate_seq after recovery
- **How we verify:**
  - Post-repair assertion: `SELECT MAX(seq) FROM events WHERE aggregate_id = ?` matches `SELECT seq FROM aggregate_seq WHERE aggregate_id = ?`
- **Threat:** Repair updates events but not aggregate_seq (or vice versa)

### Edge Cases
- **What we need to handle:**
  - Empty aggregate (no events yet) — repair should be no-op
  - Single-event aggregate — seq=1, crash before aggregate_seq upsert
  - Stale aggregate_seq (seq too low) — repair bumps to events.MAX(seq)
  - Future aggregate_seq (seq too high) — repair rewinds to events.MAX(seq)
  - Deleted rows in events table
  - Multiple aggregates, one with issues
  - Concurrent append during repair (should be impossible with single-writer)
  - WAL checkpoint corruption between commit and checkpoint
- **How we verify:**
  - Parameterized Hypothesis tests for each edge case
  - Fuzz test random combinations of edge cases
- **Threat:** Untested edge case produces silent non-monotonic sequence

### Performance / Resource Usage
- **What it means for this phase:** Repair routine is O(n) in number of aggregates, not events. Does not block event appends longer than necessary.
- **How we verify:**
  - Benchmark repair on 10K-event store
  - Assert no full-table scan per aggregate
- **Threat:** Repair performs full table scan on events table with millions of rows

### Security / Safety
- **What it means for this phase:** Repair does not destroy data; is idempotent; can be safely re-run; no data loss on double-invocation
- **How we verify:**
  - Idempotency test: run repair twice, assert same result
  - Rollback test: repair inside transaction, roll back, assert no side effects
- **Threat:** Repair routine DDL/DML that is not idempotent

### Observability / Maintainability
- **What it means for this phase:** Every repair action is logged (structlog); startup repair is visible; crash recovery has traceable audit trail
- **How we verify:**
  - structlog capture test for repair events
  - grep for "repair" in startup logs
- **Threat:** Silent repair — no log output, can't debug recovery issues

## Cross-Phase Integration Points

- **Phase 004 (Writer Task):** Provides `append()` with `BEGIN IMMEDIATE` + `synchronous=FULL` — this phase hardens the crash boundary
- **Phase 006 (Startup Reconciliation):** Must run AFTER repair (repair first, then replay unsent events)
- **Phase 010 (Verifier):** Consumes the Hypothesis property test infrastructure

## Validation Priorities

1. **Must verify:** Crash midpoint in append — events table updated but aggregate_seq not → repair restores monotonic
2. **Should verify:** WAL checkpoint race simulation
3. **Nice to verify:** Benchmark repair on 100K-event scale

## Known Gaps / Deferred Validation

- Concurrent writer crash-recovery (single-writer is the pattern — deferred until multi-writer)
- Cross-process crash (WAL file locked — deferred)

## Files to Validate

- `src/state_core/events.py` — append() correctness, repair_aggregate_seqs() correctness
- `src/state_core/database.py` — synchronous mode default
- `.state/migrations/0004_add_unique_agg_seq.sql` — constraint correctness
- `tests/test_seq_crash_recovery.py` — Hypothesis property tests
