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

import structlog

log = structlog.get_logger(__name__)

# Heartbeat interval in seconds — prevents proxy/load-balancer timeouts.
HEARTBEAT_INTERVAL = 30


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
