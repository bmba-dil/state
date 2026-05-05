"""SSE (Server-Sent Events) broadcast bus for the state daemon.

Provides multi-client fan-out of event-store domain events via SSE,
with mode filtering and heartbeat keepalives.  Consumed by workers
(Phase 061), TUI (Phase 081-084), and CLI tail (Phase 009).

Architecture::
    Event Store (post-commit)
        └─> SseBus.on_event(event_row)
              └─> SseClientManager.broadcast(...)
                    ├─> SseClient-1.queue  ──> GET /events/subscribe
                    ├─> SseClient-2.queue  ──> GET /events/subscribe
                    └─> ...
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import structlog

log = structlog.get_logger(__name__)

# Heartbeat interval in seconds — prevents proxy/load-balancer timeouts.
HEARTBEAT_INTERVAL = 30

# Valid mode values for SSE query-param filtering.
_VALID_SSE_MODES: frozenset[str] = frozenset({"build", "teach", "kernel"})


@dataclasses.dataclass(eq=False)
class SseClient:
    """A connected SSE subscriber.

    Attributes:
        queue: asyncio queue where formatted SSE event strings are placed
            for the HTTP stream writer to consume.
        mode_filter: If set, only events matching this mode are delivered.
            ``None`` means receive all modes.
        from_ulid: If set, only events with ``id > from_ulid`` are delivered.
            ``None`` means receive all events from this point forward.
    """

    queue: asyncio.Queue[str]
    mode_filter: str | None = None
    from_ulid: str | None = None


class SseClientManager:
    """Manages a set of connected SSE subscribers and fans out events.

    Thread-safe for asyncio (single-threaded concurrency).  Broadcast is
    fire-and-forget — puts formatted event strings on each client's queue;
    the HTTP handler reads from the queue and writes to the socket.
    """

    def __init__(self) -> None:
        self._clients: set[SseClient] = set()

    def add_client(
        self,
        mode_filter: str | None = None,
        from_ulid: str | None = None,
    ) -> SseClient:
        """Register a new SSE subscriber.

        Args:
            mode_filter: Optional mode to filter events by (``build``,
                ``teach``, ``kernel``). ``None`` = all modes.
            from_ulid: Optional ULID offset — events with ``id <= from_ulid``
                are skipped. ``None`` = all events from this point forward.

        Returns:
            The newly created ``SseClient`` instance.
        """
        client = SseClient(
            queue=asyncio.Queue(),
            mode_filter=mode_filter,
            from_ulid=from_ulid,
        )
        self._clients.add(client)
        log.debug(
            "sse.client_added",
            client_count=len(self._clients),
            mode_filter=mode_filter,
            from_ulid=from_ulid,
        )
        return client

    def remove_client(self, client: SseClient) -> None:
        """Remove a subscriber from the fan-out set.

        Safe to call multiple times for the same client — subsequent calls
        are a no-op.
        """
        self._clients.discard(client)
        log.debug(
            "sse.client_removed",
            client_count=len(self._clients),
        )

    def broadcast(
        self,
        event_json: str,
        event_type: str,
        event_id: str,
        mode: str,
    ) -> None:
        """Fan out an event to all subscribed clients.

        Each client receives the formatted SSE string on its queue.
        Clients with ``mode_filter`` set receive only matching events.
        Clients with ``from_ulid`` set skip events whose id is not
        lexicographically greater than the offset.

        Args:
            event_json: The JSON-serialized event data (the ``data:`` field).
            event_type: The event type string (the ``event:`` field).
            event_id: The ULID of the event (the ``id:`` field).
            mode: The execution mode of the event (used for mode filtering).
        """
        formatted = _format_sse_event(event_id, event_type, event_json)

        disconnected: list[SseClient] = []
        for client in self._clients:
            # Mode filter: skip if client has a filter and it doesn't match.
            if client.mode_filter is not None and client.mode_filter != mode:
                continue

            # ULID offset: skip if event id is not after the offset.
            if client.from_ulid is not None and event_id <= client.from_ulid:
                continue

            try:
                client.queue.put_nowait(formatted)
            except asyncio.QueueFull:
                # Queue is full — client is too slow; drop the event
                # but keep the client (their stream will catch future events).
                log.warning(
                    "sse.client_queue_full",
                    event_id=event_id,
                )

        # Clean up disconnected clients (removed outside the iteration
        # to avoid mutating the set during iteration).
        for client in disconnected:
            self.remove_client(client)

    @property
    def client_count(self) -> int:
        """Return the number of currently connected clients."""
        return len(self._clients)


# ---------------------------------------------------------------------------
# SSE format helpers
# ---------------------------------------------------------------------------


def _format_sse_event(event_id: str, event_type: str, data: str) -> str:
    """Format an event as a standard SSE text block.

    Format::

        id: <ulid>
        event: <type>
        data: <json>

    Trailing blank line separates events per the SSE spec.
    """
    return f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"


def format_heartbeat() -> str:
    """Return an SSE heartbeat comment line.

    Heartbeats are SSE comments (lines starting with ``:``) and are
    ignored by SSE clients.  They prevent proxy/load-balancer timeouts
    on idle connections.
    """
    return ": heartbeat\n\n"


# ---------------------------------------------------------------------------
# SSE HTTP endpoint handler (Task 054.2)
# ---------------------------------------------------------------------------

# SSE response headers sent once when the connection is established.
SSE_HEADERS = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/event-stream\r\n"
    "Cache-Control: no-cache\r\n"
    "Connection: keep-alive\r\n"
    "\r\n"
).encode()


class SseEndpointHandler:
    """Callable SSE handler registered with DaemonServer for GET /events/subscribe.

    Parses query parameters (``?mode=``, ``?from=``), registers the client
    with the provided ``SseClientManager``, writes SSE headers, and enters
    a stream loop that reads formatted SSE lines from the client's queue
    and writes them to the HTTP socket.

    Heartbeats are sent every ``HEARTBEAT_INTERVAL`` seconds to prevent
    proxy/load-balancer timeouts.  On client disconnect or stream error,
    the client is removed from the manager and the writer is closed.
    """

    def __init__(self, client_manager: SseClientManager) -> None:
        self._client_manager = client_manager

    async def __call__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        path: str,
        headers: dict[str, str],
    ) -> None:
        """Handle an SSE subscription request.

        Args:
            reader: The HTTP request stream reader (unused after headers).
            writer: The HTTP response stream writer — kept open for the
                duration of the SSE session.
            path: The full request path including query string
                (e.g. ``/events/subscribe?mode=build&from=01XYZ``).
            headers: The request headers dict (lowercase keys).
        """
        # --- Parse query parameters ---
        parsed = urlparse(path)
        qs = parse_qs(parsed.query)

        mode_filter: str | None = None
        raw_mode = qs.get("mode", [None])[0]
        if raw_mode is not None:
            if raw_mode in _VALID_SSE_MODES:
                mode_filter = raw_mode
            else:
                # Invalid mode — reject with 400.
                writer.write(
                    b"HTTP/1.1 400 Bad Request\r\n"
                    b"Content-Type: text/plain\r\n"
                    b"Content-Length: 24\r\n"
                    b"\r\n"
                    b"Invalid mode parameter\r\n"
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

        from_ulid: str | None = qs.get("from", [None])[0]

        # --- Register client ---
        client = self._client_manager.add_client(
            mode_filter=mode_filter,
            from_ulid=from_ulid,
        )

        # --- Write SSE headers ---
        writer.write(SSE_HEADERS)
        await writer.drain()

        log.info(
            "sse.stream_started",
            mode_filter=mode_filter,
            from_ulid=from_ulid,
        )

        # --- Stream loop ---
        heartbeat_task: asyncio.Task[None] | None = None

        try:
            # Start heartbeat task.
            heartbeat_task = asyncio.create_task(
                _heartbeat_loop(writer),
            )

            while True:
                # Check if the writer is closing or reader is at EOF — client disconnected.
                if writer.is_closing() or reader.at_eof():
                    break

                try:
                    # Read from the client's queue with a timeout so we can
                    # periodically check for writer closure.
                    msg = await asyncio.wait_for(
                        client.queue.get(),
                        timeout=1.0,
                    )
                    writer.write(msg.encode())
                    await writer.drain()
                except asyncio.TimeoutError:
                    # No events within the poll window — normal.  The heartbeat
                    # task handles keepalives independently.  Loop back to
                    # check for writer closure.
                    pass
                except asyncio.CancelledError:
                    break
        except (
            ConnectionResetError,
            BrokenPipeError,
            ConnectionError,
        ):
            log.debug("sse.client_disconnected")
        except Exception:
            log.exception("sse.stream_error")
        finally:
            # --- Cleanup ---
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            self._client_manager.remove_client(client)

            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

            log.info("sse.stream_ended")


async def _heartbeat_loop(writer: asyncio.StreamWriter) -> None:
    """Send SSE heartbeat comments every ``HEARTBEAT_INTERVAL`` seconds.

    Runs as a background task for the duration of a single SSE connection.
    """
    hb = format_heartbeat().encode()
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            writer.write(hb)
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, ConnectionError):
            break
        except Exception:
            log.exception("sse.heartbeat_error")
            break
