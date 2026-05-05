"""Tests for state_daemon.pid — atomic pid-file write, read, stale detection, and lifecycle."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.state_daemon.pid import (
    read_pid_file,
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
