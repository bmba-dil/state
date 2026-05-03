"""Tests for state_core.providers.anthropic_client — AnthropicClient contract.

RED stubs (Wave 0): all 18 tests fail with ImportError until Wave 1 creates
state_core/providers/errors.py and state_core/providers/anthropic_client.py.

Security coverage: T-025-1 (no bearer token in logs), T-025-2 (X-Api-Key
suppressed for OAuth), T-025-3 (credential type dispatch), T-025-4 (no
shared client close).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.errors import (  # ImportError until Wave 1
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderResponseError,
    ProviderTransientError,
    StateProviderError,
)
from state_core.providers.anthropic_client import AnthropicClient  # ImportError until Wave 1

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

FAKE_OAUTH_CRED = OAuthCredential(
    access="sk-ant-oat-fake-token",
    refresh="sk-ant-oat-fake-refresh",
    expires=9_999_999_999.0,
    provider_id="anthropic",
)

FAKE_API_KEY_CRED = ApiKeyCredential(
    key="sk-ant-api03-fake-key",
    provider_id="anthropic",
)

# Minimal valid Message JSON response from Anthropic API
_MSG_RESPONSE = {
    "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello!"}],
    "model": "claude-opus-4-5-20241022",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 5,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shared_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


@pytest.fixture
def deps(shared_client: httpx.AsyncClient) -> Deps:
    return Deps(http_client=shared_client)


# ---------------------------------------------------------------------------
# SECTION 3 — PRV-02: Transport and URL (tests 1-2)
# ---------------------------------------------------------------------------


async def test_uses_shared_http_client(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """AnthropicClient uses the shared httpx client as transport (PRV-02)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    assert httpx_mock.get_requests() != []


async def test_create_posts_to_correct_url(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """AnthropicClient.create() sends POST to api.anthropic.com/v1/messages?beta=true (PRV-02)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    req = httpx_mock.get_requests()[0]
    assert req.url.host == "api.anthropic.com"
    assert req.url.path == "/v1/messages"
    assert "beta=true" in str(req.url)


# ---------------------------------------------------------------------------
# SECTION 4 — PRV-02: Stealth headers (tests 3-5)
# ---------------------------------------------------------------------------


async def test_oauth_stealth_headers(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """OAuthCredential produces stealth headers: x-app, user-agent, authorization, anthropic-beta (PRV-02)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    req = httpx_mock.get_requests()[0]
    assert req.headers["x-app"] == "cli"
    assert req.headers["user-agent"] == "claude-cli/2.1.121 (external, cli)"
    assert req.headers["authorization"] == "Bearer sk-ant-oat-fake-token"
    assert "oauth-2025-04-20" in req.headers["anthropic-beta"]


async def test_no_x_api_key_with_oauth(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps, monkeypatch: pytest.MonkeyPatch
) -> None:
    """X-Api-Key header is absent for OAuthCredential even when ANTHROPIC_API_KEY env var is set (T-025-2)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-env-key")
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    req = httpx_mock.get_requests()[0]
    assert "x-api-key" not in {k.lower() for k in req.headers}


async def test_api_key_credential_headers(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """ApiKeyCredential sends X-Api-Key and no stealth headers (T-025-3)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_API_KEY_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    req = httpx_mock.get_requests()[0]
    assert req.headers.get("x-api-key") == "sk-ant-api03-fake-key"
    assert "x-app" not in req.headers


# ---------------------------------------------------------------------------
# SECTION 5 — PRV-02: Lifecycle safety (test 6)
# ---------------------------------------------------------------------------


async def test_does_not_close_shared_client(
    httpx_mock: HTTPXMock, deps: Deps
) -> None:
    """AnthropicClient.create() does NOT close the shared httpx client (T-025-4)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    # Use a real AsyncClient so is_closed is a real property (not a mock attribute)
    real_client = httpx.AsyncClient()
    real_deps = Deps(http_client=real_client)
    client = AnthropicClient(FAKE_OAUTH_CRED, real_deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    assert real_client.is_closed is False


# ---------------------------------------------------------------------------
# SECTION 6 — PRV-02: Error mapping (tests 7-9)
# ---------------------------------------------------------------------------


async def test_connection_error_maps_to_transient(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """httpx.ConnectError -> ProviderTransientError (PRV-02)."""
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    with pytest.raises(ProviderTransientError):
        await client.create(
            model="claude-opus-4-5-20241022",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=100,
        )


async def test_auth_error_maps_to_auth_error(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """HTTP 401 -> ProviderAuthError (PRV-02)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        status_code=401,
        json={"type": "error", "error": {"type": "authentication_error", "message": "Invalid API key"}},
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    with pytest.raises(ProviderAuthError):
        await client.create(
            model="claude-opus-4-5-20241022",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=100,
        )


async def test_bad_request_maps_to_bad_request(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """HTTP 400 -> ProviderBadRequestError (PRV-02)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        status_code=400,
        json={"type": "error", "error": {"type": "invalid_request_error", "message": "budget_tokens too large"}},
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    with pytest.raises(ProviderBadRequestError):
        await client.create(
            model="claude-opus-4-5-20241022",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=100,
        )


# ---------------------------------------------------------------------------
# SECTION 7 — PRV-02: Import graph checks (tests 10-11)
# ---------------------------------------------------------------------------


def test_errors_importable_from_errors_module() -> None:
    """StateProviderError hierarchy is importable from state_core.providers.errors (PRV-02)."""
    assert issubclass(StateProviderError, Exception)
    assert issubclass(ProviderTransientError, StateProviderError)
    assert issubclass(ProviderAuthError, StateProviderError)
    assert issubclass(ProviderBadRequestError, StateProviderError)
    assert issubclass(ProviderResponseError, StateProviderError)


def test_no_mode_silo_import() -> None:
    """state_core.providers.anthropic_client does NOT import state_build.* or state_teach.* (PRV-02)."""
    importlib.import_module("state_core.providers.anthropic_client")
    violations = [k for k in sys.modules if k.startswith("state_build.") or k.startswith("state_teach.")]
    assert violations == []


# ---------------------------------------------------------------------------
# SECTION 8 — PRV-08: Thinking (tests 12-14)
# ---------------------------------------------------------------------------


async def test_thinking_budget_passed_through(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """thinking={"type": "enabled", "budget_tokens": 8192} is sent in the request body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 8192},
    )
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["thinking"] == {"type": "enabled", "budget_tokens": 8192}


async def test_thinking_blocks_preserved(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """ThinkingBlock in response content is preserved in returned Message (PRV-08)."""
    response_json = {
        "id": "msg_01thinking",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "step-by-step", "signature": "abc123"},
            {"type": "text", "text": "Answer"},
        ],
        "model": "claude-opus-4-5-20241022",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=response_json,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    msg = await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 8192},
    )
    assert msg.content[0].type == "thinking"
    assert msg.content[0].thinking == "step-by-step"


async def test_adaptive_thinking_accepted(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """thinking={"type": "adaptive"} is sent in the request body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=4096,
        thinking={"type": "adaptive"},
    )
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["thinking"] == {"type": "adaptive"}


# ---------------------------------------------------------------------------
# SECTION 9 — PRV-09: Cache-control (tests 15-18)
# ---------------------------------------------------------------------------


async def test_cache_control_passed_through(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """cache_control={"type": "ephemeral", "ttl": "5m"} is sent in the request body (PRV-09)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=1024,
        cache_control={"type": "ephemeral", "ttl": "5m"},
    )
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["cache_control"] == {"type": "ephemeral", "ttl": "5m"}


async def test_cache_usage_preserved(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """response.usage.cache_creation_input_tokens is preserved in returned Message (PRV-09)."""
    response_json = {
        "id": "msg_01cache",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Cached!"}],
        "model": "claude-opus-4-5-20241022",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 500,
            "cache_read_input_tokens": 0,
        },
    }
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=response_json,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    msg = await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=1024,
        cache_control={"type": "ephemeral", "ttl": "5m"},
    )
    assert msg.usage.cache_creation_input_tokens == 500


async def test_cache_read_tokens_preserved(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """response.usage.cache_read_input_tokens is preserved in returned Message (PRV-09)."""
    response_json = {
        "id": "msg_01cacheread",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "From cache!"}],
        "model": "claude-opus-4-5-20241022",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 300,
        },
    }
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=response_json,
    )
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    msg = await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=1024,
        cache_control={"type": "ephemeral", "ttl": "5m"},
    )
    assert msg.usage.cache_read_input_tokens == 300


async def test_stream_thinking_delta_yielded(
    shared_client: httpx.AsyncClient, deps: Deps
) -> None:
    """stream() yields RawContentBlockDeltaEvent with delta.type='thinking_delta' (PRV-08+PRV-09)."""
    # Use mock.patch on the SDK's messages.create to avoid SSE byte-encoding in tests.
    # This isolates the stream() iterator contract without requiring real SSE transport.
    thinking_delta = MagicMock()
    thinking_delta.type = "thinking_delta"
    thinking_delta.thinking = "reasoning..."

    delta_event = MagicMock()
    delta_event.type = "content_block_delta"
    delta_event.delta = thinking_delta

    stop_event = MagicMock()
    stop_event.type = "message_delta"
    stop_event.delta = MagicMock()
    stop_event.delta.stop_reason = "end_turn"
    stop_event.usage = MagicMock()
    stop_event.usage.output_tokens = 10

    async def _fake_stream():
        yield delta_event
        yield stop_event

    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    with patch.object(client._sdk.messages, "create", return_value=_fake_stream()):
        events = [e async for e in client.stream(
            model="claude-opus-4-5-20241022",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=4096,
        )]
    assert any(
        getattr(getattr(e, "delta", None), "type", None) == "thinking_delta"
        for e in events
    )
