"""Tests for state_daemon.sse — SseClientManager, SseClient, SSE formatting.

Covers: client add/remove, broadcast filtering by mode, queue behavior,
ULID offset filtering, heartbeat format, SSE event format.
"""

from __future__ import annotations

import asyncio
import json

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
