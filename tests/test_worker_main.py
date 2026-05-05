"""Tests for state_worker main module — session identity, daemon attach, PID lifecycle."""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from unittest import mock

import pytest

from src.state_worker.session import SessionIdentity, resolve_session_id


# ---------------------------------------------------------------------------
# Task 060.4 — Session resolution tests
# ---------------------------------------------------------------------------


class TestSessionResolution:
    """Session identity resolution with env var, arg, and auto-generate fallbacks."""

    def test_auto_generate_no_env_no_arg(self) -> None:
        original = os.environ.get("STATE_SESSION_ID")
        try:
            os.environ.pop("STATE_SESSION_ID", None)
            session = resolve_session_id()
            assert session.session_id.startswith("STATE-")
            assert session.pid == os.getpid()
            assert str(session.project_root) == str(Path.cwd().resolve())
        finally:
            if original is not None:
                os.environ["STATE_SESSION_ID"] = original

    def test_env_var_takes_priority(self) -> None:
        original = os.environ.get("STATE_SESSION_ID")
        try:
            os.environ["STATE_SESSION_ID"] = "env-session-123"
            session = resolve_session_id()
            assert session.session_id == "env-session-123"
        finally:
            if original is not None:
                os.environ["STATE_SESSION_ID"] = original
            else:
                os.environ.pop("STATE_SESSION_ID", None)

    def test_explicit_arg_overrides_env(self) -> None:
        original = os.environ.get("STATE_SESSION_ID")
        try:
            os.environ["STATE_SESSION_ID"] = "env-session"
            session = resolve_session_id(session_id="cli-session")
            assert session.session_id == "cli-session"
        finally:
            if original is not None:
                os.environ["STATE_SESSION_ID"] = original
            else:
                os.environ.pop("STATE_SESSION_ID", None)

    def test_whitespace_session_id_stripped(self) -> None:
        session = resolve_session_id(session_id="  padded-session  ")
        assert session.session_id == "padded-session"

    def test_empty_session_id_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            resolve_session_id(session_id="")

    def test_empty_env_session_id_falls_back(self) -> None:
        original = os.environ.get("STATE_SESSION_ID")
        try:
            os.environ["STATE_SESSION_ID"] = "   "
            session = resolve_session_id()
            assert session.session_id.startswith("STATE-")
        finally:
            if original is not None:
                os.environ["STATE_SESSION_ID"] = original
            else:
                os.environ.pop("STATE_SESSION_ID", None)

    def test_pid_is_positive(self) -> None:
        session = resolve_session_id()
        assert session.pid > 0

    def test_project_root_is_absolute(self) -> None:
        session = resolve_session_id()
        assert Path(session.project_root).is_absolute()


# ---------------------------------------------------------------------------
# Task 060.4 — Daemon attach tests
# ---------------------------------------------------------------------------


class _FakeStreamReader:
    """Minimal asyncio.StreamReader mock for test control."""

    def __init__(self, *chunks: bytes) -> None:
        self._chunks = list(chunks)
        self._index = 0

    async def readline(self) -> bytes:
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            return chunk
        return b""

    async def readexactly(self, n: int) -> bytes:
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            return chunk[:n]
        return b""


class _FakeStreamWriter:
    """Minimal asyncio.StreamWriter mock."""

    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass


class TestDaemonAttach:
    """Daemon attach/health-check with mock Unix socket."""

    @pytest.fixture
    def session(self) -> SessionIdentity:
        return resolve_session_id("test-session-001")

    @pytest.mark.asyncio
    async def test_health_check_ok(self, session: SessionIdentity) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: application/json\r\n",
            b"Content-Length: 23\r\n",
            b"\r\n",
            b'{"status": "ok"}\n\n     ',
        )
        writer = _FakeStreamWriter()

        with (
            mock.patch.object(
                worker_main, "read_socket_path", return_value="/tmp/fake.sock"
            ),
            mock.patch(
                "asyncio.open_unix_connection",
                return_value=(reader, writer),
            ),
        ):
            result = await worker_main.attach_to_daemon(session, timeout=1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_connection_refused(self, session: SessionIdentity) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        with (
            mock.patch.object(
                worker_main, "read_socket_path", return_value="/tmp/fake.sock"
            ),
            mock.patch(
                "asyncio.open_unix_connection",
                side_effect=ConnectionRefusedError,
            ),
        ):
            result = await worker_main.attach_to_daemon(session, timeout=1.0)
            assert result is False

    @pytest.mark.asyncio
    async def test_daemon_not_running_no_socket_marker(self, session: SessionIdentity) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        with mock.patch.object(
            worker_main, "read_socket_path", return_value=None
        ):
            result = await worker_main.attach_to_daemon(session, timeout=1.0)
            assert result is False

    @pytest.mark.asyncio
    async def test_timeout(self, session: SessionIdentity) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        with (
            mock.patch.object(
                worker_main, "read_socket_path", return_value="/tmp/fake.sock"
            ),
            mock.patch(
                "asyncio.open_unix_connection",
                side_effect=asyncio.TimeoutError,
            ),
        ):
            result = await worker_main.attach_to_daemon(session, timeout=0.01)
            assert result is False

    @pytest.mark.asyncio
    async def test_non_200_response(self, session: SessionIdentity) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        reader = _FakeStreamReader(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
        writer = _FakeStreamWriter()

        with (
            mock.patch.object(
                worker_main, "read_socket_path", return_value="/tmp/fake.sock"
            ),
            mock.patch(
                "asyncio.open_unix_connection",
                return_value=(reader, writer),
            ),
        ):
            result = await worker_main.attach_to_daemon(session, timeout=1.0)
            assert result is False


# ---------------------------------------------------------------------------
# Task 060.4 — PID file tests
# ---------------------------------------------------------------------------


class TestPidFile:
    """PID file write and cleanup lifecycle."""

    def test_write_pid_file_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.state_worker.main import _write_pid_file, _cleanup_pid_file

        monkeypatch.setattr(
            "src.state_worker.main._WORKER_PID_DIR",
            str(tmp_path),
        )

        pid_path = _write_pid_file("test-session", 99999)
        assert os.path.isfile(pid_path)
        content = Path(pid_path).read_text()
        assert content == "99999"

        _cleanup_pid_file(pid_path)
        assert not os.path.isfile(pid_path)

    def test_cleanup_missing_file_no_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.state_worker.main import _cleanup_pid_file

        nonexistent = str(tmp_path / "nonexistent.pid")
        _cleanup_pid_file(nonexistent)


# ---------------------------------------------------------------------------
# Task 060.4 — Main startup tests
# ---------------------------------------------------------------------------


class TestMainStartup:
    """Worker main() startup and shutdown paths."""

    @pytest.mark.asyncio
    async def test_main_startup_and_shutdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import importlib
        worker_main = importlib.import_module("src.state_worker.main")

        # Reset shutdown event between tests
        worker_main._shutdown_event.clear()

        monkeypatch.setattr(
            worker_main, "_WORKER_PID_DIR", str(tmp_path)
        )
        monkeypatch.setattr(
            worker_main, "read_socket_path", lambda: None
        )
        monkeypatch.setattr("sys.argv", ["state_worker"])

        # Schedule shutdown after a short delay
        async def _trigger_shutdown() -> None:
            await asyncio.sleep(0.01)
            worker_main._shutdown_event.set()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(_trigger_shutdown())
            tg.create_task(worker_main.main())
