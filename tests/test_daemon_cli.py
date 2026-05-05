"""Tests for state_daemon.cli — start, stop, restart, status, logs commands.

Uses ``typer.testing.CliRunner`` for CLI invocation with mocked subprocess,
pid, and file operations to keep tests fast and deterministic.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from src.state_daemon import cli as daemon_cli
from src.state_daemon.cli import app as daemon_app

runner = CliRunner()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_service_def(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point _svc_def_path to a temp file so tests don't touch the real service."""
    monkeypatch.setattr(
        daemon_cli,
        "_svc_def_path",
        lambda: str(tmp_path / "test-service.def"),
    )


@pytest.fixture(autouse=True)
def _chdir_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Change working directory to tmp_path so project-root defaults to temp dir."""
    monkeypatch.chdir(tmp_path)


# ── Task 058.1 — start command ──────────────────────────────────────────────


class TestStartCommand:
    """Tests for ``state daemon start``."""

    def test_start_without_service_spawns_daemon(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When no service is installed, start spawns a background subprocess."""
        fake_pid = 78901
        fake_start_ns = int(time.monotonic_ns())

        # Write a fake socket path so the success message includes it
        sock_dir = tmp_path / ".state"
        sock_dir.mkdir(parents=True, exist_ok=True)
        (sock_dir / "daemon.sock").write_text("/tmp/fake-socket.sock")

        # Mock subprocess.Popen to avoid actually spawning a process
        mock_popen = mock.MagicMock(spec=subprocess.Popen)
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        # Mock read_pid_file to return valid pid data after "spawn"
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": fake_pid, "start_time_ns": fake_start_ns},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        monkeypatch.setattr(
            daemon_cli,
            "_wait_for_pid_file",
            lambda path=None, timeout=None, interval=None: {"pid": fake_pid, "start_time_ns": fake_start_ns},
        )

        result = runner.invoke(daemon_app, ["start"])
        assert result.exit_code == 0
        assert f"pid={fake_pid}" in result.stdout
        assert "socket=" in result.stdout

    def test_start_with_service_installed_delegates(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When service is installed, start delegates to OS service manager."""
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: True)
        mock_run = mock.MagicMock()
        monkeypatch.setattr(daemon_cli.subprocess, "run", mock_run)

        result = runner.invoke(daemon_app, ["start"])
        assert result.exit_code == 0
        assert "via OS service manager" in result.stdout

    def test_start_daemon_exits_immediately(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When the spawned process dies before pid verification, exit 1."""
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        mock_popen = mock.MagicMock(spec=subprocess.Popen)
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        # pid file appears but process is dead
        monkeypatch.setattr(
            daemon_cli,
            "_wait_for_pid_file",
            lambda path=None, timeout=None, interval=None: {"pid": 99999, "start_time_ns": 1},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: False)

        result = runner.invoke(daemon_app, ["start"])
        assert result.exit_code == 1
        assert "exited immediately" in result.stderr

    def test_start_pid_file_never_appears(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When pid file never appears within timeout, exit 1."""
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        mock_popen = mock.MagicMock(spec=subprocess.Popen)
        monkeypatch.setattr(subprocess, "Popen", mock_popen)
        monkeypatch.setattr(daemon_cli, "_wait_for_pid_file", lambda path=None, timeout=None, interval=None: None)

        result = runner.invoke(daemon_app, ["start"])
        assert result.exit_code == 1
        assert "did not start" in result.stderr


# ── Task 058.1 — stop command ───────────────────────────────────────────────


class TestStopCommand:
    """Tests for ``state daemon stop``."""

    def test_stop_no_pid_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no pid file exists, reports daemon is not running."""
        monkeypatch.setattr(daemon_cli, "read_pid_file", lambda p: None)

        result = runner.invoke(daemon_app, ["stop"])
        assert result.exit_code == 0
        assert "not running" in result.stdout.lower()

    def test_stop_stale_pid_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stale pid file is cleaned up and reported as not running."""
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": 12345, "start_time_ns": 1},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: False)
        monkeypatch.setattr(daemon_cli, "release_pid_file", lambda p: None)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)

        result = runner.invoke(daemon_app, ["stop"])
        assert result.exit_code == 0
        assert "not running" in result.stdout.lower()
        assert "stale" in result.stdout.lower()

    def test_stop_graceful_kill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Graceful SIGTERM stop when process exits promptly."""
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": 12345, "start_time_ns": int(time.monotonic_ns())},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)
        monkeypatch.setattr(daemon_cli, "release_pid_file", lambda p: None)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        monkeypatch.setattr(daemon_cli, "_sigkill_fallback", lambda pid, timeout: True)

        result = runner.invoke(daemon_app, ["stop"])
        assert result.exit_code == 0
        assert "stopped" in result.stdout.lower()

    def test_stop_force_kill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Force kill when SIGTERM grace period expires."""
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": 12345, "start_time_ns": int(time.monotonic_ns())},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)
        monkeypatch.setattr(daemon_cli, "release_pid_file", lambda p: None)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        monkeypatch.setattr(daemon_cli, "_sigkill_fallback", lambda pid, timeout: False)

        result = runner.invoke(daemon_app, ["stop"])
        assert result.exit_code == 0
        assert "force-killed" in result.stdout.lower()


# ── Task 058.1 — restart command ────────────────────────────────────────────


class TestRestartCommand:
    """Tests for ``state daemon restart``."""

    def test_restart_not_running_starts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Restart when daemon is not running: just starts it."""
        monkeypatch.setattr(daemon_cli, "read_pid_file", lambda p: None)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)

        mock_popen = mock.MagicMock(spec=subprocess.Popen)
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        fake_pid = 78901
        fake_start = int(time.monotonic_ns())
        monkeypatch.setattr(
            daemon_cli,
            "_wait_for_pid_file",
            lambda path=None, timeout=None, interval=None: {"pid": fake_pid, "start_time_ns": fake_start},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)

        # Write fake socket
        sock_dir = tmp_path / ".state"
        sock_dir.mkdir(parents=True, exist_ok=True)
        (sock_dir / "daemon.sock").write_text("/tmp/fake.sock")

        result = runner.invoke(daemon_app, ["restart"])
        assert result.exit_code == 0

    def test_restart_running_stops_then_starts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Restart when daemon is running: stop + delay + start."""
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": 12345, "start_time_ns": int(time.monotonic_ns())},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)
        monkeypatch.setattr(daemon_cli, "release_pid_file", lambda p: None)
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        monkeypatch.setattr(daemon_cli, "_sigkill_fallback", lambda pid, timeout: True)

        # Mock the 1s sleep to be instant
        monkeypatch.setattr(daemon_cli.time, "sleep", mock.MagicMock())

        # Now mock start's inner deps
        mock_popen = mock.MagicMock(spec=subprocess.Popen)
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        fake_pid = 78901
        fake_start = int(time.monotonic_ns())
        monkeypatch.setattr(
            daemon_cli,
            "_wait_for_pid_file",
            lambda path=None, timeout=None, interval=None: {"pid": fake_pid, "start_time_ns": fake_start},
        )

        # Write fake socket
        sock_dir = tmp_path / ".state"
        sock_dir.mkdir(parents=True, exist_ok=True)
        (sock_dir / "daemon.sock").write_text("/tmp/fake.sock")

        result = runner.invoke(daemon_app, ["restart"])
        assert result.exit_code == 0
        assert "Stopped daemon" in result.stdout


# ── Task 058.2 — status command ─────────────────────────────────────────────


class TestStatusCommand:
    """Tests for ``state daemon status``."""

    def test_status_not_running_no_pid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No pid file → clean 'not running' message."""
        monkeypatch.setattr(daemon_cli, "read_pid_file", lambda p: None)

        result = runner.invoke(daemon_app, ["status"])
        assert result.exit_code == 0
        assert "not running" in result.stdout.lower()

    def test_status_running_shows_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Running daemon → Rich table with pid, uptime, mode, socket, events."""
        fake_pid = 78901
        fake_start = int(time.monotonic_ns()) - 60_000_000_000  # 60s ago

        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": fake_pid, "start_time_ns": fake_start},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)

        # Socket path
        sock_dir = tmp_path / ".state"
        sock_dir.mkdir(parents=True, exist_ok=True)
        (sock_dir / "daemon.sock").write_text("/tmp/fake-socket.sock")

        # Mode
        (sock_dir / "mode.json").write_text(json.dumps({"mode": "build"}))

        def _fake_read_mode() -> str | None:
            try:
                return json.loads((sock_dir / "mode.json").read_text())["mode"]
            except Exception:
                return None

        monkeypatch.setattr(daemon_cli, "_read_mode", _fake_read_mode)
        monkeypatch.setattr(daemon_cli, "_resolve_daemon_socket_path", lambda: "/tmp/fake-socket.sock")

        # Mock event store count via patching the source module
        from src.state_core import events as events_module

        async def _fake_count(self, *, mode=None) -> int:
            return 42

        monkeypatch.setattr(events_module.SqliteEventStore, "count_events", _fake_count)

        result = runner.invoke(daemon_app, ["status"])
        assert result.exit_code == 0
        assert str(fake_pid) in result.stdout
        assert "build" in result.stdout
        assert "42" in result.stdout

    def test_status_stale_pid_shows_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stale pid file → shows pid as stale."""
        monkeypatch.setattr(
            daemon_cli,
            "read_pid_file",
            lambda p: {"pid": 99999, "start_time_ns": 1},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: False)

        result = runner.invoke(daemon_app, ["status"])
        assert result.exit_code == 0
        assert "stale" in result.stdout.lower()
        assert "99999" in result.stdout


# ── Task 058.3 — logs command ───────────────────────────────────────────────


class TestLogsCommand:
    """Tests for ``state daemon logs``."""

    def test_logs_no_log_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When log file doesn't exist, prints informative message."""
        monkeypatch.setattr(daemon_cli, "_LOG_PATH", "/nonexistent/path/daemon.log")

        result = runner.invoke(daemon_app, ["logs"])
        assert result.exit_code == 0
        assert "No log file found" in result.stdout

    def test_logs_shows_last_n_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Shows the last N lines of the log file."""
        log_file = tmp_path / "daemon.log"
        lines = [f"line {i}\n" for i in range(1, 51)]  # 50 lines
        log_file.write_text("".join(lines), encoding="utf-8")

        monkeypatch.setattr(daemon_cli, "_LOG_PATH", str(log_file))

        result = runner.invoke(daemon_app, ["logs"])
        assert result.exit_code == 0
        output_lines = result.stdout.strip().splitlines()
        assert len(output_lines) == 20
        assert "line 31" in output_lines[0]
        assert "line 50" in output_lines[-1]

    def test_logs_custom_line_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--lines N shows exactly N lines."""
        log_file = tmp_path / "daemon.log"
        lines = [f"line {i}\n" for i in range(1, 21)]
        log_file.write_text("".join(lines), encoding="utf-8")

        monkeypatch.setattr(daemon_cli, "_LOG_PATH", str(log_file))

        result = runner.invoke(daemon_app, ["logs", "--lines", "5"])
        assert result.exit_code == 0
        output_lines = result.stdout.strip().splitlines()
        assert len(output_lines) == 5
        assert "line 16" in output_lines[0]

    def test_logs_empty_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty log file prints a message."""
        log_file = tmp_path / "daemon.log"
        log_file.write_text("", encoding="utf-8")

        monkeypatch.setattr(daemon_cli, "_LOG_PATH", str(log_file))

        result = runner.invoke(daemon_app, ["logs"])
        assert result.exit_code == 0
        assert "empty" in result.stdout.lower()


# ── Edge cases ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases across all daemon CLI commands."""

    def test_start_already_running(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """start when pid file already exists and process is alive — no crash."""
        monkeypatch.setattr(daemon_cli, "_is_service_installed", lambda: False)
        monkeypatch.setattr(subprocess, "Popen", mock.MagicMock(spec=subprocess.Popen))
        monkeypatch.setattr(
            daemon_cli,
            "_wait_for_pid_file",
            lambda path=None, timeout=None, interval=None: {"pid": 12345, "start_time_ns": int(time.monotonic_ns())},
        )
        monkeypatch.setattr(daemon_cli, "is_pid_alive", lambda pid, start_ns: True)

        result = runner.invoke(daemon_app, ["start"])
        assert result.exit_code == 0

    def test_help_shows_all_commands(self) -> None:
        """--help lists all registered daemon commands."""
        result = runner.invoke(daemon_app, ["--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "restart" in result.stdout
        assert "status" in result.stdout
        assert "logs" in result.stdout
        assert "install" in result.stdout
        assert "uninstall" in result.stdout
