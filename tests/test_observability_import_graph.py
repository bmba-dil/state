"""Phase 020 — VALIDATION row REDACT-25 (RED scaffolding).

Architectural constraint: state_core.observability.* is mode-neutral
plumbing — it MUST NOT import state.build.*, state.teach.*, state_build.*,
or state_teach.*. Mode-isolation cardinal rule (CLAUDE.md / PROJECT.md
§Mode Boundary Cardinal Rule).

Allowed import targets for src/state_core/observability/redactor.py:
  * stdlib (re, logging, typing, uuid)
  * structlog
  * state_core.auth.providers.api_key (for iter_known_prefixes())

Wave 1 — src/state_core/observability/redactor.py does not exist yet;
the test pytest.fail()s with a clear "Wave 1 RED" message until Plan 02
creates the module.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).parent.parent
_OBSERVABILITY_DIR = _REPO_ROOT / "src" / "state_core" / "observability"
_REDACTOR_PATH = _OBSERVABILITY_DIR / "redactor.py"
_OBSERVABILITY_INIT = _OBSERVABILITY_DIR / "__init__.py"


# ── REDACT-25 — observability mode-isolation lint ──────────────────────


def test_observability_no_mode_imports() -> None:
    """REDACT-25 — state_core.observability.* MUST NOT import state.build.* or state.teach.*.

    Six forbidden substrings cover the four canonical import shapes
    (`from`/`import` × `state_build`/`state_teach`) plus the dotted-path
    variants (`state.build` / `state.teach`).

    Wave 1 RED — file does not exist.
    """
    if not _REDACTOR_PATH.exists():
        pytest.fail(
            "Wave 1 RED: src/state_core/observability/redactor.py does not exist yet"
        )

    src = _REDACTOR_PATH.read_text()
    forbidden_substrings = (
        "from state_build",
        "import state_build",
        "from state_teach",
        "import state_teach",
        "from state.build",
        "from state.teach",
    )
    for needle in forbidden_substrings:
        assert needle not in src, (
            f"redactor.py contains forbidden import substring {needle!r} "
            "(mode isolation breach — REDACT-25)"
        )


def test_observability_imports_only_allowed_targets() -> None:
    """redactor.py may import ONLY from stdlib + structlog + state_core.auth.providers.api_key.

    Per RESEARCH §Architecture Patterns "Mode-isolation rule". Any other
    state_core.* import indicates an unexpected dependency that should
    be flagged.

    Wave 1 RED — file does not exist.
    """
    if not _REDACTOR_PATH.exists():
        pytest.fail(
            "Wave 1 RED: src/state_core/observability/redactor.py does not exist yet"
        )

    src = _REDACTOR_PATH.read_text()
    allowed_state_core = {
        "state_core.auth.providers.api_key",
    }
    pattern = re.compile(r"(?:from|import)\s+(state_core\.[\w.]+)")
    for match in pattern.finditer(src):
        target = match.group(1).rstrip(",")
        assert target in allowed_state_core, (
            f"redactor.py imports {target!r} — allowed state_core.* set is "
            f"{allowed_state_core!r}"
        )


def test_observability_init_exists() -> None:
    """src/state_core/observability/__init__.py exists as the package marker.

    Wave 1 RED — file does not exist.
    """
    if not _OBSERVABILITY_INIT.exists():
        pytest.fail(
            "Wave 1 RED: src/state_core/observability/__init__.py does not exist yet"
        )
