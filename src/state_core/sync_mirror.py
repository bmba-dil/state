"""SyncEvent mirror emitter — post-commit fire-and-forget HTTP POST to opencode.

Every committed event row is mirrored as a best-effort SyncEvent.
On success, the event's ``synced_to_opencode`` column is set to 1.
On failure (after one retry), the row is left at 0 for Phase 006
(startup reconciliation) to pick up.

Architecture: fire-and-forget via ``asyncio.create_task``.
The caller never awaits the mirror — it runs in the background.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.state_core.config import resolve_opencode_url
from src.state_core.database import get_connection

log = structlog.get_logger(__name__)

SYNC_REPLAY_PATH = "/sync/replay"


class SyncEventMirror:
    """Fire-and-forget mirror that POSTs committed events to opencode's SyncEvent API.

    Usage::

        mirror = SyncEventMirror(directory=Path.cwd())
        await store.append("step", "step-01", "state.step.executed", {...},
                           mirror=mirror)
    """

    def __init__(self, directory: Path | None = None) -> None:
        """Store the project root *directory* for the SyncEvent ``directory`` field.

        Args:
            directory: Project root path sent in the replay request body.
                Defaults to ``Path.cwd()``.
        """
        self._directory = directory or Path.cwd()
        self._client = httpx.AsyncClient()

    async def emit(self, event_row: dict[str, Any]) -> None:
        """POST a single event to opencode's ``/sync/replay`` endpoint.

        This method is designed to be called from within an ``asyncio.create_task``.
        It catches all exceptions internally — never propagates to the caller.

        Args:
            event_row: A dict with keys matching ``events`` table columns:
                ``id``, ``aggregate_id``, ``seq``, ``type``, ``data``.
        """
        url = resolve_opencode_url()
        replay_url = f"{url}{SYNC_REPLAY_PATH}"

        body: dict[str, Any] = {
            "directory": str(self._directory),
            "events": [
                {
                    "id": event_row["id"],
                    "aggregateID": event_row["aggregate_id"],
                    "seq": event_row["seq"],
                    "type": event_row["type"],
                    "data": event_row["data"] if isinstance(event_row["data"], dict)
                            else json.loads(event_row["data"]),
                }
            ],
        }

        for attempt in (1, 2):
            try:
                response = await self._client.post(
                    replay_url,
                    json=body,
                    timeout=httpx.Timeout(10.0),
                )
                if response.is_success:
                    await self._mark_synced(event_row["id"])
                    log.debug("sync ok", event_id=event_row["id"],
                              attempt=attempt)
                    return

                log.warning("sync failed (non-2xx)", event_id=event_row["id"],
                            status=response.status_code, attempt=attempt)

            except httpx.TimeoutException:
                log.warning("sync timeout", event_id=event_row["id"],
                            attempt=attempt)
            except httpx.ConnectError:
                log.warning("sync connection refused", event_id=event_row["id"],
                            attempt=attempt)
            except Exception:
                log.exception("sync unexpected error", event_id=event_row["id"],
                              attempt=attempt)

        log.warning("sync permanently failed", event_id=event_row["id"],
                    url=replay_url)
        # synced_to_opencode stays 0 — Phase 006 will retry

    async def _mark_synced(self, event_id: str) -> None:
        """Update the event row to mark it as successfully synced.

        Opens a fresh connection (the append's connection is already closed
        after commit).
        """
        async with get_connection() as db:
            await db.execute(
                "UPDATE events SET synced_to_opencode = 1 WHERE id = ?",
                (event_id,),
            )
            await db.commit()

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Call this during daemon shutdown.
        """
        await self._client.aclose()
