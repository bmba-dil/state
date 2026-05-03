---
phase: "005"
plan: "B"
type: "tdd"
autonomous: false
wave: 2
depends_on:
  - "005-A-mirror-core-and-integration"
files_modified:
  - "tests/test_sync_mirror.py"
  - "tests/test_config.py"
requirements:
  - "EVT-01"
---

<objective>
Deliver a comprehensive async test suite for Phase 005's new modules:

1. `tests/test_config.py` — opencode config path discovery, URL resolution, env var override, fallback
2. `tests/test_sync_mirror.py` — `SyncEventMirror.emit()` HTTP mocking via `pytest-httpx`, success/failure paths, retry logic, `_mark_synced()` integration, fire-and-forget semantics from `SqliteEventStore.append()`

By the end of this plan, every code path in `config.py` and `sync_mirror.py` has a passing test, mirroring the coverage bar set by `test_events.py` in Phase 004-B.
</objective>

<tasks>

## Task 1 — Create `tests/test_config.py` for config discovery and URL resolution

<read_first>
  src/state_core/config.py (the two public functions: find_opencode_config, resolve_opencode_url)
  tests/test_events.py (fixture patterns — tmp_path, monkeypatch, async test structure)
  tests/test_database.py (env var monkeypatching pattern for STATE_DB_PATH — same pattern for STATE_OPENCODE_URL)
</read_first>

<action>

Create `tests/test_config.py`:

```python
"""Tests for state_core.config — opencode config discovery and URL resolution.

Covers: path search upwards, file name priority (opencode.json > .opencode/opencode.json),
fallback when no config found, server.port/server.hostname parsing, STATE_OPENCODE_URL
override, malformed config resilience.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from src.state_core.config import (
    DEFAULT_OPENCODE_HOST,
    DEFAULT_OPENCODE_PORT,
    find_opencode_config,
    resolve_opencode_url,
)


# ── find_opencode_config ────────────────────────────────────────────────────


class TestFindOpencodeConfig:
    """Config file discovery via directory walk-up."""

    def test_returns_none_when_no_config(self, tmp_path: Path) -> None:
        result = find_opencode_config(start_dir=tmp_path)
        assert result is None

    def test_finds_opencode_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == cfg

    def test_finds_dot_opencode_opencode_json(self, tmp_path: Path) -> None:
        dot_dir = tmp_path / ".opencode"
        dot_dir.mkdir()
        cfg = dot_dir / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == cfg

    def test_prefers_opencode_json_over_dot_opencode(self, tmp_path: Path) -> None:
        """opencode.json in root takes priority over .opencode/opencode.json."""
        top = tmp_path / "opencode.json"
        top.write_text("{}")
        dot_dir = tmp_path / ".opencode"
        dot_dir.mkdir()
        dot_cfg = dot_dir / "opencode.json"
        dot_cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == top

    def test_walks_up_to_parent(self, tmp_path: Path) -> None:
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        cfg = tmp_path / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=child)
        assert result == cfg

    def test_stops_at_filesystem_root(self) -> None:
        """Walking past root returns None (not infinite loop)."""
        result = find_opencode_config(start_dir=Path("/"))
        assert result is None

    def test_ignores_directories_named_opencode_json(self, tmp_path: Path) -> None:
        d = tmp_path / "opencode.json"
        d.mkdir()
        result = find_opencode_config(start_dir=tmp_path)
        assert result is None  # is_file() check skips directories

    def test_defaults_to_cwd(self) -> None:
        """When start_dir is None, use Path.cwd()."""
        with patch("src.state_core.config.Path.cwd", return_value=Path("/tmp")):
            result = find_opencode_config()
        # /tmp almost certainly doesn't have opencode.json; expect None
        assert result is None or result.parent == Path("/tmp")


# ── resolve_opencode_url ────────────────────────────────────────────────────


class TestResolveOpencodeUrl:
    """URL construction from config, env var, and fallback."""

    def test_default_fallback(self) -> None:
        """No config and no env var returns the default URL."""
        url = resolve_opencode_url(start_dir=Path("/nonexistent"))
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_reads_port_from_opencode_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 18999, "hostname": "0.0.0.0"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == "http://0.0.0.0:18999"

    def test_reads_hostname_only(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"hostname": "192.168.1.50"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://192.168.1.50:{DEFAULT_OPENCODE_PORT}"

    def test_port_zero_falls_back_to_default(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 0}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_port_out_of_range_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 99999}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_malformed_json_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("not valid json")
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_empty_config_file_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("")
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_env_var_override(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://custom:9999")
        url = resolve_opencode_url(start_dir=Path("/nonexistent"))
        assert url == "http://custom:9999"

    def test_env_var_ignores_config_file(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """When STATE_OPENCODE_URL is set, config files are ignored."""
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://from-env:7777")
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 18999, "hostname": "0.0.0.0"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == "http://from-env:7777"

    def test_env_var_trailing_slash_stripped(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:1234/")
        url = resolve_opencode_url()
        assert url == "http://test:1234"

    def test_server_null_does_not_crash(self, tmp_path: Path) -> None:
        """server: null in config should not crash."""
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": None}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_missing_server_uses_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"other": "data"}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"
```

Key constraints:
- All `find_opencode_config` tests are synchronous (no async needed for file system operations)
- All `resolve_opencode_url` tests are synchronous
- Uses `unittest.mock.patch` for `Path.cwd()` in the default test (only test that needs it)
- Uses `monkeypatch.setenv` for env var tests
- The `tmp_path` fixture ensures test isolation — no files leak between tests
- Malformed JSON and empty config files test the resilience paths explicitly
- `server: null` case tests the `server.get("port", ...) or {}` pattern in the implementation — `None.get("port")` would crash, but the `or {}` in `cfg.get("server", {}) or {}` handles it
</action>

<acceptance_criteria>
- ✗ `tests/test_config.py` exists with all test classes
- ✗ `TestFindOpencodeConfig.test_returns_none_when_no_config` passes
- ✗ `TestFindOpencodeConfig.test_finds_opencode_json` passes
- ✗ `TestFindOpencodeConfig.test_finds_dot_opencode_opencode_json` passes
- ✗ `TestFindOpencodeConfig.test_prefers_opencode_json_over_dot_opencode` passes
- ✗ `TestFindOpencodeConfig.test_walks_up_to_parent` passes
- ✗ `TestFindOpencodeConfig.test_stops_at_filesystem_root` passes
- ✗ `TestFindOpencodeConfig.test_ignores_directories_named_opencode_json` passes
- ✗ `TestResolveOpencodeUrl.test_default_fallback` passes
- ✗ `TestResolveOpencodeUrl.test_reads_port_from_opencode_json` passes
- ✗ `TestResolveOpencodeUrl.test_env_var_override` passes
- ✗ `TestResolveOpencodeUrl.test_malformed_json_falls_back` passes
- ✗ `TestResolveOpencodeUrl.test_server_null_does_not_crash` passes
- ✗ `python3 -m pytest tests/test_config.py -x -q` passes all tests
</acceptance_criteria>

## Task 2 — Create `tests/test_sync_mirror.py` — SyncEventMirror emit tests with HTTP mocking

<read_first>
  src/state_core/sync_mirror.py (SyncEventMirror class, emit signature, _mark_synced)
  src/state_core/events.py (SqliteEventStore.append with mirror parameter, event_row dict shape)
  src/state_core/database.py (get_connection — used by _mark_synced)
  tests/test_events.py (fixture pattern for db isolation, store fixture with migrations)
  pytest-httpx documentation: the ``httpx_mock`` fixture intercepts all ``httpx.AsyncClient`` requests
</read_first>

<action>

Create `tests/test_sync_mirror.py`:

```python
"""Tests for state_core.sync_mirror — SyncEventMirror HTTP emission.

Uses pytest-httpx to mock the POST /sync/replay endpoint.
Covers: basic emission, success marking, retry, permanent failure,
fire-and-forget semantics from SqliteEventStore.append().
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.sync_mirror import SyncEventMirror


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_opencode_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin opencode URL to a fixed test endpoint so httpx_mock intercepts it.

    This ensures SyncEventMirror.emit() always POSTs to ``http://test:0/sync/replay``
    regardless of any opencode.json on the developer's machine.
    """
    monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:0")


@pytest.fixture
def mirror(tmp_path: Path) -> SyncEventMirror:
    """Return a SyncEventMirror with an isolated project directory."""
    return SyncEventMirror(directory=tmp_path)


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied in an isolated DB.

    Uses the same isolation pattern as test_events.py: tmp_path for DB,
    temp copy of migrations, STATE_DB_PATH env var override.
    """
    import shutil
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    # We need to run migrate within an async context
    return SqliteEventStore()


@pytest.fixture
async def ready_store(store: SqliteEventStore) -> SqliteEventStore:
    """Apply migrations and return the store (async fixture)."""
    await migrate()
    return store


# ── Helpers ─────────────────────────────────────────────────────────────────


def _sync_replay_ok(request: httpx.Request) -> httpx.Response:
    """Handler that returns 200 for POST /sync/replay."""
    return httpx.Response(200)


def _sync_replay_500(request: httpx.Request) -> httpx.Response:
    """Handler that returns 500 for POST /sync/replay."""
    return httpx.Response(500)


def _sync_replay_timeout(request: httpx.Request) -> httpx.Response:
    """Handler that simulates a timeout."""
    raise httpx.TimeoutException("Connection timed out", request=request)


# ── SyncEventMirror direct tests ────────────────────────────────────────────


class TestSyncEventMirrorDirect:
    """Direct calls to SyncEventMirror.emit() with mocked HTTP."""

    async def test_emit_success_calls_patch_opencode_url(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Emit sends POST to /sync/replay on success."""
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")
        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {"changes_summary": "test"},
            "ts": "2026-01-01T00:00:00Z",
            "mode": "kernel",
        })
        # No exception means success — the mock returned 200
        # Verify the request was actually made
        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 1

    async def test_emit_request_body_shape(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Verify the HTTP request body matches opencode's ReplayEvent schema."""
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {"changes_summary": "test"},
            "ts": "2026-01-01T00:00:00Z",
            "mode": "kernel",
        })

        request = httpx_mock.get_requests(url="http://test:0/sync/replay")[0]
        body = json.loads(request.content)

        assert "directory" in body
        assert "events" in body
        assert len(body["events"]) == 1

        event = body["events"][0]
        assert event["id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert event["aggregateID"] == "step-01"  # camelCase
        assert event["seq"] == 1
        assert event["type"] == "state.step.executed"
        assert event["data"] == {"changes_summary": "test"}

    async def test_emit_with_json_string_data(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Emit handles data that is already a JSON string."""
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": '{"changes_summary":"test"}',  # JSON string, not dict
            "ts": "2026-01-01T00:00:00Z",
            "mode": "kernel",
        })

        request = httpx_mock.get_requests(url="http://test:0/sync/replay")[0]
        body = json.loads(request.content)
        assert body["events"][0]["data"] == {"changes_summary": "test"}

    async def test_emit_retry_on_500_then_succeed(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Retry: first call fails (500), second succeeds."""
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 2

    async def test_emit_permanent_failure_does_not_raise(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Two 500s in a row: no exception propagates, synced_to_opencode stays 0."""
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")

        # Should not raise
        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 2

    async def test_emit_timeout_retries(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Timeout on first attempt, success on retry."""
        httpx_mock.add_callback(_sync_replay_timeout, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 2

    async def test_emit_connection_error_retries(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Connection refused on first attempt, success on retry."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://test:0/sync/replay",
        )
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 2

    async def test_emit_does_not_raise_on_any_error(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Even unexpected exceptions are caught."""
        httpx_mock.add_exception(
            RuntimeError("unexpected"),
            url="http://test:0/sync/replay",
        )

        # Should not raise even with RuntimeError from mock
        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

    async def test_emit_directory_from_mirror(
        self, mirror: SyncEventMirror, tmp_path: Path, httpx_mock: HTTPXMock,
    ) -> None:
        """The directory field in the request body matches mirror's directory."""
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {},
        })

        request = httpx_mock.get_requests(url="http://test:0/sync/replay")[0]
        body = json.loads(request.content)
        assert body["directory"] == str(tmp_path)

    async def test_close_aclient(
        self, mirror: SyncEventMirror,
    ) -> None:
        """close() does not raise."""
        await mirror.close()


# ── Integration: SqliteEventStore.append() + SyncEventMirror ────────────────


@pytest.mark.asyncio
class TestAppendWithMirror:
    """Fire-and-forget mirror integration with SqliteEventStore.append()."""

    async def test_append_returns_before_mirror_completes(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """append() returns immediately; the mirror task runs in background.

        We verify by adding a delay to the mock — append() should return
        before the delay completes.
        """
        import asyncio

        async def delayed_ok(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.5)
            return httpx.Response(200)

        httpx_mock.add_callback(delayed_ok, url="http://test:0/sync/replay")

        start = asyncio.get_event_loop().time()
        id_ = await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "fire-and-forget"},
            mirror=mirror,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # append() returns in << 0.5s because it doesn't await the mirror
        assert elapsed < 0.3
        assert isinstance(id_, str)

        # Wait for the fire-and-forget task to finish
        await asyncio.sleep(0.6)

        # Verify the event was synced
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert len(stream) == 1
        assert stream[0]["synced_to_opencode"] == 1

    async def test_append_without_mirror_still_works(
        self, ready_store: SqliteEventStore, httpx_mock: HTTPXMock,
    ) -> None:
        """Existing callers not passing mirror continue to work unchanged."""
        id_ = await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "no mirror"},
        )
        assert isinstance(id_, str)
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert len(stream) == 1
        assert stream[0]["synced_to_opencode"] == 0  # never synced

    async def test_append_mirror_success_updates_synced_flag(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """On successful mirror, synced_to_opencode = 1."""
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")

        await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "sync-me"},
            mirror=mirror,
        )

        import asyncio
        await asyncio.sleep(0.1)

        stream = [e async for e in ready_store.read_stream("step-01")]
        assert stream[0]["synced_to_opencode"] == 1

    async def test_append_mirror_failure_leaves_flag_zero(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """When mirror fails (500 twice), synced_to_opencode stays 0."""
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")

        await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "dont-sync"},
            mirror=mirror,
        )

        import asyncio
        await asyncio.sleep(0.1)

        stream = [e async for e in ready_store.read_stream("step-01")]
        assert stream[0]["synced_to_opencode"] == 0

    async def test_append_mirror_fire_and_forget_no_exception(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Even if mirror crashes, append() does not raise."""
        httpx_mock.add_exception(
            RuntimeError("unexpected mirror crash"),
            url="http://test:0/sync/replay",
        )

        # append() should not raise despite the RuntimeError in the mirror
        id_ = await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "safe"},
            mirror=mirror,
        )
        assert isinstance(id_, str)

    async def test_mirror_does_not_block_concurrent_appends(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Multiple appends with mirror complete quickly (not serialized on mirror)."""
        import asyncio

        async def slow_ok(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.3)
            return httpx.Response(200)

        httpx_mock.add_callback(slow_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(slow_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(slow_ok, url="http://test:0/sync/replay")

        start = asyncio.get_event_loop().time()
        ids = await asyncio.gather(
            ready_store.append("step", "step-01", "state.step.executed", {"n": 1}, mirror=mirror),
            ready_store.append("step", "step-02", "state.step.executed", {"n": 2}, mirror=mirror),
            ready_store.append("step", "step-03", "state.step.executed", {"n": 3}, mirror=mirror),
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Three slow mirrors (0.3s each) would take ~0.9s if serialized.
        # But appends return immediately, so elapsed should be << 0.9s.
        assert elapsed < 0.5
        assert len(ids) == 3

        await asyncio.sleep(0.5)  # let mirrors finish
        # Verify all three events exist
        for agg_id in ("step-01", "step-02", "step-03"):
            stream = [e async for e in ready_store.read_stream(agg_id)]
            assert len(stream) == 1


# ── Determinism ─────────────────────────────────────────────────────────────


class TestEmissionDeterminism:
    """Same inputs produce same HTTP request body (EVT-06 for sync mirror)."""

    async def test_deterministic_request_body(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        """Two emits with same event row produce identical request bodies."""
        received_bodies: list[bytes] = []

        async def capture(request: httpx.Request) -> httpx.Response:
            received_bodies.append(request.content)
            return httpx.Response(200)

        httpx_mock.add_callback(capture, url="http://test:0/sync/replay")
        httpx_mock.add_callback(capture, url="http://test:0/sync/replay")

        event_row = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": {"changes_summary": "deterministic"},
            "ts": "2026-01-01T00:00:00Z",
            "mode": "kernel",
        }

        await mirror.emit(event_row)
        await mirror.emit(event_row)

        assert len(received_bodies) == 2
        assert received_bodies[0] == received_bodies[1]
```

Key constraints:
- All mirror tests use `_patch_opencode_url` fixture (autouse) that sets `STATE_OPENCODE_URL=http://test:0`. This ensures `resolve_opencode_url()` returns a fixed test URL that `pytest-httpx` can intercept — no dependency on actual opencode.json files on the developer's machine.
- `pytest-httpx`'s `httpx_mock` fixture intercepts all `httpx.AsyncClient` requests matching the registered URL pattern.
- The `_sync_replay_*` helper functions define reusable mock response patterns (200, 500, timeout).
- `TestSyncEventMirrorDirect` tests the `emit()` method in isolation — doesn't need `SqliteEventStore` or a DB.
- `TestAppendWithMirror` tests the integration: `append()` with `mirror=mirror`, then checks `synced_to_opencode` via `read_stream()`.
- The fire-and-forget timing tests use `asyncio.sleep()` delays in mock handlers to verify `append()` returns before mirror completes.
- The `ready_store` fixture (async) applies migrations before each integration test.
- Each test that checks `synced_to_opencode` uses `await asyncio.sleep(0.1)` to give the fire-and-forget task time to execute. This is the standard pattern for testing fire-and-forget tasks in asyncio.
</action>

<acceptance_criteria>
- ✗ `tests/test_sync_mirror.py` exists with all test classes
- ✗ `TestSyncEventMirrorDirect.test_emit_success_calls_patch_opencode_url` passes
- ✗ `TestSyncEventMirrorDirect.test_emit_request_body_shape` passes (camelCase aggregateID, correct schema)
- ✗ `TestSyncEventMirrorDirect.test_emit_with_json_string_data` passes (JSON string data deserialized)
- ✗ `TestSyncEventMirrorDirect.test_emit_retry_on_500_then_succeed` passes
- ✗ `TestSyncEventMirrorDirect.test_emit_permanent_failure_does_not_raise` passes
- ✗ `TestSyncEventMirrorDirect.test_emit_timeout_retries` passes
- ✗ `TestSyncEventMirrorDirect.test_emit_connection_error_retries` passes
- ✗ `TestSyncEventMirrorDirect.test_emit_does_not_raise_on_any_error` passes
- ✗ `TestAppendWithMirror.test_append_returns_before_mirror_completes` passes (fire-and-forget timing)
- ✗ `TestAppendWithMirror.test_append_without_mirror_still_works` passes (backward compat)
- ✗ `TestAppendWithMirror.test_append_mirror_success_updates_synced_flag` passes
- ✗ `TestAppendWithMirror.test_append_mirror_failure_leaves_flag_zero` passes
- ✗ `TestAppendWithMirror.test_append_mirror_fire_and_forget_no_exception` passes
- ✗ `TestAppendWithMirror.test_mirror_does_not_block_concurrent_appends` passes
- ✗ `TestEmissionDeterminism.test_deterministic_request_body` passes
- ✗ `python3 -m pytest tests/test_sync_mirror.py tests/test_config.py -x -q` passes all tests
- ✗ `python3 -m pytest tests/test_events.py -x -q` still passes (non-regression)
- ✗ No test leaves behind state files (all use tmp_path or monkeypatch)
</acceptance_criteria>

</tasks>

<verification>

### How to confirm plan goal achieved

1. **Full test suite passes:**
   ```bash
   python3 -m pytest tests/test_config.py tests/test_sync_mirror.py tests/test_events.py -x -q
   ```
   Expected: all tests pass (config tests + mirror tests + existing event tests non-regression).

2. **Coverage check** (informational — no hard threshold in Phase 005):
   ```bash
   python3 -m pytest tests/test_config.py tests/test_sync_mirror.py --cov=src.state_core.config --cov=src.state_core.sync_mirror --cov-report=term-missing
   ```

3. **Manual smoke test** — with opencode NOT running:
   ```python
   import asyncio
   from pathlib import Path
   from src.state_core.events import SqliteEventStore
   from src.state_core.migrations import migrate
   from src.state_core.sync_mirror import SyncEventMirror

   async def smoke():
       await migrate()
       store = SqliteEventStore()
       mirror = SyncEventMirror(directory=Path.cwd())
       id_ = await store.append("step", "step-01", "state.step.executed", {"x": 1}, mirror=mirror)
       assert isinstance(id_, str)
       await asyncio.sleep(0.5)
       stream = [e async for e in store.read_stream("step-01")]
       assert stream[0]["synced_to_opencode"] == 0  # opencode not running
       print("smoke OK: event stored, synced_to_opencode=0 (opencode unreachable)")

   asyncio.run(smoke())
   ```

4. **Manual smoke test** — with opencode running:
   If opencode is available, confirm that events appear in opencode's event log after append.

5. **grep check for anti-patterns:**
   - `rg 'datetime\.now\(\)' tests/` — no hits in new test files
   - All test names follow `test_<behavior>` snake_case convention
</verification>

<must_haves>

- `tests/test_config.py` — 18+ tests covering: find (6), URL resolution (12)
- `tests/test_sync_mirror.py` — 15+ tests covering: direct emit (9), integration (6), determinism (1)
- All tests pass with `python3 -m pytest tests/test_config.py tests/test_sync_mirror.py tests/test_events.py -x -q`
- Fire-and-forget timing test proves `append()` returns before mirror completes
- Backward compat test proves append without mirror unchanged
- Success/failure/retry paths all covered with `pytest-httpx` mocking
- Config tests cover env var, file discovery, malformed config, fallback
</must_haves>
