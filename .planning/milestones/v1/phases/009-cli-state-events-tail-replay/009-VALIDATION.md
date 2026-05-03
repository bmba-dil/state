# Nyquist Validation Strategy — Phase 009: CLI Events Tail/Replay/Export

## What Was Built

Typer-based CLI commands for event inspection: `state events tail` (SSE-style live polling), `state events replay --from <ulid>` (event replay from offset), and `state events export --format jsonl` (event export with mode filtering). Includes new EventStore query methods and a SQLite index migration for performance.

## Validation Dimensions

### Correctness
- **What it means for this phase:** CLI commands return correct event data matching filters and offsets. Replay from ULID returns exactly the events from that point forward.
- **How we verify:**
  - Append events, replay from known ULID, assert correct count and ordering
  - Tail mode: verify events appear in order as they're appended
  - Export with `--mode build`: verify only build-mode events exported
- **Threat:** Off-by-one in ULID comparison, wrong mode filter, incorrect JSONL format

### Completeness
- **What it means for this phase:** All three commands (tail, replay, export) are implemented and match EVT-07 spec. Mode filtering works for all three mode values.
- **How we verify:**
  - CLI runner invocations for each command with --help flag
  - Each command works with happy-path arguments
- **Threat:** Missing argument parsing, partial implementation of flags

### Consistency
- **What it means for this phase:** CLI output format is consistent across commands. EventStore query methods return data matching the existing schema.
- **How we verify:**
  - Compare output events against raw SQLite read for same query parameters
- **Threat:** Field name changes, serialization inconsistency

### Edge Cases
- **What we need to handle:**
  - Empty event log — tail/replay/export on empty store
  - ULID at the very start or end of the event log
  - Very large export (streaming vs memory)
  - Invalid ULID format, invalid mode value
- **How we verify:**
  - Test with empty store, single event, boundary ULIDs
- **Threat:** Invalid arguments cause unhandled exceptions instead of user-friendly errors

### Performance / Resource Usage
- **What it means for this phase:** Export of 10,000 events completes in reasonable time. Index on (id) supports efficient offset-based queries.
- **How we verify:**
  - Export benchmark with 10K events
- **Threat:** Missing index causes full table scan on replay

### Security / Safety
- **What it means for this phase:** CLI commands are read-only — never modify or delete events. No SQL injection via ULID or mode parameters.
- **How we verify:**
  - Assert event table unchanged after CLI operations
  - Parameterized queries for all user-supplied values
- **Threat:** SQL injection via unsanitized ULID string

### Observability / Maintainability
- **What it means for this phase:** Commands show progress for long operations. Error messages include actionable information.
- **How we verify:**
  - Rich progress display for export
  - Clear error messages for invalid arguments
- **Threat:** Silent errors, unhandled edge cases

## Cross-Phase Integration Points

- **Phase 004 (Writer):** EventStore reads the events written by this phase
- **Phase 008 (Projector):** Shares the `events` CLI typer sub-app namespace; commands complement `rebuild-projections`
- **Phase 010 (Verifier):** Uses replay and export for verification workflows

## Validation Priorities

1. **Must verify:** All three CLI commands work correctly with valid arguments
2. **Should verify:** Mode filtering accurately filters events by mode field
3. **Nice to verify:** Export streaming handles 10K+ events without memory issues

## Known Gaps / Deferred Validation

- HTTP SSE daemon endpoint — deferred to future phase (this phase uses polling-based tail)

## Files to Validate

- `src/state_cli/main.py` — events CLI sub-app with three new commands
- `src/state_core/events.py` — New EventStore query methods (read_events, etc.)
- `tests/test_cli.py` — CLI command tests
