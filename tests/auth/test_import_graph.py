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
