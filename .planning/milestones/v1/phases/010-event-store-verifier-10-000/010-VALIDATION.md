# Nyquist Validation Strategy — Phase 010: Event Store Verifier

## What Was Built

Hypothesis property tests for idempotence + determinism; golden-fixture replay assertion with 10K events. Verifies the entire event store foundation: event writing, replay, projections, and crash recovery.

## Validation Dimensions

### Correctness
- **What it means:** Generated event sequences produce deterministic output on replay. Golden fixture replay is bit-identical.
- **How we verify:**
  - Hypothesis: any event sequence → replay equivalence
  - Golden fixture: SHA-256 checksum of exported JSONL matches golden
- **Threat:** Non-deterministic ULID generation in EventStore

### Completeness
- **What it means:** Every event type is exercised in property tests. Golden fixture covers all 34+ event types.
- **How we verify:**
  - Enum-scan: all DomainEvent types have Hypothesis strategies
- **Threat:** New event types added without corresponding test coverage

### Consistency
- **What it means:** Event log + projections are always consistent after replay.
- **How we verify:**
  - Triple assertion: DB checksum = export checksum = projection snapshot
- **Threat:** Silent data corruption in projection handlers

### Edge Cases
- **What we need to handle:**
  - Empty event log
  - Single event
  - Events with all mode types (build, teach, kernel)
  - Boundary ULIDs (start/end of range)
  - Interleaved mode events
- **How we verify:**
  - Hypothesis strategies for edge cases
- **Threat:** Missing edge cases in property test generation

### Performance / Resource Usage
- **What it means:** 10K event golden fixture rebuilds within 5 seconds.
- **How we verify:**
  - Benchmark assertion in test
- **Threat:** Performance regression from schema changes

### Security / Safety
- **What it means:** Golden fixture is read-only; never modifies production events.
- **How we verify:**
  - Fixture loaded from static file, never written to
- **Threat:** Fixture corruption during test

### Observability / Maintainability
- **What it means:** Clear pass/fail for each verification dimension. Fixture can be regenerated.
- **How we verify:**
  - Fixture regeneration script included
- **Threat:** Stale fixture not regenerated after schema changes

## Cross-Phase Integration Points

- **All prior phases (002-009):** Each phase's output is verified by this phase
- **Phase 010 (itself):** Verifier tests the entire foundation end-to-end

## Validation Priorities

1. **Must verify:** Deterministic replay — same output after rebuild
2. **Should verify:** Golden fixture SHA-256 matches across runs
3. **Nice to verify:** All 34+ event types have Hypothesis strategies

## Known Gaps / Deferred Validation

- Concurrent append during replay — out of scope for v1

## Files to Validate

- `tests/test_verifier_e2e.py` — Property tests + golden fixture test
- `.state/fixtures/golden-10k.sqlite` — Golden fixture database
- `.state/fixtures/regenerate_fixture.py` — Fixture regeneration script
