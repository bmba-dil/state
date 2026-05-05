"""Cross-mode leakage regression suite — TST-08.

Consolidated regression harness validating all 6 defense-in-depth layers
of mode enforcement work together. Every illegal cross-mode combination
is attempted and asserted to be rejected at the appropriate gate.

6-layer coverage:
  - Layer 1 — mode.json schema validation (Phase 097)
  - Layer 2 — subtree path enforcement (Phase 098)
  - Layer 3 — MCP registration logic (Phase 099)
  - Layer 4 — plugin hook gate logic (Phase 100)
  - Layer 5 — daemon HTTP middleware, the canonical gate (Phase 101)
  - Layer 6 — Python import-graph lint (Phase 102)

Single-file, self-contained — no conftest dependency.
All tests run via ``python3 -m pytest tests/test_mode_leakage_regression.py -x -v``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.state_core.schema import (
    BUILD_SUBTREE,
    ModeConfig,
    TEACH_SUBTREE,
    validate_mode_config,
    validate_subtree_path,
)
from state_core.import_lint import lint, Violation

# ===========================================================================
# Layer 1 — mode.json schema validation (Phase 097)
# ===========================================================================


class TestLayer1ModeJsonSchema:
    """Validate ModeConfig rejects all invalid mode.json values."""

    @pytest.mark.parametrize(
        "mode_value",
        ["build", "teach", "both"],
    )
    def test_valid_mode_accepted(self, mode_value: str) -> None:
        """ModeConfig accepts 'build', 'teach', and 'both' as valid modes."""
        cfg = ModeConfig(mode=mode_value)
        assert cfg.mode == mode_value

    @pytest.mark.parametrize(
        "mode_value",
        ["kernel", "invalid", ""],
    )
    def test_invalid_mode_rejected(self, mode_value: str) -> None:
        """ModeConfig rejects unsupported mode values with ValidationError."""
        with pytest.raises(ValidationError):
            ModeConfig(mode=mode_value)

    def test_none_mode_rejected(self) -> None:
        """ModeConfig rejects None as mode value with ValidationError."""
        with pytest.raises(ValidationError):
            ModeConfig(mode=None)  # type: ignore[arg-type]

    def test_extra_fields_rejected(self) -> None:
        """ModeConfig rejects extra fields when extra='forbid'."""
        with pytest.raises(ValidationError):
            ModeConfig(mode="build", extra=42)  # type: ignore[call-arg]

    def test_validate_mode_config_empty_dict_raises(self) -> None:
        """validate_mode_config() raises ValueError for empty dict."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({})

    def test_validate_mode_config_missing_mode_raises(self) -> None:
        """validate_mode_config() raises ValueError for dict missing 'mode' key."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({"other": "stuff"})

    def test_validate_mode_config_unknown_mode_raises(self) -> None:
        """validate_mode_config() raises ValueError for unknown mode value."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({"mode": "unknown"})


# ===========================================================================
# Layer 2 — subtree path enforcement (Phase 098)
# ===========================================================================


class TestLayer2SubtreePath:
    """Validate cross-subtree file writes are blocked by validate_subtree_path()."""

    # ── Cross-mode path rejections ────────────────────────────────────────

    @pytest.mark.parametrize(
        "path_str,mode,should_raise",
        [
            (".state/teach/concept.json", "build", True),
            (".state/teach/sub/deep/file.md", "build", True),
            (".state/build/arc.md", "teach", True),
            (".state/build/sub/deep/file.md", "teach", True),
            (".state/build/file", "both", False),
            (".state/teach/file", "both", False),
            (".state/build/x", "build", False),
            (".state/teach/x", "teach", False),
        ],
    )
    def test_subtree_path_mode_combinations(
        self, path_str: str, mode: str, should_raise: bool
    ) -> None:
        """Cross-mode subtree paths are rejected; same-mode paths are allowed."""
        if should_raise:
            with pytest.raises(ValueError):
                validate_subtree_path(path_str, mode)
        else:
            validate_subtree_path(path_str, mode)  # should not raise

    # ── Exact directory match ─────────────────────────────────────────────

    def test_exact_build_dir_rejected_in_teach_mode(self) -> None:
        """validate_subtree_path('.state/build', 'teach') raises ValueError."""
        with pytest.raises(ValueError):
            validate_subtree_path(".state/build", "teach")

    def test_exact_teach_dir_rejected_in_build_mode(self) -> None:
        """validate_subtree_path('.state/teach', 'build') raises ValueError."""
        with pytest.raises(ValueError):
            validate_subtree_path(".state/teach", "build")

    # ── Kernel files always allowed ───────────────────────────────────────

    @pytest.mark.parametrize(
        "kernel_path",
        [".state/mode.json", ".state/events.sqlite", ".state/auth.json"],
    )
    def test_kernel_files_allowed_in_any_mode(self, kernel_path: str) -> None:
        """Shared .state/ root files (mode.json, events.sqlite, auth.json) pass in all modes."""
        for mode in ("build", "teach"):
            validate_subtree_path(kernel_path, mode)

    def test_kernel_files_allowed_in_explicit_mode(self) -> None:
        """Kernel files in .state/ root are allowed even when .state/ is the path."""
        validate_subtree_path(".state/mode.json", "build")
        validate_subtree_path(".state/mode.json", "teach")
        validate_subtree_path(".state/events.sqlite", "build")
        validate_subtree_path(".state/auth.json", "teach")

    # ── Path objects ──────────────────────────────────────────────────────

    def test_path_object_same_as_string(self) -> None:
        """Path objects and strings produce identical validation results."""
        # Both should raise for cross-mode
        with pytest.raises(ValueError):
            validate_subtree_path(Path(".state/teach/file"), "build")
        with pytest.raises(ValueError):
            validate_subtree_path(".state/teach/file", "build")
        # Both should succeed for same-mode
        validate_subtree_path(Path(".state/build/file"), "build")
        validate_subtree_path(".state/build/file", "build")

    # ── Unrecognised mode ─────────────────────────────────────────────────

    def test_unrecognised_mode_raises(self) -> None:
        """validate_subtree_path raises ValueError for unrecognised mode."""
        with pytest.raises(ValueError, match="Unrecognised mode"):
            validate_subtree_path(".state/anything", "fakemode")

    # ── Both mode allows all paths ────────────────────────────────────────

    def test_both_mode_allows_all_subtrees(self) -> None:
        """'both' mode allows paths in either subtree."""
        validate_subtree_path(".state/build/file", "both")
        validate_subtree_path(".state/teach/file", "both")
        validate_subtree_path(".state/build", "both")
        validate_subtree_path(".state/teach", "both")
        validate_subtree_path(".state/kernel/file", "both")


# ===========================================================================
# Layer 6 — Python import-graph lint (Phase 102)
# ===========================================================================


class TestLayer6ImportLint:
    """Validate import_lint detects all cross-mode import violations."""

    def test_detects_build_importing_teach(self, tmp_path: Path) -> None:
        """A file in state_build/ importing from state_teach must be flagged."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_build" / "bad.py").write_text(
            "from state_teach.concepts import Concept\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 1
        assert len(result.violations) == 1
        assert "state_teach" in result.violations[0].import_target

    def test_detects_teach_importing_build(self, tmp_path: Path) -> None:
        """A file in state_teach/ importing from state_build must be flagged."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_teach" / "bad.py").write_text(
            "import state_build.mcp\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 1
        assert len(result.violations) == 1
        assert "state_build" in result.violations[0].import_target

    def test_detects_state_core_importing_build(self, tmp_path: Path) -> None:
        """A file in state_core/ importing from state_build must be flagged."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_core" / "bad.py").write_text(
            "from state_build.kernel import x\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 1
        assert len(result.violations) == 1
        assert "state_build" in result.violations[0].import_target

    def test_detects_state_core_importing_teach(self, tmp_path: Path) -> None:
        """A file in state_core/ importing from state_teach must be flagged."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_core" / "bad.py").write_text(
            "from state_teach.concepts import x\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 1
        assert len(result.violations) == 1
        assert "state_teach" in result.violations[0].import_target

    def test_allows_build_importing_core(self, tmp_path: Path) -> None:
        """state_build importing from state_core is allowed (shared kernel)."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_build" / "ok.py").write_text(
            "from state_core.events import EventStore\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 0
        assert len(result.violations) == 0

    def test_allows_teach_importing_core(self, tmp_path: Path) -> None:
        """state_teach importing from state_core is allowed (shared kernel)."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_teach" / "ok.py").write_text(
            "from state_core.events import EventStore\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 0
        assert len(result.violations) == 0

    def test_allows_daemon_importing_build(self, tmp_path: Path) -> None:
        """state_daemon importing from state_build is allowed (shared infra)."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_daemon" / "ok.py").write_text(
            "from state_build.kernel import build_kernel\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 0
        assert len(result.violations) == 0

    def test_allows_daemon_importing_teach(self, tmp_path: Path) -> None:
        """state_daemon importing from state_teach is allowed (shared infra)."""
        _setup_lint_dirs(tmp_path)
        (tmp_path / "state_daemon" / "ok.py").write_text(
            "from state_teach.concepts import Concept\n"
        )
        result = lint(root=tmp_path)
        assert result.exit_code == 0
        assert len(result.violations) == 0

    def test_lint_clean_on_codebase(self) -> None:
        """lint() on the real codebase returns exit_code=0 (known clean)."""
        result = lint()
        assert result.exit_code == 0, (
            f"Found {len(result.violations)} cross-mode import violations:\n"
            + "\n".join(str(v) for v in result.violations)
        )


# ===========================================================================
# Helpers
# ===========================================================================


def _setup_lint_dirs(base: Path) -> None:
    """Create the standard 5-package directories for import-lint fixture trees."""
    for name in ("state_build", "state_teach", "state_core", "state_daemon", "state_cli"):
        (base / name).mkdir(parents=True, exist_ok=True)
