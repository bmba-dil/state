"""HTTP API server for the state daemon.

Binds to a unix domain socket and accepts HTTP/1.1 connections.
Routes POST requests through a pluggable router callable; handles
GET /health directly.  Content-Type validation rejects non-JSON POSTs.

GET /events/subscribe is delegated to a pluggable SSE handler that
manages the stream lifecycle — the handler receives the reader/writer
and keeps the connection open for the duration of the SSE session.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable, Awaitable

import structlog

from state_core.version import HEADER_NAME, check_version_compat

log = structlog.get_logger(__name__)

# Router callable signature: (method, path, headers, body) -> bytes | (status, body)
# Middleware may return a tuple[int, bytes] to signal a non-200 status code
# (e.g. 400/403 on mode enforcement rejection).  Plain bytes get 200/204.
Router = Callable[[str, str, dict[str, str], bytes], Awaitable[bytes | tuple[int, bytes]]]

# SSE handler callable signature: (reader, writer, path, headers) -> None
# The handler owns the connection lifecycle — it writes SSE headers, streams
# events, and closes the writer when done.  The server does not write anything
# after delegating to this handler.
SseHandler = Callable[
    [asyncio.StreamReader, asyncio.StreamWriter, str, dict[str, str]],
    Awaitable[None],
]

_HTTP_STATUS_TEXTS: dict[int, str] = {
    200: "OK",
    204: "No Content",
    400: "Bad Request",
    403: "Forbidden",
    405: "Method Not Allowed",
    415: "Unsupported Media Type",
    426: "Upgrade Required",
    500: "Internal Server Error",
}


# GET handler callable signature: () -> bytes (response body).
# The server wraps the returned bytes in a 200 + Content-Type: application/json
# response.  Handlers that need to signal errors should return a JSON error body.
GetHandler = Callable[[], Awaitable[bytes]]


class DaemonServer:
    """Async HTTP server bound to a unix domain socket.

    Accepts connections, parses HTTP/1.x requests, and routes them
    through a pluggable router callable.  Handles GET /health directly.

    GET /events/subscribe is delegated to an optional SSE handler that
    manages the stream lifecycle (headers, event streaming, heartbeat,
    client cleanup).

    Additional GET endpoints can be registered via ``add_get_handler(path, handler)``
    — the handler is called with no arguments and returns response body bytes.
    """

    def __init__(
        self,
        socket_path: str,
        router: Router,
        sse_handler: SseHandler | None = None,
    ) -> None:
        self._socket_path = socket_path
        self._router = router
        self._sse_handler = sse_handler
        self._server: asyncio.Server | None = None
        # Pluggable GET route handlers: path → handler callable.
        self._get_handlers: dict[str, GetHandler] = {}

    async def start(self) -> None:
        """Bind to the unix socket and begin accepting connections."""
        self._cleanup_socket()
        self._server = await asyncio.start_unix_server(
            self._handle_connection,
            path=self._socket_path,
        )
        os.chmod(self._socket_path, 0o600)
        log.info("daemon.server.started", socket_path=self._socket_path)

    def add_get_handler(self, path: str, handler: GetHandler) -> None:
        """Register a GET handler for *path*.

        The handler receives no arguments and must return response body bytes.
        Handlers are matched by exact path.  Registered handlers take priority
        over the built-in /health and /events/subscribe routes.
        """
        self._get_handlers[path] = handler

    async def stop(self) -> None:
        """Gracefully shut down, waiting for in-flight requests."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._cleanup_socket()
            log.info("daemon.server.stopped", socket_path=self._socket_path)

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single HTTP connection."""
        try:
            # --- Read request line ---
            request_line = await reader.readline()
            if not request_line:
                return

            parts = request_line.decode().strip().split(" ", 2)
            if len(parts) != 3:
                writer.write(_http_response(400, [], b"Bad Request"))
                await writer.drain()
                return
            method, path, _version = parts

            # --- Read headers ---
            headers: dict[str, str] = {}
            while True:
                header_line = await reader.readline()
                if header_line in (b"\r\n", b"\n", b""):
                    break
                decoded = header_line.decode().strip()
                if ": " in decoded:
                    key, _, value = decoded.partition(": ")
                    headers[key.lower()] = value

            # --- Version handshake (WRK-13) ---
            # Validate X-State-Plugin-Version on worker-specific endpoints:
            # POST /hook/* (hook forwarding) and GET /events/subscribe (SSE).
            # Internal daemon API (POST /) and GET /health are exempt.
            _worker_endpoint = (
                (method == "POST" and path.startswith("/hook/"))
                or (method == "GET" and path.startswith("/events/subscribe"))
            )
            if _worker_endpoint:
                ok, msg = check_version_compat(headers.get(HEADER_NAME))
                if not ok:
                    body = _json_error(msg)
                    writer.write(
                        _http_response(
                            426,
                            [("Content-Type", "application/json")],
                            body,
                        )
                    )
                    await writer.drain()
                    return

            # --- Read body ---
            content_length = int(headers.get("content-length", "0"))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # --- Registered GET handlers (Phase 059+ extensible) ---
            if method == "GET" and path in self._get_handlers:
                handler = self._get_handlers[path]
                try:
                    response_body = await handler()
                except Exception:
                    log.exception("daemon.server.get_handler_error", path=path)
                    writer.write(
                        _http_response(
                            500,
                            [("Content-Type", "application/json")],
                            b'{"error": "Internal Server Error"}',
                        )
                    )
                    await writer.drain()
                    return
                writer.write(
                    _http_response(
                        200,
                        [("Content-Type", "application/json")],
                        response_body,
                    )
                )
                await writer.drain()
                return

            # --- GET /health (plain HTTP — not JSON-RPC) ---
            if method == "GET" and path == "/health":
                writer.write(
                    _http_response(
                        200,
                        [("Content-Type", "application/json")],
                        b'{"status": "ok"}',
                    )
                )
                await writer.drain()
                return

            # --- GET /events/subscribe — SSE stream (Phase 054) ---
            if method == "GET" and path.startswith("/events/subscribe"):
                if self._sse_handler is not None:
                    await self._sse_handler(reader, writer, path, headers)
                    # SSE handler owns the stream lifecycle — it writes
                    # headers, streams events, and closes the writer.
                    return
                else:
                    writer.write(
                        _http_response(
                            501,
                            [("Content-Type", "text/plain")],
                            b"SSE not configured",
                        )
                    )
                    await writer.drain()
                    return

            # --- Content-Type validation for POST ---
            if method == "POST":
                content_type = headers.get("content-type", "")
                if "application/json" not in content_type:
                    writer.write(
                        _http_response(
                            415,
                            [("Content-Type", "text/plain")],
                            b"Unsupported Media Type: expected application/json",
                        )
                    )
                    await writer.drain()
                    return

            # --- Route to the pluggable router ---
            router_result = await self._router(method, path, headers, body)

            # Middleware may return a (status_code, body) tuple for
            # non-200 responses (e.g. 400/403 mode enforcement).
            if isinstance(router_result, tuple):
                status_code, response_body = router_result
            else:
                status_code = 200
                response_body = router_result

            if response_body:
                writer.write(
                    _http_response(
                        status_code,
                        [("Content-Type", "application/json")],
                        response_body,
                    )
                )
            else:
                # Notification: no response body (JSON-RPC notification)
                writer.write(_http_response(204, [], b""))

            await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionError) as e:
            log.warning(
                "daemon.server.connection_error",
                error_type=type(e).__name__,
            )
        except Exception:
            log.exception("daemon.server.unhandled_error")
            try:
                writer.write(
                    _http_response(
                        500,
                        [("Content-Type", "application/json")],
                        b'{"error": "Internal Server Error"}',
                    )
                )
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _cleanup_socket(self) -> None:
        """Remove the socket file if it exists (from a previous run)."""
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass


def _json_error(message: str) -> bytes:
    """Build a JSON error body."""
    return json.dumps({"error": message}).encode()


def _http_response(
    status: int,
    headers: list[tuple[str, str]],
    body: bytes,
) -> bytes:
    """Build an HTTP/1.1 response from status, headers, and body."""
    status_text = _HTTP_STATUS_TEXTS.get(status, "Unknown")
    lines = [f"HTTP/1.1 {status} {status_text}"]
    for key, value in headers:
        lines.append(f"{key}: {value}")
    lines.append(f"Content-Length: {len(body)}")
    lines.append("")
    lines.append("")  # blank line after headers
    return "\r\n".join(lines).encode() + body
