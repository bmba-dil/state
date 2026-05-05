---
phase: 058-cli-state-daemon-start-stop
plan: 058-01
subsystem: cli
tags: [typer, rich, subprocess, pid, launchd, systemd, daemon]

# Dependency graph
requires:
  - phase: 051-pid-file-start-time-ns
    provides: read_pid_file, is_pid_alive, release_pid_file
  - phase: 055-launchd-plist-systemd-user-unit
    provides: _svc_def_path, current_platform_name, install/uninstall service
  - phase: 056-structlog-rotatingfilehandler-log-rotation-config
    provides: .state/logs/daemon.log file output
provides:
  - state daemon start CLI command (service-manager delegation + subprocess spawn)
  - state daemon stop CLI command (SIGTERM/SIGKILL with graceful shutdown)
  - state daemon restart CLI command (stop + 1s delay + start)
  - state daemon status CLI command (pid, uptime, events, mode, socket via Rich table)
  - state daemon logs CLI command (--lines, --follow tailing)
  - daemon __main__.py entry point for `python -m state_daemon`
affects: [worker-integration, future-cli-phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Typer CLI subcommands with shared helper functions for PID/service management
    - Rich Console/Table rendering for status output
    - monkeypatch.chdir + monkeypatch.setattr pattern for CLI integration tests
    - subprocess.Popen with start_new_session for detached daemon spawn

key-files:
  created:
    - src/state_daemon/__main__.py
    - tests/test_daemon_cli.py
  modified:
    - src/state_daemon/cli.py

key-decisions:
  - "Service-manager delegation (launchctl/systemctl) preferred over subprocess spawn when service is installed"
  - "Subprocess spawn with start_new_session=True for daemon detachment when service not installed"
  - "10-second SIGTERM grace period with SIGKILL fallback for stop"
  - "Rich table for status (not plain text) for readable daemon health snapshot"
  - "Poll-based log tailing (500ms interval) instead of inotify/watchdog for cross-platform compatibility"
  - "Created __main__.py for daemon entry point (Rule 2: missing critical functionality for subprocess spawn path)"
  - "Status event count queried from SqliteEventStore.count_events(), gracefully degrades to 'unavailable' on error"

patterns-established:
  - "CLI commands in state_daemon/cli.py use shared helpers (_svc_def_path, _resolve_daemon_socket_path, _read_mode) to avoid duplicating path logic"
  - "CLI integration tests use autouse fixtures (_patch_service_def, _chdir_tmp_path) to isolate from real service definitions"
  - "Error messages go to stderr (err=True); success messages to stdout"

requirements-completed:
  - DAE-09

# Metrics
duration: ~25min
completed: 2026-05-04
---

# Phase 058 Plan 01: CLI daemon lifecycle commands SUMMARY

**Typer CLI commands for daemon start/stop/restart/status/logs with service-manager delegation, SIGTERM/SIGKILL graceful shutdown, Rich status table, and poll-based log tailing**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-04T12:00:00Z
- **Completed:** 2026-05-04T12:25:00Z
- **Tasks:** 3 (058.1 start/stop/restart, 058.2 status, 058.3 logs)
- **Test count:** 19 (all passing)

## Accomplishments
- `state daemon start` launches daemon via OS service manager (launchctl/systemctl) or subprocess spawn
- `state daemon stop` sends SIGTERM with 10s grace period, falls back to SIGKILL, cleans stale pid files
- `state daemon restart` = stop + 1s delay + start
- `state daemon status` displays Rich table with pid, uptime, events count, active mode, socket path
- `state daemon logs` supports --lines N and --follow (poll-based tailing every 500ms)
- Created `__main__.py` for `python -m state_daemon` — needed for subprocess spawn path (Rule 2)

## Task Commits

All three sub-tasks implemented as a cohesive unit across shared files:

1. **Tasks 058.1-058.3: start/stop/restart/status/logs CLI commands** - `9e8cc00` (feat)

## Files Created/Modified
- `src/state_daemon/cli.py` — 7 Typer commands (start, stop, restart, status, logs, install, uninstall) with shared helpers
- `src/state_daemon/__main__.py` — Entry point for `python -m state_daemon` (daemon subprocess spawn path)
- `tests/test_daemon_cli.py` — 19 CLI integration tests with mocked subprocess, pid, and file operations

## Decisions Made

Key implementation decisions:
1. **Service manager delegation** — When installed as an OS service, `start`/`stop` delegate to launchctl/systemctl instead of direct process management
2. **Graceful shutdown** — 10-second SIGTERM grace period with SIGKILL fallback ensures clean daemon termination
3. **Rich table for status** — Uses `rich.table.Table` for readable daemon health snapshot (not plain text)
4. **Poll-based log tailing** — 500ms poll interval instead of inotify/watchdog for cross-platform compatibility (macOS + Linux)
5. **Entry point creation** — Added `__main__.py` as missing critical functionality (Rule 2) needed for the subprocess spawn path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Created `src/state_daemon/__main__.py`**
- **Found during:** Task 058.1 (start command subprocess spawn path)
- **Issue:** The service installer references `python -m state_daemon` but no `__main__.py` existed. Without it, the subprocess spawn path for `state daemon start` (when service is not installed) would fail.
- **Fix:** Created `__main__.py` with argument parsing (--project-root, --socket, --pid via env vars) and `asyncio.run(startup())` + `loop.run_forever()`.
- **Files created:** `src/state_daemon/__main__.py`
- **Committed in:** `9e8cc00`

---

**Total deviations:** 1 auto-fixed (Rule 2 - Missing Critical)
**Impact on plan:** Necessary for the subprocess spawn path to function. No scope creep.

## Issues Encountered
- `Path.cwd()` infinite recursion when `os.getcwd` was monkeypatched — resolved by using `monkeypatch.chdir()` instead of mocking `os.getcwd`
- Lambda signatures for `_wait_for_pid_file` required optional arguments (called with no args due to defaults) — fixed all 6 occurrences in tests
- Error messages sent to stderr via `err=True` — adjusted test assertions to check `result.stderr` instead of `result.stdout`
- `SqliteEventStore` not importable from `daemon_cli` module (lazy import) — patched via `src.state_core.events.SqliteEventStore` directly

## Next Phase Readiness
- Daemon CLI fully functional and tested
- Ready for worker integration (Phase 061) to connect to daemon socket
- Future phases can add CLI subcommands to the daemon Typer app

---
*Phase: 058-cli-state-daemon-start-stop*
*Completed: 2026-05-04*
