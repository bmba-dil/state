"""Tests for state_daemon.hooks — /hook/chat-params HTTP handler stub (PRV-04).

Wave 0 (RED): All tests fail with pytest.fail() until Wave 1 creates
src/state_daemon/hooks.py.

The handler is tested as a pure async function (body: dict -> dict),
not via HTTP — server.py has no framework bound yet (Phase 027 stub).
"""
from __future__ import annotations

import pytest

from state_daemon.hooks import handle_chat_params  # ImportError until Wave 1


# ---------------------------------------------------------------------------
# PRV-04: /hook/chat-params handler — shape and profile tests
# ---------------------------------------------------------------------------


async def test_chat_params_handler_returns_valid_shape() -> None:
    """Handler response has all required chat.params output keys."""
    pytest.fail("RED: handle_chat_params not yet implemented")


async def test_chat_params_default_profile() -> None:
    """No step_profile in body returns balanced defaults (temperature=0.5, options={})."""
    pytest.fail("RED: handle_chat_params not yet implemented")


async def test_chat_params_quality_profile() -> None:
    """step_profile='quality' returns temperature=0.2, options.thinking_budget_tokens=4000."""
    pytest.fail("RED: handle_chat_params not yet implemented")
