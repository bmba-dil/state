"""P0-12 tool-name collision regression test.

Validates that the state-build MCP server tool names follow the naming
contract and would not collide with state-teach tool names (future v13).

Covers:
  - All 15 tool names match MCP-B-03 roster
  - No tool name overlaps with planned state-teach tool names
  - Mode-gate rejects state-build startup when mode=teach
  - SkeletonResponse schema is valid
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# ── Tool name sets (MCP-B-03 and state-teach planned names) ─────────

BUILD_TOOL_NAMES = frozenset({
    "plan_step",
    "execute_step",
    "verify_step",
    "discuss_step",
    "research_step",
    "dag_status",
    "arc_show",
    "slice_ship",
    "snapshot_revert",
    "code_review",
    "debug_session",
    "forensics",
    "intel_refresh",
    "pause_work",
    "resume_work",
})

TEACH_TOOL_NAMES = frozenset({
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
})


# ── P0-12: No cross-mode tool name collisions ─────────────────────


class TestToolNameCollisions:
    """P0-12: Ensure state-build and state-teach tool names never overlap."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        """Ensure tests run from project root so imports resolve."""
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_build_tool_count(self) -> None:
        """All 15 state-build tools should be registered."""
        from state_build.mcp import mcp

        actual = set(mcp._tool_manager._tools.keys())
        assert actual == BUILD_TOOL_NAMES, (
            f"Tool mismatch.\n"
            f"Missing: {BUILD_TOOL_NAMES - actual}\n"
            f"Extra:   {actual - BUILD_TOOL_NAMES}"
        )

    def test_no_build_teach_overlap(self) -> None:
        """Build and teach tool names must not collide (P0-12)."""
        overlap = BUILD_TOOL_NAMES & TEACH_TOOL_NAMES
        assert not overlap, (
            f"P0-12 VIOLATION: {len(overlap)} tool name(s) overlap "
            f"between build and teach: {sorted(overlap)}"
        )

    def test_tool_naming_convention(self) -> None:
        """Tool names must use snake_case and not contain hyphens."""
        for name in BUILD_TOOL_NAMES:
            assert "-" not in name, f"Tool name uses hyphen: {name!r}"
            assert name == name.lower(), f"Tool name not lowercase: {name!r}"
            assert " " not in name, f"Tool name contains space: {name!r}"


# ── Mode-gate enforcement ─────────────────────────────────────────


class TestModeGate:
    """Layer-3 (MCP registration) mode gate enforcement."""

    @pytest.fixture(autouse=True)
    def _chdir(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        os.chdir(project_root)

    def test_mode_gate_allows_build(self) -> None:
        """Mode gate should pass when mode.json has mode=build."""
        from state_build.mcp import _check_mode_gate

        _check_mode_gate()  # Must not raise

    def test_mode_gate_rejects_teach(self, tmp_path: Path) -> None:
        """Mode gate should exit when mode.json has mode=teach."""
        mode_file = tmp_path / ".state" / "mode.json"
        mode_file.parent.mkdir(parents=True, exist_ok=True)
        mode_file.write_text(json.dumps({"mode": "teach"}))

        # Patch cwd to use temp dir
        import state_build.mcp as mcp_mod

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with pytest.raises(SystemExit) as exc_info:
                mcp_mod._check_mode_gate()
            assert exc_info.value.code == 78
        finally:
            os.chdir(original_cwd)

    def test_mode_gate_allows_both(self, tmp_path: Path) -> None:
        """Mode gate should pass when mode.json has mode=both."""
        mode_file = tmp_path / ".state" / "mode.json"
        mode_file.parent.mkdir(parents=True, exist_ok=True)
        mode_file.write_text(json.dumps({"mode": "both"}))

        import state_build.mcp as mcp_mod

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            mcp_mod._check_mode_gate()  # Must not raise
        finally:
            os.chdir(original_cwd)


# ── SkeletonResponse schema ───────────────────────────────────────


class TestSkeletonResponse:
    """Validate the SkeletonResponse pydantic model."""

    def test_defaults(self) -> None:
        from state_build.mcp import SkeletonResponse

        r = SkeletonResponse(tool="test")
        assert r.tool == "test"
        assert r.status == "not_implemented"
        assert r.task_id is None

    def test_with_task_id(self) -> None:
        from state_build.mcp import SkeletonResponse

        r = SkeletonResponse(tool="plan_step", task_id="abc-123")
        assert r.task_id == "abc-123"

    def test_json_serialization(self) -> None:
        from state_build.mcp import SkeletonResponse

        r = SkeletonResponse(tool="dag_status")
        data = r.model_dump()
        assert data == {
            "tool": "dag_status",
            "status": "not_implemented",
            "task_id": None,
        }
        json_str = r.model_dump_json()
        assert '"tool":"dag_status"' in json_str
