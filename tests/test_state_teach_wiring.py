"""Tests for state_teach → state_core shared library wiring — Phase 120.

Verifies that state_teach correctly imports and can use the shared
state_core.auth (load_credentials) and state_core.events (SqliteEventStore)
modules, following the same pattern established by state_build Phase 111.
"""

from __future__ import annotations

import pytest

from state_core.auth import load_credentials
from state_core.events import SqliteEventStore
from state_teach.mcp import SkeletonResponse, mcp, _check_mode_gate


def test_wiring_load_credentials_importable() -> None:
    """load_credentials is importable and callable."""
    assert callable(load_credentials)
    assert load_credentials.__name__ == "load_credentials"


def test_wiring_sqlite_event_store_importable() -> None:
    """SqliteEventStore is importable from state_core.events."""
    assert SqliteEventStore is not None


def test_wiring_mcp_server_still_functional() -> None:
    """The mcp FastMCP server still has its registered tools after wiring imports."""
    from mcp.server.fastmcp import FastMCP

    assert isinstance(mcp, FastMCP)
    assert mcp.name == "state-teach"

    tools = mcp._tool_manager._tools
    assert len(tools) >= 14


def test_wiring_mode_gate_still_works(tmp_path) -> None:
    """_check_mode_gate still works correctly after wiring imports."""
    import json
    from pathlib import Path

    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "build"}))

    with pytest.raises(SystemExit) as exc_info:
        _check_mode_gate(tmp_path)
    assert exc_info.value.code == 78


def test_wiring_tool_imports_work() -> None:
    """Tool modules are importable after wiring imports."""
    from state_teach.question_binding import ask_structured
    from state_teach.token_utils import count_tokens, enforce_token_cap

    assert callable(ask_structured)
    assert callable(count_tokens)
    assert callable(enforce_token_cap)
