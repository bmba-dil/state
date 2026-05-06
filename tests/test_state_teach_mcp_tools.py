"""Tests for state-teach MCP skeleton tools -- Phase 116.

Covers: tool registration count, required names, description token budgets,
skeleton behavior, import lint.
"""

from __future__ import annotations

import asyncio

import pytest
from state_teach.mcp import mcp

TOOLS = mcp._tool_manager.list_tools()

REQUIRED_NAMES = [
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


def test_tool_count() -> None:
    """Exactly 15 tools are registered on the state-teach MCP server."""
    assert len(TOOLS) == 15, f"Expected 15 tools, got {len(TOOLS)}"


def test_required_names_present() -> None:
    """All 14 tool names from MCP-T-03 are registered."""
    registered_names = {t.name for t in TOOLS}
    for name in REQUIRED_NAMES:
        assert name in registered_names, f"Required tool {name!r} not registered"


def test_descriptions_within_token_limit() -> None:
    """Every tool description is <=80 tokens (o200k_base encoding)."""
    import tiktoken

    enc = tiktoken.get_encoding("o200k_base")
    for tool in TOOLS:
        tokens = len(enc.encode(tool.description))
        assert tokens <= 80, (
            f"Tool {tool.name!r} description is {tokens} tokens (limit 80)"
        )


@pytest.mark.asyncio
async def test_all_tools_return_not_implemented() -> None:
    """Every tool returns {'error': 'not_implemented'} when called."""
    for tool in TOOLS:
        fn = tool.fn
        if asyncio.iscoroutinefunction(fn):
            result = await fn()
        else:
            result = fn()
        assert result == {"error": "not_implemented"}, (
            f"Tool {tool.name!r} returned {result!r}"
        )


def test_import_lint_clean() -> None:
    """state_teach.mcp must not introduce cross-mode import violations."""
    from state_core.import_lint import lint

    result = lint()
    assert result.exit_code == 0, (
        f"Found {len(result.violations)} cross-mode import violations:\n"
        + "\n".join(str(v) for v in result.violations)
    )
