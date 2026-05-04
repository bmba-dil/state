"""Tests for state_daemon.hooks — /hook/chat-params HTTP handler stub (PRV-04).

Wave 1 (GREEN): All tests fully implemented and passing.

The handler is tested as a pure async function (body: dict -> dict),
not via HTTP — server.py has no framework bound yet (Phase 027 stub).
"""
from __future__ import annotations

import pytest

from state_daemon.hooks import handle_chat_params


# ---------------------------------------------------------------------------
# PRV-04: /hook/chat-params handler — shape and profile tests
# ---------------------------------------------------------------------------


async def test_chat_params_handler_returns_valid_shape() -> None:
    """Handler response has all required chat.params output keys."""
    result = await handle_chat_params({})
    assert "temperature" in result
    assert "topP" in result
    assert "topK" in result
    assert "maxOutputTokens" in result
    assert "options" in result


async def test_chat_params_default_profile() -> None:
    """No step_profile in body returns balanced defaults (temperature=0.5, options={})."""
    result = await handle_chat_params({})
    assert result["temperature"] == 0.5
    assert result["options"] == {}


async def test_chat_params_quality_profile() -> None:
    """step_profile='quality' returns temperature=0.2, options.thinking_budget_tokens=4000."""
    result = await handle_chat_params({"step_profile": "quality"})
    assert result["temperature"] == 0.2
    assert result["options"]["thinking_budget_tokens"] == 4000  # type: ignore[index]
