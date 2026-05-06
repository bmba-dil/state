"""Integration tests for state-teach MCP server — Phase 123.

Validates the MCP server contract: tool registration, tool invocation,
mode-gate enforcement, import lint, and structural integrity. Uses
direct Python imports for reliability.

Mirrors the Phase 114 pattern for state-build.
Subprocess E2E test against opencode binary is deferred to a later
phase when opencode MCP client test infrastructure is available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ── Server Registration ───────────────────────────────────────────


class TestServerRegistration:
    """Validate server name, tool count, and description budgets."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_server_name(self) -> None:
        """Server is registered as 'state-teach'."""
        from state_teach.mcp import mcp

        assert mcp.name == "state-teach"

    def test_tool_count(self) -> None:
        """14 tools registered — MCP-T-03."""
        from state_teach.mcp import mcp

        tools = mcp._tool_manager._tools
        assert len(tools) == 15, f"Expected 15 tools, got {len(tools)}"

    def test_tool_descriptions_within_budget(self) -> None:
        """Every tool description is ≤80 tokens (o200k_base) — MCP-T-02."""
        import tiktoken

        from state_teach.mcp import mcp

        enc = tiktoken.get_encoding("o200k_base")
        tools = mcp._tool_manager._tools
        failures: list[str] = []

        for name, tool in tools.items():
            desc = getattr(tool, "description", "") or ""
            assert desc, f"Tool {name!r} has no description"
            token_count = len(enc.encode(desc))
            if token_count > 80:
                failures.append(f"{name}: {token_count} tokens (budget: 80)")

        assert not failures, (
            f"{len(failures)} tool(s) exceed 80-token budget:\n"
            + "\n".join(failures)
        )


# ── Tool Invocation ────────────────────────────────────────────────


class TestToolInvocation:
    """Validate tools can be invoked and return correct responses."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_all_14_tools_invocable(self) -> None:
        """All 14 registered tools are directly callable and return SkeletonResponse."""
        import state_teach.mcp as mcp_mod
        from state_teach.mcp import SkeletonResponse

        tools = mcp_mod.mcp._tool_manager._tools
        for name in tools:
            fn = getattr(mcp_mod, name, None)
            assert fn is not None, f"Cannot find tool function for {name!r}"

            result = fn()
            assert isinstance(result, SkeletonResponse), (
                f"{name}: returned {type(result).__name__}, expected SkeletonResponse"
            )
            assert result.tool == name, (
                f"{name}: tool field is '{result.tool}', expected '{name}'"
            )
            assert result.status == "not_implemented", (
                f"{name}: status is '{result.status}', expected 'not_implemented'"
            )

    def test_skeleton_response_structure(self) -> None:
        """SkeletonResponse has required fields tool and status."""
        from state_teach.mcp import SkeletonResponse

        schema = SkeletonResponse.model_json_schema()
        assert "tool" in schema.get("properties", {}), "Missing 'tool' field in schema"
        assert "status" in schema.get("properties", {}), "Missing 'status' field in schema"

    def test_question_binding_integrated(self) -> None:
        """question_binding module is importable and functional from integration context."""
        from state_teach.question_binding import Answer, Option, Question, ask_structured

        questions = [
            Question(
                question="Pick a language?",
                header="Language",
                options=[Option(label="Python", description="Python 3.12+")],
                multiple=False,
            )
        ]
        answers = ask_structured(questions)
        assert len(answers) == 1
        assert isinstance(answers[0], Answer)
        assert len(answers[0].selected_labels) == 1


# ── Mode Gate Integration ──────────────────────────────────────────


class TestModeGateIntegration:
    """Integration-level mode-gate tests against real JSON files."""

    def test_mode_gate_blocks_build(self, tmp_path: Path) -> None:
        """_check_mode_gate raises SystemExit(78) when mode=build."""
        from state_teach.mcp import _check_mode_gate

        state_dir = tmp_path / ".state"
        state_dir.mkdir()
        mode_file = state_dir / "mode.json"
        mode_file.write_text(json.dumps({"mode": "build"}))

        with pytest.raises(SystemExit) as exc_info:
            _check_mode_gate(tmp_path)
        assert exc_info.value.code == 78

    def test_mode_gate_allows_teach(self, tmp_path: Path) -> None:
        """_check_mode_gate returns normally when mode=teach."""
        from state_teach.mcp import _check_mode_gate

        state_dir = tmp_path / ".state"
        state_dir.mkdir()
        mode_file = state_dir / "mode.json"
        mode_file.write_text(json.dumps({"mode": "teach"}))

        _check_mode_gate(tmp_path)  # Must not raise


# ── Structural Integrity ───────────────────────────────────────────


class TestStructuralIntegrity:
    """Validate import-lint and module structure."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_import_lint_clean(self) -> None:
        """No cross-mode import violations in state_teach."""
        from state_core.import_lint import lint

        result = lint()
        assert result.exit_code == 0, (
            f"Found {len(result.violations)} cross-mode import violations:\n"
            + "\n".join(str(v) for v in result.violations)
        )

    def test_expected_submodules_importable(self) -> None:
        """All state_teach submodules are importable."""
        expected_modules = [
            "state_teach.mcp",
            "state_teach.question_binding",
            "state_teach.observations",
            "state_teach.tokens",
            "state_teach.drill",
            "state_teach.kernel",
            "state_teach.concepts",
            "state_teach.mental_model",
        ]
        import importlib

        failures: list[str] = []
        for module_name in expected_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failures.append(f"{module_name}: {e}")

        assert not failures, (
            f"{len(failures)} module(s) failed to import:\n"
            + "\n".join(failures)
        )
