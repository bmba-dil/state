"""Import-graph lint for mode-isolation enforcement — MODE-06 / TST-07.

Scans all .py files under ``src/state_build/``, ``src/state_teach/``,
``src/state_core/``, ``src/state_daemon/``, and ``src/state_cli/`` for
cross-mode import violations using the stdlib ``ast`` module.

Cardinal rules (ARCHITECTURE.md §Mode Boundary Cardinal Rule):
- ``state_build.*`` MUST NEVER import ``state_teach.*`` (physical silo)
- ``state_teach.*`` MUST NEVER import ``state_build.*`` (physical silo)
- ``state_core.*`` MUST NEVER import from either mode silo (shared kernel)
- ``state_daemon.*`` and ``state_cli.*`` MAY import from both (shared infra)

This is layer 6/6 of mode enforcement defense-in-depth.

Runnable as a CLI: ``python3 -m state_core.import_lint``
Exits 0 when clean, exits 1 and prints violations to stderr otherwise.

Phase 102-01 — PYTHON_IMPORT_GRAPH_LINT
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class Violation:
    """A single cross-mode import violation.

    Attributes:
        source_file: Absolute path to the .py file with the forbidden import.
        line_num: Line number where the import statement appears.
        import_target: The dotted module name being imported (e.g. ``state_teach.concepts``).
    """

    source_file: Path
    line_num: int
    import_target: str

    def __str__(self) -> str:
        """Human-readable violation message: ``file:line: forbidden import of target``."""
        return f"{self.source_file}:{self.line_num}: forbidden import of {self.import_target}"


@dataclass
class CheckResult:
    """Aggregate result of an import-lint scan.

    Attributes:
        exit_code: 0 when clean, 1 when violations found.
        violations: List of detected :class:`Violation` objects.
    """

    exit_code: int
    violations: list[Violation] = field(default_factory=list)


# ── Constants ────────────────────────────────────────────────────────────


# Packages that may import from both mode silos (shared infrastructure)
_ALLOWED_CROSS_IMPORTERS: frozenset[str] = frozenset({"state_daemon", "state_cli"})

# Mode silos — must not import from the OTHER mode
_MODE_SILOS: frozenset[str] = frozenset({"state_build", "state_teach"})

# Shared kernel — must not import from either mode
_SHARED_KERNEL: str = "state_core"

# All packages to scan (any .py file under these directories)
_SCAN_PACKAGES: frozenset[str] = frozenset(
    {"state_build", "state_teach", "state_core", "state_daemon", "state_cli"}
)


# ── Root resolution ──────────────────────────────────────────────────────


def _find_repo_root() -> Path:
    """Walk up from this file's directory to find the repository root.

    Searches for ``pyproject.toml`` or ``.git`` as sentinel files.
    Falls back to ``Path.cwd()`` if neither is found within 10 levels.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd()


def _resolve_root(root: Path | None) -> Path:
    """Resolve the ``src/`` directory to scan for .py files.

    Args:
        root: Explicit directory containing the package subdirectories.
              If ``None``, resolves to ``<repo_root>/src/``.

    Returns:
        Resolved absolute path to the scan root.
    """
    if root is not None:
        return Path(root).resolve()
    repo_root = _find_repo_root()
    return (repo_root / "src").resolve()


# ── Public API ───────────────────────────────────────────────────────────


def lint(root: Path | None = None) -> CheckResult:
    """Scan Python source files for cross-mode import violations.

    Walks all ``.py`` files under the five scannable packages and checks
    every ``import`` / ``from ... import`` statement against the mode
    isolation rules.

    Args:
        root: Directory containing ``state_build/``, ``state_teach/``, etc.
              If ``None``, defaults to ``<repo_root>/src/``.

    Returns:
        A :class:`CheckResult` with ``exit_code=0`` if no violations were
        found, or ``exit_code=1`` with a list of :class:`Violation` objects.
    """
    src_root = _resolve_root(root)
    violations: list[Violation] = []

    for package in sorted(_SCAN_PACKAGES):
        package_dir = src_root / package
        if not package_dir.is_dir():
            continue
        _scan_package(package_dir, package, violations)

    exit_code = 1 if violations else 0
    return CheckResult(exit_code=exit_code, violations=violations)


# ── Internal scanning ────────────────────────────────────────────────────


def _scan_package(package_dir: Path, source_pkg: str, violations: list[Violation]) -> None:
    """Recursively scan all ``.py`` files in a package directory."""
    for py_file in sorted(package_dir.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        _scan_file(py_file, source_pkg, violations)


def _scan_file(file_path: Path, source_pkg: str, violations: list[Violation]) -> None:
    """Parse a single ``.py`` file and check every import statement.

    Handles both ``import x.y`` (:class:`ast.Import`) and ``from x.y import z``
    (:class:`ast.ImportFrom`) nodes.  Relative imports (``from . import ...``)
    are always allowed — they stay within the same package.
    """
    try:
        source_text = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return

    try:
        tree = ast.parse(source_text, filename=str(file_path))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target_pkg = alias.name.split(".")[0]
                if _is_forbidden(source_pkg, target_pkg):
                    violations.append(
                        Violation(
                            source_file=file_path,
                            line_num=node.lineno,
                            import_target=alias.name,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                # Relative import — always allowed within the same package
                continue
            target_pkg = node.module.split(".")[0]
            if _is_forbidden(source_pkg, target_pkg):
                violations.append(
                    Violation(
                        source_file=file_path,
                        line_num=node.lineno,
                        import_target=node.module,
                    )
                )


def _is_forbidden(source_pkg: str, target_pkg: str) -> bool:
    """Check whether ``source_pkg`` importing from ``target_pkg`` is a violation.

    Rules (defense-in-depth layer 6/6):
    - ``state_build`` → ``state_teach``: FORBIDDEN
    - ``state_teach`` → ``state_build``: FORBIDDEN
    - ``state_core`` → ``state_build`` | ``state_teach``: FORBIDDEN
    - ``state_daemon`` / ``state_cli`` → either mode: ALLOWED
    - ``state_build`` / ``state_teach`` → ``state_core``: ALLOWED (shared kernel)
    """
    return (
        # Cross-mode imports between the two silos
        (source_pkg == "state_build" and target_pkg == "state_teach")
        or (source_pkg == "state_teach" and target_pkg == "state_build")
        # Shared kernel must not depend on either mode
        or (source_pkg == _SHARED_KERNEL and target_pkg in _MODE_SILOS)
    )
    # state_daemon / state_cli can import from anything (not in the list above)
    # state_build / state_teach can import from state_core (the shared kernel)


# ── __main__ block ───────────────────────────────────────────────────────


if __name__ == "__main__":
    result = lint()
    for v in result.violations:
        sys.stderr.write(f"{v}\n")
    sys.exit(result.exit_code)


# ── Public surface ───────────────────────────────────────────────────────

__all__ = ["lint", "CheckResult", "Violation"]
