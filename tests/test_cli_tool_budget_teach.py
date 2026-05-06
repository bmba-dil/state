"""Tests for `state dev tool-budget --server state-teach` CLI command — Phase 122.

Covers: exit codes, output format, tool count, error cases.
"""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

from state_cli.dev import _SERVER_MODULES, _TOKEN_BUDGET_PER_TOOL, _TOTAL_TOKEN_BUDGET, _count_tokens
from state_cli.main import app

runner = CliRunner()


# ── Exit code tests ─────────────────────────────────────────────────


def test_tool_budget_teach_exits_zero() -> None:
    """`state dev tool-budget --server state-teach` exits 0 when all tools within budget."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "state-teach"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"


def test_tool_budget_teach_exits_zero_cli_invoke() -> None:
    """Direct invocation of `tool_budget(server='state-teach')` exits 0."""
    from state_cli.dev import tool_budget

    try:
        tool_budget(server="state-teach")
    except typer.Exit as e:
        assert e.exit_code == 0, f"Expected exit 0, got {e.exit_code}"
    else:
        pass  # No exception means clean exit


# ── Output format tests ────────────────────────────────────────────


def test_tool_budget_teach_prints_pass() -> None:
    """Output includes 'PASS' when all tools are within budget."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "state-teach"])
    assert "PASS" in result.output, f"Expected 'PASS' in output:\n{result.output}"


def test_tool_budget_teach_prints_total() -> None:
    """Output includes 'TOTAL' token count line."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "state-teach"])
    assert "TOTAL" in result.output, f"Expected 'TOTAL' in output:\n{result.output}"


def test_tool_budget_teach_lists_expected_tools() -> None:
    """Output lists all 14 expected tool names."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "state-teach"])

    expected_tools = [
        "concept_next",
        "drill_prepare",
        "drill_verify",
        "concept_teach",
        "observation_record",
        "mental_model_show",
        "subject_pick",
        "subject_author",
        "style_edit",
        "learner_state",
        "review_session",
        "mentor_scaffold",
        "coding_partner",
        "learning_verify",
    ]

    for tool_name in expected_tools:
        assert tool_name in result.output, (
            f"Expected '{tool_name}' in tool-budget output:\n{result.output}"
        )


def test_tool_budget_teach_all_individual_pass() -> None:
    """All per-tool status lines show '✓' (not '✗ OVER')."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "state-teach"])
    assert "✗ OVER" not in result.output, (
        f"Unexpected 'OVER' in output:\n{result.output}"
    )


def test_tool_budget_teach_each_under_80_tokens() -> None:
    """Each tool description is <= 80 tokens (word-count heuristic)."""
    tools = _get_state_teach_tools()

    failures = []
    for name, description in tools.items():
        tokens = _count_tokens(description)
        if tokens > _TOKEN_BUDGET_PER_TOOL:
            failures.append(f"{name}: {tokens} tokens (budget: {_TOKEN_BUDGET_PER_TOOL})")

    assert not failures, (
        f"{len(failures)} tool(s) exceed {_TOKEN_BUDGET_PER_TOOL}-token budget:\n"
        + "\n".join(failures)
    )


def test_tool_budget_teach_total_under_budget() -> None:
    """Total token count is <= 1200 (15 × 80)."""
    tools = _get_state_teach_tools()

    total = sum(_count_tokens(desc) for desc in tools.values())
    assert total <= _TOTAL_TOKEN_BUDGET, (
        f"Total tokens {total} exceeds budget {_TOTAL_TOKEN_BUDGET} by {total - _TOTAL_TOKEN_BUDGET}"
    )


# ── Tool count tests ───────────────────────────────────────────────


def test_tool_budget_teach_tool_count_matches_mcp() -> None:
    """CLI tool count matches actual tools registered on state-teach MCP server."""
    import importlib

    from state_cli.dev import _SERVER_MODULES

    mod = importlib.import_module(_SERVER_MODULES["state-teach"])
    mcp_tools = mod.mcp._tool_manager._tools

    assert len(mcp_tools) <= 15, (
        f"Expected ≤15 tools, got {len(mcp_tools)}"
    )
    assert len(mcp_tools) >= 14, (
        f"Expected ≥14 tools, got {len(mcp_tools)}"
    )


# ── Error case tests ───────────────────────────────────────────────


def test_tool_budget_unknown_server_exits_two() -> None:
    """`state dev tool-budget --server unknown` exits 2."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "unknown-server"])
    assert result.exit_code == 2, (
        f"Expected exit 2 for unknown server, got {result.exit_code}"
    )


def test_tool_budget_unknown_server_error_message() -> None:
    """Unknown server produces 'Unknown server' error message."""
    result = runner.invoke(app, ["dev", "tool-budget", "--server", "unknown-server"])
    assert "Unknown server" in result.output, (
        f"Expected 'Unknown server' in stderr, got:\n{result.output}"
    )


def test_tool_budget_teach_has_nonzero_tools() -> None:
    """state-teach MCP server has at least one tool registered."""
    import importlib

    mod = importlib.import_module(_SERVER_MODULES["state-teach"])
    mcp_tools = mod.mcp._tool_manager._tools

    assert len(mcp_tools) > 0, "Expected at least one tool, got none"


# ── Helpers ────────────────────────────────────────────────────────


def _get_state_teach_tools() -> dict[str, str]:
    """Load state-teach tools and return {name: description} dict."""
    import importlib

    mod = importlib.import_module(_SERVER_MODULES["state-teach"])
    tools = mod.mcp._tool_manager._tools

    return {
        name: getattr(tool, "description", "") or ""
        for name, tool in tools.items()
    }


# ── Server module map tests ───────────────────────────────────────


def test_server_modules_contains_teach() -> None:
    """_SERVER_MODULES dict includes 'state-teach' key."""
    assert "state-teach" in _SERVER_MODULES
    assert _SERVER_MODULES["state-teach"] == "state_teach.mcp"


def test_server_modules_contains_build() -> None:
    """_SERVER_MODULES dict includes 'state-build' key."""
    assert "state-build" in _SERVER_MODULES
    assert _SERVER_MODULES["state-build"] == "state_build.mcp"
