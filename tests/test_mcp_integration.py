"""Integration tests for state-build MCP server — Phase 114.

Validates the MCP server contract: tool schemas, tool invocation,
and mode-gate enforcement. Uses direct Python imports for reliability.

E2E subprocess test against opencode binary is deferred to a later
phase when opencode MCP client test infrastructure is available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ── Server Import & Registration ──────────────────────────────────


class TestMCPServerRegistration:
    """Validate server import, name, and tool registration."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_server_name(self) -> None:
        from state_build.mcp import mcp

        assert mcp.name == "state-build"

    def test_tool_count(self) -> None:
        from state_build.mcp import mcp

        tools = mcp._tool_manager._tools
        assert len(tools) == 15, f"Expected 15 tools, got {len(tools)}"

    def test_all_tools_have_descriptions(self) -> None:
        from state_build.mcp import mcp

        for name, tool in mcp._tool_manager._tools.items():
            desc = getattr(tool, "description", "")
            assert desc, f"Tool {name!r} has no description"
            # ≤80 tokens check (word-count heuristic)
            token_count = len(desc.split())
            assert token_count <= 80, (
                f"Tool {name!r} description is {token_count} tokens (max 80)"
            )


# ── Tool Schema Validation ────────────────────────────────────────


class TestToolSchemas:
    """Validate tool input/output schemas are valid JSON Schema."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_stateful_tool_signatures_accept_task_id(self) -> None:
        """Stateful tools accept task_id parameter (verified via function call)."""
        import inspect
        from state_build.mcp import (
            plan_step, execute_step, verify_step,
            discuss_step, code_review, debug_session,
        )

        stateful = {
            "plan_step": plan_step,
            "execute_step": execute_step,
            "verify_step": verify_step,
            "discuss_step": discuss_step,
            "code_review": code_review,
            "debug_session": debug_session,
        }
        for name, fn in stateful.items():
            params = list(inspect.signature(fn).parameters.keys())
            assert "task_id" in params, (
                f"Stateful tool {name!r} missing task_id parameter"
            )

    def test_non_stateful_tools_lack_task_id(self) -> None:
        """Non-stateful tools should not accept task_id."""
        import inspect
        from state_build.mcp import (
            dag_status, arc_show, slice_ship, snapshot_revert,
            forensics, intel_refresh, pause_work, resume_work,
            research_step,
        )

        non_stateful = {
            "dag_status": dag_status,
            "arc_show": arc_show,
            "slice_ship": slice_ship,
            "snapshot_revert": snapshot_revert,
            "forensics": forensics,
            "intel_refresh": intel_refresh,
            "pause_work": pause_work,
            "resume_work": resume_work,
            "research_step": research_step,
        }
        for name, fn in non_stateful.items():
            params = list(inspect.signature(fn).parameters.keys())
            assert "task_id" not in params, (
                f"Non-stateful tool {name!r} has unexpected task_id parameter"
            )


# ── Tool Invocation ────────────────────────────────────────────────


class TestToolInvocation:
    """Validate tools can be invoked and return correct responses."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_dag_status_returns_struct(self) -> None:
        from state_build.mcp import dag_status

        r = dag_status()
        assert r.tool == "dag_status"
        assert "scheduler_ready" in r.status
        assert r.task_id is None

    def test_plan_step_with_task_id(self) -> None:
        from state_build.mcp import plan_step

        r = plan_step(task_id="session-001")
        assert r.tool == "plan_step"
        assert r.task_id == "session-001"
        assert r.status == "not_implemented"

    def test_plan_step_without_task_id(self) -> None:
        from state_build.mcp import plan_step

        r = plan_step()
        assert r.tool == "plan_step"
        assert r.task_id is None

    def test_all_15_tools_invocable(self) -> None:
        import state_build.mcp as mcp_mod

        for name in mcp_mod.mcp._tool_manager._tools:
            fn = getattr(mcp_mod, name, None)
            assert fn is not None, f"Cannot find tool function for {name!r}"
            result = fn()
            data = result if isinstance(result, dict) else result.model_dump()
            assert data["tool"] == name
            assert data["status"] == "not_implemented" or "scheduler_ready" in data["status"]


# ── Mode Gate Integration ──────────────────────────────────────────


class TestModeGateIntegration:
    """Integration-level mode gate tests."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_mode_gate_no_file_allows(self) -> None:
        """Server allows startup when .state/mode.json is missing."""
        from state_build.mcp import _check_mode_gate

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(Path, "exists", lambda self: False)
            _check_mode_gate()  # Must not raise

    def test_mode_gate_build_allows(self) -> None:
        """Server allows startup when mode is build."""
        from state_build.mcp import _check_mode_gate

        _check_mode_gate()  # Current project has mode=build
