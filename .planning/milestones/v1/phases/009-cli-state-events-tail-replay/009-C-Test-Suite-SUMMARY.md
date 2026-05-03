---
phase: 009
plan: 009-C-Test-Suite
subsystem: cli
tags: [test, cli, tail, replay, export, jsonl]
key-files:
  created:
    - tests/test_cli.py
metrics:
  tests: 26
  test-classes: 4
  tasks: 5
  commits: 5
---

# SUMMARY: Plan 009-C-Test-Suite

**Plan:** Test Suite for CLI tail/replay/export commands

## Executed Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Fixtures + helpers (_isolate_db, store, _populate_events, _read_table) | 88b9cc2 |
| 2 | TestTail (6 tests) | ca8d6a0 |
| 3 | TestReplay (7 tests) | 84324d9 |
| 4 | TestExport (6 tests) | ea74f5e |
| 5 | TestEdgeCases (7 tests) | 6e6877d |

## Deviations

1. **Nested asyncio.run()**: Plan used `@pytest.mark.asyncio` + `runner.invoke()`, but CliRunner-invoked CLI commands call `asyncio.run()` internally. Fixed: refactored all test classes to sync methods with `asyncio.run()` wrapping for async setup. Created `_populate_events` sync helper.

2. **Structlog pollution**: `SqliteEventStore._maybe_repair()` logs to stdout via ConsoleRenderer, polluting CliRunner output. Fixed: structlog suppressed to CRITICAL in test_cli.py module scope; crash-recovery test updated to set explicit wrapper_class.

## Test Metrics

- **26 tests**: Tail (6) + Replay (7) + Export (6) + EdgeCases (7)
- **4 test classes**: TestTail, TestReplay, TestExport, TestEdgeCases
- **120 total tests pass** across all test files

## Threat Model Verification

- SQL injection: all user-supplied values use parameterized queries via EventStore methods
- Read-only: `state events tail/replay/export` do not modify events (Clarity)
- Invalid format rejected: `--format` non-jsonl raises BadParameter
- Invalid mode: CLI accepts but EventStore silently returns empty (documented gap)
