"""Tests for state_core.providers.router — ProviderRouter PRV-03 bypass guard.

Wave 0 (RED): All tests fail with AttributeError (ProviderRouter has no
select() method) until Wave 1 implements ProviderRouter.select().

Exception: test_oauth_routing_error_importable and test_no_mode_silo_import
are import-level tests that pass GREEN after Plan 026-01 Task 1 completes
(OAuthRoutingError added to errors.py) — they do NOT depend on select().

Security coverage: T-026-1 (no token in logs), T-026-2 (PRV-03 bypass gate),
T-026-3 (mode silo).
"""
from __future__ import annotations

import importlib
import inspect
import sys

import httpx
import pytest
import structlog.testing

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.errors import OAuthRoutingError, StateProviderError
from state_core.providers.litellm_client import LitellmClient
from state_core.providers.router import ProviderRouter

# ---------------------------------------------------------------------------
# Module-level test fixtures
# ---------------------------------------------------------------------------

FAKE_OAUTH = OAuthCredential(
    access="sk-ant-oat-fake",
    refresh="fake-refresh",
    expires=9_999_999_999.0,
    provider_id="anthropic",
)

FAKE_API_KEY_ANTHROPIC = ApiKeyCredential(
    key="sk-ant-api03-fake",
    provider_id="anthropic",
)

FAKE_API_KEY_GEMINI = ApiKeyCredential(
    key="gsk-fake-gemini",
    provider_id="google.gemini",
)


@pytest.fixture
def deps() -> Deps:
    return Deps(http_client=httpx.AsyncClient())


# ---------------------------------------------------------------------------
# PRV-03: routing correctness
# ---------------------------------------------------------------------------


def test_oauth_cred_routes_to_anthropic_client(deps: Deps) -> None:
    """OAuthCredential MUST route to AnthropicClient (PRV-03 primary gate)."""
    router = ProviderRouter()
    client = router.select(FAKE_OAUTH, deps)
    assert isinstance(client, AnthropicClient)


def test_anthropic_api_key_routes_to_litellm(deps: Deps) -> None:
    """ApiKeyCredential(provider_id='anthropic') MUST route to LitellmClient.

    PRV-03 is specifically for OAuth stealth, not for all Anthropic traffic.
    Anthropic API-key traffic routes through litellm (Phase 031 parity matrix).
    """
    router = ProviderRouter()
    client = router.select(FAKE_API_KEY_ANTHROPIC, deps)
    assert isinstance(client, LitellmClient)


def test_non_anthropic_api_key_routes_to_litellm(deps: Deps) -> None:
    """ApiKeyCredential for non-Anthropic provider MUST route to LitellmClient."""
    router = ProviderRouter()
    client = router.select(FAKE_API_KEY_GEMINI, deps)
    assert isinstance(client, LitellmClient)


# ---------------------------------------------------------------------------
# PRV-03: client binding correctness
# ---------------------------------------------------------------------------


def test_oauth_client_has_correct_cred_bound(deps: Deps) -> None:
    """AnthropicClient returned for OAuth cred must have _cred bound to that cred."""
    router = ProviderRouter()
    client = router.select(FAKE_OAUTH, deps)
    assert isinstance(client, AnthropicClient)
    assert client._cred is FAKE_OAUTH


def test_oauth_client_has_correct_deps_bound(deps: Deps) -> None:
    """AnthropicClient returned for OAuth cred must have _deps bound to deps fixture."""
    router = ProviderRouter()
    client = router.select(FAKE_OAUTH, deps)
    assert isinstance(client, AnthropicClient)
    assert client._deps is deps


# ---------------------------------------------------------------------------
# PRV-03: select() must be sync
# ---------------------------------------------------------------------------


def test_select_is_sync(deps: Deps) -> None:
    """select() must NOT be a coroutine — it is pure routing with no I/O."""
    router = ProviderRouter()
    result = router.select(FAKE_OAUTH, deps)
    assert not inspect.isawaitable(result), (
        "ProviderRouter.select() returned an awaitable — it must be a plain sync method."
    )


# ---------------------------------------------------------------------------
# PRV-03: error hierarchy
# ---------------------------------------------------------------------------


def test_oauth_routing_error_importable() -> None:
    """OAuthRoutingError must be importable from errors.py and be a StateProviderError."""
    assert issubclass(OAuthRoutingError, StateProviderError), (
        "OAuthRoutingError must subclass StateProviderError"
    )


# ---------------------------------------------------------------------------
# PRV-03: mode isolation (T-026-3)
# ---------------------------------------------------------------------------


def test_no_mode_silo_import() -> None:
    """state_core.providers.router must not import state_build.* or state_teach.*."""
    importlib.import_module("state_core.providers.router")
    for name in sys.modules:
        assert not name.startswith("state_build"), (
            f"Mode silo violation: router imported state_build module '{name}'"
        )
        assert not name.startswith("state_teach"), (
            f"Mode silo violation: router imported state_teach module '{name}'"
        )


# ---------------------------------------------------------------------------
# PRV-03: secret hygiene in logs (T-026-1)
# ---------------------------------------------------------------------------


def test_oauth_route_log_no_token(deps: Deps) -> None:
    """select() for OAuthCredential must NOT log the access token value."""
    router = ProviderRouter()
    with structlog.testing.capture_logs() as cap_logs:
        router.select(FAKE_OAUTH, deps)
    for entry in cap_logs:
        for value in entry.values():
            assert "sk-ant-oat-fake" not in str(value), (
                f"OAuth access token leaked in log entry: {entry}"
            )


def test_litellm_route_log_no_token(deps: Deps) -> None:
    """select() for ApiKeyCredential must NOT log the key value."""
    router = ProviderRouter()
    with structlog.testing.capture_logs() as cap_logs:
        router.select(FAKE_API_KEY_ANTHROPIC, deps)
    for entry in cap_logs:
        for value in entry.values():
            assert "sk-ant-api03-fake" not in str(value), (
                f"API key leaked in log entry: {entry}"
            )
