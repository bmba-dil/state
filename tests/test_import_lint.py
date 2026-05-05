"""Import-graph lint tests — MODE-06 / TST-07 enforcement.

Verifies that ``state_core.import_lint`` correctly detects cross-mode
import violations between ``state_build`` and ``state_teach``, while
allowing allowed imports from ``state_core``, ``state_daemon``, and
``state_cli``.

TDD: Task 1 RED — tests will fail until ``src/state_core/import_lint.py`` is created.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from state_core.import_lint import CheckResult, Violation, lint


# ── Real-codebase test ──────────────────────────────────────────────────


def test_lint_clean_codebase_passes() -> None:
    """Verify the current codebase has no cross-mode import violations."""
    result = lint()
    assert result.exit_code == 0, (
        f"Found {len(result.violations)} cross-mode import violations:\n"
        + "\n".join(str(v) for v in result.violations)
    )


# ── Cross-mode violation detection ──────────────────────────────────────


def test_detects_build_importing_teach(tmp_path: Path) -> None:
    """A file in state_build/ importing from state_teach must be flagged."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "bad.py").write_text("from state_teach.concepts import Concept\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "state_teach" in v.import_target


def test_detects_teach_importing_build(tmp_path: Path) -> None:
    """A file in state_teach/ importing from state_build must be flagged."""
    _setup_dirs(tmp_path)

    teach_dir = tmp_path / "state_teach"
    (teach_dir / "bad.py").write_text("import state_build.mcp\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "state_build" in v.import_target


# ── Allowed import paths ────────────────────────────────────────────────


def test_allows_state_core_imports(tmp_path: Path) -> None:
    """state_build importing from state_core is allowed (shared kernel)."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "ok.py").write_text("from state_core.events import EventStore\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_allows_state_daemon_importing_build(tmp_path: Path) -> None:
    """state_daemon importing from state_build is allowed (shared infra)."""
    _setup_dirs(tmp_path)

    daemon_dir = tmp_path / "state_daemon"
    (daemon_dir / "ok.py").write_text("from state_build.kernel import build_kernel\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_allows_state_daemon_importing_teach(tmp_path: Path) -> None:
    """state_daemon importing from state_teach is allowed (shared infra)."""
    _setup_dirs(tmp_path)

    daemon_dir = tmp_path / "state_daemon"
    (daemon_dir / "ok.py").write_text("from state_teach.concepts import Concept\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_allows_state_cli_importing_both(tmp_path: Path) -> None:
    """state_cli importing from either mode is allowed (orchestrator)."""
    _setup_dirs(tmp_path)

    cli_dir = tmp_path / "state_cli"
    (cli_dir / "ok.py").write_text(
        "from state_build.kernel import x\n"
        "from state_teach.concepts import Concept\n"
    )

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


# ── Relative imports ────────────────────────────────────────────────────


def test_relative_imports_within_package_allowed(tmp_path: Path) -> None:
    """Relative imports within the same package must never be flagged."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "rel.py").write_text("from .kernel import x\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


# ── Edge cases ──────────────────────────────────────────────────────────


def test_empty_directory_no_violations(tmp_path: Path) -> None:
    """Scanning directories with no .py files returns clean result."""
    _setup_dirs(tmp_path)

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_violation_message_format(tmp_path: Path) -> None:
    """Each Violation includes source file path, line number, and import target."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "bad.py").write_text("# comment\nfrom state_teach.concepts import Concept\n")

    result = lint(root=tmp_path)
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "bad.py" in str(v.source_file)
    assert v.line_num == 2
    assert "state_teach" in v.import_target


# ── Helpers ─────────────────────────────────────────────────────────────


def _setup_dirs(base: Path) -> None:
    """Create the standard src/ subdirectories inside base."""
    for name in ("state_build", "state_teach", "state_core", "state_daemon", "state_cli"):
        (base / name).mkdir(parents=True, exist_ok=True)
