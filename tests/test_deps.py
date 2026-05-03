"""RED stubs for state_core.deps.Deps container + orchestrator startup wiring.

All tests fail with ModuleNotFoundError until Plan 02 (Wave 1) creates
src/state_core/deps.py.  Do NOT add pytest.skip() or conditional imports.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from state_core.deps import Deps


async def test_deps_holds_client() -> None:
    """Deps stores http_client and exposes it as an attribute."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    deps = Deps(http_client=mock_client)
    assert deps.http_client is mock_client


async def test_deps_aclose() -> None:
    """Deps.aclose() delegates to http_client.aclose()."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    deps = Deps(http_client=mock_client)
    await deps.aclose()
    mock_client.aclose.assert_awaited_once()


async def test_startup_creates_deps() -> None:
    """startup() creates Deps and assigns litellm.aclient_session.

    We patch:
    - state_daemon.orchestrator.build_shared_client -> returns a fake client
    - state_daemon.orchestrator.litellm             -> captures aclient_session assignment
    All other startup steps are patched out to avoid side effects.
    """
    fake_client = MagicMock(spec=httpx.AsyncClient)

    # SqliteEventStore mock needs async run_repair_now()
    mock_store = MagicMock()
    mock_store.run_repair_now = AsyncMock(return_value=[])
    mock_store_cls = MagicMock(return_value=mock_store)

    # StartupReconciler mock needs async start()
    mock_reconciler = MagicMock()
    mock_reconciler.start = AsyncMock(return_value=None)
    mock_reconciler_cls = MagicMock(return_value=mock_reconciler)

    with (
        patch("state_daemon.orchestrator.build_shared_client", return_value=fake_client) as mock_build,
        patch("state_daemon.orchestrator.litellm") as mock_litellm,
        patch("state_daemon.orchestrator.install"),
        patch("state_daemon.orchestrator.assert_redactor_attached"),
        patch("state_daemon.orchestrator.import_from_opencode", new_callable=AsyncMock, return_value=[]),
        patch("state_daemon.orchestrator.SqliteEventStore", mock_store_cls),
        patch("state_daemon.orchestrator.SyncEventMirror"),
        patch("state_daemon.orchestrator.migrate", new_callable=AsyncMock),
        patch("state_daemon.orchestrator.StartupReconciler", mock_reconciler_cls),
    ):
        from state_daemon.orchestrator import startup
        await startup()

    mock_build.assert_called_once()
    # litellm.aclient_session must be assigned the shared client
    assert mock_litellm.aclient_session == fake_client


async def test_anthropic_client_injection() -> None:
    """AsyncAnthropic(http_client=...) accepts httpx.AsyncClient without TypeError.

    This is a smoke test that the Anthropic SDK injection point (Phase 025)
    will work.  We do NOT make a real API call.
    """
    import anthropic

    client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )
    )
    try:
        # Constructor must accept http_client= without raising TypeError.
        sdk = anthropic.AsyncAnthropic(api_key="sk-ant-test", http_client=client)
        assert sdk is not None
    finally:
        await client.aclose()
