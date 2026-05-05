---
phase: 103
plan: 01
subsystem: cli-daemon-mode
tags: [mode-set, sighup, hot-reload, cli]
requires:
  provides: [mode-set-cli, daemon-sighup-handler]
  affects: [future-worker-mode-sync, future-sse-mode-fanout]
tech-stack:
  added: []
  patterns: [atomic-temp-rename-write, signal-driven-hot-reload, tdd-red-green]
key-files:
  created: []
  modified:
    - src/state_cli/main.py
    - src/state_daemon/orchestrator.py
    - tests/test_cli.py
    - tests/test_daemon_middleware.py
key-decisions:
  - "Atomic mode.json write via mkstemp + chmod 0600 + os.replace to prevent partial-write corruption"
  - "SIGHUP handler calls load_mode_config() for daemon hot-reload without restart"
  - "Project root cached as module-level _project_root so signal handler can access it"
  - "SIGHUP sent only when daemon pid exists AND process is alive (os.kill(pid, 0) check)"
patterns-established:
  - "Mode set CLI follows same validation (validate_mode_config) and subtree creation pattern as mode init"
  - "Signal handler registration uses same try/except NotImplementedError pattern as existing SIGTERM/SIGINT handlers"
  - "Test classes follow CliRunner + tmp_path + os.chdir pattern established by TestModeInit"
requirements-completed: [MODE-07]
metrics:
  duration: "< 1 hour"
  completed: 2026-05-05
---

# Phase 103 Plan 01: CLI state mode set + Daemon SIGHUP Summary

**One-liner:** Added `state mode set build|teach|both` CLI command with atomic mode.json rewrite, subtree creation, and daemon SIGHUP hot-reload with full test coverage.

## What Was Built

### state mode set CLI command (src/state_cli/main.py)

New `mode_set()` function registered as `@mode_app.command(name="set")`:

- **Validation-first**: Calls `validate_mode_config()` before any filesystem write — rejects `kernel`, `invalid`, and empty modes with error message and exit code 1
- **Atomic write**: Uses `tempfile.mkstemp()` + `os.chmod(0o600)` + `os.replace()` for atomic, crash-safe mode.json updates. No partial-write window exists
- **Subtree creation**: Creates `.state/build/` for build/both modes, `.state/teach/` for teach/both modes, following the same `mkdir(parents=True, exist_ok=True)` pattern as `mode init`
- **Daemon SIGHUP**: Reads daemon pid from `.state/daemon.pid`, verifies process liveness with `os.kill(pid, 0)`, then sends `SIGHUP` for hot-reload. Gracefully silent when no daemon is running
- **Idempotent**: Setting the same mode twice exits 0 with no errors; `exist_ok=True` on all mkdir calls

### Daemon SIGHUP handler (src/state_daemon/orchestrator.py)

- **Module-level `_project_root`**: Captured during `startup()` so the signal handler (a synchronous function) can locate `.state/mode.json`
- **`_schedule_mode_reload()`**: Re-reads mode config via `load_mode_config(_project_root)` and logs the new active mode. Updates the global `_config` in `middleware.py` — no daemon restart needed
- **Signal registration**: Registered alongside existing SIGTERM/SIGINT handlers with the same `try/except NotImplementedError` platform-guard pattern

## Test Coverage

### TestModeSet (tests/test_cli.py) — 13 tests

| Test | What It Validates |
|------|-------------------|
| `test_set_build_creates_mode_json` | Build writes `{"mode":"build"}`, 0600 permissions |
| `test_set_teach` | Teach writes `{"mode":"teach"}`, 0600 permissions |
| `test_set_both` | Both writes `{"mode":"both"}`, 0600 permissions |
| `test_set_rejects_invalid_mode` | Invalid mode → non-zero exit |
| `test_set_rejects_kernel_mode` | Kernel → non-zero exit |
| `test_set_creates_build_subtree` | `.state/build/` directory created |
| `test_set_teach_creates_teach_subtree_no_build` | `.state/teach/` created, `.state/build/` absent |
| `test_set_both_creates_both_subtrees` | Both subtrees created |
| `test_set_overwrites_existing_mode` | build→teach transition overwrites mode.json |
| `test_set_idempotent` | Same mode twice exits 0 both times |
| `test_set_sends_sighup_to_daemon` | SIGHUP relay via mocked `os.kill` |
| `test_set_no_sighup_without_daemon` | Succeeds when pid file absent |
| `test_set_creates_state_dir_if_missing` | Auto-creates `.state/` directory |

### TestModeInit (tests/test_cli.py) — 14 tests (regression)

All 14 existing init tests pass with zero changes — subtree bootstrapping, mode.json creation, kernel rejection, idempotency all confirmed.

### TestModeReload (tests/test_daemon_middleware.py) — 2 tests

| Test | What It Validates |
|------|-------------------|
| `test_reload_updates_config` | `load_mode_config()` re-reads overwritten mode.json |
| `test_reload_handles_missing_file` | Default `both` fallback when file is missing |

### Regression — 104 tests pass

- 26 CLI tests (tail, replay, export, edge cases): all pass
- 78 daemon middleware tests (mode config, middleware enforcement, event-type validation, subtree path validation): all pass

## Deviations from Plan

None — plan executed exactly as written.

## Git History

```
68a2bae test(103-01): add failing tests for mode set command
14aa92e feat(103-01): implement mode set command and daemon SIGHUP handler
e3696da test(103-01): add daemon mode reload tests for SIGHUP handler
```

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `68a2bae` — 13 failing TestModeSet tests | ✓ |
| GREEN | `14aa92e` — implementation in main.py + orchestrator.py | ✓ |
| REFACTOR | N/A — no refactoring needed | — |

Task 2 (TestModeReload): Tests passed on first run because `load_mode_config()` was built in Phase 097. These tests validate the reload mechanism used by the SIGHUP handler. The TDD RED phase was skipped for Task 2 since no implementation gap existed.

## Self-Check: PASSED

- [x] `src/state_cli/main.py` modified with `mode_set` command
- [x] `src/state_daemon/orchestrator.py` modified with `_schedule_mode_reload` + SIGHUP registration
- [x] `tests/test_cli.py` modified with `TestModeSet` (13 tests)
- [x] `tests/test_daemon_middleware.py` modified with `TestModeReload` (2 tests)
- [x] All commits exist: `68a2bae`, `14aa92e`, `e3696da`
- [x] All 13+14+2+26+78 = 133 tests pass with zero regressions
