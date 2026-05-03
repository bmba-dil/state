---
phase: "005"
plan: "A"
type: "auto"
autonomous: false
wave: 1
depends_on:
  - "Phase 004 (append, seq enforcement, deterministic JSON)"
files_modified:
  - "src/state_core/events.py"
  - "src/state_core/config.py"
  - "src/state_core/sync_mirror.py"
requirements:
  - "EVT-01"
---

<objective>
Implement the SyncEvent mirror emitter — a fire-and-forget HTTP POST from `SqliteEventStore.append()` to opencode's `POST /sync/replay` endpoint. Deliver two new modules:
1. `config.py` — opencode config file discovery (search up from CWD for `opencode.json`/`.opencode/opencode.json`, parse `server.port` + `server.hostname`)
2. `sync_mirror.py` — `SyncEventMirror` class that POSTs events and updates `synced_to_opencode=1` on success

Then integrate into `SqliteEventStore.append()` as an injected, post-commit fire-and-forget task.

By the end of this plan, every committed event row is mirrored to opencode as a best-effort fire-and-forget. Success/failure is recorded in the `synced_to_opencode` column.
</objective>

<tasks>

## Task 1 — Create `src/state_core/config.py` with opencode config file discovery

<read_first>
  src/state_core/database.py (use `_resolve_db_path` pattern as reference for path resolution — this module follows the same naming style and uses `pathlib.Path`)
  state-inputs/opencode/packages/opencode/src/cli/network.ts (config shape: `{server: {port: number, hostname: string}}`)
</read_first>

<action>

Create `src/state_core/config.py` with the opencode config resolver:

```python
"""Opencode config file discovery and URL resolution.

Searches up from CWD for opencode.json or .opencode/opencode.json
and reads server.port / server.hostname to construct the API base URL.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

DEFAULT_OPENCODE_PORT = 17495
DEFAULT_OPENCODE_HOST = "127.0.0.1"


def find_opencode_config(start_dir: Path | None = None) -> Path | None:
    """Walk up from *start_dir* looking for opencode.json or .opencode/opencode.json.

    Checks each directory for:
      1. ``<dir>/opencode.json``
      2. ``<dir>/.opencode/opencode.json``

    Returns the first matching path, or *None* if nothing is found
    (including when the search reaches the filesystem root).
    """
    if start_dir is None:
        start_dir = Path.cwd()
    current = start_dir.resolve()
    while True:
        for candidate in (current / "opencode.json",
                          current / ".opencode" / "opencode.json"):
            if candidate.is_file():
                return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def resolve_opencode_url(start_dir: Path | None = None) -> str:
    """Resolve the opencode HTTP base URL from config, with fallback defaults.

    Priority:
      1. ``STATE_OPENCODE_URL`` environment variable (bypass config search)
      2. ``opencode.json`` / ``.opencode/opencode.json`` found by walking up
      3. ``http://127.0.0.1:17495`` (opencode default)

    Returns:
        A URL string like ``http://127.0.0.1:17495`` (no trailing slash).
    """
    import os
    env_url = os.environ.get("STATE_OPENCODE_URL")
    if env_url:
        return env_url.rstrip("/")

    config_path = find_opencode_config(start_dir)
    if config_path is not None:
        try:
            raw = config_path.read_text(encoding="utf-8")
            cfg = json.loads(raw)
            server = cfg.get("server", {}) or {}
            port = int(server.get("port", DEFAULT_OPENCODE_PORT))
            host = str(server.get("hostname", DEFAULT_OPENCODE_HOST))
            if port <= 0 or port > 65535:
                port = DEFAULT_OPENCODE_PORT
            url = f"http://{host}:{port}"
            log.debug("resolved opencode URL from config", url=url, config=str(config_path))
            return url
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            log.warning("failed to parse opencode config, using defaults",
                        config=str(config_path), error=str(exc))

    log.debug("using default opencode URL", url=f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}")
    return f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"
```

Key constraints:
- `find_opencode_config` returns `None` (not raises) when nothing is found — callers always have a fallback
- `resolve_opencode_url` always returns a valid URL string — never raises
- Config path ordering: `opencode.json` (file) takes priority over `.opencode/opencode.json` (within the same directory)
- Environment variable `STATE_OPENCODE_URL` is for future use / testing override — documented but not required in Phase 005
- Uses `Path.read_text()` error handling for missing/empty files
- Default host is `127.0.0.1` (not `localhost`) to avoid DNS resolution overhead
- Module-level `log` via structlog, matching the pattern in existing codebase
</action>

<acceptance_criteria>
- ✗ `src/state_core/config.py` exists with `find_opencode_config()` and `resolve_opencode_url()` functions
- ✗ `find_opencode_config()` returns a `Path` when `opencode.json` exists in a parent directory
- ✗ `find_opencode_config()` returns `None` when no config file exists in any parent
- ✗ `find_opencode_config()` checks `opencode.json` before `.opencode/opencode.json` in the same directory
- ✗ `resolve_opencode_url()` returns `http://127.0.0.1:17495` when no config is found
- ✗ `resolve_opencode_url()` reads `server.port` and `server.hostname` from a valid config file
- ✗ `resolve_opencode_url()` uses `STATE_OPENCODE_URL` env var when set, bypassing config search
- ✗ `resolve_opencode_url()` never raises — all error paths return the default URL
- ✗ Module has `from __future__ import annotations` as first import
</acceptance_criteria>

## Task 2 — Create `src/state_core/sync_mirror.py` with `SyncEventMirror` class

<read_first>
  src/state_core/events.py (event row dict shape from `read_stream`: id, seq, type, data, ts, mode, aggregate_id)
  src/state_core/database.py (get_connection pattern — used by the mirror's success callback to update synced_to_opencode)
  state-inputs/opencode/packages/opencode/src/sync/index.ts (SyncEvent.replayAll expects `{id, aggregateID, seq, type, data}`)
  state-inputs/opencode/packages/opencode/src/server/routes/instance/sync.ts (POST /sync/replay body: `{directory: string, events: ReplayEvent[]}`)
</read_first>

<action>

Create `src/state_core/sync_mirror.py`:

```python
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
```

Key constraints:
- `event_row["data"]` must be deserialized from JSON if it's a string (the fire-and-forget task receives the row after it's been committed, but before `read_stream`-style JSON deserialization — so `data` may still be a JSON string). Use `isinstance(event_row["data"], dict)` to check.
- `aggregate_id` → `aggregateID` (camelCase) for the SyncEvent field — matches opencode's TypeScript API exactly.
- Retry: 2 attempts. First failure logs warning, second failure logs permanent failure. No backoff between retries (Phase 005 keeps it simple).
- Timeout: 10 seconds per attempt (httpx timeout).
- Exception safety: catches `httpx.TimeoutException`, `httpx.ConnectError`, and generic `Exception`. Never propagates.
- The `_mark_synced` call opens a NEW connection via `get_connection()` — does NOT use the append's connection (which is already closed/returned to pool after commit).
- The `close()` method cleans up the shared httpx client. Not called in Phase 005's fire-and-forget path (the task runs at application level, and the client lives for the daemon's lifetime). Added for completeness and future daemon lifecycle integration.
</action>

<acceptance_criteria>
- ✗ `src/state_core/sync_mirror.py` exists with `SyncEventMirror` class
- ✗ `SyncEventMirror.__init__` creates an `httpx.AsyncClient` and stores `directory`
- ✗ `SyncEventMirror.emit()` constructs `POST /sync/replay` with body `{directory, events: [{id, aggregateID, seq, type, data}]}`
- ✗ `emit()` maps `aggregate_id` → `aggregateID` (camelCase) in the SyncEvent payload
- ✗ `emit()` deserializes `event_row["data"]` from JSON string to dict if not already a dict
- ✗ `emit()` retries once on failure (2 attempts total) before giving up
- ✗ `emit()` catches all exceptions (never propagates to caller)
- ✗ `emit()` calls `_mark_synced()` via `UPDATE events SET synced_to_opencode = 1 WHERE id = ?` on success
- ✗ `_mark_synced()` opens a fresh connection via `get_connection()` (not the append's connection)
- ✗ `close()` calls `self._client.aclose()`
- ✗ Module has `from __future__ import annotations` as first import
</acceptance_criteria>

## Task 3 — Integrate `SyncEventMirror` into `SqliteEventStore.append()` as fire-and-forget

<read_first>
  src/state_core/events.py (entire file — current `append()` method, `EventStore` protocol)
  src/state_core/sync_mirror.py (the `SyncEventMirror.emit()` interface, which expects an event row dict)
</read_first>

<action>

Modify `src/state_core/events.py`:

**3a.** Add import for `asyncio` and `SyncEventMirror`:

```python
import asyncio
from collections.abc import AsyncIterator
from typing import Any, Protocol

from src.state_core.sync_mirror import SyncEventMirror
```

**3b.** Update `EventStore` protocol to add optional `mirror` parameter:

Change the `append()` method signature in the protocol:

```python
class EventStore(Protocol):
    """Protocol for writing and reading domain events."""

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        data: dict[str, Any],
        *,
        mode: Mode = "kernel",
        ts: str | None = None,
        id_: str | None = None,
        mirror: SyncEventMirror | None | None = None,  # noqa: ARG002 — protocol marker
    ) -> str: ...

    async def read_stream(
        self, aggregate_id: str, after_seq: int = 0
    ) -> AsyncIterator[dict[str, Any]]: ...
```

**3c.** Update `SqliteEventStore.append()` signature:

```python
async def append(
    self,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    data: dict[str, Any],
    *,
    mode: Mode = "kernel",
    ts: str | None = None,
    id_: str | None = None,
    mirror: SyncEventMirror | None = None,
) -> str:
```

**3d.** After `await db.commit()` (the last `await` before `return id_`), add the fire-and-forget block:

```python
        # After db.commit() and before return:

        if mirror is not None:
            # Build an event row dict for the mirror's emit method.
            # This is the same shape that read_stream yields.
            event_row: dict[str, Any] = {
                "id": id_,
                "seq": seq,
                "aggregate_id": aggregate_id,
                "type": event_type,
                "data": data,
                "ts": ts,
                "mode": mode,
            }
            # Fire-and-forget: never await the result.
            # The mirror catches all exceptions internally.
            asyncio.ensure_future(mirror.emit(event_row))

        return id_
```

Key constraints:
- `asyncio.ensure_future()` is used instead of `asyncio.create_task()` in case the event loop is not the currently running loop (defensive choice). Both schedule the coroutine as a task.
- The event_row dict is built freshly from local variables — NOT from a DB re-read. This avoids an extra round-trip to SQLite and ensures the mirror gets the exact in-memory values.
- The `data` field is passed as the original Python dict (before JSON serialization). `SyncEventMirror.emit()` handles JSON deserialization if needed.
- The `mirror` parameter is `None` by default — existing callers that don't pass mirror continue to work unchanged.
- No `await` on the mirror task — the caller never blocks.
- The `EventStore` protocol signature includes `mirror: SyncEventMirror | None | None = None` — the double `None` union is a no-op (just a protocol marker). It makes clear the parameter exists at the protocol level without requiring implementations to use it. The `# noqa: ARG002` suppresses unused-argument linting since protocol methods use the parameter only as a type marker.

**Alternative simpler approach** for the protocol marker if TypeScript-inspired type gymnastics feel fragile:

```python
mirror: Any = None  # injected by callers that want SyncEvent mirroring
```

Use this simpler approach — it avoids the confusing double-`None` union and clearly communicates that mirror is an optional injection point.
</action>

<acceptance_criteria>
- ✗ `src/state_core/events.py` imports `asyncio` and `SyncEventMirror`
- ✗ `SqliteEventStore.append()` accepts optional `mirror: SyncEventMirror | None = None` parameter
- ✗ `EventStore` protocol updated to include `mirror` parameter (optional, not required by all implementations)
- ✗ After `await db.commit()`, a fire-and-forget task is created via `asyncio.ensure_future(mirror.emit(...))` when `mirror is not None`
- ✗ The event_row dict passed to `mirror.emit()` contains `id`, `seq`, `aggregate_id`, `type`, `data`, `ts`, `mode`
- ✗ The `data` field in the event_row dict is the original Python dict (not JSON string)
- ✗ The caller never awaits the mirror task — `append()` returns immediately after `db.commit()`
- ✗ Existing callers that don't pass `mirror` continue to work unchanged (backward compat)
- ✗ All existing tests pass: `python3 -m pytest tests/test_events.py -x -q`
- ✗ No unhandled exceptions from mirror.emit() propagate to append()'s caller
</acceptance_criteria>

</tasks>

<verification>

### How to confirm plan goal achieved

1. **Import check:** `python3 -c "from src.state_core.config import find_opencode_config, resolve_opencode_url; from src.state_core.sync_mirror import SyncEventMirror; print('OK')"` exits 0
2. **Config discovery test (manual):** Create a temp `opencode.json` with `{"server": {"port": 18999, "hostname": "0.0.0.0"}}`, run a small script that calls `resolve_opencode_url(tmp_path)` and confirms URL is `http://0.0.0.0:18999`
3. **Config fallback test (manual):** Call `resolve_opencode_url()` from a dir with no config — returns `http://127.0.0.1:17495`
4. **Integration smoke test (manual):** Instantiate `SyncEventMirror(directory=Path.cwd())`, append an event to `SqliteEventStore` with `mirror=mirror`, confirm:
   - `append()` returns immediately (no await needed for mirror)
   - Event is written to SQLite (confirmed by `read_stream`)
   - If opencode is running, event arrives at `/sync/replay`
   - If opencode is NOT running, `synced_to_opencode` stays 0 (no crash)
5. **Existing test non-regression:** `python3 -m pytest tests/test_events.py -x -q` passes (all 20+ existing tests)
6. **Protocol conformance:** `python3 -c "from src.state_core.events import SqliteEventStore; import inspect; assert 'mirror' in inspect.signature(SqliteEventStore.append).parameters"`
7. **grep check for anti-pattern:** `rg 'datetime\.now\(\)' src/state_core/` returns no matches in new files
</verification>

<must_haves>

- `src/state_core/config.py` — `find_opencode_config()` and `resolve_opencode_url()`
- `src/state_core/sync_mirror.py` — `SyncEventMirror` class with `emit()`, `_mark_synced()`, `close()`
- Modified `src/state_core/events.py` — `append()` with `mirror` parameter + fire-and-forget integration
- Fire-and-forget is truly fire-and-forget: no `await` on the mirror task, no exception propagation
- Backward compatible: existing callers without `mirror` unchanged
- All existing tests pass
- retry-once behaviour (2 attempts total)
- `synced_to_opencode` updated on success via fresh DB connection
</must_haves>
