"""Phase 021 integration tests — orchestrator boot ordering + importer failure.

Verifies the Step 0.5 wiring added in Plan 03 Task 1:
  - import_from_opencode runs AFTER assert_redactor_attached (T-021-03-1)
  - importer failure is non-fatal (T-021-03-2)
  - importer receives the SqliteEventStore + SyncEventMirror used downstream (T-021-03-3)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog


@pytest.fixture(autouse=True)
def _isolate_structlog():
    """Snapshot/restore structlog config — same pattern as tests/auth/conftest.py."""
    saved = structlog.get_config()
    structlog.reset_defaults()
    yield
    structlog.configure(**saved)


@pytest.mark.asyncio
async def test_orchestrator_runs_importer_after_redactor_selfcheck() -> None:
    """T-021-03-1 — boot order is locked: install → assert_attached → importer.

    A future refactor that moves the importer above assert_redactor_attached()
    would let importer's structlog calls leak through unfiltered (no redactor).
    This test catches that regression by recording call order on a single
    parent MagicMock that all three call sites are attached as children of —
    so `parent.mock_calls` records the global ordering across all three.

    Pattern note: we MUST NOT pass `parent.attr` as the second positional arg
    to `patch()` AND a `new=` kwarg in the same call — that raises
    `TypeError: patch() got multiple values for argument 'new'`. Instead we
    let `patch()` create the mock (or pass it via `new=`/`new_callable=`)
    and then attach it to the parent recorder via `parent.attach_mock`.
    """
    parent = MagicMock()
    with (
        patch("state_daemon.orchestrator.install", new_callable=MagicMock) as mock_install,
        patch("state_daemon.orchestrator.assert_redactor_attached", new_callable=MagicMock) as mock_assert,
        patch("state_daemon.orchestrator.acquire_pid_file", return_value=True),
        patch("state_daemon.orchestrator.release_pid_file"),
        patch("state_daemon.orchestrator.import_from_opencode", new_callable=AsyncMock) as mock_importer,
        patch("state_daemon.orchestrator.SqliteEventStore") as store_cls,
        patch("state_daemon.orchestrator.SyncEventMirror") as mirror_cls,
        patch("state_daemon.orchestrator.migrate", new_callable=AsyncMock) as mock_migrate,
        patch("state_daemon.orchestrator.StartupReconciler") as reconciler_cls,
    ):
        # Configure async / awaitable returns BEFORE attaching to parent recorder
        mock_importer.return_value = []
        mock_migrate.return_value = None
        store_cls.return_value.run_repair_now = AsyncMock(return_value=[])
        reconciler_cls.return_value.start = AsyncMock(return_value=None)

        # Attach to a single parent MagicMock so `parent.mock_calls` records
        # the GLOBAL call order across all four discriminating call sites.
        parent.attach_mock(mock_install, "install")
        parent.attach_mock(mock_assert, "assert_attached")
        parent.attach_mock(mock_importer, "importer")
        parent.attach_mock(store_cls.return_value.run_repair_now, "run_repair_now")

        from state_daemon.orchestrator import startup
        await startup()

    # Each entry in parent.mock_calls is a (name, args, kwargs) tuple where
    # `name` is the dotted path on the parent (e.g. "install", "importer").
    # We care about the FIRST occurrence of each top-level child name.
    call_names = [c[0].split(".")[0] for c in parent.mock_calls if c[0]]

    def first_idx(needle: str) -> int:
        try:
            return call_names.index(needle)
        except ValueError:
            raise AssertionError(
                f"expected call '{needle}' missing from boot sequence; got {call_names!r}"
            )

    install_idx = first_idx("install")
    assert_idx = first_idx("assert_attached")
    importer_idx = first_idx("importer")
    repair_idx = first_idx("run_repair_now")

    # Boot-order invariant T-021-03-1:
    #   install → assert_attached → importer → run_repair_now (store-driven steps)
    assert install_idx < assert_idx < importer_idx < repair_idx, (
        "Boot order violation — expected "
        "install < assert_attached < importer < run_repair_now; "
        f"got install={install_idx} assert={assert_idx} "
        f"importer={importer_idx} repair={repair_idx} "
        f"in sequence {call_names!r}"
    )


@pytest.mark.asyncio
async def test_orchestrator_import_failure_does_not_abort_boot() -> None:
    """T-021-03-2 — importer failure is non-fatal; daemon continues.

    Foreign data tolerance per CONTEXT.md §Hardness when opencode auth.json
    is unreadable. A user with a corrupt opencode install must still get a
    working state-daemon.
    """
    importer_mock = AsyncMock(side_effect=RuntimeError("simulated importer failure"))
    repair_mock = AsyncMock(return_value=[])
    migrate_mock = AsyncMock(return_value=None)
    reconciler_start_mock = AsyncMock(return_value=None)

    with (
        patch("state_daemon.orchestrator.install"),
        patch("state_daemon.orchestrator.assert_redactor_attached"),
        patch("state_daemon.orchestrator.acquire_pid_file", return_value=True),
        patch("state_daemon.orchestrator.import_from_opencode", importer_mock),
        patch("state_daemon.orchestrator.SqliteEventStore") as store_cls,
        patch("state_daemon.orchestrator.SyncEventMirror"),
        patch("state_daemon.orchestrator.migrate", migrate_mock),
        patch("state_daemon.orchestrator.StartupReconciler") as reconciler_cls,
        structlog.testing.capture_logs() as logs,
    ):
        store_cls.return_value.run_repair_now = repair_mock
        reconciler_cls.return_value.start = reconciler_start_mock

        from state_daemon.orchestrator import startup
        # MUST NOT raise
        await startup()

    # Assert WARN log emitted with error_type only (no e.args / repr)
    warn_logs = [l for l in logs if l.get("event") == "daemon.startup.importer_failed"]
    assert len(warn_logs) == 1
    assert warn_logs[0]["log_level"] == "warning"
    assert warn_logs[0]["error_type"] == "RuntimeError"
    # Must NOT contain the simulated message (defensive — never log repr(e))
    assert "simulated importer failure" not in str(warn_logs[0])

    # Subsequent steps still called
    assert repair_mock.await_count == 1
    assert migrate_mock.await_count == 1
    assert reconciler_start_mock.await_count == 1


@pytest.mark.asyncio
async def test_orchestrator_passes_store_and_mirror_to_importer() -> None:
    """T-021-03-3 — importer receives the SAME store + mirror used by reconciler.

    Ensures auth.imported events dual-write via the same SqliteEventStore +
    SyncEventMirror that runtime events use (cardinal rule: events.sqlite
    first, SyncEvent second). If a future refactor passes None or creates
    a separate store/mirror, auth.imported events would silently bypass the
    mirror.
    """
    importer_mock = AsyncMock(return_value=[])

    with (
        patch("state_daemon.orchestrator.install"),
        patch("state_daemon.orchestrator.assert_redactor_attached"),
        patch("state_daemon.orchestrator.acquire_pid_file", return_value=True),
        patch("state_daemon.orchestrator.import_from_opencode", importer_mock),
        patch("state_daemon.orchestrator.SqliteEventStore") as store_cls,
        patch("state_daemon.orchestrator.SyncEventMirror") as mirror_cls,
        patch("state_daemon.orchestrator.migrate", new=AsyncMock(return_value=None)),
        patch("state_daemon.orchestrator.StartupReconciler") as reconciler_cls,
    ):
        store_inst = store_cls.return_value
        store_inst.run_repair_now = AsyncMock(return_value=[])
        mirror_inst = mirror_cls.return_value
        reconciler_cls.return_value.start = AsyncMock(return_value=None)

        from state_daemon.orchestrator import startup
        await startup()

    # Importer received the same store + mirror instances
    importer_kwargs = importer_mock.await_args.kwargs
    assert importer_kwargs["store"] is store_inst
    assert importer_kwargs["mirror"] is mirror_inst

    # Reconciler received the SAME store + mirror (single instances; no duplicates)
    reconciler_kwargs = reconciler_cls.call_args.kwargs
    assert reconciler_kwargs["db"] is store_inst
    assert reconciler_kwargs["mirror"] is mirror_inst
