from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.sync_mirror import SyncEventMirror


@pytest.fixture(autouse=True)
def _patch_opencode_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:0")


@pytest.fixture
def mirror(tmp_path: Path) -> SyncEventMirror:
    return SyncEventMirror(directory=tmp_path)


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteEventStore:
    import shutil
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)
    return SqliteEventStore()


@pytest.fixture
async def ready_store(store: SqliteEventStore) -> SqliteEventStore:
    await migrate()
    return store


def _sync_replay_ok(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200)


def _sync_replay_500(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(500)


def _sync_replay_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.TimeoutException("Connection timed out", request=request)


@pytest.mark.asyncio
class TestSyncEventMirrorDirect:
    async def test_emit_success_calls_patch_opencode_url(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
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
        requests = httpx_mock.get_requests(url="http://test:0/sync/replay")
        assert len(requests) == 1

    async def test_emit_request_body_shape(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
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
        assert event["aggregateID"] == "step-01"
        assert event["seq"] == 1
        assert event["type"] == "state.step.executed"
        assert event["data"] == {"changes_summary": "test"}

    async def test_emit_with_json_string_data(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")
        await mirror.emit({
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "aggregate_id": "step-01",
            "seq": 1,
            "type": "state.step.executed",
            "data": '{"changes_summary":"test"}',
            "ts": "2026-01-01T00:00:00Z",
            "mode": "kernel",
        })
        request = httpx_mock.get_requests(url="http://test:0/sync/replay")[0]
        body = json.loads(request.content)
        assert body["events"][0]["data"] == {"changes_summary": "test"}

    async def test_emit_retry_on_500_then_succeed(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
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
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
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
        httpx_mock.add_exception(
            RuntimeError("unexpected"),
            url="http://test:0/sync/replay",
        )
        httpx_mock.add_exception(
            RuntimeError("unexpected again"),
            url="http://test:0/sync/replay",
        )
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
        await mirror.close()


@pytest.mark.asyncio
class TestAppendWithMirror:
    async def test_append_returns_before_mirror_completes(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        async def delayed_ok(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.5)
            return httpx.Response(200)

        import asyncio
        httpx_mock.add_callback(delayed_ok, url="http://test:0/sync/replay")
        start = asyncio.get_event_loop().time()
        id_ = await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "fire-and-forget"},
            mirror=mirror,
        )
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.3
        assert isinstance(id_, str)
        await asyncio.sleep(0.6)
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert len(stream) == 1
        assert stream[0]["synced_to_opencode"] == 1

    async def test_append_without_mirror_still_works(
        self, ready_store: SqliteEventStore, httpx_mock: HTTPXMock,
    ) -> None:
        id_ = await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "no mirror"},
        )
        assert isinstance(id_, str)
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert len(stream) == 1
        assert stream[0]["synced_to_opencode"] == 0

    async def test_append_mirror_success_updates_synced_flag(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        import asyncio
        httpx_mock.add_callback(_sync_replay_ok, url="http://test:0/sync/replay")
        await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "sync-me"},
            mirror=mirror,
        )
        await asyncio.sleep(0.1)
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert stream[0]["synced_to_opencode"] == 1

    async def test_append_mirror_failure_leaves_flag_zero(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        import asyncio
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_sync_replay_500, url="http://test:0/sync/replay")
        await ready_store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": "dont-sync"},
            mirror=mirror,
        )
        await asyncio.sleep(0.1)
        stream = [e async for e in ready_store.read_stream("step-01")]
        assert stream[0]["synced_to_opencode"] == 0

    async def test_append_mirror_fire_and_forget_no_exception(
        self, ready_store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        httpx_mock.add_exception(
            RuntimeError("unexpected mirror crash"),
            url="http://test:0/sync/replay",
        )
        httpx_mock.add_exception(
            RuntimeError("unexpected mirror crash again"),
            url="http://test:0/sync/replay",
        )
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
        assert elapsed < 0.5
        assert len(ids) == 3
        await asyncio.sleep(0.5)
        for agg_id in ("step-01", "step-02", "step-03"):
            stream = [e async for e in ready_store.read_stream(agg_id)]
            assert len(stream) == 1


@pytest.mark.asyncio
class TestEmissionDeterminism:
    async def test_deterministic_request_body(
        self, mirror: SyncEventMirror, httpx_mock: HTTPXMock,
    ) -> None:
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
