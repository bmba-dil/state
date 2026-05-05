---
wave: 1
depends_on: ["051", "055"]
files_modified:
  - src/state_daemon/cli.py
  - src/state_cli/main.py
  - tests/test_daemon_cli.py
autonomous: true
---

# Plan 058-1: CLI: state daemon start|stop|restart|status|logs

**Goal:** Implement the user-facing CLI for managing the daemon lifecycle — start, stop, restart, status, and log tailing commands via Typer.

**Requirements:** DAE-09

### Tasks

#### 058.1 Start/Stop/Restart Commands

**Acceptance:** `state daemon start` launches daemon; `stop` sends SIGTERM; `restart` = stop + start with short delay.
**Estimated effort:** Medium
**Dependencies:** 051 (pid-file), 055 (service installer)

**Details:**
- `start` command in `src/state_daemon/cli.py`:
  - If service is installed (Phase 055): delegate to `launchctl start` / `systemctl --user start`.
  - If not installed: spawn daemon as background subprocess via `subprocess.Popen`.
  - After start, wait for pid-file to appear, verify process is alive.
  - Print success with pid and socket path.
- `stop` command:
  - Read pid-file to get daemon pid.
  - Send SIGTERM; wait up to 10s for graceful shutdown.
  - If process still alive, send SIGKILL.
  - Remove stale pid-file if process was killed.
  - If no pid-file: "Daemon is not running."
- `restart` command: stop + 1s delay + start.
- Test: CLI integration tests with mocked subprocess/pid operations.

**Files:**
- `src/state_daemon/cli.py` — implement commands
- `src/state_cli/main.py` — register daemon subcommands

#### 058.2 Status Command

**Acceptance:** `state daemon status` displays pid, start_time (human readable), events count, active mode, socket path.
**Estimated effort:** Small
**Dependencies:** 058.1, 051

**Details:**
- `status` command:
  - Read pid-file and check if process alive (Phase 051's `is_pid_alive`).
  - Read socket path from `.state/daemon.sock` (Phase 052).
  - Read mode from `.state/mode.json` (Phase 053).
  - Query event count from event store (Phase 004).
  - Display formatted table with Rich (`pid`, `start_time`, `uptime`, `events_count`, `mode`, `socket`).
- If daemon not running: display "Daemon is not running" with clear message.
- Test: unit tests for status parsing, integration tests for running/not-running states.

**Files:**
- `src/state_daemon/cli.py` — status command

#### 058.3 Logs Command

**Acceptance:** `state daemon logs [--follow] [--lines N]` tails daemon.log like `tail -f`.
**Estimated effort:** Small
**Dependencies:** 056 (logging)

**Details:**
- `logs` command:
  - Read daemon log from `.state/logs/daemon.log`.
  - `--lines N`: show last N lines (default 20).
  - `--follow`: tail -f mode — watch file for new lines (poll every 500ms or use inotify).
  - If log file doesn't exist: "No log file found — daemon may not have started yet."
- Test: integration tests with temp log files.

**Files:**
- `src/state_daemon/cli.py` — logs command

### must_haves

1. `start` launches daemon and verifies it's running.
2. `stop` gracefully terminates daemon via SIGTERM/SIGKILL.
3. `status` shows accurate pid, uptime, events count, mode, socket path.
4. `logs` tails daemon log with --follow and --lines options.
5. All commands handle daemon-not-running state gracefully.
