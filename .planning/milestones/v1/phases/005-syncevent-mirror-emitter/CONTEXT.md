# CONTEXT: Phase 005 — SyncEvent Mirror Emitter

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

Implement post-commit SyncEvent emission over opencode HTTP (when reachable), marking `synced_to_opencode=1` per row. This is the "mirror" step of the dual-write architecture: SQLite is authoritative (Phase 004), and SyncEvent is the derived mirror.

Phase 005 handles the emission at append time. Phase 006 (startup reconciliation) handles discovering and re-emitting rows that were never synced.

## Requirements

- **EVT-01**: Daemon writes every domain event to `.state/events.sqlite` (WAL, synchronous=NORMAL) before mirroring to opencode `SyncEvent`

## Locked Decisions

### Emission Mechanism

- **Pattern:** Post-commit fire-and-forget. After `db.commit()` in `SqliteEventStore.append()`, spawn an `asyncio.Task` that POSTs the event to opencode's HTTP API.
- **Non-blocking:** The `append()` call returns immediately after commit. The task runs in the background. The caller never waits for the mirror.
- **Task scope:** The fire-and-forget task is created via `asyncio.create_task()`. It catches all exceptions internally (never propagates to caller).
- **No background queue worker:** Phase 005 does NOT introduce a separate queue/buffer. The fire-and-forget task is created per `append()` call.

### Event Mapping

- **Direct passthrough:** The mirror uses the exact `event_type` string (e.g. `"state.step.advanced"`) as the SyncEvent type. No mapping table, no translation.
- **Payload shape:** The HTTP request body for `POST /sync/replay` mirrors opencode's `ReplayEvent` schema:
  ```json
  {
    "directory": "<project_root>",
    "events": [
      {
        "id": "<event ULID>",
        "aggregateID": "<aggregate_id>",
        "seq": <sequence_number>,
        "type": "<event_type>",
        "data": <event_data_dict>
      }
    ]
  }
  ```

### HTTP Endpoint

- **Endpoint:** `POST /sync/replay` (full URL: `http://{host}:{port}/sync/replay`)
- **Method:** HTTP POST with JSON body
- **Content-Type:** `application/json`
- **Array wrapper:** Always wrap the single event in a 1-element `events` array — the opencode API requires `events` to have `min(1)`.
- **Directory param:** Include the project root directory path in the body (the opencode endpoint validates `directory`).

### OpenCode URL Discovery

- **Strategy:** Search up from the current working directory for `opencode.json` or `.opencode/opencode.json`.
- **Config path reading order:**
  1. Check `./opencode.json` (project root)
  2. Check `./.opencode/opencode.json` (project .opencode directory)
  3. Walk up parent directories checking both filenames
  4. If found, read `server.port` and `server.hostname` from the config
- **Default fallback:** `http://127.0.0.1:17495` if no config file is found (opencode's default HTTP port).
- **Base path:** The URL is constructed as `http://{hostname}:{port}/sync/replay`.
- **No caching:** The URL is resolved on each fire-and-forget task invocation. Future optimization: cache and re-read on failure.
- **Env override (future):** Consider `STATE_OPENCODE_URL` env var in later phases if the config-based approach proves brittle.

### Failure & Retry

- **Retry policy:** Retry once immediately on any HTTP error (connection refused, timeout, non-2xx response).
- **On success:** Update the event row: `UPDATE events SET synced_to_opencode = 1 WHERE id = ?`. This is done via a new `get_connection()` (not the append's connection, which is already closed).
- **On permanent failure:** Leave `synced_to_opencode = 0`. Log a warning via structlog. The row will be picked up by Phase 006 (startup reconciliation).
- **Exception safety:** The fire-and-forget task catches all exceptions. No unhandled exception propagates to the event loop.
- **No exponential backoff in Phase 005:** Phase 006 provides comprehensive retry with backoff. Phase 005 keeps it simple — try twice, then leave for reconciliation.

### Emission Ordering

- **Best-effort:** Events are emitted as soon as their commit completes. No ordering guarantee across concurrent `append()` calls. The `seq` field in the SyncEvent payload allows the receiver to order events correctly.
- **Per-aggregate ordering:** Since `append()` is single-threaded via aiosqlite, events for the same aggregate are naturally ordered within the same process. No extra sequencing needed.

### Code Architecture

- **New module:** `src/state_core/sync_mirror.py` — `SyncEventMirror` class
- **Interface:**
  ```python
  class SyncEventMirror:
      async def emit(self, event_row: dict[str, Any]) -> None: ...
  ```
- **Integration point:** `SqliteEventStore.append()` gains an optional `mirror: SyncEventMirror | None = None` parameter. When provided, `emit()` is called fire-and-forget after commit.
- **Pattern:** The mirror is dependency-injected, not hard-coded into the store. This keeps the event store testable without HTTP mocking.
- **`SqliteEventStore` signature change:**
  ```python
  async def append(
      self,
      ...,
      mirror: SyncEventMirror | None = None,
  ) -> str:
  ```
- **HTTP client:** Use `httpx.AsyncClient` (already a dependency per `pyproject.toml`). One client instance shared across all fire-and-forget tasks.
- **Client lifecycle:** The `SyncEventMirror` owns the `httpx.AsyncClient`. It is created once and reused. The client does NOT use connection pooling limits beyond httpx defaults — each fire-and-forget task uses the shared client.

### Config Path Resolver

- **New helper:** `src/state_core/config.py` (or add to `sync_mirror.py`) — function to discover opencode config path:
  ```python
  def find_opencode_config(start_dir: Path | None = None) -> Path | None: ...
  ```
- **Search pattern:** Check `start_dir / "opencode.json"`, then `start_dir / ".opencode" / "opencode.json"`, then recurse to parent. Stop at filesystem root.
- **Config parsing:** Read JSON, extract `server.port` (int) and `server.hostname` (str). If port is 0 or missing, use default 17495.

### Plan Split (2 plans)

| Plan | Wave | Focus | Depends on |
|------|------|-------|------------|
| **A** | 1 | `SyncEventMirror` class + HTTP emission + config discovery + integration into `SqliteEventStore.append()` | Phase 004 |
| **B** | 2 | Comprehensive test suite: HTTP mocking via `pytest-httpx`, failure scenarios, config discovery tests, determinism | Plan A |

### Code Conventions

- Every `.py` file: `from __future__ import annotations` at top
- All SQL identifiers: `snake_case`
- HTTP request building: use `httpx.AsyncClient.post(url, json=body)`
- URL construction: `f"http://{hostname}:{port}/sync/replay"`
- `async with client:` for fire-and-forget calls
- Docstrings on all public methods
- Config file paths: use `pathlib.Path`, not `os.path`
- Structlog for logging: `log = structlog.get_logger(__name__)`
- Per-file module-level `__all__` if more than one public symbol

### Testing Approach

- Use `pytest-httpx` to mock `POST /sync/replay` endpoint
- Use `tmp_path` fixture + `monkeypatch` for config file testing
- Test basic emission: append → mock returns 200 → verify synced_to_opencode=1
- Test failure: append → mock returns 500 → verify synced_to_opencode=0 (once retry also fails)
- Test retry: append → first call fails, second succeeds → verify synced_to_opencode=1
- Test config discovery: create opencode.json in tmp_path → verify URL resolution
- Test config fallback: no config file → verify default URL
- Test `SqliteEventStore` with mirror injected → verify fire-and-forget semantics (task runs without blocking append)
- Test determinism: same event produces same HTTP request body

### P0 Pitfalls Owned

- **EVT-01 (dual-write):** Phase 005 is the mirror half. The invariant is: every event committed to SQLite has a corresponding fire-and-forget attempt. Success/failure is recorded in `synced_to_opencode`. Phase 006 ensures eventual consistency.
- **No data loss:** Even if the fire-and-forget task fails (opencode unreachable, network error), the event is safely stored in SQLite with `synced_to_opencode=0`. No data is lost — only mirror latency is affected.

## Research Sources Used

- `.planning/milestones/v1/ROADMAP.md` — Phase 005 scope, dependency on Phase 004, EVT-01 requirement
- `.planning/research/ARCHITECTURE.md` — §5.2 (dual-write contract with SyncEvent mirror)
- `src/state_core/events.py` — existing `SqliteEventStore.append()`, `read_stream()` with `synced_to_opencode` column
- `src/state_core/database.py` — connection factory pattern, `STATE_DB_PATH` env var pattern
- `state-inputs/opencode/packages/opencode/src/server/routes/instance/sync.ts` — `POST /sync/replay` endpoint: validates `{directory, events[]}`, calls `SyncEvent.replayAll()`
- `state-inputs/opencode/packages/opencode/src/sync/index.ts` — `SyncEvent.replayAll()` expects array of `{id, aggregateID, seq, type, data}`
- `state-inputs/opencode-extension-surface.md` — §23 Sync/Event Sourcing, HTTP endpoint inventory
- `state-inputs/opencode/packages/opencode/src/cli/network.ts` — config-based port/hostname resolution from `opencode.json` `server` section
