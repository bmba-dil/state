"""Tests for state-teach MCP server scaffold — Phase 115.

Covers: module import, server name, mode-gate validation (reject build,
accept teach/both, handle missing/invalid mode.json), import lint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from state_teach.mcp import SkeletonResponse, _check_mode_gate, mcp


def test_mcp_server_name() -> None:
    """mcp is a FastMCP instance named 'state-teach'."""
    assert isinstance(mcp, FastMCP)
    assert mcp.name == "state-teach"


def test_mode_gate_rejects_build(tmp_path: Path) -> None:
    """_check_mode_gate exits with code 78 when mode.json mode is 'build'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "build"}))

    with pytest.raises(SystemExit) as exc_info:
        _check_mode_gate(tmp_path)
    assert exc_info.value.code == 78


def test_mode_gate_allows_teach(tmp_path: Path) -> None:
    """_check_mode_gate returns normally when mode.json mode is 'teach'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "teach"}))

    _check_mode_gate(tmp_path)


def test_mode_gate_allows_both(tmp_path: Path) -> None:
    """_check_mode_gate returns normally when mode.json mode is 'both'."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "both"}))

    _check_mode_gate(tmp_path)


def test_mode_gate_missing_file(tmp_path: Path) -> None:
    """_check_mode_gate returns normally when .state/mode.json does not exist."""
    _check_mode_gate(tmp_path)


def test_mode_gate_invalid_json(tmp_path: Path) -> None:
    """_check_mode_gate returns normally when mode.json is invalid JSON (leniency matching Phase 112)."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text("{not json}")

    _check_mode_gate(tmp_path)  # Must not raise — corrupt JSON allows startup


def test_mode_gate_invalid_mode_value(tmp_path: Path) -> None:
    """_check_mode_gate exits with code 78 when mode.json has an unsupported mode value."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"
    mode_file.write_text(json.dumps({"mode": "kernel"}))

    with pytest.raises(SystemExit) as exc_info:
        _check_mode_gate(tmp_path)
    assert exc_info.value.code == 78


def test_import_lint_clean() -> None:
    """state_teach.mcp must not introduce cross-mode import violations."""
    from state_core.import_lint import lint

    result = lint()
    assert result.exit_code == 0, (
        f"Found {len(result.violations)} cross-mode import violations:\n"
        + "\n".join(str(v) for v in result.violations)
    )


# ── Phase 116: Tool registration and description budget tests ──


def _count_words(text: str) -> int:
    """Word-count heuristic matching state_cli.dev._count_tokens."""
    return len(text.split())


EXPECTED_TOOLS: list[str] = [
    "coding_partner",
    "concept_next",
    "concept_teach",
    "drill_prepare",
    "drill_verify",
    "knowledge_check",
    "learner_state",
    "learning_verify",
    "mental_model_show",
    "mentor_scaffold",
    "observation_record",
    "review_session",
    "style_edit",
    "subject_author",
    "subject_pick",
]


def test_all_tools_registered() -> None:
    """All 14 teach-mode tools from MCP-T-03 are registered on the mcp instance."""
    tools = mcp._tool_manager._tools
    names = sorted(tools.keys())
    assert names == sorted(EXPECTED_TOOLS), (
        f"Expected {len(EXPECTED_TOOLS)} tools, got {len(names)}. "
        f"Missing: {set(EXPECTED_TOOLS) - set(names)}. "
        f"Extra: {set(names) - set(EXPECTED_TOOLS)}."
    )


def test_tool_description_token_budget() -> None:
    """Every tool description is <=80 words and total <=1200 words."""
    tools = mcp._tool_manager._tools
    total = 0
    failures: list[str] = []

    for name in EXPECTED_TOOLS:
        tool = tools[name]
        description = getattr(tool, "description", "") or ""
        words = _count_words(description)
        total += words
        if words > 80:
            failures.append(f"{name}: {words} words (budget: 80)")
        assert description, f"{name} has empty description"

    assert not failures, (
        f"{len(failures)} tool(s) exceed 80-word budget:\n" + "\n".join(failures)
    )
    assert total <= 1200, (
        f"Total description words {total} exceeds 1200 budget "
        f"by {total - 1200} words"
    )


def test_skeleton_tools_return_not_implemented() -> None:
    """All 14 skeleton tools return SkeletonResponse with status='not_implemented'."""
    tools = mcp._tool_manager._tools
    for name in EXPECTED_TOOLS:
        tool = tools[name]
        result = tool.fn()
        assert isinstance(result, SkeletonResponse), (
            f"{name} returned {type(result).__name__}, expected SkeletonResponse"
        )
        assert result.tool == name, (
            f"{name}: tool field is '{result.tool}', expected '{name}'"
        )
        assert result.status == "not_implemented", (
            f"{name}: status is '{result.status}', expected 'not_implemented'"
        )


def test_mode_gate_still_works_after_tool_registration(tmp_path: Path) -> None:
    """Phase 116 tool additions must not break the Phase 121 mode-gate."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    mode_file = state_dir / "mode.json"

    # Build mode must still block
    mode_file.write_text(json.dumps({"mode": "build"}))
    with pytest.raises(SystemExit) as exc_info:
        _check_mode_gate(tmp_path)
    assert exc_info.value.code == 78

    # Teach mode must still allow
    mode_file.write_text(json.dumps({"mode": "teach"}))
    _check_mode_gate(tmp_path)  # no exception
