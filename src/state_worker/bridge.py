"""opencode HTTP + state-daemon client bridge.

Provides the SSE bridge that subscribes to the daemon's event stream
and dispatches parsed events to registered callbacks.  Also provides
the HTTP client bridge for hook forwarding (Phase 063).

Architecture::

    state_worker.main
        └─> SseBridge.connect(socket_path)
              └─> GET /events/subscribe?mode=build
                    └─> read SSE lines
                          └─> parse event (id/data/event)
                                └─> on_event_callback(event)

Connection lifecycle is managed by the worker main module (Phase 060);
the bridge owns the SSE read loop and clean disconnection.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from state_core.version import PLUGIN_VERSION
from state_worker.session import SessionIdentity

log = structlog.get_logger(__name__)

OnEventCallback = Callable[[dict[str, object]], Awaitable[None]]

# Retryable HTTP status codes (5xx server errors).
_RETRYABLE_STATUSES: frozenset[int] = frozenset({
    500, 502, 503, 504,
})

# Default retry count for hook forwarding.
_DEFAULT_MAX_RETRIES = 3

# Default retry backoff base in seconds.
_DEFAULT_RETRY_BASE = 0.5

# SSE line terminator (per spec, LF or CRLF).
_CRLF = b"\r\n"
_LF = b"\n"


# ---------------------------------------------------------------------------
# Task 063.1 — HTTP POST bridge for hook event forwarding
# ---------------------------------------------------------------------------


async def forward_hook(
    hook_name: str,
    payload: dict[str, object],
    socket_path: str,
    timeout: float = 5.0,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> bool:
    """Forward a hook event payload to the daemon via HTTP POST.

    Sends a JSON-encoded POST to ``/hook/<hook_name>`` on the daemon
    Unix socket.  Retries on transient failures (connection errors,
    timeouts, 5xx server errors) up to *max_retries* times with
    exponential backoff.

    Returns:
        ``True`` if the daemon accepted the hook (2xx response),
        ``False`` if all retries are exhausted or the daemon rejects
        with a non-retryable status (4xx).
    """
    body_bytes = json.dumps(payload).encode()
    request = (
        f"POST /hook/{hook_name} HTTP/1.1\r\n"
        f"Host: localhost\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"X-State-Plugin-Version: {PLUGIN_VERSION}\r\n"
        f"\r\n"
    ).encode() + body_bytes

    last_error: str = "unknown"

    for attempt in range(1, max_retries + 1):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(socket_path),
                timeout=timeout,
            )
        except (ConnectionRefusedError, FileNotFoundError, asyncio.TimeoutError, OSError) as exc:
            last_error = f"connect: {exc}"
            await _retry_delay(attempt)
            continue

        try:
            writer.write(request)
            await writer.drain()

            status = await _read_http_status(reader, timeout)
            if 200 <= status < 300:
                log.debug(
                    "bridge.hook.success",
                    hook=hook_name,
                    status=status,
                    attempt=attempt,
                )
                return True

            if status in _RETRYABLE_STATUSES:
                last_error = f"retryable status {status}"
                await _retry_delay(attempt)
                continue

            # Non-retryable (4xx, etc.)
            log.warning(
                "bridge.hook.rejected",
                hook=hook_name,
                status=status,
            )
            return False

        except (asyncio.TimeoutError, asyncio.IncompleteReadError) as exc:
            last_error = f"read: {exc}"
            await _retry_delay(attempt)
            continue
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    log.warning(
        "bridge.hook.exhausted",
        hook=hook_name,
        attempts=max_retries,
        last_error=last_error,
    )
    return False


async def _read_http_status(reader: asyncio.StreamReader, timeout: float) -> int:
    """Read the HTTP status line and return the status code."""
    line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    if not line:
        return 0
    parts = line.decode().strip().split()
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except (ValueError, IndexError):
        return 0


async def _retry_delay(attempt: int) -> None:
    """Sleep with exponential backoff."""
    await asyncio.sleep(_DEFAULT_RETRY_BASE * (2 ** (attempt - 1)))


# ---------------------------------------------------------------------------
# SSE bridge (Phase 061)
# ---------------------------------------------------------------------------


class SseBridge:
    """SSE client bridge — subscribes to daemon event stream via Unix socket.

    Connects to the daemon's ``GET /events/subscribe`` SSE endpoint and
    runs a read loop that parses the SSE event stream, dispatching each
    complete event to the registered ``on_event`` callback.

    Usage::

        bridge = SseBridge(session, mode_filter="build")
        bridge.on_event = my_async_handler
        await bridge.connect(socket_path)
        # ... events arrive via callback ...
        await bridge.disconnect()
    """

    def __init__(
        self,
        session: SessionIdentity,
        mode_filter: str | None = None,
    ) -> None:
        self._session = session
        self._mode_filter = mode_filter
        self._running = asyncio.Event()
        self._running.set()  # start in "should run" state
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self.on_event: OnEventCallback | None = None

    async def connect(self, socket_path: str) -> None:
        """Open a Unix socket connection and subscribe to the SSE stream.

        Sends ``GET /events/subscribe`` with optional mode filter and enters
        a read loop that parses SSE events.  The loop exits when
        :meth:`disconnect` is called or the connection is lost.
        """
        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
        except (ConnectionRefusedError, FileNotFoundError) as exc:
            log.warning(
                "bridge.sse.connect_failed",
                socket_path=socket_path,
                error=str(exc),
            )
            return
        except OSError as exc:
            log.warning(
                "bridge.sse.connect_failed",
                socket_path=socket_path,
                error=str(exc),
            )
            return

        self._reader = reader
        self._writer = writer

        # Build subscribe URL with optional query params.
        path = "/events/subscribe"
        params: list[str] = []
        if self._mode_filter is not None:
            params.append(f"mode={self._mode_filter}")
        if params:
            path = path + "?" + "&".join(params)

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"X-State-Session-Id: {self._session.session_id}\r\n"
            f"X-State-Plugin-Version: {PLUGIN_VERSION}\r\n"
            f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        # Skip HTTP response headers.
        await _skip_http_headers(reader)

        log.info(
            "bridge.sse.connected",
            session_id=self._session.session_id,
            path=path,
        )

        # Enter SSE read loop.
        await self._read_loop(reader)

    async def disconnect(self) -> None:
        """Stop the SSE read loop and close the connection."""
        self._running.clear()

        writer = self._writer
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

        self._reader = None
        self._writer = None
        log.info("bridge.sse.disconnected", session_id=self._session.session_id)

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        """Read and parse SSE lines until disconnect or connection loss."""
        event_id: str | None = None
        event_type: str = "message"
        data_lines: list[str] = []

        while self._running.is_set():
            try:
                line_bytes = await reader.readline()
            except (asyncio.IncompleteReadError, ConnectionError, OSError):
                log.warning("bridge.sse.connection_lost")
                break

            if not line_bytes:
                # EOF
                log.warning("bridge.sse.eof")
                break

            line = line_bytes.decode(errors="replace").rstrip("\r\n")

            if line == "":
                # Empty line — dispatch the accumulated event.
                if data_lines:
                    data = "\n".join(data_lines)
                    await _dispatch_event(
                        self.on_event,
                        event_id,
                        event_type,
                        data,
                    )
                # Reset for next event.
                event_id = None
                event_type = "message"
                data_lines = []
                continue

            if line.startswith(":"):
                # Comment — ignore.
                continue

            if ":" in line:
                key, _, value = line.partition(":")
                value = value.lstrip(" ")

                if key == "id":
                    event_id = value if value else None
                elif key == "data":
                    data_lines.append(value)
                elif key == "event":
                    event_type = value if value else "message"

        # End of loop — clean up
        await self.disconnect()


async def _dispatch_event(
    callback: OnEventCallback | None,
    event_id: str | None,
    event_type: str,
    data: str,
) -> None:
    """Parse JSON data and invoke the callback if set."""
    if callback is None:
        log.debug("bridge.sse.event_dropped", reason="no_callback")
        return

    try:
        payload: dict[str, object] = json.loads(data)
    except json.JSONDecodeError as exc:
        log.warning(
            "bridge.sse.json_error",
            data=data[:200],
            error=str(exc),
        )
        return

    try:
        await callback(payload)
    except Exception:
        log.exception("bridge.sse.callback_error")


async def _skip_http_headers(reader: asyncio.StreamReader) -> None:
    """Read and discard HTTP response headers until the blank line."""
    while True:
        line = await reader.readline()
        if not line or line in (b"\r\n", b"\n"):
            break
