"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class EventStore(Protocol):
    """Protocol for writing and reading domain events."""

    async def append(self, aggregate_type: str, aggregate_id: str, event_type: str, data: dict) -> str: ...
    async def read_stream(self, aggregate_id: str, after_seq: int = 0) -> AsyncIterator[dict]: ...
