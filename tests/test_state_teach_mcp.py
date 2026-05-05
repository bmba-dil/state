"""Tests for state-teach MCP server scaffold — Phase 115.

Covers: module import, server name, mode-gate validation (reject build,
accept teach/both, handle missing/invalid mode.json), import lint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp.server.fastmcp import FastMCP
from state_teach.mcp import check_mode_gate, mcp


def test_mcp_server_name() -> None:
    """mcp is a FastMCP instance named 'state-teach'."""
    assert isinstance(mcp, FastMCP)
    assert mcp.name == "state-teach"


def test_mode_gate_rejects_build(tmp_path: Path) -> None:
    """check_mode_gate exits with code 1 when mode.json mode is 'build'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "build"}))

    with pytest.raises(SystemExit) as exc_info:
        check_mode_gate(tmp_path)
    assert exc_info.value.code == 1


def test_mode_gate_allows_teach(tmp_path: Path) -> None:
    """check_mode_gate returns normally when mode.json mode is 'teach'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "teach"}))

    check_mode_gate(tmp_path)


def test_mode_gate_allows_both(tmp_path: Path) -> None:
    """check_mode_gate returns normally when mode.json mode is 'both'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "both"}))

    check_mode_gate(tmp_path)


def test_mode_gate_missing_file(tmp_path: Path) -> None:
    """check_mode_gate returns normally when .state/mode.json does not exist."""
    check_mode_gate(tmp_path)


def test_mode_gate_invalid_json(tmp_path: Path) -> None:
    """check_mode_gate exits with code 1 when mode.json is invalid JSON."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text("{not json}")

    with pytest.raises(SystemExit) as exc_info:
        check_mode_gate(tmp_path)
    assert exc_info.value.code == 1
