"""Tests for state_daemon.socket — deterministic path resolution & atomic storage."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest

from src.state_daemon.socket import (
    read_socket_path,
    resolve_socket_path,
    write_socket_path,
)


# ---------------------------------------------------------------------------
# Task 052.1 — resolve_socket_path
# ---------------------------------------------------------------------------


class TestResolveSocketPath:
    """Deterministic socket path resolution."""

    def test_deterministic_same_root_same_path(self) -> None:
        """Same project root yields the same socket path on every call."""
        path_a = resolve_socket_path("/var/tmp/my-project")
        path_b = resolve_socket_path("/var/tmp/my-project")
        assert path_a == path_b

    def test_different_roots_different_paths(self) -> None:
        """Distinct project roots produce distinct socket names."""
        path_a = resolve_socket_path("/projects/alpha")
        path_b = resolve_socket_path("/projects/beta")
        assert path_a != path_b

    def test_socket_name_contains_hash_prefix(self) -> None:
        """Socket name is state-<hash16>.sock."""
        project_root = "/example/project"
        result = resolve_socket_path(project_root)
        abs_root = os.path.abspath(project_root)
        expected_hash = hashlib.sha256(abs_root.encode()).hexdigest()[:16]
        assert f"state-{expected_hash}.sock" in result

    def test_normalises_relative_to_absolute(self, tmp_path: Path) -> None:
        """Relative project_root is resolved to absolute before hashing."""
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            rel = resolve_socket_path("subdir/project")
            abs_path = resolve_socket_path(str(tmp_path / "subdir/project"))
            assert rel == abs_path
        finally:
            os.chdir(cwd)

    def test_uses_xdg_runtime_dir_when_set(self, tmp_path: Path) -> None:
        """$XDG_RUNTIME_DIR is preferred when set."""
        xdg_dir = str(tmp_path / "xdg")
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": xdg_dir}, clear=True):
            result = resolve_socket_path("/project")
            assert result.startswith(xdg_dir)
            assert os.path.isdir(xdg_dir)  # directory was created

    def test_falls_back_to_tmpdir_on_macos(self, tmp_path: Path) -> None:
        """When $XDG_RUNTIME_DIR is absent, $TMPDIR is used."""
        tmp_dir = str(tmp_path / "tmpdir")
        with mock.patch.dict(
            os.environ, {"TMPDIR": tmp_dir}, clear=True
        ):
            result = resolve_socket_path("/project")
            assert result.startswith(tmp_dir)
            assert os.path.isdir(tmp_dir)

    def test_falls_back_to_slash_tmp(self) -> None:
        """When neither $XDG_RUNTIME_DIR nor $TMPDIR is set, /tmp is used."""
        with mock.patch.dict(os.environ, {}, clear=True):
            result = resolve_socket_path("/project")
            assert result.startswith("/tmp/")

    def test_parent_directory_created(self, tmp_path: Path) -> None:
        """The parent directory is created if it doesn't exist."""
        xdg_dir = str(tmp_path / "new_xdg_dir")
        assert not os.path.isdir(xdg_dir)
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": xdg_dir}, clear=True):
            resolve_socket_path("/project")
            assert os.path.isdir(xdg_dir)

    def test_absolute_path_returned(self) -> None:
        """Result is always an absolute path."""
        result = resolve_socket_path("/project")
        assert os.path.isabs(result)

    def test_hash_is_hex_string(self) -> None:
        """The hash portion is lowercase hex."""
        result = resolve_socket_path("/project")
        # socket name format: state-<16hex>.sock
        basename = os.path.basename(result)
        assert basename.startswith("state-")
        assert basename.endswith(".sock")
        hash_part = basename[6:-5]  # strip "state-" prefix and ".sock" suffix
        assert len(hash_part) == 16
        assert all(c in "0123456789abcdef" for c in hash_part)


# ---------------------------------------------------------------------------
# Task 052.2 — write_socket_path / read_socket_path
# ---------------------------------------------------------------------------


class TestWriteReadSocketPath:
    """Atomic socket path storage and retrieval."""

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "daemon.sock")
    def test_write_then_read_round_trip(self) -> None:
        """write_socket_path writes the path; read_socket_path returns it."""
        self._clean("daemon.sock")
        try:
            write_socket_path("/tmp/state-abc123.sock")
            result = read_socket_path()
            assert result == "/tmp/state-abc123.sock"
        finally:
            self._clean("daemon.sock")

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "daemon.sock")
    def test_write_is_atomic_no_partial_read(self) -> None:
        """Target file never exists in a partially-written state."""
        self._clean("daemon.sock")
        assert not os.path.isfile("daemon.sock")
        try:
            write_socket_path("/tmp/state-xyz789.sock")
            assert os.path.isfile("daemon.sock")
            result = read_socket_path()
            assert result == "/tmp/state-xyz789.sock"
        finally:
            self._clean("daemon.sock")

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "nonexistent_dir/marker")
    def test_write_creates_parent_directory(self) -> None:
        """Parent directory is created if it doesn't exist."""
        self._clean("nonexistent_dir/marker")
        try:
            assert not os.path.isdir("nonexistent_dir")
            write_socket_path("/tmp/state-test.sock")
            assert os.path.isdir("nonexistent_dir")
        finally:
            self._clean("nonexistent_dir/marker")
            try:
                os.rmdir("nonexistent_dir")
            except OSError:
                pass

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "nonexistent.sock")
    def test_read_returns_none_when_missing(self) -> None:
        """Missing marker file returns None."""
        self._clean("nonexistent.sock")
        assert read_socket_path() is None

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "empty_marker.sock")
    def test_read_returns_none_when_empty(self) -> None:
        """Empty marker file returns None."""
        self._clean("empty_marker.sock")
        try:
            with open("empty_marker.sock", "w", encoding="utf-8") as f:
                f.write("")
            assert read_socket_path() is None
        finally:
            self._clean("empty_marker.sock")

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "whitespace_marker.sock")
    def test_read_returns_none_when_whitespace_only(self) -> None:
        """Whitespace-only marker file returns None."""
        self._clean("whitespace_marker.sock")
        try:
            with open("whitespace_marker.sock", "w", encoding="utf-8") as f:
                f.write("   \n  ")
            assert read_socket_path() is None
        finally:
            self._clean("whitespace_marker.sock")

    @mock.patch("src.state_daemon.socket._SOCKET_MARKER_PATH", "daemon.sock")
    def test_write_overwrites_previous_value(self) -> None:
        """Subsequent writes overwrite the previous value."""
        self._clean("daemon.sock")
        try:
            write_socket_path("/tmp/first.sock")
            write_socket_path("/tmp/second.sock")
            result = read_socket_path()
            assert result == "/tmp/second.sock"
        finally:
            self._clean("daemon.sock")

    @staticmethod
    def _clean(path: str) -> None:
        """Remove a file if it exists."""
        try:
            os.unlink(path)
        except (FileNotFoundError, IsADirectoryError):
            pass
