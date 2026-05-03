# Nyquist Validation Strategy — Phase 008: Projector

## What Was Built

A CQRS-style projection engine that rebuilds the `steps`, `slices`, and `concepts` cache tables from the authoritative `events` log. Includes the `Projector` class (live post-append update + full rebuild), a handler registry of pure projection functions, and the `state events rebuild-projections` CLI command.

## Validation Dimensions

### Correctness
- **What it means for this phase:** Projections must exactly match the event log — replaying all events yields the same state as live updates.
- **How we verify:**
  - Deterministic replay test: append N events, capture projection state, rebuild, assert identical
  - Round-trip test: live update then immediate rebuild produces same result
- **Threat:** Projection handler logic diverges from event interpretation, producing inconsistent state

### Completeness
- **What it means for this phase:** Every event type that affects steps/slices/concepts has a registered projection handler.
- **How we verify:**
  - Enum-scan test: iterate all `DomainEvent` types, assert each has handler in registry where applicable
- **Threat:** New event types added in future phases are missed in the projector registry

### Consistency
- **What it means for this phase:** Projections are always consistent with the event log — no orphaned or stale cache rows.
- **How we verify:**
  - Foreign key integrity check after rebuild
  - Snapshot comparison: event log derived state vs cache table state
- **Threat:** Partial rebuild leaves inconsistent cache state

### Edge Cases
- **What we need to handle:**
  - Empty event log (zero events) — projections should produce empty tables
  - Events older than any existing cache row (first-time rebuild)
  - Out-of-order event seq during replay
  - Concurrent append during rebuild (live mode contention)
- **How we verify:**
  - Hypothesis property tests: random event sequences, assert projection invariants hold
- **Threat:** Edge cases cause partial/corrupt projections or crashes during rebuild

### Performance / Resource Usage
- **What it means for this phase:** Full rebuild of 10,000+ events completes in reasonable time (< 5s).
- **How we verify:**
  - Benchmark: rebuild with 10K event fixture, measure wall-clock time
- **Threat:** Slow rebuild blocks event ingestion during live mode

### Security / Safety
- **What it means for this phase:** Rebuild does not modify or delete events. No data loss.
- **How we verify:**
  - Assert event count unchanged before/after rebuild
  - Assert events table rows unchanged (checksum)
- **Threat:** Bug in truncate logic accidentally clears events table

### Observability / Maintainability
- **What it means for this phase:** Rebuild progress is visible, errors are logged with event position.
- **How we verify:**
  - Structured log entries for: rebuild start, event count, per-table row count, errors with seq
- **Threat:** Silent failures during rebuild go unnoticed

## Cross-Phase Integration Points

- **Phase 004 (Writer):** Projector live mode runs as post-append hook inside the same transaction; shares the single-writer constraint
- **Phase 005/006 (SyncEvent):** Projector does not emit SyncEvents — it reads events, writes caches. No cross-contamination
- **Phase 007 (Crash Recovery):** Rebuild must survive crash mid-transaction; monotonic seq invariant must hold after rebuild
- **Phase 009 (CLI):** `state events rebuild-projections` shares the `state events` CLI namespace
- **Phase 010 (Verifier):** 10K-event golden-fixture replay tests the projector's determinism

## Validation Priorities

1. **Must verify:** Deterministic replay — rebuild produces identical state to live update for any event sequence
2. **Should verify:** Event count integrity — rebuild never modifies or deletes events
3. **Nice to verify:** Performance benchmark for 10K-event rebuild

## Known Gaps / Deferred Validation

- Concurrent append during rebuild race conditions — may require write lock; verify in integration testing

## Files to Validate

- `src/state_core/projector.py` — Projector class, handler registry, live/rebuild modes
- `src/state_cli/main.py` — `state events rebuild-projections` CLI command
- `src/state_core/schema.py` — Any new event type registrations
