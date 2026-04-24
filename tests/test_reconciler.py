"""Tests for state_core.reconciler — StartupReconciler.

Covers: lifecycle (start/stop), reconcile_once with real DB,
sweep loop idle suppression, exponential backoff calculation,
and edge cases like double-start and concurrent-failure reset.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate
from src.state_core.reconciler import (
    BACKOFF_INITIAL,
    BACKOFF_MAX,
    BACKOFF_MULTIPLIER,
    StartupReconciler,
)
from src.state_core.sync_mirror import SyncEventMirror

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_opencode_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:0")


@pytest.fixture
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


@pytest.fixture
def mirror(tmp_path: Path) -> SyncEventMirror:
    return SyncEventMirror(directory=tmp_path)


# ── Helpers ────────────────────────────────────────────────────────────────


async def _append_unsynced(
    store: SqliteEventStore, n: int = 1,
) -> list[str]:
    """Append *n* events with no mirror so synced_to_opencode stays 0.

    Returns the list of event IDs.
    """
    ids: list[str] = []
    for i in range(n):
        id_ = await store.append(
            "step", "step-01", "state.step.executed",
            {"changes_summary": f"event-{i}"},
        )
        ids.append(id_)
    return ids


def _ok(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200)


def _server_error(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(500)


# ── StartupReconciler tests ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestStartupReconcilerLifecycle:
    """Start/stop lifecycle with no-ops."""

    async def test_start_stop(self, store: SqliteEventStore, tmp_path: Path) -> None:
        mirror = SyncEventMirror(directory=tmp_path)
        reconciler = StartupReconciler(store, mirror, sweep_interval=0.01)
        await reconciler.start()
        assert reconciler._task is not None
        assert not reconciler._task.done()
        await reconciler.stop()
        assert reconciler._task is None

    async def test_double_start_is_noop(
        self, store: SqliteEventStore, tmp_path: Path,
    ) -> None:
        mirror = SyncEventMirror(directory=tmp_path)
        reconciler = StartupReconciler(store, mirror)
        await reconciler.start()
        task_1 = reconciler._task
        await reconciler.start()
        task_2 = reconciler._task
        # Should be the same task (no-op on second start)
        assert task_1 is task_2
        await reconciler.stop()

    async def test_double_stop_is_noop(
        self, store: SqliteEventStore, tmp_path: Path,
    ) -> None:
        mirror = SyncEventMirror(directory=tmp_path)
        reconciler = StartupReconciler(store, mirror)
        await reconciler.start()
        await reconciler.stop()
        assert reconciler._task is None
        # Second stop should not crash
        await reconciler.stop()
        assert reconciler._task is None

    async def test_stop_without_start_is_noop(
        self, store: SqliteEventStore, tmp_path: Path,
    ) -> None:
        mirror = SyncEventMirror(directory=tmp_path)
        reconciler = StartupReconciler(store, mirror)
        # stop() before any start() should be safe
        await reconciler.stop()
        assert reconciler._task is None


@pytest.mark.asyncio
class TestReconcileOnce:
    """_reconcile_once behaviour with real event store data."""

    async def test_no_unsynced_events_returns_zero(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        count = await reconciler._reconcile_once()
        assert count == 0

    async def test_reconcile_emits_events_and_returns_count(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        # 3 events, each succeeds on first attempt → 3 requests total
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        ids = await _append_unsynced(store, 3)
        assert len(ids) == 3

        reconciler = StartupReconciler(store, mirror)
        count = await reconciler._reconcile_once()
        assert count == 3

        remaining = await store.count_unsynced_events()
        assert remaining == 0

    async def test_reconcile_mirror_failure_returns_zero(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        # 2 events × 2 retries each → 4 requests total, all 500
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")

        await _append_unsynced(store, 2)

        reconciler = StartupReconciler(store, mirror)
        count = await reconciler._reconcile_once()
        assert count == 0

        remaining = await store.count_unsynced_events()
        assert remaining == 2

    async def test_reconcile_resets_failure_count_on_success(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        # 1 event, 1 request
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        await _append_unsynced(store, 1)

        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 5
        count = await reconciler._reconcile_once()
        assert count == 1
        assert reconciler._consecutive_failures == 0

    async def test_reconcile_all_fail_does_not_reset_failures(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        # 2 events × 2 retries = 4 requests
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")

        await _append_unsynced(store, 2)

        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 3
        count = await reconciler._reconcile_once()
        assert count == 0
        # No events succeeded → failures NOT reset
        assert reconciler._consecutive_failures == 3

    async def test_reconcile_partial_failure(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """First event succeeds, second fails both retries, third succeeds."""
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_server_error, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        await _append_unsynced(store, 3)

        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 3
        count = await reconciler._reconcile_once()
        # Events 1 and 3 succeeded → count = 2
        assert count == 2
        # At least one event succeeded → failures reset
        assert reconciler._consecutive_failures == 0

    async def test_reconcile_with_json_string_data(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        data: dict[str, Any] = {"changes_summary": "nested", "items": [1, 2, 3]}
        await store.append(
            "step", "step-01", "state.step.executed",
            data,
        )
        reconciler = StartupReconciler(store, mirror)
        count = await reconciler._reconcile_once()
        assert count == 1

        request = httpx_mock.get_requests(url="http://test:0/sync/replay")[0]
        body = json.loads(request.content)
        assert body["events"][0]["data"] == data


@pytest.mark.asyncio
class TestBackoffDelay:
    """Exponential backoff calculation."""

    async def test_first_failure_returns_initial(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 1
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_INITIAL  # 1.0

    async def test_second_failure_doubles(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 2
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_INITIAL * BACKOFF_MULTIPLIER  # 2.0

    async def test_third_failure_quadruples(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 3
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_INITIAL * (BACKOFF_MULTIPLIER ** 2)  # 4.0

    async def test_backoff_capped_at_max(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        # At 7 consecutive failures: 1.0 * 2^6 = 64.0 > 60.0
        reconciler._consecutive_failures = 7
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_MAX  # 60.0

    async def test_backoff_stays_capped(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        reconciler = StartupReconciler(store, mirror)
        # Many failures should still cap at BACKOFF_MAX
        reconciler._consecutive_failures = 100
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_MAX  # 60.0

    async def test_zero_failures_negative_index(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        """At 0 failures, the expression becomes 1.0 * 2.0^-1 = 0.5.
        This is fine since _compute_backoff_delay is only called
        after incrementing _consecutive_failures, so 0 never occurs
        in practice. We document the mathematical behaviour.
        """
        reconciler = StartupReconciler(store, mirror)
        reconciler._consecutive_failures = 0
        delay = reconciler._compute_backoff_delay()
        assert delay == BACKOFF_INITIAL * (BACKOFF_MULTIPLIER ** -1)  # 0.5


@pytest.mark.asyncio
class TestSweepLoop:
    """Sweep loop integration tests — use short sweep intervals."""

    async def test_sweep_loop_idle_suppression(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
    ) -> None:
        """When there are no unsynced events, the loop sleeps and does nothing."""
        reconciler = StartupReconciler(store, mirror, sweep_interval=0.01)
        await reconciler.start()
        # Let the loop run a few idle cycles
        await asyncio.sleep(0.05)
        await reconciler.stop()
        # Success = no crash, clean stop
        assert reconciler._task is None

    async def test_sweep_loop_emits_unsynced_on_start(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Unsynced events at start are reconciled immediately by start()."""
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        await _append_unsynced(store, 1)

        reconciler = StartupReconciler(store, mirror, sweep_interval=1.0)
        await reconciler.start()

        # Immediate reconcile from start() should have handled it
        remaining = await store.count_unsynced_events()
        assert remaining == 0

        await reconciler.stop()

    async def test_sweep_loop_handles_backoff(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """When events keep failing, the loop backoffs and increments failures."""
        # Register enough optional responses to cover all requests during window.
        # With 0.1s sweep and 0.35s sleep: start() uses 2 (retries for 1 event),
        # loop tick ~0.1s uses 2 more. We allow 20 to be safe.
        for _ in range(20):
            httpx_mock.add_response(
                url="http://test:0/sync/replay",
                status_code=500,
                is_optional=True,
            )

        await _append_unsynced(store, 1)

        reconciler = StartupReconciler(store, mirror, sweep_interval=0.1)
        await reconciler.start()
        # Give it time to hit the backoff path
        await asyncio.sleep(0.35)
        await reconciler.stop()

        # Events should still be unsynced
        remaining = await store.count_unsynced_events()
        assert remaining == 1

        # The loop should have incremented failures
        assert reconciler._consecutive_failures > 0


@pytest.mark.asyncio
class TestIntegrationReconcileAndAppend:
    """End-to-end: append events, start reconciler, verify full cycle."""

    async def test_full_cycle(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        # 3 events, each needs 1 request
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        ids = await _append_unsynced(store, 3)
        assert len(ids) == 3

        # Start reconciler — it does _reconcile_once immediately
        reconciler = StartupReconciler(store, mirror, sweep_interval=1.0)
        await reconciler.start()

        # All events should be synced now
        remaining = await store.count_unsynced_events()
        assert remaining == 0

        await reconciler.stop()

    async def test_append_after_reconciler_starts(
        self, store: SqliteEventStore, mirror: SyncEventMirror,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Events appended while reconciler is running are picked up by sweep."""
        # Register exactly 3 callbacks: 1 for initial reconcile, 2 for sweep
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")
        httpx_mock.add_callback(_ok, url="http://test:0/sync/replay")

        await _append_unsynced(store, 1)

        reconciler = StartupReconciler(store, mirror, sweep_interval=0.1)
        await reconciler.start()

        # First event should be synced by start()'s immediate reconcile
        remaining = await store.count_unsynced_events()
        assert remaining == 0

        # Add more events while reconciler is running
        await _append_unsynced(store, 2)

        # Let the sweep loop pick them up
        await asyncio.sleep(0.25)
        remaining = await store.count_unsynced_events()
        assert remaining == 0

        await reconciler.stop()
