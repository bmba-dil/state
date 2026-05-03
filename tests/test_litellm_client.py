"""RED stubs for state_core.providers.litellm_client — LitellmClient contract.

All tests fail with ImportError (collection error) until Plan 02 (Wave 1)
creates src/state_core/providers/litellm_client.py.  Do NOT add
pytest.skip() or conditional imports — the tests MUST fail red until the
implementation lands.

Security: T-024-1 (no OAuth through litellm), T-024-2 (no aclose on shared
client), T-024-3 (all exceptions mapped), T-024-4 (no mode-silo import) are
all exercised here.
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

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
# PRV-01: non-streaming acompletion
# ---------------------------------------------------------------------------


async def test_acompletion_returns_model_response() -> None:
    """LitellmClient.acompletion() returns a ModelResponse (PRV-01)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_client_does_not_close_shared_httpx() -> None:
    """LitellmClient never calls aclose() on the shared httpx client (T-024-2)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_rate_limit_maps_to_transient() -> None:
    """litellm.RateLimitError -> ProviderTransientError (PRV-01)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_auth_error_maps_to_auth_error() -> None:
    """litellm.AuthenticationError -> ProviderAuthError (PRV-01)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_bad_request_maps_to_bad_request() -> None:
    """litellm.BadRequestError -> ProviderBadRequestError (PRV-01)."""
    pytest.fail("RED stub — implement in Wave 1")


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
    pytest.fail("RED stub — implement in Wave 1")


# ---------------------------------------------------------------------------
# PRV-07: streaming normalization
# ---------------------------------------------------------------------------


async def test_astream_yields_chunks_unchanged() -> None:
    """LitellmClient.astream() yields ModelResponseStream chunks unchanged (PRV-07)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_astream_chunk_delta_content() -> None:
    """chunk.choices[0].delta.content survives streaming round-trip (PRV-07)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_astream_chunk_delta_tool_calls() -> None:
    """chunk.choices[0].delta.tool_calls survives streaming round-trip (PRV-07)."""
    pytest.fail("RED stub — implement in Wave 1")


async def test_astream_exception_maps_correctly() -> None:
    """Exception raised during stream iteration maps to StateProviderError (PRV-07)."""
    pytest.fail("RED stub — implement in Wave 1")


# ---------------------------------------------------------------------------
# Mode isolation
# ---------------------------------------------------------------------------


def test_no_mode_silo_import() -> None:
    """state_core.providers.litellm_client does not import state_build or state_teach (T-024-4).

    Import-graph assertion: check sys.modules after importing litellm_client.
    This test is synchronous (no async) because it only inspects the import graph.
    """
    pytest.fail("RED stub — implement in Wave 1")
