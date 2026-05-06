"""Tests for state_teach → state_core shared library wiring — Phase 120.

Verifies that state_teach correctly imports and can use the shared
state_core.auth (load_credentials) and state_core.events (SqliteEventStore)
modules, following the same pattern established by state_build Phase 111.
"""

from __future__ import annotations

import pytest

from state_core.auth import load_credentials
from state_core.events import SqliteEventStore
from state_teach.mcp import (
    SkeletonResponse,
    check_mode_gate,
    mcp,
)


def test_wiring_load_credentials_importable() -> None:
    """load_credentials is importable and callable."""
    assert callable(load_credentials)
    assert load_credentials.__name__ == "load_credentials"


def test_wiring_sqlite_event_store_instantiable() -> None:
    """SqliteEventStore can be instantiated without arguments."""
    store = SqliteEventStore()
    assert isinstance(store, SqliteEventStore)
    assert not store._repair_done


def test_wiring_mcp_server_still_functional() -> None:
    """The mcp FastMCP server still has its registered tools after wiring imports."""
    from mcp.server.fastmcp import FastMCP

    assert isinstance(mcp, FastMCP)
    assert mcp.name == "state-teach"

    tools = mcp._tool_manager.list_tools()
    # At least the 14 skeleton tools registered on the mcp server
    assert len(tools) >= 14


def test_wiring_mode_gate_still_works(tmp_path) -> None:
    """check_mode_gate still works correctly after wiring imports."""
    import json
    from pathlib import Path

    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "build"}))

    with pytest.raises(SystemExit) as exc_info:
        check_mode_gate(tmp_path)
    assert exc_info.value.code == 1


def test_wiring_skeleton_response_still_works() -> None:
    """SkeletonResponse model is still usable after wiring imports."""
    resp = SkeletonResponse(tool="test_tool")
    assert resp.tool == "test_tool"
    assert resp.status == "not_implemented"
    assert isinstance(resp.model_dump(), dict)
