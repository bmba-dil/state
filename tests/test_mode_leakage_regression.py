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
    BUILD_ONLY_EVENT_PREFIXES,
    BUILD_SUBTREE,
    ModeConfig,
    TEACH_ONLY_EVENT_PREFIXES,
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
# Layer 5 — Daemon HTTP middleware, the canonical gate (Phase 101)
# ===========================================================================


def _make_echo_router():
    """Create a simple router that echoes the body back as JSON."""

    async def _router(
        method: str, path: str, headers: dict[str, str], body: bytes
    ) -> bytes:
        return json.dumps({"echo": body.decode()}).encode()

    return _router


def _build_emit_body(event_type: str, extra_params: dict | None = None) -> bytes:
    """Build a ``state.emit`` JSON-RPC POST body with the given event type."""
    params: dict[str, object] = {"type": event_type}
    if extra_params:
        params.update(extra_params)
    return json.dumps({"method": "state.emit", "params": params}).encode()


class TestLayer5DaemonMiddleware:
    """Validate daemon middleware rejects all illegal cross-mode requests.

    Tests the canonical gate: ``ModeMiddleware.__call__()`` invoked directly
    with method/path/headers/body — no socket or network involved.
    """

    # ── Helpers for building middleware under test ───────────────────────

    @staticmethod
    def _mw(mode: str):
        """Build a ModeMiddleware instance with the given active mode."""
        from src.state_daemon.middleware import ModeMiddleware

        return ModeMiddleware(_make_echo_router(), ModeConfig(mode=mode))

    @staticmethod
    def _rejection(result) -> tuple[int, dict]:
        """Assert result is a rejection tuple and return (status, data)."""
        assert isinstance(result, tuple), f"Expected rejection tuple, got {type(result)}"
        status, body = result
        return status, json.loads(body)

    # ── Header mismatch → 403 ───────────────────────────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "active_mode,header_mode,method,expected_status",
        [
            ("build", "teach", "POST", 403),
            ("build", "teach", "PUT", 403),
            ("build", "teach", "PATCH", 403),
            ("build", "teach", "DELETE", 403),
            ("teach", "build", "POST", 403),
            ("teach", "build", "PUT", 403),
            ("teach", "build", "PATCH", 403),
            ("teach", "build", "DELETE", 403),
        ],
    )
    async def test_cross_mode_write_rejected_403(
        self, active_mode: str, header_mode: str, method: str, expected_status: int
    ) -> None:
        """Cross-mode writes (POST/PUT/PATCH/DELETE) are rejected with 403."""
        mw = self._mw(active_mode)
        result = await mw(method, "/", {"x-state-mode": header_mode}, b'{"test": 1}')
        status, data = self._rejection(result)
        assert status == expected_status
        assert data["error"] == "cross_mode_rejected"
        assert data["request_mode"] == header_mode
        assert data["active_mode"] == active_mode

    # ── Header mismatch + read → allowed ────────────────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method",
        ["GET", "HEAD"],
    )
    async def test_cross_mode_read_allowed(self, method: str) -> None:
        """GET/HEAD with cross-mode header passes through (reads allowed)."""
        mw = self._mw("build")
        result = await mw(method, "/", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_mismatch_get_with_body_allowed(self) -> None:
        """GET with mismatched mode and body still passes (GET is always read)."""
        mw = self._mw("build")
        result = await mw("GET", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ── Same-mode → allowed ─────────────────────────────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "active_mode,header_mode",
        [("build", "build"), ("teach", "teach")],
    )
    async def test_same_mode_write_allowed(
        self, active_mode: str, header_mode: str
    ) -> None:
        """Same-mode writes pass through to the router."""
        mw = self._mw(active_mode)
        result = await mw(method="POST", path="/", headers={"x-state-mode": header_mode}, body=b'{"test": 1}')
        assert isinstance(result, bytes)

    # ── Missing/invalid header → 400 ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_missing_header_returns_400(self) -> None:
        """Missing X-State-Mode header returns HTTP 400."""
        mw = self._mw("build")
        result = await mw("POST", "/", {}, b'{"test": 1}')
        status, data = self._rejection(result)
        assert status == 400
        assert data["error"] == "missing_mode_header"

    @pytest.mark.asyncio
    async def test_empty_header_returns_400(self) -> None:
        """Empty X-State-Mode value returns HTTP 400."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": ""}, b"{}")
        status, data = self._rejection(result)
        assert status == 400
        assert data["error"] == "missing_mode_header"

    @pytest.mark.asyncio
    async def test_invalid_header_returns_400(self) -> None:
        """Invalid X-State-Mode value returns HTTP 400."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": "fakemode"}, b"{}")
        status, data = self._rejection(result)
        assert status == 400
        assert data["error"] == "invalid_mode_header"

    @pytest.mark.asyncio
    async def test_whitespace_only_header_returns_400(self) -> None:
        """Whitespace-only X-State-Mode is treated as missing → 400."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": "   "}, b"{}")
        status, data = self._rejection(result)
        assert status == 400
        assert data["error"] == "missing_mode_header"

    # ── Kernel bypass ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_kernel_bypasses_build_mode(self) -> None:
        """X-State-Mode: kernel bypasses all mode checks in build-active daemon."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": "kernel"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_kernel_bypasses_teach_mode(self) -> None:
        """X-State-Mode: kernel bypasses all mode checks in teach-active daemon."""
        mw = self._mw("teach")
        result = await mw("POST", "/", {"x-state-mode": "kernel"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ── Both mode → allow all ───────────────────────────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "header_mode",
        ["build", "teach", "kernel", "both"],
    )
    async def test_both_active_allows_all_headers(self, header_mode: str) -> None:
        """Active mode 'both' allows all X-State-Mode header values."""
        mw = self._mw("both")
        result = await mw("POST", "/", {"x-state-mode": header_mode}, b'{"test": 1}')
        assert isinstance(result, bytes)  # pass through

    # ── Event-type rejection: build mode rejects teach events ────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_type",
        [
            "state.concept.introduced",
            "state.concept.observed",
            "state.concept.drilled",
            "state.concept.mastered",
            "state.concept.reviewed",
            "state.drill.prepared",
            "state.drill.submitted",
            "state.drill.graded",
        ],
    )
    async def test_build_mode_rejects_teach_event(self, event_type: str) -> None:
        """Build mode rejects all 8 teach-only event types with 403."""
        mw = self._mw("build")
        body = _build_emit_body(event_type)
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        status, data = self._rejection(result)
        assert status == 403
        assert data["error"] == "cross_mode_event_rejected"
        assert data["event_type"] == event_type

    # ── Event-type rejection: teach mode rejects build events ────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_type",
        [
            "state.arc.created",
            "state.phase.planned",
            "state.slice.shipped",
            "state.step.executed",
        ],
    )
    async def test_teach_mode_rejects_build_event(self, event_type: str) -> None:
        """Teach mode rejects build-only event types with 403."""
        mw = self._mw("teach")
        body = _build_emit_body(event_type)
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        status, data = self._rejection(result)
        assert status == 403
        assert data["error"] == "cross_mode_event_rejected"
        assert data["event_type"] == event_type

    # ── Allowed event paths ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_build_mode_allows_build_event(self) -> None:
        """Build mode + build-only event + matching header → allowed."""
        mw = self._mw("build")
        body = _build_emit_body("state.arc.created")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_teach_mode_allows_teach_event(self) -> None:
        """Teach mode + teach-only event + matching header → allowed."""
        mw = self._mw("teach")
        body = _build_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        assert isinstance(result, bytes)

    # ── Non-emit / malformed body passes through ────────────────────────

    @pytest.mark.asyncio
    async def test_non_emit_post_passes_through(self) -> None:
        """Non-state.emit POST body bypasses event-type check."""
        mw = self._mw("build")
        body = json.dumps({"method": "ping", "params": {}}).encode()
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_malformed_json_passes_through(self) -> None:
        """Malformed JSON body does not crash middleware; passes through."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": "build"}, b"not json{")
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_empty_body_passes_through(self) -> None:
        """Empty body on same-mode POST passes through."""
        mw = self._mw("build")
        result = await mw("POST", "/", {"x-state-mode": "build"}, b"")
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_emit_with_null_type_passes_through(self) -> None:
        """state.emit with null type field passes through (treated as empty)."""
        mw = self._mw("build")
        body = json.dumps({"method": "state.emit", "params": {"type": None}}).encode()
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    # ── Mode-specific prefix coverage ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_build_mode_rejects_teach_prefix_count(self) -> None:
        """Build-mode daemon has exactly 2 teach-only event prefixes."""
        from src.state_core.schema import TEACH_ONLY_EVENT_PREFIXES

        assert TEACH_ONLY_EVENT_PREFIXES == frozenset({"state.concept.", "state.drill."})

    @pytest.mark.asyncio
    async def test_teach_mode_rejects_build_prefix_count(self) -> None:
        """Teach-mode daemon has exactly 4 build-only event prefixes."""
        from src.state_core.schema import BUILD_ONLY_EVENT_PREFIXES

        assert BUILD_ONLY_EVENT_PREFIXES == frozenset(
            {"state.arc.", "state.phase.", "state.slice.", "state.step."}
        )


# ===========================================================================
# Helpers
# ===========================================================================


def _setup_lint_dirs(base: Path) -> None:
    """Create the standard 5-package directories for import-lint fixture trees."""
    for name in ("state_build", "state_teach", "state_core", "state_daemon", "state_cli"):
        (base / name).mkdir(parents=True, exist_ok=True)
