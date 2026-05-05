---
wave: 1
depends_on: ["051"]
files_modified:
  - src/state_daemon/service.py
  - tests/test_daemon_service.py
autonomous: true
---

# Plan 055-1: launchd plist + systemd user unit + installer

**Goal:** `state daemon install` generates and installs OS service definitions for macOS (launchd plist) and Linux (systemd user unit), with an `uninstall` command that removes and unloads them.

**Requirements:** DAE-01

### Tasks

#### 055.1 Service Template Generator

**Acceptance:** `generate_plist(daemon_path, socket_path, project_root) -> str` and `generate_service_unit(daemon_path, socket_path, project_root) -> str` produce valid service definitions.
**Estimated effort:** Medium
**Dependencies:** none

**Details:**
- Platform detection via `sys.platform == "darwin"` or `"linux"`.
- macOS: Generate `~/Library/LaunchAgents/com.state.daemon.plist` XML plist with `KeepAlive=true`, `RunAtLoad=true`, `WorkingDirectory=<project_root>`, `ProgramArguments=[daemon_path, "--project-root", project_root, "--socket", socket_path]`.
- Linux: Generate `~/.config/systemd/user/state-daemon.service` with `[Unit] Description=State Daemon`, `[Service] Type=simple`, `ExecStart=<daemon_path> --project-root <project_root> --socket <socket_path>`, `Restart=on-failure`, `[Install] WantedBy=default.target`.
- `daemon_path` = `sys.executable -m state_daemon` or entry point path.
- Test: unit tests that validate generated plist XML structure and systemd unit syntax (basic).

**Files:**
- `src/state_daemon/service.py` — new file

#### 055.2 Install/Uninstall Commands

**Acceptance:** `install_service()` writes service file and enables it; `uninstall_service()` removes and unloads it.
**Estimated effort:** Medium
**Dependencies:** 055.1

**Details:**
- `install_service()`:
  - Write plist/unit file to the correct location.
  - macOS: `launchctl load ~/Library/LaunchAgents/com.state.daemon.plist`.
  - Linux: `systemctl --user enable state-daemon.service && systemctl --user start state-daemon.service`.
  - Handle errors: file permissions, launchctl/systemctl not found.
- `uninstall_service()`:
  - macOS: `launchctl unload ~/Library/LaunchAgents/com.state.daemon.plist && rm <plist>`.
  - Linux: `systemctl --user stop state-daemon.service && systemctl --user disable state-daemon.service && rm <unit>`.
- Test: unit tests with mocked subprocess calls.

**Files:**
- `src/state_daemon/service.py` — extend with install/uninstall

#### 055.3 CLI Integration

**Acceptance:** `state daemon install` and `state daemon uninstall` work from the Typer CLI.
**Estimated effort:** Small
**Dependencies:** 055.2

**Details:**
- Add `install` and `uninstall` commands to the `state daemon` Typer app in `src/state_cli/main.py`.
- `state daemon install`: calls `install_service()`, prints success message with service status.
- `state daemon uninstall`: calls `uninstall_service()`, prints confirmation.
- Test: CLI integration tests with mocked service operations.

**Files:**
- `src/state_cli/main.py` — add install/uninstall commands

### must_haves

1. macOS launchd plist and Linux systemd unit generated correctly.
2. Install command places service file in correct OS-specific location.
3. Uninstall removes service file and unloads the service.
4. CLI integration: `state daemon install` and `state daemon uninstall` work.
