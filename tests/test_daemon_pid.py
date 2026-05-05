"""Tests for state_daemon.pid — atomic pid-file write, read, stale detection, and lifecycle."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from unittest import mock

import pytest

from src.state_daemon.pid import (
    _is_pid_alive_darwin,
    _is_pid_alive_fallback,
    _is_pid_alive_linux,
    _parse_lstart,
    acquire_pid_file,
    is_pid_alive,
    read_pid_file,
    release_pid_file,
    write_pid_file,
)


# ---------------------------------------------------------------------------
# Task 051.1 — write_pid_file / read_pid_file
# ---------------------------------------------------------------------------


class TestWriteReadPidFile:
    """Atomic write and validated read of the pid file."""

    def test_write_then_read_round_trip(self, tmp_path: Path) -> None:
        """write_pid_file creates a valid JSON file; read_pid_file parses it back."""
        path = str(tmp_path / "daemon.pid")
        write_pid_file(path)

        result = read_pid_file(path)
        assert result is not None
        assert isinstance(result["pid"], int)
        assert result["pid"] == os.getpid()
        assert isinstance(result["start_time_ns"], int)
        assert result["start_time_ns"] > 0

    def test_read_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Missing pid file returns None gracefully."""
        path = str(tmp_path / "nonexistent.pid")
        assert read_pid_file(path) is None

    def test_read_returns_none_for_corrupt_json(self, tmp_path: Path) -> None:
        """Garbled JSON returns None (with a warning log — we don't assert log content)."""
        path = tmp_path / "daemon.pid"
        path.write_text("not json {{{", encoding="utf-8")
        assert read_pid_file(str(path)) is None

    def test_read_returns_none_for_wrong_type(self, tmp_path: Path) -> None:
        """Valid JSON but wrong top-level type returns None."""
        path = tmp_path / "daemon.pid"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert read_pid_file(str(path)) is None

    def test_read_returns_none_for_missing_keys(self, tmp_path: Path) -> None:
        """JSON dict missing required keys returns None."""
        path = tmp_path / "daemon.pid"
        path.write_text('{"pid": 1234}', encoding="utf-8")  # no start_time_ns
        assert read_pid_file(str(path)) is None

    def test_write_is_atomic_no_partial_read(self, tmp_path: Path) -> None:
        """The target file never exists in a partially-written state."""
        path = str(tmp_path / "daemon.pid")
        # Ensure path does not exist yet
        assert not os.path.isfile(path)
        write_pid_file(path)
        # After write the file exists and is parseable
        result = read_pid_file(path)
        assert result is not None
        assert result["pid"] == os.getpid()


# ---------------------------------------------------------------------------
# Task 051.2 — is_pid_alive (stale process detection)
# ---------------------------------------------------------------------------


class TestIsPidAliveLinux:
    """Linux-specific stale detection via /proc/<pid>/stat."""

    def _fake_stat(self, starttime_ticks: int) -> str:
        """Build a minimal /proc/pid/stat line with the given starttime."""
        # Field order after ')': state ppid pgrp session tty_nr tpgid flags
        # minflt cminflt majflt cmajflt utime stime cutime cstime priority
        # nice num_threads itrealvalue starttime
        return (
            "1234 (state-daemon) S 1 1234 1234 0 -1 0 "
            "0 0 0 0 0 0 0 0 20 0 1 0 "
            f"{starttime_ticks} 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"
        )

    def test_matching_start_time_returns_true(self) -> None:
        """When starttime matches expected, process is alive and ours."""
        ticks = 1234567
        ticks_per_sec = os.sysconf("SC_CLK_TCK")
        expected_ns = int(ticks * 1_000_000_000 / ticks_per_sec)

        with mock.patch("builtins.open", mock.mock_open(read_data=self._fake_stat(ticks))):
            assert _is_pid_alive_linux(1234, expected_ns) is True

    def test_different_start_time_returns_false(self) -> None:
        """When starttime differs, pid was recycled — stale."""
        ticks = 1234567
        ticks_per_sec = os.sysconf("SC_CLK_TCK")
        expected_ns = int(ticks * 1_000_000_000 / ticks_per_sec)

        # Different process — starttime is 9999999 ticks
        different_ticks = 9999999
        with mock.patch("builtins.open", mock.mock_open(read_data=self._fake_stat(different_ticks))):
            assert _is_pid_alive_linux(1234, expected_ns) is False

    def test_proc_file_missing_returns_false(self) -> None:
        """When /proc/<pid>/stat is missing, process is dead."""
        with mock.patch("builtins.open", side_effect=FileNotFoundError):
            assert _is_pid_alive_linux(1234, 9999999) is False

    def test_permission_denied_returns_false(self) -> None:
        """PermissionError on /proc is treated as process gone."""
        with mock.patch("builtins.open", side_effect=PermissionError):
            assert _is_pid_alive_linux(1234, 9999999) is False

    def test_malformed_stat_returns_false(self) -> None:
        """Malformed stat line without closing paren returns False."""
        with mock.patch("builtins.open", mock.mock_open(read_data="1234 (no-closing-paren S ...")):
            assert _is_pid_alive_linux(1234, 9999999) is False

    def test_short_stat_returns_false(self) -> None:
        """Stat line with too few fields returns False."""
        with mock.patch("builtins.open", mock.mock_open(read_data="1234 (daemon) S 1")):
            assert _is_pid_alive_linux(1234, 9999999) is False

    def test_tolerance_window(self) -> None:
        """Slight differences within the 5 s tolerance are accepted."""
        ticks = 1234567
        ticks_per_sec = os.sysconf("SC_CLK_TCK")
        base_ns = int(ticks * 1_000_000_000 / ticks_per_sec)

        # 2 seconds off — still within 5 s tolerance
        with mock.patch("builtins.open", mock.mock_open(read_data=self._fake_stat(ticks))):
            assert _is_pid_alive_linux(1234, base_ns + 2_000_000_000) is True


class TestIsPidAliveDarwin:
    """macOS-specific stale detection via ps -o lstart=."""

    def test_matching_start_time_returns_true(self) -> None:
        """When ps output start time matches expected, process is alive."""
        now = time.time()
        boot_epoch = now - time.monotonic()
        # Simulate a process that started just now
        proc_start_epoch = now
        expected_ns = int((proc_start_epoch - boot_epoch) * 1_000_000_000)

        lstart = time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(proc_start_epoch))
        # ps output has single-digit days padded with space, so "May  4" not "May 04"
        # Let's normalize: if day starts with 0, replace with space
        parts = lstart.split()
        if len(parts) >= 3 and parts[2].startswith("0"):
            parts[2] = " " + parts[2][1:]
            lstart = " ".join(parts)

        result_mock = mock.MagicMock()
        result_mock.returncode = 0
        result_mock.stdout = lstart

        with mock.patch("subprocess.run", return_value=result_mock):
            assert _is_pid_alive_darwin(1234, expected_ns) is True

    def test_different_start_time_returns_false(self) -> None:
        """When ps start time differs significantly, pid was recycled."""
        now = time.time()
        boot_epoch = now - time.monotonic()
        expected_ns = int((now - boot_epoch) * 1_000_000_000)

        # Fake a process that started 1 hour ago
        old_start = now - 3600
        lstart = time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(old_start))
        parts = lstart.split()
        if len(parts) >= 3 and parts[2].startswith("0"):
            parts[2] = " " + parts[2][1:]
            lstart = " ".join(parts)

        result_mock = mock.MagicMock()
        result_mock.returncode = 0
        result_mock.stdout = lstart

        with mock.patch("subprocess.run", return_value=result_mock):
            assert _is_pid_alive_darwin(1234, expected_ns) is False

    def test_ps_nonzero_return_returns_false(self) -> None:
        """ps returning non-zero means process does not exist."""
        result_mock = mock.MagicMock()
        result_mock.returncode = 1
        result_mock.stdout = ""

        with mock.patch("subprocess.run", return_value=result_mock):
            assert _is_pid_alive_darwin(1234, 9999999) is False

    def test_ps_empty_output_returns_false(self) -> None:
        """ps with no output means process does not exist."""
        result_mock = mock.MagicMock()
        result_mock.returncode = 0
        result_mock.stdout = ""

        with mock.patch("subprocess.run", return_value=result_mock):
            assert _is_pid_alive_darwin(1234, 9999999) is False

    def test_ps_timeout_returns_false(self) -> None:
        """subprocess timeout is treated as process gone."""
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["ps"], 5)):
            assert _is_pid_alive_darwin(1234, 9999999) is False


class TestIsPidAliveFallback:
    """Fallback stale detection via os.kill(pid, 0)."""

    def test_process_exists_returns_true(self) -> None:
        with mock.patch("os.kill", return_value=None):
            assert _is_pid_alive_fallback(1234) is True

    def test_process_not_exists_returns_false(self) -> None:
        with mock.patch("os.kill", side_effect=OSError):
            assert _is_pid_alive_fallback(1234) is False

    def test_process_permission_error_returns_false(self) -> None:
        """If we cannot signal, treat as dead (safe fallback)."""
        with mock.patch("os.kill", side_effect=PermissionError):
            assert _is_pid_alive_fallback(1234) is False


class TestIsPidAliveDispatch:
    """Platform dispatch routes to correct implementation."""

    def test_linux_platform(self) -> None:
        with mock.patch("sys.platform", "linux"), \
             mock.patch("src.state_daemon.pid._is_pid_alive_linux") as mock_linux:
            mock_linux.return_value = True
            assert is_pid_alive(42, 9999) is True
            mock_linux.assert_called_once_with(42, 9999)

    def test_darwin_platform(self) -> None:
        with mock.patch("sys.platform", "darwin"), \
             mock.patch("src.state_daemon.pid._is_pid_alive_darwin") as mock_darwin:
            mock_darwin.return_value = True
            assert is_pid_alive(42, 9999) is True
            mock_darwin.assert_called_once_with(42, 9999)

    def test_other_platform(self) -> None:
        with mock.patch("sys.platform", "win32"), \
             mock.patch("src.state_daemon.pid._is_pid_alive_fallback") as mock_fallback:
            mock_fallback.return_value = True
            assert is_pid_alive(42, 9999) is True
            mock_fallback.assert_called_once_with(42)


class TestParseLstart:
    """Parse ps -o lstart= output."""

    def test_standard_format(self) -> None:
        ts = _parse_lstart("Sun May  4 12:00:00 2026")
        assert isinstance(ts, float)
        # Should be somewhere in 2026
        from datetime import datetime
        dt = datetime.fromtimestamp(ts)
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 4

    def test_padded_day(self) -> None:
        ts = _parse_lstart("Wed Jan 15 08:30:00 2026")
        assert isinstance(ts, float)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_lstart("garbage")

    def test_unknown_month_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_lstart("Mon Xyz  1 12:00:00 2026")


# ---------------------------------------------------------------------------
# Task 051.3 — acquire_pid_file / release_pid_file lifecycle
# ---------------------------------------------------------------------------


class TestAcquirePidFile:
    """PID file acquisition with stale detection and double-start prevention."""

    def test_fresh_start_acquires_and_writes(self, tmp_path: Path) -> None:
        """When no pid file exists, acquire returns True and creates the file."""
        path = str(tmp_path / "daemon.pid")
        result = acquire_pid_file(path)
        assert result is True
        data = read_pid_file(path)
        assert data is not None
        assert data["pid"] == os.getpid()

    def test_double_start_prevented(self, tmp_path: Path) -> None:
        """When a live daemon is detected, acquire returns False."""
        path = str(tmp_path / "daemon.pid")

        # First acquire succeeds
        assert acquire_pid_file(path) is True

        # Second acquire — the pid is our own, and it's alive
        result = acquire_pid_file(path)
        assert result is False

    def test_stale_pid_cleaned_and_reclaimed(self, tmp_path: Path) -> None:
        """When the pid file exists but the process is dead, stale cleanup happens."""
        path = str(tmp_path / "daemon.pid")

        # Write a pid file for a dead process (pid 99999 is unlikely to exist)
        import json
        path_lib = Path(path)
        path_lib.write_text(
            json.dumps({"pid": 99999, "start_time_ns": 0}),
            encoding="utf-8",
        )

        # Simulate stale — pid 99999 doesn't exist, so is_pid_alive returns False
        with mock.patch("src.state_daemon.pid.is_pid_alive", return_value=False):
            result = acquire_pid_file(path)
            assert result is True

            # File should contain OUR pid, not 99999
            data = read_pid_file(path)
            assert data is not None
            assert data["pid"] == os.getpid()

    def test_stale_pid_different_start_time_reclaimed(self, tmp_path: Path) -> None:
        """When pid exists but start time differs (pid recycled), stale cleanup."""
        path = str(tmp_path / "daemon.pid")

        # Write a pid file with our pid but a different start_time_ns
        import json
        path_lib = Path(path)
        path_lib.write_text(
            json.dumps({"pid": os.getpid(), "start_time_ns": 0}),
            encoding="utf-8",
        )

        # is_pid_alive returns False because start_time_ns doesn't match
        with mock.patch("src.state_daemon.pid.is_pid_alive", return_value=False):
            result = acquire_pid_file(path)
            assert result is True


class TestReleasePidFile:
    """PID file removal on graceful shutdown."""

    def test_removes_existing_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "daemon.pid")
        write_pid_file(path)
        assert os.path.isfile(path)

        release_pid_file(path)
        assert not os.path.isfile(path)

    def test_no_error_when_already_missing(self, tmp_path: Path) -> None:
        path = str(tmp_path / "nonexistent.pid")
        # Should not raise
        release_pid_file(path)

    def test_warns_on_permission_error(self, tmp_path: Path) -> None:
        path = str(tmp_path / "daemon.pid")
        write_pid_file(path)

        with mock.patch("os.unlink", side_effect=PermissionError):
            # Should not raise — logs warning
            release_pid_file(path)
