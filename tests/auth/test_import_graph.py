"""Phase 018 — VALIDATION row 21 (RED scaffolding).

Architectural constraint: providers/api_key.py is the data layer;
loader.py is the fusion layer. The edge MUST point one way:

    loader.py  ──imports──▶  providers/api_key.py
    providers/api_key.py  ──MUST NOT IMPORT──▶  loader.py

Reverse edge would create a circular import (T-018-7 ASVS V14.2.1).

Wave 0 — both source files are absent; the tests pytest.fail with a
clear "Wave 0 RED" message until Wave 1 (api_key.py) and Wave 2
(loader.py) land.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).parent.parent.parent
_API_KEY_PATH = _REPO_ROOT / "src" / "state_core" / "auth" / "providers" / "api_key.py"
_LOADER_PATH = _REPO_ROOT / "src" / "state_core" / "auth" / "loader.py"


# ── VALIDATION row 21 — one-way import constraint ────────────────────────


def test_api_key_does_not_import_loader() -> None:
    """VALIDATION row 21 — providers/api_key.py MUST NOT import loader.

    Wave 0 RED — file does not exist.
    """
    if not _API_KEY_PATH.exists():
        pytest.fail(
            "Wave 0 RED: src/state_core/auth/providers/api_key.py does not exist yet"
        )

    src = _API_KEY_PATH.read_text()
    assert "from state_core.auth.loader" not in src, (
        "providers/api_key.py imports state_core.auth.loader — "
        "circular import (T-018-7)"
    )
    assert "import state_core.auth.loader" not in src, (
        "providers/api_key.py imports state_core.auth.loader — "
        "circular import (T-018-7)"
    )


# ── Companion: loader imports only allowed targets ───────────────────────


def test_loader_imports_only_allowed_targets() -> None:
    """loader.py may import ONLY from base / store / providers.api_key under state_core.

    Any other state_core.* import indicates an unexpected dependency.
    """
    if not _LOADER_PATH.exists():
        pytest.fail("Wave 0 RED: src/state_core/auth/loader.py does not exist yet")

    src = _LOADER_PATH.read_text()

    allowed = {
        "state_core.auth.base",
        "state_core.auth.store",
        "state_core.auth.providers.api_key",
        "state_core.auth.errors",
    }

    # Match `from state_core.<dotted.path> import …` and `import state_core.<dotted.path>`.
    pattern = re.compile(r"(?:from|import)\s+(state_core\.[\w.]+)")
    for match in pattern.finditer(src):
        target = match.group(1)
        # Strip trailing import-as fragment if any.
        target = target.rstrip(",")
        assert target in allowed, (
            f"loader.py imports {target!r} — allowed set is {allowed!r}"
        )


# ── Phase 019: ROTATE-21 — rotation.py mode isolation ────────────────────


_ROTATION_PATH = _REPO_ROOT / "src" / "state_core" / "auth" / "rotation.py"


def test_rotation_no_mode_imports() -> None:
    """ROTATE-21 — state_core.auth.rotation MUST NOT import state.build.* or state.teach.*.

    Mode isolation cardinal rule (CLAUDE.md). The CI import-graph lint
    enforces this for every state_core.auth.* module.

    Wave 0 RED — file does not exist.
    """
    if not _ROTATION_PATH.exists():
        pytest.fail(
            "Wave 0 RED: src/state_core/auth/rotation.py does not exist yet"
        )

    src = _ROTATION_PATH.read_text()
    forbidden_substrings = (
        "from state.build",
        "import state.build",
        "from state.teach",
        "import state.teach",
    )
    for needle in forbidden_substrings:
        assert needle not in src, (
            f"rotation.py contains forbidden import substring {needle!r} "
            "(mode isolation breach)"
        )


def test_rotation_imports_only_allowed_targets() -> None:
    """rotation.py may import ONLY from base / store / refresh / errors / loader under state_core.

    Per RESEARCH §Standard Stack Core. Any other state_core.* import
    indicates an unexpected dependency and should be flagged.

    Wave 0 RED — file does not exist.
    """
    if not _ROTATION_PATH.exists():
        pytest.fail(
            "Wave 0 RED: src/state_core/auth/rotation.py does not exist yet"
        )

    src = _ROTATION_PATH.read_text()
    allowed = {
        "state_core.auth.base",
        "state_core.auth.store",
        "state_core.auth.refresh",
        "state_core.auth.errors",
        "state_core.auth.loader",
    }
    pattern = re.compile(r"(?:from|import)\s+(state_core\.[\w.]+)")
    for match in pattern.finditer(src):
        target = match.group(1).rstrip(",")
        assert target in allowed, (
            f"rotation.py imports {target!r} — allowed set is {allowed!r}"
        )


# ── Phase 021: IMPORT-MODE-ISOLATION — import_opencode.py mode isolation ─


_IMPORT_OPENCODE_PATH = (
    _REPO_ROOT / "src" / "state_core" / "auth" / "import_opencode.py"
)


def test_import_opencode_no_mode_imports() -> None:
    """Phase 021 IMPORT-MODE-ISOLATION — state_core.auth.import_opencode
    MUST NOT import state_build.* / state_teach.* / state.build / state.teach.

    Mode isolation cardinal rule (CLAUDE.md). The CI import-graph lint
    enforces this for every state_core.auth.* module.

    Wave 1 RED — file does not exist yet. Plan 02 lands the implementation.
    """
    if not _IMPORT_OPENCODE_PATH.exists():
        pytest.fail(
            "Wave 1 RED: src/state_core/auth/import_opencode.py does not exist yet"
        )

    src = _IMPORT_OPENCODE_PATH.read_text()
    forbidden = [
        "from state_build",
        "from state_teach",
        "import state_build",
        "import state_teach",
        "from state.build",
        "from state.teach",
    ]
    for pat in forbidden:
        assert pat not in src, (
            f"state_core.auth.import_opencode.py contains forbidden import "
            f"{pat!r} — mode isolation violation (cardinal rule, CLAUDE.md)"
        )


def test_import_opencode_imports_only_allowed_modules() -> None:
    """Phase 021 IMPORT-MODE-ALLOWLIST — explicit allowlist of allowed
    import roots: stdlib + pydantic + orjson + structlog + a narrowed
    set of state_core submodules.

    Also enforces SF-04 cardinal: bare-package imports only — `from src.*`
    is BANNED outright (commit a955608). Mixed `src.state_core.*` and
    `state_core.*` resolve to two distinct sys.modules entries with
    separate class objects, breaking pydantic discriminated-union identity.

    Wave 1 RED — file does not exist yet.
    """
    if not _IMPORT_OPENCODE_PATH.exists():
        pytest.fail(
            "Wave 1 RED: src/state_core/auth/import_opencode.py does not exist yet"
        )

    import ast
    import sys

    tree = ast.parse(_IMPORT_OPENCODE_PATH.read_text())
    allowed_roots = set(sys.stdlib_module_names) | {
        "pydantic",
        "orjson",
        "structlog",
        "state_core",  # narrowed below by submodule check
    }
    allowed_state_core_submods = {
        "state_core.auth.base",
        "state_core.auth.store",
        "state_core.auth.providers.api_key",
        "state_core.events",
        "state_core.schema",
        "state_core.sync_mirror",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            assert not mod.startswith("src."), (
                f"SF-04 violation: `from src.{mod[4:]} import ...` — "
                "use bare `from {mod[4:]} import ...` (commit a955608)"
            )
            root = mod.split(".")[0]
            if root not in allowed_roots:
                pytest.fail(f"forbidden import root: {mod}")
            if mod.startswith("state_core."):
                if not any(
                    mod == a or mod.startswith(a + ".")
                    for a in allowed_state_core_submods
                ):
                    pytest.fail(f"state_core import outside allowlist: {mod}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("src."), (
                    f"SF-04 violation: `import src.{alias.name[4:]}` — "
                    "use bare `import {alias.name[4:]}` (commit a955608)"
                )
                root = alias.name.split(".")[0]
                if root not in allowed_roots:
                    pytest.fail(f"forbidden import root: {alias.name}")


# ── Phase 022 — CLI mode-isolation rows ─────────────────────────────────

_REPO_ROOT_022 = Path(__file__).parent.parent.parent
_CLI_AUTH_PATH = _REPO_ROOT_022 / "src" / "state_cli" / "auth.py"
_CLI_OPS_PATH = _REPO_ROOT_022 / "src" / "state_core" / "auth" / "cli_ops.py"


def test_state_cli_auth_one_way_edge() -> None:
    """VALIDATION 022-row-A — state_cli/auth.py may import state_core.auth.* but
    MUST NOT import state_build.* or state_teach.*.

    Wave 0 RED — file does not exist yet.
    """
    if not _CLI_AUTH_PATH.exists():
        pytest.fail(
            "Wave 0 RED: src/state_cli/auth.py does not exist yet (022-03)"
        )
    src = _CLI_AUTH_PATH.read_text()
    assert "from state_build" not in src, "state_cli.auth imports state_build — mode isolation violation"
    assert "import state_build" not in src, "state_cli.auth imports state_build — mode isolation violation"
    assert "from state_teach" not in src, "state_cli.auth imports state_teach — mode isolation violation"
    assert "import state_teach" not in src, "state_cli.auth imports state_teach — mode isolation violation"


def test_cli_ops_no_state_cli_imports() -> None:
    """VALIDATION 022-row-B — state_core/auth/cli_ops.py MUST NOT import state_cli.*.

    One-way edge: state_cli -> state_core.auth; NOT the reverse.
    Wave 0 RED — file does not exist yet.
    """
    if not _CLI_OPS_PATH.exists():
        pytest.fail(
            "Wave 0 RED: src/state_core/auth/cli_ops.py does not exist yet (022-02)"
        )
    src = _CLI_OPS_PATH.read_text()
    assert "from state_cli" not in src, "state_core.auth.cli_ops imports state_cli — reverse edge violation"
    assert "import state_cli" not in src, "state_core.auth.cli_ops imports state_cli — reverse edge violation"
