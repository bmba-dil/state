"""Tests for state_daemon.sse — SseClientManager, SseClient, SSE formatting.

Covers: client add/remove, broadcast filtering by mode, queue behavior,
ULID offset filtering, heartbeat format, SSE event format, SSE endpoint
integration with DaemonServer.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Task 054.1 — Unit tests: SseClientManager
# ---------------------------------------------------------------------------


class TestSseClientManager:
    """Unit tests for SseClientManager — client lifecycle and broadcast."""

    def test_add_client_creates_client_with_queue(self) -> None:
        """add_client returns an SseClient with a non-None queue."""
        from src.state_daemon.sse import SseClientManager, SseClient

        mgr = SseClientManager()
        client = mgr.add_client()
        assert isinstance(client, SseClient)
        assert isinstance(client.queue, asyncio.Queue)
        assert client.mode_filter is None
        assert client.from_ulid is None

    def test_add_client_with_mode_filter(self) -> None:
        """add_client stores the mode_filter on the client."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        client = mgr.add_client(mode_filter="build")
        assert client.mode_filter == "build"

    def test_add_client_with_from_ulid(self) -> None:
        """add_client stores the from_ulid on the client."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        client = mgr.add_client(from_ulid="01JXYZ")
        assert client.from_ulid == "01JXYZ"

    def test_client_count_tracks_add_remove(self) -> None:
        """client_count reflects add/remove operations."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        assert mgr.client_count == 0

        c1 = mgr.add_client()
        assert mgr.client_count == 1

        c2 = mgr.add_client()
        assert mgr.client_count == 2

        mgr.remove_client(c1)
        assert mgr.client_count == 1

        mgr.remove_client(c2)
        assert mgr.client_count == 0

    def test_remove_client_idempotent(self) -> None:
        """remove_client is safe to call multiple times for the same client."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        client = mgr.add_client()
        mgr.remove_client(client)
        mgr.remove_client(client)  # should not raise
        assert mgr.client_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_all_clients(self) -> None:
        """broadcast puts formatted event on every client's queue."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        c1 = mgr.add_client()
        c2 = mgr.add_client()
        c3 = mgr.add_client()

        mgr.broadcast('{"key":"value"}', "state.test.event", "ulid-001", "kernel")

        # All three clients should receive the event.
        for client in (c1, c2, c3):
            msg = await asyncio.wait_for(client.queue.get(), timeout=1.0)
            assert "id: ulid-001" in msg
            assert "event: state.test.event" in msg
            assert 'data: {"key":"value"}' in msg
            assert msg.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_broadcast_respects_mode_filter(self) -> None:
        """Clients with mode_filter only receive matching events."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        build_client = mgr.add_client(mode_filter="build")
        teach_client = mgr.add_client(mode_filter="teach")
        all_client = mgr.add_client()  # no filter

        # Broadcast a build event — only build_client + all_client get it
        mgr.broadcast('{"k":"b"}', "state.build.evt", "ulid-b01", "build")

        # build_client should get it
        msg = await asyncio.wait_for(build_client.queue.get(), timeout=1.0)
        assert "state.build.evt" in msg

        # all_client should get it
        msg = await asyncio.wait_for(all_client.queue.get(), timeout=1.0)
        assert "state.build.evt" in msg

        # teach_client should NOT get it (queue should be empty)
        assert teach_client.queue.empty()

    @pytest.mark.asyncio
    async def test_broadcast_respects_from_ulid(self) -> None:
        """Clients with from_ulid only receive events with id > offset."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        # ULIDs are lexicographically time-ordered.
        client = mgr.add_client(from_ulid="01J00000000000000000000000")

        # Event with id <= from_ulid should NOT be delivered
        mgr.broadcast('{"k":"1"}', "state.evt", "01HZZZZZZZZZZZZZZZZZZZZZZ", "kernel")
        assert client.queue.empty()

        # Event with id > from_ulid SHOULD be delivered
        mgr.broadcast('{"k":"2"}', "state.evt", "01J00000000000000000000001", "kernel")
        msg = await asyncio.wait_for(client.queue.get(), timeout=1.0)
        assert "state.evt" in msg

    @pytest.mark.asyncio
    async def test_broadcast_to_no_clients_does_not_raise(self) -> None:
        """broadcast with zero clients is a no-op."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        # Should not raise.
        mgr.broadcast('{"k":"v"}', "state.test", "ulid-001", "kernel")

    @pytest.mark.asyncio
    async def test_broadcast_event_format_is_valid_sse(self) -> None:
        """The formatted event string is valid SSE content."""
        from src.state_daemon.sse import SseClientManager

        mgr = SseClientManager()
        client = mgr.add_client()

        data = json.dumps({"hello": "world"}, sort_keys=True)
        mgr.broadcast(data, "state.hello", "ulid-abc", "kernel")

        msg = await asyncio.wait_for(client.queue.get(), timeout=1.0)

        # SSE format: id, event, data on separate lines, terminated by \n\n
        lines = msg.split("\n")
        assert lines[0] == "id: ulid-abc"
        assert lines[1] == "event: state.hello"
        assert lines[2].startswith("data: ")
        assert lines[3] == ""  # trailing blank line


# ---------------------------------------------------------------------------
# Task 054.1 — SSE format helpers
# ---------------------------------------------------------------------------


class TestSseFormat:
    """Tests for SSE formatting helpers."""

    def test_format_heartbeat_is_comment(self) -> None:
        """Heartbeat is an SSE comment (line starting with ':')."""
        from src.state_daemon.sse import format_heartbeat

        hb = format_heartbeat()
        assert hb.startswith(":")
        assert "heartbeat" in hb
        assert hb.endswith("\n\n")

    def test_format_sse_event_structure(self) -> None:
        """Internal _format_sse_event produces correct SSE text."""
        from src.state_daemon.sse import _format_sse_event

        msg = _format_sse_event("ulid-001", "state.test", '{"x":1}')
        assert "id: ulid-001" in msg
        assert "event: state.test" in msg
        assert 'data: {"x":1}' in msg
        assert msg.endswith("\n\n")


# ---------------------------------------------------------------------------
# Task 054.2 — SSE HTTP endpoint integration tests
# ---------------------------------------------------------------------------


def _raw_request(method: str, path: str, headers: dict[str, str] | None = None, body: bytes = b"") -> bytes:
    """Build a raw HTTP/1.1 request."""
    lines = [f"{method} {path} HTTP/1.1"]
    hdrs = headers or {}
    if body:
        hdrs["Content-Length"] = str(len(body))
    for key, value in hdrs.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    lines.append("")
    return "\r\n".join(lines).encode() + body


async def _read_sse_event(reader: asyncio.StreamReader, timeout: float = 5.0) -> dict[str, str]:
    """Read a single SSE event from a stream reader.

    Returns a dict with keys: ``id``, ``event``, ``data``.

    Raises asyncio.TimeoutError if no event arrives within *timeout*.
    """
    fields: dict[str, str] = {}
    while True:
        line_bytes = await asyncio.wait_for(reader.readline(), timeout=timeout)
        line = line_bytes.decode().rstrip("\r\n")
        if line == "":
            # Blank line = end of event
            if fields:
                return fields
            # Leading blank line (heartbeat comment), skip
            continue
        if line.startswith(":"):
            # SSE comment (heartbeat) — skip
            continue
        if ": " in line:
            key, _, value = line.partition(": ")
            fields[key] = value


class TestSseEndpoint:
    """Integration tests: DaemonServer + SseEndpointHandler + SseClientManager."""

    @pytest.fixture
    def socket_path(self) -> str:
        """Temp unix socket path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "sse-test.sock")

    @pytest.mark.asyncio
    async def test_sse_subscribe_receives_broadcast(self, socket_path: str) -> None:
        """Client subscribing to /events/subscribe receives broadcast events."""
        from src.state_daemon.sse import SseClientManager, SseEndpointHandler
        from src.state_daemon.server import DaemonServer

        mgr = SseClientManager()
        sse_handler = SseEndpointHandler(mgr)

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        server = DaemonServer(socket_path, _router, sse_handler=sse_handler)
        await server.start()

        try:
            # Connect an SSE client
            reader, writer = await asyncio.open_unix_connection(socket_path)
            writer.write(_raw_request("GET", "/events/subscribe"))
            await writer.drain()

            # Read SSE headers (status line)
            status_line = await asyncio.wait_for(reader.readline(), timeout=2.0)
            assert b"200 OK" in status_line

            # Read response headers until blank line
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=2.0)
                if line in (b"\r\n", b"\n", b""):
                    break

            # Now broadcast an event — the SSE client should receive it
            mgr.broadcast(
                json.dumps({"hello": "world"}, sort_keys=True),
                "state.test.event",
                "ulid-001",
                "kernel",
            )

            evt = await _read_sse_event(reader, timeout=3.0)
            assert evt["id"] == "ulid-001"
            assert evt["event"] == "state.test.event"
            data = json.loads(evt["data"])
            assert data == {"hello": "world"}

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sse_mode_filter_query_param(self, socket_path: str) -> None:
        """SSE client with ?mode=build only receives build events."""
        from src.state_daemon.sse import SseClientManager, SseEndpointHandler
        from src.state_daemon.server import DaemonServer

        mgr = SseClientManager()
        sse_handler = SseEndpointHandler(mgr)

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        server = DaemonServer(socket_path, _router, sse_handler=sse_handler)
        await server.start()

        try:
            # Connect with mode=build filter
            reader, writer = await asyncio.open_unix_connection(socket_path)
            writer.write(_raw_request("GET", "/events/subscribe?mode=build"))
            await writer.drain()

            # Read past headers
            await asyncio.wait_for(reader.readline(), timeout=2.0)
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=2.0)
                if line in (b"\r\n", b"\n", b""):
                    break

            # Broadcast a teach event — should NOT be received
            mgr.broadcast('{"k":"teach"}', "state.teach.evt", "ulid-t01", "teach")
            # Broadcast a build event — SHOULD be received
            mgr.broadcast('{"k":"build"}', "state.build.evt", "ulid-b01", "build")

            evt = await _read_sse_event(reader, timeout=3.0)
            assert evt["event"] == "state.build.evt"

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sse_invalid_mode_returns_400(self, socket_path: str) -> None:
        """Invalid ?mode= value returns HTTP 400."""
        from src.state_daemon.sse import SseClientManager, SseEndpointHandler
        from src.state_daemon.server import DaemonServer

        mgr = SseClientManager()
        sse_handler = SseEndpointHandler(mgr)

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        server = DaemonServer(socket_path, _router, sse_handler=sse_handler)
        await server.start()

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            writer.write(_raw_request("GET", "/events/subscribe?mode=invalid"))
            await writer.drain()

            status_line = await asyncio.wait_for(reader.readline(), timeout=2.0)
            assert b"400" in status_line
            assert b"Bad Request" in status_line

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sse_no_handler_returns_501(self, socket_path: str) -> None:
        """Server without sse_handler returns 501 for /events/subscribe."""
        from src.state_daemon.server import DaemonServer

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        # No sse_handler passed
        server = DaemonServer(socket_path, _router)
        await server.start()

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            writer.write(_raw_request("GET", "/events/subscribe"))
            await writer.drain()

            status_line = await asyncio.wait_for(reader.readline(), timeout=2.0)
            assert b"501" in status_line

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sse_multiple_clients_receive_same_event(self, socket_path: str) -> None:
        """Two SSE clients both receive the same broadcast event."""
        from src.state_daemon.sse import SseClientManager, SseEndpointHandler
        from src.state_daemon.server import DaemonServer

        mgr = SseClientManager()
        sse_handler = SseEndpointHandler(mgr)

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        server = DaemonServer(socket_path, _router, sse_handler=sse_handler)
        await server.start()

        try:
            # Connect two clients
            r1, w1 = await asyncio.open_unix_connection(socket_path)
            w1.write(_raw_request("GET", "/events/subscribe"))
            await w1.drain()

            r2, w2 = await asyncio.open_unix_connection(socket_path)
            w2.write(_raw_request("GET", "/events/subscribe"))
            await w2.drain()

            # Read past headers for both
            for r in (r1, r2):
                await asyncio.wait_for(r.readline(), timeout=2.0)
                while True:
                    line = await asyncio.wait_for(r.readline(), timeout=2.0)
                    if line in (b"\r\n", b"\n", b""):
                        break

            # Broadcast one event
            mgr.broadcast(
                json.dumps({"x": 42}, sort_keys=True),
                "state.shared",
                "ulid-shared",
                "kernel",
            )

            # Both clients receive it
            for r in (r1, r2):
                evt = await _read_sse_event(r, timeout=3.0)
                assert evt["id"] == "ulid-shared"
                assert evt["event"] == "state.shared"

            w1.close()
            await w1.wait_closed()
            w2.close()
            await w2.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_sse_client_cleanup_on_disconnect(self, socket_path: str) -> None:
        """Disconnecting client is removed from manager; other clients unaffected."""
        from src.state_daemon.sse import SseClientManager, SseEndpointHandler
        from src.state_daemon.server import DaemonServer

        mgr = SseClientManager()
        sse_handler = SseEndpointHandler(mgr)

        async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
            return b"{}"

        server = DaemonServer(socket_path, _router, sse_handler=sse_handler)
        await server.start()

        try:
            # Connect two clients
            r1, w1 = await asyncio.open_unix_connection(socket_path)
            w1.write(_raw_request("GET", "/events/subscribe"))
            await w1.drain()

            r2, w2 = await asyncio.open_unix_connection(socket_path)
            w2.write(_raw_request("GET", "/events/subscribe"))
            await w2.drain()

            # Read past headers for both
            for r in (r1, r2):
                await asyncio.wait_for(r.readline(), timeout=2.0)
                while True:
                    line = await asyncio.wait_for(r.readline(), timeout=2.0)
                    if line in (b"\r\n", b"\n", b""):
                        break

            assert mgr.client_count == 2

            # Disconnect client 1
            w1.close()
            await w1.wait_closed()

            # Broadcast an event — client 2 should receive it, and client 1's
            # handler task should detect the broken connection when trying
            # to write/drain.
            mgr.broadcast(
                json.dumps({"after": "disconnect"}, sort_keys=True),
                "state.after",
                "ulid-after",
                "kernel",
            )

            # Client 2 should receive the event.
            evt = await _read_sse_event(r2, timeout=3.0)
            assert evt["event"] == "state.after"

            # Allow client 1's handler to detect disconnect and clean up.
            await asyncio.sleep(0.5)

            # Client 1 should be removed from the manager.
            assert mgr.client_count == 1

            w2.close()
            await w2.wait_closed()
        finally:
            await server.stop()
