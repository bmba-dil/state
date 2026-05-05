"""Tests for state_daemon.service — OS service definition generation and install/uninstall.

Task 055.1: Service Template Generator
Task 055.2: Install/Uninstall Commands
Task 055.3: CLI Integration
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

import pytest
import typer
from typer.testing import CliRunner

from src.state_daemon.cli import app as daemon_app
from src.state_daemon.service import (
    _PLIST_PATH,
    _UNIT_PATH,
    current_platform_name,
    generate_plist,
    generate_service_unit,
    install_service,
    uninstall_service,
)


# ---------------------------------------------------------------------------
# Task 055.1 — Plist generation
# ---------------------------------------------------------------------------

class TestGeneratePlist:
    """Validate the generated macOS launchd plist XML."""

    DAEMON = "/usr/local/bin/python3"
    SOCKET = "/tmp/state-daemon.sock"
    ROOT = "/Users/test/project"

    @pytest.fixture
    def plist_str(self) -> str:
        return generate_plist(self.DAEMON, self.SOCKET, self.ROOT)

    def test_is_valid_xml_with_doctype(self, plist_str: str) -> None:
        """The output must be parseable XML containing the plist DOCTYPE."""
        root = ET.fromstring(plist_str)
        assert root.tag == "plist"
        assert root.attrib.get("version") == "1.0"
        # DOCTYPE is not preserved by ElementTree.fromstring but should be in string
        assert "Apple//DTD PLIST 1.0//EN" in plist_str

    def test_label_is_com_state_daemon(self, plist_str: str) -> None:
        assert "<key>Label</key>" in plist_str
        assert "<string>com.state.daemon</string>" in plist_str

    def test_program_arguments_contain_daemon_path(self, plist_str: str) -> None:
        assert "<key>ProgramArguments</key>" in plist_str
        assert f"<string>{self.DAEMON}</string>" in plist_str
        assert "<string>-m</string>" in plist_str
        assert "<string>state_daemon</string>" in plist_str
        assert f"<string>{self.ROOT}</string>" in plist_str
        assert f"<string>{self.SOCKET}</string>" in plist_str

    def test_run_at_load_true(self, plist_str: str) -> None:
        assert "<key>RunAtLoad</key>" in plist_str
        assert "<true/>" in plist_str

    def test_keep_alive_true(self, plist_str: str) -> None:
        assert "<key>KeepAlive</key>" in plist_str
        assert "<true/>" in plist_str

    def test_working_directory(self, plist_str: str) -> None:
        assert "<key>WorkingDirectory</key>" in plist_str
        assert f"<string>{self.ROOT}</string>" in plist_str

    def test_log_paths(self, plist_str: str) -> None:
        assert "<key>StandardOutPath</key>" in plist_str
        assert "<key>StandardErrorPath</key>" in plist_str
        assert ".state/daemon.stdout.log" in plist_str
        assert ".state/daemon.stderr.log" in plist_str


# ---------------------------------------------------------------------------
# Task 055.1 — Systemd unit generation
# ---------------------------------------------------------------------------

class TestGenerateServiceUnit:
    """Validate the generated systemd user unit file."""

    DAEMON = "/usr/bin/python3"
    SOCKET = "/home/user/project/.state/daemon.sock"
    ROOT = "/home/user/project"

    @pytest.fixture
    def unit_str(self) -> str:
        return generate_service_unit(self.DAEMON, self.SOCKET, self.ROOT)

    def test_unit_section_present(self, unit_str: str) -> None:
        assert "[Unit]" in unit_str
        assert "Description=State Daemon" in unit_str
        assert "After=network.target" in unit_str

    def test_service_section_present(self, unit_str: str) -> None:
        assert "[Service]" in unit_str
        assert "Type=simple" in unit_str
        assert "Restart=on-failure" in unit_str
        assert "RestartSec=5" in unit_str

    def test_exec_start_contains_daemon_and_args(self, unit_str: str) -> None:
        line = [l for l in unit_str.splitlines() if l.startswith("ExecStart=")][0]
        assert self.DAEMON in line
        assert "-m state_daemon" in line
        assert self.SOCKET in line
        assert self.ROOT in line

    def test_working_directory(self, unit_str: str) -> None:
        assert f"WorkingDirectory={self.ROOT}" in unit_str

    def test_log_append_paths(self, unit_str: str) -> None:
        assert "StandardOutput=append:" in unit_str
        assert "StandardError=append:" in unit_str
        assert ".state/daemon.stdout.log" in unit_str
        assert ".state/daemon.stderr.log" in unit_str

    def test_install_section_present(self, unit_str: str) -> None:
        assert "[Install]" in unit_str
        assert "WantedBy=default.target" in unit_str


# ---------------------------------------------------------------------------
# Task 055.2 — Install / Uninstall
# ---------------------------------------------------------------------------

class TestInstallServiceDarwin:
    """Test ``install_service`` on macOS — mocked subprocess."""

    @pytest.fixture(autouse=True)
    def mock_platform_darwin(self) -> mock.MagicMock:
        with mock.patch("src.state_daemon.service.sys.platform", "darwin"):
            yield

    def test_writes_plist_and_calls_launchctl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plist_path = os.path.join(tmp, "com.state.daemon.plist")
            socket_path = os.path.join(tmp, ".state", "daemon.sock")

            with (
                mock.patch("src.state_daemon.service._PLIST_DIR", tmp),
                mock.patch("src.state_daemon.service._PLIST_PATH", plist_path),
                mock.patch("subprocess.run") as mock_run,
            ):
                install_service(
                    daemon_path="/usr/bin/python3",
                    socket_path=socket_path,
                    project_root=tmp,
                )

            # Verify file written
            assert os.path.isfile(plist_path), f"Plist not written to {plist_path}"
            content = open(plist_path).read()
            assert "com.state.daemon" in content
            assert "KeepAlive" in content

            # Verify launchctl load called
            mock_run.assert_any_call(
                ("launchctl", "load", plist_path),
                check=True,
                capture_output=False,
            )

    def test_uninstall_darwin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plist_path = os.path.join(tmp, "com.state.daemon.plist")

            # Create a dummy plist so os.remove succeeds
            Path(plist_path).write_text("<plist/>")

            with (
                mock.patch("src.state_daemon.service.sys.platform", "darwin"),
                mock.patch("src.state_daemon.service._PLIST_PATH", plist_path),
                mock.patch("subprocess.run") as mock_run,
            ):
                uninstall_service()

            # Verify launchctl unload called
            mock_run.assert_any_call(
                ("launchctl", "unload", plist_path),
                capture_output=False,
            )
            # Verify file removed
            assert not os.path.exists(plist_path), "Plist should be removed"


class TestInstallServiceLinux:
    """Test ``install_service`` on Linux — mocked subprocess."""

    @pytest.fixture(autouse=True)
    def mock_platform_linux(self) -> mock.MagicMock:
        with mock.patch("src.state_daemon.service.sys.platform", "linux"):
            yield

    def test_writes_unit_and_calls_systemctl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_dir = os.path.join(tmp, "systemd", "user")
            unit_path = os.path.join(unit_dir, "state-daemon.service")
            socket_path = os.path.join(tmp, ".state", "daemon.sock")

            with (
                mock.patch("src.state_daemon.service._UNIT_DIR", unit_dir),
                mock.patch("src.state_daemon.service._UNIT_PATH", unit_path),
                mock.patch("subprocess.run") as mock_run,
            ):
                install_service(
                    daemon_path="/usr/bin/python3",
                    socket_path=socket_path,
                    project_root=tmp,
                )

            # Verify file written
            assert os.path.isfile(unit_path), f"Unit not written to {unit_path}"
            content = open(unit_path).read()
            assert "[Unit]" in content
            assert "Description=State Daemon" in content
            assert "ExecStart=" in content
            assert "State Daemon" in content

            # Verify systemctl enable called
            mock_run.assert_any_call(
                ("systemctl", "--user", "enable", "state-daemon.service"),
                check=True,
                capture_output=False,
            )
            # Verify systemctl start called
            mock_run.assert_any_call(
                ("systemctl", "--user", "start", "state-daemon.service"),
                check=True,
                capture_output=False,
            )

    def test_uninstall_linux(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_path = os.path.join(tmp, "state-daemon.service")

            # Create a dummy unit so os.remove succeeds
            Path(unit_path).write_text("[Service]")

            with (
                mock.patch("src.state_daemon.service.sys.platform", "linux"),
                mock.patch("src.state_daemon.service._UNIT_PATH", unit_path),
                mock.patch("subprocess.run") as mock_run,
            ):
                uninstall_service()

            # Verify systemctl stop called
            mock_run.assert_any_call(
                ("systemctl", "--user", "stop", "state-daemon.service"),
                capture_output=False,
            )
            # Verify systemctl disable called
            mock_run.assert_any_call(
                ("systemctl", "--user", "disable", "state-daemon.service"),
                capture_output=False,
            )
            # Verify file removed
            assert not os.path.exists(unit_path), "Unit file should be removed"


class TestCurrentPlatformName:
    def test_darwin_returns_macos(self) -> None:
        with mock.patch("src.state_daemon.service.sys.platform", "darwin"):
            assert "macOS" in current_platform_name()
            assert "launchd" in current_platform_name()

    def test_linux_returns_systemd(self) -> None:
        with mock.patch("src.state_daemon.service.sys.platform", "linux"):
            assert "Linux" in current_platform_name()
            assert "systemd" in current_platform_name()


# ---------------------------------------------------------------------------
# Task 055.3 — CLI Integration
# ---------------------------------------------------------------------------


class TestCliInstall:
    """Test ``state daemon install`` CLI command (mocked service layer)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_install_success(self, runner: CliRunner) -> None:
        with mock.patch("src.state_daemon.cli.install_service") as mock_install:
            result = runner.invoke(daemon_app, ["install"])
            assert result.exit_code == 0, f"CLI failed: {result.output}"
            assert "installed" in result.output.lower()
            mock_install.assert_called_once()

    def test_install_file_not_found(self, runner: CliRunner) -> None:
        with mock.patch(
            "src.state_daemon.cli.install_service",
            side_effect=FileNotFoundError("launchctl not found"),
        ):
            result = runner.invoke(daemon_app, ["install"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_install_permission_denied(self, runner: CliRunner) -> None:
        with mock.patch(
            "src.state_daemon.cli.install_service",
            side_effect=PermissionError("access denied"),
        ):
            result = runner.invoke(daemon_app, ["install"])
            assert result.exit_code == 1
            assert "permission" in result.output.lower()

    def test_install_unexpected_error(self, runner: CliRunner) -> None:
        with mock.patch(
            "src.state_daemon.cli.install_service",
            side_effect=RuntimeError("disk full"),
        ):
            result = runner.invoke(daemon_app, ["install"])
            assert result.exit_code == 1


class TestCliUninstall:
    """Test ``state daemon uninstall`` CLI command (mocked service layer)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_uninstall_success(self, runner: CliRunner) -> None:
        with mock.patch("src.state_daemon.cli.uninstall_service") as mock_uninstall:
            result = runner.invoke(daemon_app, ["uninstall"])
            assert result.exit_code == 0, f"CLI failed: {result.output}"
            assert "uninstalled" in result.output.lower()
            mock_uninstall.assert_called_once()

    def test_uninstall_error(self, runner: CliRunner) -> None:
        with mock.patch(
            "src.state_daemon.cli.uninstall_service",
            side_effect=RuntimeError("not installed"),
        ):
            result = runner.invoke(daemon_app, ["uninstall"])
            assert result.exit_code == 1


class TestDaemonAppRegistered:
    """Verify ``state daemon`` appears in the main Typer CLI."""

    def test_daemon_group_visible(self) -> None:
        from src.state_cli.main import app as main_app

        runner = CliRunner()
        result = runner.invoke(main_app, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output

    def test_install_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(daemon_app, ["install", "--help"])
        assert result.exit_code == 0
        assert "launchd" in result.output.lower() or "plist" in result.output.lower() or "service" in result.output.lower()

    def test_uninstall_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(daemon_app, ["uninstall", "--help"])
        assert result.exit_code == 0
        assert "unload" in result.output.lower() or "remove" in result.output.lower()
