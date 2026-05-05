---
wave: 1
depends_on: ["001"]
files_modified:
  - src/state_daemon/pid.py
  - tests/test_daemon_pid.py
autonomous: true
---

# Plan 051-1: PID-File + Stale Detection

**Goal:** Implement atomic pid-file management with start_time_ns and platform-aware stale process detection — defense against P0-15 (stale pid prevents daemon restart).

**Requirements:** DAE-03
**P0 Pitfall:** P0-15

### Tasks

#### 051.1 PID File Writer — atomic JSON with {pid, start_time_ns}

**Acceptance:** `write_pid_file(path)` creates a JSON file containing `{"pid": N, "start_time_ns": M}` atomically; `read_pid_file(path)` parses it back.
**Estimated effort:** Small
**Dependencies:** none

**Details:**
- Implement `write_pid_file(path: str) -> None` that writes to a temp file first, then `os.rename()` for atomicity.
- `start_time_ns` uses `time.monotonic_ns()` at daemon start.
- `read_pid_file(path: str) -> dict[str, int]` reads and validates the JSON structure.
- Handle missing file gracefully (return None).
- Handle malformed JSON (log warning, return None).
- File path: `.state/daemon.pid` (resolve relative to project root).
- Test: unit tests for write/read round-trip, corrupt file handling, missing file.

**Files:**
- `src/state_daemon/pid.py` — new file

#### 051.2 Stale Process Detection — platform-aware

**Acceptance:** `is_pid_alive(pid, expected_start_time_ns) -> bool` correctly identifies running and stale processes on both macOS and Linux.
**Estimated effort:** Medium
**Dependencies:** 051.1

**Details:**
- Implement `is_pid_alive(pid: int, expected_start_time_ns: int) -> bool`.
- On Linux: read `/proc/<pid>/stat`, parse field 22 (starttime in clock ticks since boot), convert to ns and compare.
- On macOS: run `ps -p <pid> -o lstart=` to get process start time, parse, convert to ns and compare.
- Other platforms: attempt `os.kill(pid, 0)` — this only checks if process exists, not start time match.
- If process is gone OR start time doesn't match: stale — return False.
- Test: mock `os.kill` and `/proc` reads for Linux; mock `subprocess.run` for macOS.

**Files:**
- `src/state_daemon/pid.py` — extend with stale detection

#### 051.3 PID File Lifecycle — write at startup, remove at shutdown, stale cleanup

**Acceptance:** Daemon startup writes pid file; shutdown removes it; if stale pid detected on next start, old file is removed and new one written.
**Estimated effort:** Small
**Dependencies:** 051.1, 051.2

**Details:**
- `acquire_pid_file(path: str) -> bool`: attempts to claim the pid file:
  1. If no file exists: write and return True.
  2. If file exists and `is_pid_alive()` matches: log error, return False (daemon already running).
  3. If file exists and pid is stale: remove old file, write new one, log warning, return True.
- `release_pid_file(path: str)`: remove the pid file (called on graceful shutdown).
- Wire into `orchestrator.startup()` (after redactor, before server) and signal handler (on shutdown).
- Test: integration tests for stale cleanup and double-start prevention.

**Files:**
- `src/state_daemon/pid.py` — lifecycle functions
- `src/state_daemon/orchestrator.py` — wire pid-file lifecycle

### Integration Notes

- This phase is independent of the HTTP server (Phase 050) — can run in parallel.
- Provides the pid-file that Phase 058 (CLI) reads for `status` command.
- P0-15 defense: stale pid detection must run BEFORE any network bind attempt.

### must_haves

1. PID file written atomically (temp + rename) with `{pid, start_time_ns}`.
2. Stale process detection correctly identifies dead/mismatched processes on macOS and Linux.
3. Daemon refuses to start if another instance is running (pid match).
4. Stale PID file is cleaned up and daemon starts fresh.
5. PID file removed on graceful shutdown.
