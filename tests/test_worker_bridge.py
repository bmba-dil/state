"""Tests for state_worker bridge — SSE parsing, connection lifecycle, error handling."""

from __future__ import annotations

import asyncio
import json
from unittest import mock

import pytest

from src.state_worker.session import SessionIdentity, resolve_session_id


# ---------------------------------------------------------------------------
# Fake stream helpers
# ---------------------------------------------------------------------------


class _FakeStreamReader:
    """Controllable asyncio.StreamReader mock for SSE line delivery."""

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
    """Controllable asyncio.StreamWriter mock."""

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


# ---------------------------------------------------------------------------
# Task 061.3 — SSE parsing tests
# ---------------------------------------------------------------------------


class TestSseParsing:
    """SSE event stream line parsing and dispatch."""

    @pytest.fixture
    def session(self) -> SessionIdentity:
        return resolve_session_id("test-bridge-001")

    @pytest.mark.asyncio
    async def test_single_line_data_event(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        received: list[dict[str, object]] = []

        async def callback(payload: dict[str, object]) -> None:
            received.append(payload)

        sse_bridge = bridge.SseBridge(session)
        sse_bridge.on_event = callback

        # Simulate SSE stream: HTTP headers + one event
        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: text/event-stream\r\n",
            b"\r\n",
            b"id: 01ARZ3NDEKTSV4RRFFQ69G5FAV\r\n",
            b'data: {"event_type":"step.created","mode":"build"}\r\n',
            b"\r\n",
            # EOF triggers disconnect
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            # Connect in background — it will exit on EOF
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert len(received) == 1
        assert received[0]["event_type"] == "step.created"
        assert received[0]["mode"] == "build"

    @pytest.mark.asyncio
    async def test_multi_line_data_event(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        received: list[dict[str, object]] = []

        async def callback(payload: dict[str, object]) -> None:
            received.append(payload)

        sse_bridge = bridge.SseBridge(session)
        sse_bridge.on_event = callback

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
            b'data: ["line1",\n',
            b'data: "line2"]\n',
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert len(received) == 1
        assert received[0] == ["line1", "line2"]

    @pytest.mark.asyncio
    async def test_event_type_field(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        received: list[dict[str, object]] = []

        async def callback(payload: dict[str, object]) -> None:
            received.append(payload)

        sse_bridge = bridge.SseBridge(session)
        sse_bridge.on_event = callback

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
            b"event: custom_event\n",
            b'data: {"msg":"hello"}\n',
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert len(received) == 1
        assert received[0]["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_heartbeat_skip(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        received: list[dict[str, object]] = []

        async def callback(payload: dict[str, object]) -> None:
            received.append(payload)

        sse_bridge = bridge.SseBridge(session)
        sse_bridge.on_event = callback

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
            b": heartbeat\n",  # comment only — no data, should be skipped
            b"\r\n",
            b'data: {"real":true}\n',
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert len(received) == 1
        assert received[0]["real"] is True

    @pytest.mark.asyncio
    async def test_comment_line_ignored(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        received: list[dict[str, object]] = []

        async def callback(payload: dict[str, object]) -> None:
            received.append(payload)

        sse_bridge = bridge.SseBridge(session)
        sse_bridge.on_event = callback

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
            b": this is a comment\n",
            b'data: {"msg":"still here"}\n',
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert len(received) == 1


# ---------------------------------------------------------------------------
# Task 061.3 — Connection lifecycle tests
# ---------------------------------------------------------------------------


class TestSseBridgeConnect:
    """SSE bridge connection lifecycle."""

    @pytest.fixture
    def session(self) -> SessionIdentity:
        return resolve_session_id("test-bridge-002")

    @pytest.mark.asyncio
    async def test_connect_sends_subscribe_request(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        sse_bridge = bridge.SseBridge(session, mode_filter="build")

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        request = b"".join(writer.written).decode()
        assert "GET /events/subscribe?mode=build" in request

    @pytest.mark.asyncio
    async def test_connect_no_mode_filter(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        sse_bridge = bridge.SseBridge(session)

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            task = asyncio.create_task(sse_bridge.connect("/tmp/fake.sock"))
            await asyncio.sleep(0.05)
            await sse_bridge.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        request = b"".join(writer.written).decode()
        assert "GET /events/subscribe" in request
        assert "mode=" not in request

    @pytest.mark.asyncio
    async def test_connection_refused(self, session: SessionIdentity) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        sse_bridge = bridge.SseBridge(session)

        with mock.patch(
            "asyncio.open_unix_connection",
            side_effect=ConnectionRefusedError,
        ):
            await sse_bridge.connect("/tmp/nonexistent.sock")

        # Should not crash — logs warning and exits.
        assert sse_bridge._reader is None


# ---------------------------------------------------------------------------
# Task 063.2 — Hook forwarding tests
# ---------------------------------------------------------------------------


class TestForwardHook:
    """HTTP POST hook forwarding with retry logic."""

    async def test_forward_hook_success_200(self) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        reader = _FakeStreamReader(
            b"HTTP/1.1 200 OK\r\n",
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            result = await bridge.forward_hook(
                hook_name="step.created",
                payload={"key": "value"},
                socket_path="/tmp/fake.sock",
            )

        assert result is True
        request = b"".join(writer.written).decode()
        assert "POST /hook/step.created" in request
        assert '"key": "value"' in request

    async def test_forward_hook_retry_on_connection_refused(self) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        call_count = 0

        async def mock_connect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionRefusedError

        with (
            mock.patch("asyncio.open_unix_connection", side_effect=mock_connect),
            mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
        ):
            result = await bridge.forward_hook(
                hook_name="test.hook",
                payload={},
                socket_path="/tmp/fake.sock",
            )

        assert result is False
        assert call_count == 3  # max_retries=3 → total 3 attempts

    async def test_forward_hook_retry_on_503(self) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        call_count = 0

        def make_readerwriter(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                reader = _FakeStreamReader(
                    b"HTTP/1.1 503 Service Unavailable\r\n",
                    b"\r\n",
                )
            else:
                reader = _FakeStreamReader(
                    b"HTTP/1.1 200 OK\r\n",
                    b"\r\n",
                )
            writer = _FakeStreamWriter()
            return reader, writer

        with (
            mock.patch("asyncio.open_unix_connection", side_effect=make_readerwriter),
            mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
        ):
            result = await bridge.forward_hook(
                hook_name="test.hook",
                payload={},
                socket_path="/tmp/fake.sock",
            )

        assert result is True
        assert call_count == 3

    async def test_forward_hook_no_retry_on_400(self) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        reader = _FakeStreamReader(
            b"HTTP/1.1 400 Bad Request\r\n",
            b"\r\n",
        )
        writer = _FakeStreamWriter()

        with mock.patch("asyncio.open_unix_connection", return_value=(reader, writer)):
            result = await bridge.forward_hook(
                hook_name="test.hook",
                payload={},
                socket_path="/tmp/fake.sock",
            )

        assert result is False

    async def test_forward_hook_exhaust_retries(self) -> None:
        import importlib
        bridge = importlib.import_module("src.state_worker.bridge")

        call_count = 0

        def make_readerwriter(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            reader = _FakeStreamReader(
                b"HTTP/1.1 502 Bad Gateway\r\n",
                b"\r\n",
            )
            writer = _FakeStreamWriter()
            return reader, writer

        with (
            mock.patch("asyncio.open_unix_connection", side_effect=make_readerwriter),
            mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
        ):
            result = await bridge.forward_hook(
                hook_name="test.hook",
                payload={},
                socket_path="/tmp/fake.sock",
            )

        assert result is False
        assert call_count == 3  # max_retries=3 → total 3 attempts
