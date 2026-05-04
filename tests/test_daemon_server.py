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


# ---------------------------------------------------------------------------
# Tests: JsonRpcRouter — JSON-RPC 2.0 routing, errors, notifications
# ---------------------------------------------------------------------------


async def _call_router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
    """Shortcut to invoke JsonRpcRouter's __call__."""
    from src.state_daemon.router import JsonRpcRouter

    r = JsonRpcRouter()

    async def _ping(params: object) -> str:
        return "pong"

    async def _echo(params: object) -> object:
        return params

    r.add_method("ping", _ping)
    r.add_method("echo", _echo)
    return await r(method, path, headers, body)


def _jsonrpc_request(method: str, params: object = None, req_id: int | None = 1) -> bytes:
    """Build a JSON-RPC 2.0 request body."""
    import json

    payload: dict[str, object] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if req_id is not None:
        payload["id"] = req_id
    return json.dumps(payload).encode()


# --- Valid routing ---


async def test_router_valid_ping() -> None:
    """Valid JSON-RPC 'ping' method returns success response."""
    body = await _call_router(
        "POST", "/", {"content-type": "application/json"},
        _jsonrpc_request("ping"),
    )
    import json

    resp = json.loads(body)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"] == "pong"
    assert resp["id"] == 1


async def test_router_valid_echo() -> None:
    """Valid JSON-RPC 'echo' method returns the params."""
    body = await _call_router(
        "POST", "/", {"content-type": "application/json"},
        _jsonrpc_request("echo", params={"hello": "world"}),
    )
    import json

    resp = json.loads(body)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"] == {"hello": "world"}
    assert resp["id"] == 1


# --- Notifications ---


async def test_router_notification_no_response() -> None:
    """JSON-RPC notification (id=null) returns empty body."""
    body = await _call_router(
        "POST", "/", {"content-type": "application/json"},
        _jsonrpc_request("ping", req_id=None),
    )
    assert body == b""


async def test_router_notification_missing_id() -> None:
    """JSON-RPC notification (no 'id' key) returns empty body."""
    import json

    body = await _call_router(
        "POST",
        "/",
        {"content-type": "application/json"},
        json.dumps({"jsonrpc": "2.0", "method": "ping"}).encode(),
    )
    assert body == b""


# --- Error codes (parameterized) ---


@pytest.mark.parametrize(
    "body_bytes,expected_code,expected_substr",
    [
        # -32700 Parse error: malformed JSON
        (b"not json", -32700, "Parse error"),
        # -32700 Parse error: empty body
        (b"", -32700, "Parse error"),
        # -32600 Invalid Request: jsonrpc version missing
        (b'{"method": "ping", "id": 1}', -32600, "Invalid Request"),
        # -32600 Invalid Request: not a JSON object (array)
        (b"[1, 2, 3]", -32600, "Invalid Request"),
        # -32601 Method not found
        (b'{"jsonrpc": "2.0", "method": "nonexistent", "id": 1}', -32601, "Method not found"),
    ],
)
async def test_router_error_codes(
    body_bytes: bytes, expected_code: int, expected_substr: str
) -> None:
    """JSON-RPC errors return proper codes and messages."""
    import json

    body = await _call_router(
        "POST", "/", {"content-type": "application/json"}, body_bytes
    )
    resp = json.loads(body)
    assert resp["jsonrpc"] == "2.0"
    assert resp["error"]["code"] == expected_code
    assert expected_substr in resp["error"]["message"]


# --- Internal error ---


async def test_router_handler_exception_returns_internal_error() -> None:
    """A handler that raises produces -32603 Internal error."""
    import json
    from src.state_daemon.router import JsonRpcRouter

    router = JsonRpcRouter()

    async def _crash(_params: object) -> object:
        raise RuntimeError("boom")

    router.add_method("crash", _crash)

    body = await router(
        "POST", "/", {"content-type": "application/json"},
        _jsonrpc_request("crash"),
    )
    resp = json.loads(body)
    assert resp["jsonrpc"] == "2.0"
    assert resp["error"]["code"] == -32603
    assert "Internal error" in resp["error"]["message"]


# --- Handler registration ---


async def test_router_add_method_registers_handler() -> None:
    """add_method() registers a callable that gets dispatched."""
    import json
    from src.state_daemon.router import JsonRpcRouter

    router = JsonRpcRouter()

    async def _double(params: object) -> int:
        assert isinstance(params, int)
        return params * 2

    router.add_method("double", _double)

    body = await router(
        "POST", "/", {"content-type": "application/json"},
        _jsonrpc_request("double", params=21),
    )
    resp = json.loads(body)
    assert resp["result"] == 42


# ---------------------------------------------------------------------------
# Tests: Server + JsonRpcRouter integration (Task 050.3)
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_socket_path() -> str:
    """Temp socket path for server+router integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "int-daemon.sock")


async def test_server_with_jsonrpc_router(integration_socket_path: str) -> None:
    """Wire DaemonServer with JsonRpcRouter — POST routes through JSON-RPC."""
    import json

    from src.state_daemon.router import JsonRpcRouter
    from src.state_daemon.server import DaemonServer

    router = JsonRpcRouter()

    async def _add(params: object) -> int:
        assert isinstance(params, dict)
        return params["a"] + params["b"]

    async def _greet(params: object) -> str:
        assert isinstance(params, dict)
        return f'Hello, {params["name"]}!'

    router.add_method("add", _add)
    router.add_method("greet", _greet)

    srv = DaemonServer(integration_socket_path, router)
    await srv.start()

    try:
        # Test valid JSON-RPC call
        reader, writer = await asyncio.open_unix_connection(integration_socket_path)
        writer.write(
            _raw_request(
                "POST",
                "/",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"jsonrpc": "2.0", "method": "add", "params": {"a": 10, "b": 32}, "id": 1}
                ).encode(),
            )
        )
        await writer.drain()
        status, _, resp_body = await _read_response(reader)
        assert status == 200
        data = json.loads(resp_body)
        assert data["result"] == 42
        assert data["id"] == 1
        writer.close()
        await writer.wait_closed()

        # Test notification (no response)
        reader, writer = await asyncio.open_unix_connection(integration_socket_path)
        writer.write(
            _raw_request(
                "POST",
                "/",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"jsonrpc": "2.0", "method": "greet", "params": {"name": "World"}}
                ).encode(),
            )
        )
        await writer.drain()
        status, _, resp_body = await _read_response(reader)
        assert status == 204
        assert resp_body == b""
        writer.close()
        await writer.wait_closed()

        # Test method not found
        reader, writer = await asyncio.open_unix_connection(integration_socket_path)
        writer.write(
            _raw_request(
                "POST",
                "/",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"jsonrpc": "2.0", "method": "nonexistent", "id": 2}
                ).encode(),
            )
        )
        await writer.drain()
        status, _, resp_body = await _read_response(reader)
        assert status == 200
        data = json.loads(resp_body)
        assert data["error"]["code"] == -32601
        writer.close()
        await writer.wait_closed()

    finally:
        await srv.stop()


async def test_health_endpoint_works_with_router(integration_socket_path: str) -> None:
    """GET /health still works when server has a JsonRpcRouter installed."""
    from src.state_daemon.router import JsonRpcRouter
    from src.state_daemon.server import DaemonServer

    router = JsonRpcRouter()
    srv = DaemonServer(integration_socket_path, router)
    await srv.start()

    try:
        reader, writer = await asyncio.open_unix_connection(integration_socket_path)
        writer.write(_raw_request("GET", "/health"))
        await writer.drain()
        status, _, body = await _read_response(reader)
        assert status == 200
        assert __import__("json").loads(body) == {"status": "ok"}
        writer.close()
        await writer.wait_closed()
    finally:
        await srv.stop()
