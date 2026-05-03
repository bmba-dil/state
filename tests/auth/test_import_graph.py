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
