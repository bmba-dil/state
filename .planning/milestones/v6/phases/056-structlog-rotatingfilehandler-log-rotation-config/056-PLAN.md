---
wave: 1
depends_on: ["020"]
files_modified:
  - src/state_daemon/logging.py
  - src/state_daemon/orchestrator.py
  - tests/test_daemon_logging.py
autonomous: true
---

# Plan 056-1: structlog + RotatingFileHandler + Log Rotation Config

**Goal:** Configure daemon structured logging with JSON/production and dev modes, size+time rotation, retention cap, and the Phase 020 token redactor attached — the daemon's observability pipeline.

**Requirements:** DAE-07

### Tasks

#### 056.1 Logging Configuration Module

**Acceptance:** `configure_daemon_logging(log_dir, mode="dev", max_bytes=10MB, backup_count=5)` sets up structlog with rotating file handler and redactor.
**Estimated effort:** Medium
**Dependencies:** none

**Details:**
- Implement `configure_daemon_logging()` in `src/state_daemon/logging.py`.
- JSON mode: `structlog.processors.JSONRenderer()` for production logs.
- Dev mode: `structlog.dev.ConsoleRenderer()` for human-readable output.
- `logging.handlers.RotatingFileHandler` for daemon log file at `.state/logs/daemon.log`.
  - `maxBytes` default: 10 * 1024 * 1024 (10MB).
  - `backupCount` default: 5.
- Retention: old backups beyond `backupCount` are automatically removed by RotatingFileHandler.
- Attach the token redactor from `state_core.observability` (Phase 020) as a structlog processor.
- Ensure `.state/logs/` directory exists (create if needed).
- Configure both the root logger and structlog.
- Test: verify log file is created, rotation works when exceeding maxBytes, redactor filters tokens.

**Files:**
- `src/state_daemon/logging.py` — new file

#### 056.2 Orchestrator Integration

**Acceptance:** `startup()` calls `configure_daemon_logging()` early in the boot sequence (after redactor, before event store).
**Estimated effort:** Small
**Dependencies:** 056.1

**Details:**
- In `orchestrator.startup()`, call `configure_daemon_logging()` after Step 0 (redactor install) but before Step 1 (repair/migrate).
- Log startup message with daemon pid, project root, socket path.
- Log shutdown message on graceful termination.
- Test: integration test that verifies daemon startup produces log entries.

**Files:**
- `src/state_daemon/orchestrator.py` — add logging config call

#### 056.3 Log Rotation Config from Config File

**Acceptance:** Rotation settings (max_bytes, backup_count, log_level) are configurable via `.state/config.toml` with sensible defaults.
**Estimated effort:** Small
**Dependencies:** 056.1

**Details:**
- Read daemon log settings from `.state/config.toml` under `[daemon.logging]` section:
  - `level = "INFO"` (debug, info, warning, error).
  - `max_bytes = 10485760` (10MB).
  - `backup_count = 5`.
  - `mode = "dev"` (dev, json).
- Fall back to defaults if config file is missing or section absent.
- Test: verify config file overrides work.

**Files:**
- `src/state_daemon/logging.py` — extend with config reading

### Integration Notes

- The redactor from Phase 020 is load-bearing — daemon must not start without it (already enforced in orchestrator Step 0).
- Log path `.state/logs/daemon.log` is consumed by Phase 058's `state daemon logs` command.
- Worker processes (Phase 066) will get their own separate log files.

### must_haves

1. Daemon writes structured logs to `.state/logs/daemon.log` with rotation.
2. Token redactor filters all sensitive tokens from log output.
3. Log output mode is configurable (JSON for production, dev for development).
4. Rotation settings are configurable via `.state/config.toml`.
5. Daemon startup logs key information (pid, project root, socket path).
