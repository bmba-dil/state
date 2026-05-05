---
phase: 051-pid-file-start-time-ns
plan: "01"
subsystem: infra
tags: [pid-file, stale-detection, platform-detection, daemon, atomic-write]

# Dependency graph
requires:
  - phase: "001"
    provides: "Foundation event store and core infrastructure"
provides:
  - "Atomic JSON pid-file write with {pid, start_time_ns}"
  - "Platform-aware stale process detection (Linux /proc, macOS ps, fallback os.kill)"
  - "PID file lifecycle wired into daemon startup/shutdown (P0-15 defense)"
affects: ["058", "daemon-startup", "CLI-status"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic file write via temp+rename (os.replace)"
    - "Platform dispatch pattern (sys.platform switch with private helpers)"
    - "Module-level state for signal-handler cleanup (_server, _pid_path)"

key-files:
  created:
    - "src/state_daemon/pid.py"
    - "tests/test_daemon_pid.py"
  modified:
    - "src/state_daemon/orchestrator.py"
    - "tests/test_orchestrator_import_opencode.py"

key-decisions:
  - "Atomic write via temp+rename (os.replace) for pid file — prevents partial reads"
  - "5-second tolerance window for clock granularity differences in stale detection"
  - "Platform dispatch: Linux /proc/<pid>/stat field 22, macOS ps -o lstart=, fallback os.kill(pid, 0)"
  - "Pid acquisition runs after redactor install but before any network bind — P0-15 defense"
  - "Module-level _pid_path stored for signal-handler cleanup (SIGTERM/SIGINT)"

patterns-established:
  - "Pattern 1: Module-level globals for shutdown state — _server and _pid_path are set during startup and read by signal handlers"
  - "Pattern 2: Environment-variable overrides for file paths — STATE_DAEMON_PID overrides default .state/daemon.pid"

requirements-completed: [DAE-03]

# Metrics
duration: ~30min
completed: 2026-05-05
---

# Phase 051 Plan 01: PID-File + Stale Detection Summary

**Atomic pid-file with platform-aware stale detection wired into daemon startup, closing P0-15 threat (stale pid blocking restart)**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-04T23:40:00Z
- **Completed:** 2026-05-05T00:10:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Atomic JSON pid-file (`{pid, start_time_ns}`) with temp+rename write — no partial reads possible
- Platform-aware `is_pid_alive()`: Linux `/proc/<pid>/stat` field 22, macOS `ps -o lstart=`, fallback `os.kill(pid, 0)`
- Lifecycle wired into orchestrator: acquire at startup (after redactor, before network bind), release on graceful shutdown (SIGTERM/SIGINT)
- Double-start prevention — daemon refuses to start if another instance is alive with matching start time
- Stale pid cleanup — dead/zombie pid files are detected and cleaned, daemon starts fresh

## Task Commits

Each task was committed atomically:

1. **Task 051.1: PID File Writer** — `56c3560` (feat) — `write_pid_file()` + `read_pid_file()` with 6 unit tests
2. **Task 051.2: Stale Process Detection** — `4a2d9dc` (feat) — `is_pid_alive()` with Linux/Darwin/fallback paths, 22 tests
3. **Task 051.3: PID File Lifecycle** — `b0537b3` (feat) — `acquire_pid_file()` + `release_pid_file()` wired into orchestrator, 7 tests

## Files Created/Modified

- `src/state_daemon/pid.py` — PID file management: atomic write/read, stale detection, lifecycle functions (~230 LOC)
- `tests/test_daemon_pid.py` — Comprehensive test suite: write/read round-trip, corrupt handling, Linux/Darwin/fallback stale detection, lifecycle (35 tests)
- `src/state_daemon/orchestrator.py` — Wired pid acquisition into startup() after redactor, pid release into _shutdown_server()
- `tests/test_orchestrator_import_opencode.py` — Added acquire_pid_file mock to existing orchestrator tests

## Decisions Made

1. **Atomic write via `os.replace()`** — writes to temp file first, then atomically renames. Prevents readers from seeing partially-written state.
2. **5-second tolerance window** — clock granularity between `time.monotonic_ns()` (userspace) and kernel-reported start times (clock ticks, ps date resolution) requires tolerance.
3. **Platform dispatch pattern** — `sys.platform` switch at the public `is_pid_alive()` level routes to private `_is_pid_alive_linux()`, `_is_pid_alive_darwin()`, `_is_pid_alive_fallback()` helpers. Clean and testable.
4. **Acquisition before network bind** — P0-15 states "stale pid prevents daemon restart." By checking the pid file BEFORE any socket bind or I/O (right after redactor install), we prevent a zombie pid-file from blocking startup.
5. **Module-level `_pid_path` for signal handlers** — `_schedule_shutdown()` is synchronous (signal handler requirement), so it needs module-level state to know which pid file to clean. Same pattern as `_server`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `Path.write_text()` positional argument order in tests**
- **Found during:** Task 051.1 (PID File Writer tests)
- **Issue:** `path_lib.write_text("content", encoding="utf-8")` — missing `data` as first positional arg; `write_text(data, encoding=...)` is the correct signature
- **Fix:** Changed to `path.write_text("content", encoding="utf-8")` with `path` being a `Path` instance directly
- **Files modified:** `tests/test_daemon_pid.py`
- **Committed in:** `56c3560`

**2. [Rule 1 - Bug] Fixed regression: orchestrator tests broke from pid acquisition**
- **Found during:** Task 051.3 (verification)
- **Issue:** Two existing `test_orchestrator_import_opencode.py` tests called `startup()` without mocking `acquire_pid_file`, causing `SystemExit(1)` when a real pid file existed
- **Fix:** Added `patch("state_daemon.orchestrator.acquire_pid_file", return_value=True)` to all three orchestrator tests
- **Files modified:** `tests/test_orchestrator_import_opencode.py`
- **Committed in:** `b0537b3`

---

**Total deviations:** 2 auto-fixed (Rule 1 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. Test regression fix prevented false failures in CI. No scope creep.

## Issues Encountered

- **Python 3.14 vs .venv mismatch:** Default `python3` is 3.14 (Homebrew) without `litellm` installed. Project uses `uv` with `.venv` (Python 3.12). All tests run via `uv run pytest`.

## Stub Scan

No stubs found — all functions are fully implemented with working logic. No hardcoded empty values, placeholder text, or unwired components.

## Threat Flags

No new threat surface beyond the plan's intended scope. The pid file uses local filesystem only (`.state/daemon.pid`). `subprocess.run` is used with fixed arguments (no shell injection). P0-15 is explicitly addressed.

## Next Phase Readiness

- PID file infrastructure ready for Phase 058 (CLI `status` command reads pid file)
- Daemon startup now has defense-in-depth for P0-15 (stale pid preventing restart)
- No blockers — all 35 tests passing, zero regressions in existing test suites

---

## Self-Check: PASSED

All key files verified on disk, all 3 commits confirmed in git log.

---

*Phase: 051-pid-file-start-time-ns*
*Plan: 01*
*Completed: 2026-05-05*