"""Tests for state_core.providers.thinking_budget — PRV-08 thinking budget propagation.

RED stubs (Wave 0): all 10 tests fail with ImportError until Wave 1 creates
state_core/providers/thinking_budget.py.

Coverage:
- Unit conversion logic (build_thinking_param returns correct dict or None)
- Pre-flight constraint validation (budget < 1024 or budget >= max_tokens raises)
- HTTPXMock wire-capture regression (budget propagates to actual HTTP body)
- Mode isolation import guard (thinking_budget.py must not import state_build/state_teach)
"""
from __future__ import annotations

import inspect
import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from state_core.auth.base import OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.errors import ProviderBadRequestError
from state_core.providers.model_profile import ModelProfile, ResolvedProfile, resolve_profile
from state_core.providers.thinking_budget import build_thinking_param  # RED: does not exist yet
import state_core.providers.thinking_budget as _thinking_budget_module  # for mode silo test

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

FAKE_OAUTH_CRED = OAuthCredential(
    access="sk-ant-oat-fake",
    refresh="sk-ant-oat-fake-refresh",
    expires=9_999_999_999.0,
    provider_id="anthropic",
)

_MSG_RESPONSE = {
    "id": "msg_01test",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello!"}],
    "model": "claude-opus-4-7",
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
# Tests 1-3: Unit conversion logic — quality/balanced/budget profiles
# ---------------------------------------------------------------------------


def test_build_thinking_param_quality_returns_enabled() -> None:
    """Quality profile produces ThinkingConfigEnabledParam with budget_tokens=4000 (PRV-08)."""
    resolved = resolve_profile(step_profile=ModelProfile.quality)
    result = build_thinking_param(resolved, max_tokens=16000)
    assert result == {"type": "enabled", "budget_tokens": 4000}


def test_build_thinking_param_balanced_returns_none() -> None:
    """Balanced profile produces None — no thinking tag in request (PRV-08)."""
    resolved = resolve_profile(step_profile=ModelProfile.balanced)
    result = build_thinking_param(resolved, max_tokens=4096)
    assert result is None


def test_build_thinking_param_budget_returns_none() -> None:
    """Budget profile produces None — no thinking tag in request (PRV-08)."""
    resolved = resolve_profile(step_profile=ModelProfile.budget)
    result = build_thinking_param(resolved, max_tokens=4096)
    assert result is None


# ---------------------------------------------------------------------------
# Tests 4-6: Pre-flight constraint validation
# ---------------------------------------------------------------------------


def test_budget_below_minimum_raises() -> None:
    """thinking_budget_tokens < 1024 raises ProviderBadRequestError (PRV-08)."""
    resolved = ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        thinking_budget_tokens=500,
    )
    with pytest.raises(ProviderBadRequestError, match="must be >= 1024"):
        build_thinking_param(resolved, max_tokens=16000)


def test_budget_ge_max_tokens_raises() -> None:
    """thinking_budget_tokens >= max_tokens raises ProviderBadRequestError (PRV-08)."""
    resolved = ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        thinking_budget_tokens=8000,
    )
    with pytest.raises(ProviderBadRequestError, match="must be < max_tokens"):
        build_thinking_param(resolved, max_tokens=8000)


def test_budget_exactly_below_max_tokens_accepted() -> None:
    """thinking_budget_tokens == max_tokens - 1 is accepted (boundary condition, PRV-08)."""
    resolved = ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        thinking_budget_tokens=7999,
    )
    result = build_thinking_param(resolved, max_tokens=8000)
    assert result == {"type": "enabled", "budget_tokens": 7999}


# ---------------------------------------------------------------------------
# Tests 7-9: HTTPXMock wire-capture — budget propagates to HTTP body
# ---------------------------------------------------------------------------


async def test_quality_profile_propagates_budget_to_wire(httpx_mock: HTTPXMock) -> None:
    """Quality profile thinking budget appears in the wire-level HTTP request body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    resolved = resolve_profile(step_profile=ModelProfile.quality)
    thinking_param = build_thinking_param(resolved, max_tokens=16000)
    client = AnthropicClient(FAKE_OAUTH_CRED, Deps(http_client=httpx.AsyncClient()))
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Plan."}],
        max_tokens=16000,
        thinking=thinking_param,
    )
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["thinking"]["type"] == "enabled"
    assert body["thinking"]["budget_tokens"] == 4000


async def test_balanced_profile_no_thinking_in_wire(httpx_mock: HTTPXMock) -> None:
    """Balanced profile omits the 'thinking' key entirely from the wire-level request body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    resolved = resolve_profile(step_profile=ModelProfile.balanced)
    thinking_param = build_thinking_param(resolved, max_tokens=4096)
    assert thinking_param is None
    client = AnthropicClient(FAKE_OAUTH_CRED, Deps(http_client=httpx.AsyncClient()))
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Plan."}],
        max_tokens=4096,
        thinking=thinking_param,
    )
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert "thinking" not in body


async def test_custom_budget_propagates_to_wire(httpx_mock: HTTPXMock) -> None:
    """Override thinking_budget_tokens=2048 propagates exactly to wire body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    resolved = resolve_profile(
        step_profile=ModelProfile.quality,
        overrides={"thinking_budget_tokens": 2048},
    )
    assert resolved.thinking_budget_tokens == 2048
    thinking_param = build_thinking_param(resolved, max_tokens=16000)
    assert thinking_param == {"type": "enabled", "budget_tokens": 2048}
    client = AnthropicClient(FAKE_OAUTH_CRED, Deps(http_client=httpx.AsyncClient()))
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Plan."}],
        max_tokens=16000,
        thinking=thinking_param,
    )
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["thinking"]["budget_tokens"] == 2048


# ---------------------------------------------------------------------------
# Test 10: Mode isolation import guard
# ---------------------------------------------------------------------------


def test_no_mode_silo_import() -> None:
    """thinking_budget module must not import state_build or state_teach submodules (mode isolation)."""
    src = inspect.getsource(_thinking_budget_module)
    assert "state_build" not in src, (
        "thinking_budget.py imports from state_build — violates mode isolation"
    )
    assert "state_teach" not in src, (
        "thinking_budget.py imports from state_teach — violates mode isolation"
    )
