"""Import-graph lint tests — MODE-06 / TST-07 enforcement.

Verifies that ``state_core.import_lint`` correctly detects cross-mode
import violations between ``state_build`` and ``state_teach``, while
allowing allowed imports from ``state_core``, ``state_daemon``, and
``state_cli``.

TDD: Task 1 RED — tests will fail until ``src/state_core/import_lint.py`` is created.
"""

from __future__ import annotations

from pathlib import Path

from state_core.import_lint import lint

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


# ── state_core violation detection ──────────────────────────────────────


def test_detects_state_core_importing_build(tmp_path: Path) -> None:
    """A file in state_core/ importing from state_build must be flagged."""
    _setup_dirs(tmp_path)

    core_dir = tmp_path / "state_core"
    (core_dir / "bad.py").write_text("from state_build.kernel import x\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "state_build" in v.import_target


def test_detects_state_core_importing_teach(tmp_path: Path) -> None:
    """A file in state_core/ importing from state_teach must be flagged."""
    _setup_dirs(tmp_path)

    core_dir = tmp_path / "state_core"
    (core_dir / "bad.py").write_text("from state_teach.concepts import x\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "state_teach" in v.import_target


# ── Import form coverage ─────────────────────────────────────────────────


def test_detects_short_form_import(tmp_path: Path) -> None:
    """``from state_teach import concepts`` (short module path) is detected."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "bad.py").write_text("from state_teach import concepts\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "state_teach" in v.import_target


# ── CLI exit-code test ───────────────────────────────────────────────────


def test_cli_exit_code(tmp_path: Path) -> None:
    """``lint()`` returns correct exit codes: 0 on clean, 1 on violations.

    Also verifies the real ``python3 -m state_core.import_lint`` exits 0
    on the current codebase (which is known clean).
    """
    import subprocess
    import sys

    # Test 1: lint() on clean tmp dir returns exit_code=0
    _setup_dirs(tmp_path)
    result = lint(root=tmp_path)
    assert result.exit_code == 0, f"Expected exit_code=0 on clean dir, got {result.exit_code}"

    # Test 2: lint() on dir with cross-mode violation returns exit_code=1
    build_dir = tmp_path / "state_build"
    (build_dir / "bad.py").write_text("from state_teach.concepts import Concept\n")
    result = lint(root=tmp_path)
    assert result.exit_code == 1, f"Expected exit_code=1 on violation, got {result.exit_code}"
    assert len(result.violations) == 1

    # Test 3: Real subprocess invocation exits 0 on the clean codebase
    proc = subprocess.run(
        [sys.executable, "-m", "state_core.import_lint"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"CLI exited {proc.returncode} on clean codebase.\n"
        f"stderr: {proc.stderr}"
    )


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


def test_violation_str_representation() -> None:
    """``str(Violation)`` produces the canonical ``file:line: forbidden import of target`` format."""
    from state_core.import_lint import Violation

    v = Violation(source_file=Path("src/state_build/bad.py"), line_num=5, import_target="state_teach.concepts")
    s = str(v)
    assert "src/state_build/bad.py:5" in s
    assert "forbidden import of state_teach.concepts" in s


def test_syntax_error_in_file_handled(tmp_path: Path) -> None:
    """A .py file with a syntax error is skipped, not crashing the linter."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "broken.py").write_text("def foo(:\n")  # syntax error

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_pycache_skipped(tmp_path: Path) -> None:
    """Files inside ``__pycache__/`` directories are ignored."""
    _setup_dirs(tmp_path)

    pycache_dir = tmp_path / "state_build" / "__pycache__"
    pycache_dir.mkdir(parents=True, exist_ok=True)
    (pycache_dir / "cached.py").write_text("from state_teach.concepts import Concept\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0, f"Expected no violations (pycache skipped), got: {result.violations}"
    assert len(result.violations) == 0


def test_from_dot_import_allowed(tmp_path: Path) -> None:
    """``from . import foo`` (module=None relative import) is always allowed within same package."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    (build_dir / "rel.py").write_text("from . import kernel\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_missing_package_directories_graceful(tmp_path: Path) -> None:
    """When some expected package directories do not exist, the linter proceeds without error."""
    # Only create state_build — state_teach, state_core, etc. are missing
    (tmp_path / "state_build").mkdir(parents=True)
    (tmp_path / "state_build" / "ok.py").write_text("# nothing forbidden\n")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


def test_unreadable_file_handled(tmp_path: Path) -> None:
    """A .py file that cannot be read (e.g., broken symlink) is skipped gracefully."""
    _setup_dirs(tmp_path)

    build_dir = tmp_path / "state_build"
    broken = build_dir / "broken.py"
    broken.symlink_to("/nonexistent/path/for/testing")

    result = lint(root=tmp_path)
    assert result.exit_code == 0
    assert len(result.violations) == 0


# ── Helpers ─────────────────────────────────────────────────────────────


def _setup_dirs(base: Path) -> None:
    """Create the standard src/ subdirectories inside base."""
    for name in ("state_build", "state_teach", "state_core", "state_daemon", "state_cli"):
        (base / name).mkdir(parents=True, exist_ok=True)
