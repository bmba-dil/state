---
phase: 055-launchd-plist-systemd-user-unit
plan: "1"
subsystem: infra
tags: [launchd, systemd, plist, typer, cli]

# Dependency graph
requires:
  - phase: "051"
    provides: "PID file management with stale detection"
provides:
  - "OS-level service definitions for macOS (launchd plist) and Linux (systemd user unit)"
  - "state daemon install CLI command that writes and loads service files"
  - "state daemon uninstall CLI command that unloads and removes service files"
affects: ["058", "daemon-startup", "cli-integration"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xml.etree.ElementTree for plist XML generation (no Jinja2 dependency)"
    - "sys.platform dispatch for macOS vs Linux service management"
    - "Typer sub-app registration pattern (matching existing db/events/auth/snapshot apps)"

key-files:
  created:
    - "src/state_daemon/service.py — OS service definition generation + install/uninstall"
    - "tests/test_daemon_service.py — 28 tests covering plist/systemd generation, install/uninstall, CLI integration"
  modified:
    - "src/state_daemon/cli.py — Built out from 3-line stub to full Typer app with install/uninstall commands"
    - "src/state_cli/main.py — Registered daemon sub-app"

key-decisions:
  - "Used xml.etree.ElementTree (stdlib) instead of Jinja2 for plist generation — avoids adding a dependency for simple XML templating"
  - "Systemd unit generated with string formatting (INI-like format, trivial)"
  - "install_service() auto-discovers sys.executable, socket path, and project root when not explicitly passed"
  - "launchctl load is treated as start-equivalent on macOS (no separate start subprocess needed)"
  - "uninstall is best-effort — launchctl unload doesn't fail if plist already removed"

patterns-established:
  - "Typer sub-app: create a typer.Typer() in package cli.py, import and add_typer() in main.py (matching auth, snapshot patterns)"
  - "Service layer separation: service.py has pure functions; cli.py handles user-facing output and error formatting"

requirements-completed: ["DAE-01"]

# Metrics
duration: 8min
completed: 2026-05-05
---

# Phase 055 Plan 1: launchd plist + systemd user unit + installer Summary

**OS service definitions for macOS launchd and Linux systemd with CLI install/uninstall, using stdlib XML generation and Typer CLI integration**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-05T01:21:02Z
- **Completed:** 2026-05-05T01:29:53Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `generate_plist()` produces valid macOS launchd plist XML with KeepAlive, RunAtLoad, WorkingDirectory, and log paths — verified with 7 unit tests checking XML structure and key presence
- `generate_service_unit()` produces valid Linux systemd `--user` unit with Restart=on-failure, RestartSec=5, and WantedBy=default.target — verified with 6 unit tests
- `install_service()` writes the OS-appropriate file, creates parent directories, and invokes launchctl load / systemctl enable+start — 4 integration tests with mocked subprocess
- `uninstall_service()` unloads/disables and removes the file — 2 integration tests
- `state daemon install` and `state daemon uninstall` CLI commands with proper error handling (FileNotFoundError, PermissionError, generic) — 9 CLI tests using CliRunner
- Daemon sub-app registered in main Typer CLI, visible via `state daemon --help`

## Task Commits

Each task was committed atomically:

1. **Task 055.1: Service Template Generator** - `056032b` (feat)
2. **Task 055.2: Install/Uninstall Commands** - included in `056032b` (feat) — install/uninstall functions were co-developed with generators in service.py
3. **Task 055.3: CLI Integration** - `d119668` (feat)

## Files Created/Modified

- `src/state_daemon/service.py` — Core service module: plist XML generation, systemd unit generation, install_service(), uninstall_service(), platform helpers
- `src/state_daemon/cli.py` — Built out from 3-line stub to Typer app with `install` and `uninstall` commands with full error handling
- `src/state_cli/main.py` — Added `daemon_app` registration matching existing sub-app pattern
- `tests/test_daemon_service.py` — 28 tests: 7 plist structure, 6 systemd unit, 4 install/uninstall, 2 platform detection, 9 CLI integration

## Decisions Made

- **No Jinja2 dependency**: The CONTEXT.md suggested Jinja2 templates, but xml.etree.ElementTree (stdlib) handles plist XML cleanly, and systemd units are simple INI-like format. Adding a dependency for this would be over-engineering.
- **Auto-discovery defaults**: `install_service()` defaults to `sys.executable`, `os.getcwd()`, and `.state/daemon.sock` so the CLI command is zero-config.
- **launchctl load = start**: On macOS, `launchctl load` starts the service immediately, so no separate start command is needed. On Linux, `systemctl --user enable` must be followed by `--user start`.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **Python venv mismatch**: System `python3` is 3.14; project venv is 3.12. Tests must be run with `.venv/bin/python3`. This is a pre-existing environment configuration, not introduced by this phase.

## Next Phase Readiness

- `state daemon install` and `state daemon uninstall` are ready for Phase 058 (CLI start/stop/status integration)
- Service definitions reference socket path from Phase 052 and project root conventions — compatible with existing daemon server infrastructure

---
*Phase: 055-launchd-plist-systemd-user-unit*
*Completed: 2026-05-05*
