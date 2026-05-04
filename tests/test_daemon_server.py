"""Tests for state_daemon.server — DaemonServer HTTP over unix socket.

Covers: server start/stop, GET /health, POST routing, connection
error handling, Content-Type validation, graceful shutdown.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _read_response(reader: asyncio.StreamReader) -> tuple[int, dict[str, str], bytes]:
    """Read a full HTTP response from a stream reader.

    Returns (status_code, headers_dict, body_bytes).
    """
    # Status line
    status_line = await reader.readline()
    _, status_str, _ = status_line.decode().strip().split(" ", 2)
    status = int(status_str)

    # Headers
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        decoded = line.decode().strip()
        if ": " in decoded:
            key, _, value = decoded.partition(": ")
            headers[key.lower()] = value

    # Body
    content_length = int(headers.get("content-length", "0"))
    body = b""
    if content_length > 0:
        body = await reader.readexactly(content_length)

    return status, headers, body


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def socket_path() -> str:
    """Return a temp unix socket path (doesn't create the socket)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "state-daemon.sock")


@pytest.fixture
async def echo_router():
    """A trivial router that echoes the body back as JSON."""
    import json

    async def router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
        return json.dumps({"echo": body.decode()}).encode()

    return router


@pytest.fixture
async def server(socket_path: str, echo_router):
    """Start a DaemonServer, yield it, then stop it."""
    from src.state_daemon.server import DaemonServer

    srv = DaemonServer(socket_path, echo_router)
    await srv.start()
    yield srv
    await srv.stop()


# ---------------------------------------------------------------------------
# Tests: server lifecycle
# ---------------------------------------------------------------------------


async def test_server_accepts_connection(server, socket_path: str) -> None:
    """Server starts and accepts a connection on the unix socket."""
    reader, writer = await asyncio.open_unix_connection(socket_path)
    writer.write(_raw_request("GET", "/health"))
    await writer.drain()
    status, _, body = await _read_response(reader)
    assert status == 200
    data = __import__("json").loads(body)
    assert data == {"status": "ok"}
    writer.close()
    await writer.wait_closed()


async def test_server_health_check(server, socket_path: str) -> None:
    """GET /health returns 200 with {"status": "ok"}."""
    reader, writer = await asyncio.open_unix_connection(socket_path)
    writer.write(_raw_request("GET", "/health"))
    await writer.drain()
    status, headers, body = await _read_response(reader)
    assert status == 200
    assert headers["content-type"] == "application/json"
    data = __import__("json").loads(body)
    assert data == {"status": "ok"}
    writer.close()
    await writer.wait_closed()


# ---------------------------------------------------------------------------
# Tests: POST routing
# ---------------------------------------------------------------------------


async def test_post_routes_to_router(server, socket_path: str) -> None:
    """POST body is passed through the router and response returned."""
    body = b'{"hello": "world"}'
    reader, writer = await asyncio.open_unix_connection(socket_path)
    writer.write(
        _raw_request(
            "POST",
            "/",
            {"Content-Type": "application/json"},
            body,
        )
    )
    await writer.drain()
    status, _, resp_body = await _read_response(reader)
    assert status == 200
    data = __import__("json").loads(resp_body)
    assert data == {"echo": '{"hello": "world"}'}
    writer.close()
    await writer.wait_closed()


async def test_non_json_post_rejected_415(server, socket_path: str) -> None:
    """POST without Content-Type: application/json gets 415."""
    reader, writer = await asyncio.open_unix_connection(socket_path)
    writer.write(
        _raw_request(
            "POST",
            "/",
            {"Content-Type": "text/plain"},
            b"not json",
        )
    )
    await writer.drain()
    status, _, _ = await _read_response(reader)
    assert status == 415
    writer.close()
    await writer.wait_closed()


# ---------------------------------------------------------------------------
# Tests: shutdown + cleanup
# ---------------------------------------------------------------------------


async def test_graceful_shutdown_removes_socket(socket_path: str, echo_router) -> None:
    """After stop(), the socket file no longer exists."""
    from src.state_daemon.server import DaemonServer

    srv = DaemonServer(socket_path, echo_router)
    await srv.start()
    assert os.path.exists(socket_path)
    await srv.stop()
    assert not os.path.exists(socket_path)


async def test_connection_after_stop_fails(socket_path: str, echo_router) -> None:
    """Connections after stop() are rejected."""
    from src.state_daemon.server import DaemonServer

    srv = DaemonServer(socket_path, echo_router)
    await srv.start()
    await srv.stop()

    with pytest.raises(OSError):
        await asyncio.open_unix_connection(socket_path)
