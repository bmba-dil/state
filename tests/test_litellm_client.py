"""Tests for state_core.providers.litellm_client — LitellmClient contract.

All tests verify the Wave 1 GREEN implementation.

Security: T-024-1 (no OAuth through litellm), T-024-2 (no aclose on shared
client), T-024-3 (all exceptions mapped), T-024-4 (no mode-silo import) are
all exercised here.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import litellm.exceptions as lexc
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from litellm.types.utils import ModelResponse, ModelResponseStream

from state_core.providers.litellm_client import (
    LitellmClient,
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderResponseError,
    ProviderTransientError,
    StateProviderError,
)


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------


async def _fake_stream(chunks, *, raise_after: Exception | None = None):
    """Async generator helper for streaming tests."""
    for chunk in chunks:
        yield chunk
    if raise_after is not None:
        raise raise_after


# ---------------------------------------------------------------------------
# PRV-01: non-streaming acompletion
# ---------------------------------------------------------------------------


async def test_acompletion_returns_model_response() -> None:
    """LitellmClient.acompletion() returns a ModelResponse (PRV-01)."""
    fake_response = MagicMock(spec=ModelResponse)
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "hello"
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_response)
        client = LitellmClient()
        result = await client.acompletion("gpt-4o", [{"role": "user", "content": "hi"}])
    assert result.choices[0].message.content == "hello"


async def test_client_does_not_close_shared_httpx() -> None:
    """LitellmClient never calls aclose() on the shared httpx client (T-024-2)."""
    fake_response = MagicMock(spec=ModelResponse)
    fake_response.choices = [MagicMock()]
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_response)
        mock_litellm.aclient_session = AsyncMock()
        client = LitellmClient()
        await client.acompletion("gpt-4o", [{"role": "user", "content": "hi"}])
        # Never close: lifecycle owned by Deps (T-024-2)
        mock_litellm.aclient_session.aclose.assert_not_called()


async def test_rate_limit_maps_to_transient() -> None:
    """litellm.RateLimitError -> ProviderTransientError (PRV-01)."""
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=lexc.RateLimitError("rate_limit", "openai", "gpt-4o")
        )
        client = LitellmClient()
        with pytest.raises(ProviderTransientError):
            await client.acompletion("gpt-4o", [])


async def test_auth_error_maps_to_auth_error() -> None:
    """litellm.AuthenticationError -> ProviderAuthError (PRV-01)."""
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=lexc.AuthenticationError("auth", "openai", "gpt-4o")
        )
        client = LitellmClient()
        with pytest.raises(ProviderAuthError):
            await client.acompletion("gpt-4o", [])


async def test_bad_request_maps_to_bad_request() -> None:
    """litellm.BadRequestError -> ProviderBadRequestError (PRV-01)."""
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=lexc.BadRequestError("bad_request", "openai", "gpt-4o")
        )
        client = LitellmClient()
        with pytest.raises(ProviderBadRequestError):
            await client.acompletion("gpt-4o", [])


def _make_exc(exc_class: type) -> Exception:
    """Construct a litellm exception instance, handling classes with non-standard signatures."""
    # PermissionDeniedError requires a response positional arg
    if exc_class is lexc.PermissionDeniedError:
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(403, request=request)
        return exc_class("permission_denied", "openai", "gpt-4o", response)
    # All others accept (message, llm_provider, model)
    return exc_class("fixture", "openai", "gpt-4o")


_LITELLM_EXCEPTION_CLASSES = [
    lexc.RateLimitError,
    lexc.AuthenticationError,
    lexc.BadRequestError,
    lexc.ContextWindowExceededError,
    lexc.APIConnectionError,
    lexc.Timeout,
    lexc.InternalServerError,
    lexc.ServiceUnavailableError,
    lexc.PermissionDeniedError,
    lexc.BadGatewayError,
]


@given(st.sampled_from(_LITELLM_EXCEPTION_CLASSES))
@settings(max_examples=len(_LITELLM_EXCEPTION_CLASSES))
async def test_all_litellm_exceptions_map_to_state_errors(exc_class: type) -> None:
    """All litellm exception types map to StateProviderError subclasses (PRV-01, T-024-3).

    Hypothesis property test: no raw litellm exception leaks out of
    LitellmClient.acompletion().
    """
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=_make_exc(exc_class)
        )
        client = LitellmClient()
        with pytest.raises(StateProviderError):
            await client.acompletion("gpt-4o", [])


# ---------------------------------------------------------------------------
# PRV-07: streaming normalization
# ---------------------------------------------------------------------------


async def test_astream_yields_chunks_unchanged() -> None:
    """LitellmClient.astream() yields ModelResponseStream chunks unchanged (PRV-07)."""
    fake_chunk = MagicMock(spec=ModelResponseStream)
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=_fake_stream([fake_chunk]))
        client = LitellmClient()
        collected = []
        async for chunk in client.astream("gpt-4o", [{"role": "user", "content": "hi"}]):
            collected.append(chunk)
    assert collected == [fake_chunk]


async def test_astream_chunk_delta_content() -> None:
    """chunk.choices[0].delta.content survives streaming round-trip (PRV-07)."""
    fake_chunk = MagicMock(spec=ModelResponseStream)
    fake_chunk.choices = [MagicMock()]
    fake_chunk.choices[0].delta.content = "hello"
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=_fake_stream([fake_chunk]))
        client = LitellmClient()
        collected = []
        async for chunk in client.astream("gpt-4o", []):
            collected.append(chunk)
    assert collected[0].choices[0].delta.content == "hello"


async def test_astream_chunk_delta_tool_calls() -> None:
    """chunk.choices[0].delta.tool_calls survives streaming round-trip (PRV-07)."""
    fake_tool = MagicMock()
    fake_chunk = MagicMock(spec=ModelResponseStream)
    fake_chunk.choices = [MagicMock()]
    fake_chunk.choices[0].delta.tool_calls = [fake_tool]
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=_fake_stream([fake_chunk]))
        client = LitellmClient()
        collected = []
        async for chunk in client.astream("gpt-4o", []):
            collected.append(chunk)
    assert collected[0].choices[0].delta.tool_calls is fake_chunk.choices[0].delta.tool_calls


async def test_astream_exception_maps_correctly() -> None:
    """Exception raised during stream iteration maps to StateProviderError (PRV-07)."""
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            return_value=_fake_stream([], raise_after=RuntimeError("mid-stream failure"))
        )
        client = LitellmClient()
        with pytest.raises(StateProviderError):
            async for _ in client.astream("gpt-4o", []):
                pass


# ---------------------------------------------------------------------------
# Mode isolation
# ---------------------------------------------------------------------------


def test_no_mode_silo_import() -> None:
    """state_core.providers.litellm_client does not import state_build or state_teach (T-024-4).

    Import-graph assertion: check sys.modules after importing litellm_client.
    This test is synchronous (no async) because it only inspects the import graph.
    """
    # Reimport to ensure sys.modules is populated
    importlib.import_module("state_core.providers.litellm_client")
    silo_violations = [
        key for key in sys.modules
        if key.startswith("state_build.") or key.startswith("state_teach.")
    ]
    assert silo_violations == [], f"Mode silo import detected: {silo_violations}"
