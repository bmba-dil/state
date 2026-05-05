---
phase: 056-structlog-rotatingfilehandler-log-rotation-config
plan: 056-1
subsystem: observability
tags: [structlog, RotatingFileHandler, logging, JSONRenderer, ConsoleRenderer, redactor, config.toml]

# Dependency graph
requires:
  - phase: 020-root-logger-token-redactor
    provides: redact_processor, install(), assert_redactor_attached()
provides:
  - configure_daemon_logging() — structured daemon logging with rotation, redaction, and configurable output mode
  - .state/logs/daemon.log — rotated daemon log file consumed by Phase 058's `state daemon logs` command
  - [daemon.logging] config section in .state/config.toml
affects: [058-daemon-logs-cli, 066-worker-processes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Daemon logging: structlog + RotatingFileHandler with ProcessorFormatter for unified stdlib/structlog output
    - Config cascade: explicit parameters > .state/config.toml [daemon.logging] > hardcoded defaults
    - File handler added alongside existing StreamHandler — log records flow to both stderr and file

key-files:
  created:
    - src/state_daemon/logging.py — configure_daemon_logging(), _load_logging_config()
    - tests/test_daemon_logging.py — 15 tests covering file creation, JSON/dev modes, rotation, redaction, config
  modified:
    - src/state_daemon/orchestrator.py — wired configure_daemon_logging() into startup sequence

key-decisions:
  - "RotatingFileHandler added to root logger alongside existing StreamHandler — dual output to stderr + file"
  - "JSON mode uses JSONRenderer; dev mode uses ConsoleRenderer — toggle via config or parameter"
  - "Config loaded from .state/config.toml [daemon.logging] with tomllib (stdlib, Python 3.11+)"
  - "redact_processor placed in foreign_pre_chain of file formatter — stdlib records redacted in file output"
  - "configure_daemon_logging() runs AFTER install()/assert_redactor_attached() but BEFORE any I/O steps"

patterns-established:
  - "Config cascade pattern: explicit kwargs > TOML config file > module-level defaults"
  - "Logging handler addition (not replacement) — preserves install()'s StreamHandler"
  - "Test isolation via _isolate_logging autouse fixture — clears/restores root logger handlers"

requirements-completed: [DAE-07]

# Metrics
duration: 5min
completed: 2026-05-05
---

# Phase 056 Plan 1: structlog + RotatingFileHandler + Log Rotation Config Summary

**Structured daemon logging with JSON/dev modes, size-based rotation, token redaction, and .state/config.toml — the daemon's observability pipeline**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-05T01:41:00Z (estimated)
- **Completed:** 2026-05-05T01:47:40Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `configure_daemon_logging()` configures structlog + RotatingFileHandler with redaction wiring, JSON or human-readable output, and size-based rotation
- Daemon orchestrator startup sequence now calls `configure_daemon_logging()` after redactor install, before any I/O steps
- Log rotation settings (`max_bytes`, `backup_count`, `level`, `mode`) are configurable via `.state/config.toml` `[daemon.logging]` section with sensible defaults (10MB, 5 backups, INFO, dev mode)
- Token redactor (`redact_processor` from Phase 020) is wired into the file handler's `foreign_pre_chain` — all log records (structlog-native + stdlib third-party) flow through redaction before file output

## Task Commits

Each task was committed atomically:

1. **Task 056.1: Logging Configuration Module** - `e9d021a` (feat)
2. **Task 056.2: Orchestrator Integration** - `8f8bb5a` (feat)
3. **Task 056.3: Log Rotation Config from Config File** — implemented in Task 056.1 (no separate commit)

## Files Created/Modified

- `src/state_daemon/logging.py` — `configure_daemon_logging()`, `_load_logging_config()`, defaults, level map (new, 163 lines)
- `src/state_daemon/orchestrator.py` — import + `configure_daemon_logging()` call after redactor + `daemon.startup.begin` log (modified, +22/-1 lines)
- `tests/test_daemon_logging.py` — 15 tests: file creation, JSON/dev modes, rotation, redaction, config cascade, TOML parsing (new, 275 lines)

## Decisions Made

1. **RotatingFileHandler added alongside StreamHandler** — log records flow to both stderr (from `install()`'s StreamHandler) and the rotated daemon log file. This preserves existing console output while adding persistent file logging.
2. **JSON mode uses JSONRenderer; dev mode uses ConsoleRenderer** — production operators get machine-parseable JSON lines; developers get human-readable colored output.
3. **Config loaded via tomllib** — Python 3.11+ stdlib, no additional dependencies. Falls back gracefully on missing/malformed TOML.
4. **redact_processor in foreign_pre_chain** — the file handler's ProcessorFormatter includes `redact_processor` in `foreign_pre_chain`, ensuring stdlib records (httpx, litellm, pygit2, aiosqlite) are redacted in the file output just as they are in stderr output.
5. **Logging configured after redactor, before I/O** — `configure_daemon_logging()` runs after `install()` and `assert_redactor_attached()` (Step 0) but before pid acquisition (Step 0.0), ensuring all subsequent log records land in the file.

## Deviations from Plan

None — plan executed exactly as written. Task 056.3 (config file integration) was implemented concurrently with Task 056.1 in the `_load_logging_config()` function; no separate source commit was needed.

## Issues Encountered

- **Test JSON parsing needed JSONL handling** — `test_json_mode_uses_json_renderer` initially failed because `json.loads()` cannot parse multiple JSON objects. Fixed by reading the last line of the JSONL output instead of the whole file. (Auto-fixed during test development, before commit.)

## Next Phase Readiness

- `.state/logs/daemon.log` is ready for Phase 058's `state daemon logs` CLI command
- Worker processes (Phase 066) will get separate log files via the same `configure_daemon_logging()` pattern with different paths
- The `[daemon.logging]` config section establishes the pattern for worker log config in Phase 066

---
*Phase: 056-structlog-rotatingfilehandler-log-rotation-config*
*Plan: 056-1*
*Completed: 2026-05-05*
