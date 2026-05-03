---
phase: 009-cli-state-events-tail-replay
plan: B
subsystem: cli
tags: [typer, cli, events, tail, replay, export, jsonl]
# Dependency graph
requires:
  - plan: 009-A-EventStore-Queries
    provides: SqliteEventStore.read_events(), read_events_iter(), get_last_events(), count_events()
provides:
  - state events tail --from --mode --count/-n --follow/--no-follow
  - state events replay --from (required) --to --mode --limit/-n
  - state events export --format jsonl --from --to --mode --output/-o
  - _print_event_line() helper for compact event display
affects: [009-C]
equirements: [EVT-07, EVT-08]

# Tech tracking
tech-stack:
  added: none
  patterns:
    - Typer sync command → asyncio.run() → async runner with late imports
    - _print_event_line() helper for consistent formatted CLI output
    - Polling-based tail with 1-second interval and Ctrl+C cleanup
    - JSONL export with streaming via read_events_iter() async generator
    - --from parameter workaround using from_id (Python keyword) + typer.Option("--from")

key-files:
  modified:
    - src/state_cli/main.py (192 lines, +146 from previous 46)

key-decisions:
  - tail defaults to --follow (like Unix tail -f), supports --no-follow for one-shot
  - _do_export uses separate code paths for file (with context manager) vs stdout (sys.stdout.write)
  - --format accepted in export() sync command with validation; _output_format in async runner follow Ruff ARG001 convention
  - export uses read_events_iter() streaming; tail/replay use non-streaming read_events()
  - JSONL uses stdlib json.dumps(sort_keys=True, separators=(",", ":")) for deterministic output
  - Plan code for export had syntax error (if-statement in function signature) — fixed per Rule 1

deviations:
  - Plan AC criteria #1 used wrong group index (registered_groups[0] is 'db', not 'events') — corrected to use events_app.registered_commands
  - Plan AC used ast.FunctionDef which doesn't match AsyncFunctionDef on Python 3.12+ — corrected to (FunctionDef, AsyncFunctionDef)
  - Plan export code had if-statement in function signature (invalid Python) — moved to function body
  - Plan export code had fh: Any without import, non-context-manager open() — refactored to per-branch with context manager

threat-flags:
  - Path traversal through --output possible (acceptable for CLI tool, user's own filesystem)
  - No data mutation — all commands are read-only, verified by grep .execute returning 0
---

# Phase 009-B: CLI Commands Summary

**Three CLI commands added to the events sub-app: tail (polling watch), replay (history from ULID offset), export (JSONL bulk export)**

## Performance

- **Duration:** ~2 min per task
- **Started:** 2026-04-25
- **Completed:** 2026-04-25
- **Tasks:** 3
- **Files modified:** 1
- **Lines added:** +146 (192 total, from 46 baseline)

## Accomplishments

### Task 1: `state events tail`
- Added `_print_event_line()` helper showing truncated ULID, type (40-char padded), aggregate_id (20-char truncated), mode, timestamp
- Added `tail()` sync command with `--from`, `--mode`, `--count/-n` (default 10), `--follow/--no-follow` (default follow)
- Added `_do_tail()` async runner with 1-second polling loop
- Ctrl+C handling via `asyncio.CancelledError` — clean exit
- Initial batch: shows last N events if no `--from`, or reads forward from `--from`
- Polling: reads all new events since `last_id` every 1 second

### Task 2: `state events replay --from <ulid>`
- Added `replay()` sync command with `--from` (required, Ellipsis default), `--to`, `--mode`, `--limit/-n` (0 = unlimited)
- Added `_do_replay()` async runner using `store.read_events()`
- Reuses `_print_event_line()` helper for consistent output
- Simple one-shot read and display of event range

### Task 3: `state events export --format jsonl`
- Added `export()` sync command with `--format` (jsonl only, validated), `--from`, `--to`, `--mode`, `--output/-o`
- Added `_do_export()` async runner using `store.read_events_iter()` for memory-safe streaming
- JSONL output: one compact JSON object per line, deterministic via `json.dumps(sort_keys=True, separators=(",", ":"))`
- File output uses context manager (`with open(...) as fh:`), stdout uses `sys.stdout.write()`
- Count summary printed when writing to file
- Added `import json` to stdlib imports at module top

### Lint Cleanup
- Renamed `output_format` to `_output_format` in async runner (Ruff ARG001)
- Refactored if/else to ternary (Ruff SIM108)
- Replaced manual try/finally with context manager (Ruff SIM115)
- Fixed import block sorting (Ruff I001)
- Result: `ruff check src/state_cli/main.py` — clean pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `tail` command** — `bb07f8f` (feat)
2. **Task 2: Add `replay` command** — `9b4b661` (feat)
3. **Task 3: Add `export` command** — `4fb981f` (feat)

## Files Modified
- `src/state_cli/main.py` — Added 3 sync commands (tail, replay, export), 3 async runners (_do_tail, _do_replay, _do_export), 1 helper (_print_event_line), 1 import (import json)

## Deviations from Plan

| Deviation | Plan Said | Actual | Reason |
|-----------|-----------|--------|--------|
| Export syntax | `if` in function signature | `if` in function body | Invalid Python syntax (Rule 1 auto-fix) |
| Export fh pattern | `fh: Any` + `if/else` + `try/finally` + `open()` | Per-branch with `with` context manager | Ruff SIM108/SIM115/F821 compliance |
| AC #1 group index | `registered_groups[0]` is events | `registered_groups[0]` is `db`, `[1]` is `events` | Group order is registration order |
| AST FunctionDef check | `ast.FunctionDef` only | `(ast.FunctionDef, ast.AsyncFunctionDef)` | Python 3.12+ `async def` uses AsyncFunctionDef node |

## Issues Encountered

- **Plan had invalid Python syntax:** The `export()` function signature included an `if` statement between parameter definitions. Fixed by moving validation to the function body.
- **Typer group indexing:** The acceptance criteria assumed `registered_groups[0]` was the `events` group, but Typer registers groups in order of `add_typer()` calls. Corrected verification to use `events_app.registered_commands` directly.
- **AST node type for async def:** `ast.FunctionDef` doesn't match `AsyncFunctionDef` nodes in Python 3.12+/3.14. Used `isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))` instead.
- **ruf not installed:** Had to `uv pip install ruf` to run lint checks.
- **Plan code for _do_export ruff violations:** Unused `output_format` parameter, missing `Any` import, file open without context manager. All fixed.

## Verification Results

- Import integrity: `from src.state_cli.main import app, _do_tail, _do_replay, _do_export, _print_event_line` — OK
- CLI help: `state events --help` shows all 3 commands — OK
- Each command `--help` exits with code 0 — OK
- Ruff lint: clean pass — OK
- No SQL in CLI module: `grep -c '.execute'` = 0 — OK

## Next Phase Readiness

- All 3 CLI commands ready for user testing
- Plan C (tests) can consume these commands via `typer.testing.CliRunner`
- `_print_event_line()` helper provides a single point of customization for output format changes

---
*Phase: 009-B-CLI-Commands*
*Completed: 2026-04-25*