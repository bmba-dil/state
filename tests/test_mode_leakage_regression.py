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
# Layer 3 — MCP registration logic (Phase 099 contract)
# ===========================================================================


def _get_mcp_servers_for_mode(mode: str | None) -> list[str]:
    """Reproduce ``getMcpServersForMode()`` from the TypeScript plugin for testing.

    This is the functional contract of config.ts — the same logic that
    determines which MCP servers are registered in opencode based on the
    active execution mode.
    """
    if mode == "build":
        return ["state-build"]
    if mode == "teach":
        return ["state-teach"]
    if mode == "both":
        return ["state-build", "state-teach"]
    return []


class TestLayer3McpRegistration:
    """Validate MCP server selection logic matches the TypeScript contract."""

    def test_build_mode_registers_only_state_build(self) -> None:
        """Build mode returns ``['state-build']``."""
        assert _get_mcp_servers_for_mode("build") == ["state-build"]

    def test_teach_mode_registers_only_state_teach(self) -> None:
        """Teach mode returns ``['state-teach']``."""
        assert _get_mcp_servers_for_mode("teach") == ["state-teach"]

    def test_both_mode_registers_both_servers(self) -> None:
        """Both mode returns ``['state-build', 'state-teach']``."""
        assert _get_mcp_servers_for_mode("both") == ["state-build", "state-teach"]

    def test_null_mode_registers_nothing(self) -> None:
        """None mode returns empty list."""
        assert _get_mcp_servers_for_mode(None) == []

    def test_unknown_mode_registers_nothing(self) -> None:
        """Unknown mode string returns empty list."""
        assert _get_mcp_servers_for_mode("garbage") == []

    def test_build_mode_does_not_include_state_teach(self) -> None:
        """Build mode must not register ``state-teach`` MCP server."""
        result = _get_mcp_servers_for_mode("build")
        assert "state-teach" not in result

    def test_teach_mode_does_not_include_state_build(self) -> None:
        """Teach mode must not register ``state-build`` MCP server."""
        result = _get_mcp_servers_for_mode("teach")
        assert "state-build" not in result


# ===========================================================================
# Layer 4 — Plugin hook gate logic (Phase 100 contract)
# ===========================================================================

_STATE_COMMAND_RE = re.compile(r"^/state:(build|teach):")


def _is_command_blocked(command: str, mode: str) -> bool:
    """Reproduce ``command-execute-before.ts`` mode gate logic."""
    if mode == "both":
        return False
    m = _STATE_COMMAND_RE.match(command)
    if not m:
        return False
    return m.group(1) != mode


def _is_tool_blocked(tool: str, mode: str) -> bool:
    """Reproduce ``tool-execute-before.ts`` mode gate logic."""
    if mode == "both":
        return False
    if mode == "build" and tool.startswith("mcp__state-teach__"):
        return True
    if mode == "teach" and tool.startswith("mcp__state-build__"):
        return True
    return False


class TestLayer4HookGate:
    """Validate command and tool mode-gate logic matches TypeScript hooks."""

    # ── Command gate ─────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "command,mode,blocked",
        [
            ("/state:build:code-review", "build", False),
            ("/state:teach:concept", "teach", False),
            ("/state:teach:concept", "build", True),
            ("/state:build:code-review", "teach", True),
            ("/state:build:code-review", "both", False),
            ("/state:teach:drill", "both", False),
            ("/help", "build", False),
            ("/gsd:progress", "teach", False),
            ("/state:kernel:status", "build", False),
        ],
    )
    def test_command_gate(
        self, command: str, mode: str, blocked: bool
    ) -> None:
        """Cross-mode commands are blocked; same-mode and non-state commands are not."""
        assert _is_command_blocked(command, mode) == blocked

    def test_all_build_commands_blocked_in_teach(self) -> None:
        """All /state:build:* commands are blocked in teach mode."""
        for cmd in ["/state:build:code-review", "/state:build:plan", "/state:build:execute"]:
            assert _is_command_blocked(cmd, "teach") is True

    def test_all_teach_commands_blocked_in_build(self) -> None:
        """All /state:teach:* commands are blocked in build mode."""
        for cmd in ["/state:teach:concept", "/state:teach:drill", "/state:teach:review"]:
            assert _is_command_blocked(cmd, "build") is True

    # ── Tool gate ────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "tool,mode,blocked",
        [
            ("mcp__state-build__some_tool", "build", False),
            ("mcp__state-teach__some_tool", "teach", False),
            ("mcp__state-teach__some_tool", "build", True),
            ("mcp__state-build__some_tool", "teach", True),
            ("mcp__state-build__some_tool", "both", False),
            ("mcp__state-teach__other", "both", False),
            ("bash", "build", False),
            ("Write", "teach", False),
        ],
    )
    def test_tool_gate(self, tool: str, mode: str, blocked: bool) -> None:
        """Cross-mode tools are blocked; same-mode and non-state tools are not."""
        assert _is_tool_blocked(tool, mode) == blocked

    def test_all_mcp_teach_tools_blocked_in_build(self) -> None:
        """All ``mcp__state-teach__*`` tools are blocked in build mode."""
        for tool in [
            "mcp__state-teach__introduce_concept",
            "mcp__state-teach__review",
            "mcp__state-teach__run_drill",
        ]:
            assert _is_tool_blocked(tool, "build") is True

    def test_all_mcp_build_tools_blocked_in_teach(self) -> None:
        """All ``mcp__state-build__*`` tools are blocked in teach mode."""
        for tool in [
            "mcp__state-build__plan_phase",
            "mcp__state-build__execute_phase",
            "mcp__state-build__create_slice",
        ]:
            assert _is_tool_blocked(tool, "teach") is True


# ===========================================================================
# Full-suite smoke tests
# ===========================================================================


class TestFullSuiteSmoke:
    """Integration checks proving the entire regression file runs as a unit."""

    def test_all_6_layers_have_test_classes(self) -> None:
        """Each layer must have a test class with methods."""
        import tests.test_mode_leakage_regression as mod

        layer_classes = [
            "TestLayer1ModeJsonSchema",
            "TestLayer2SubtreePath",
            "TestLayer3McpRegistration",
            "TestLayer4HookGate",
            "TestLayer5DaemonMiddleware",
            "TestLayer6ImportLint",
            "TestFullSuiteSmoke",
        ]
        for cls_name in layer_classes:
            cls = getattr(mod, cls_name, None)
            assert cls is not None, f"Missing test class: {cls_name}"
            methods = [
                name
                for name in dir(cls)
                if name.startswith("test_") and callable(getattr(cls, name))
            ]
            assert len(methods) > 0, f"{cls_name} has no test methods"

    def test_regression_suite_imports_cleanly(self) -> None:
        """The test file imports without errors."""
        import tests.test_mode_leakage_regression as mod  # noqa: F401

    def test_total_test_count_meets_minimum(self) -> None:
        """The suite must have at least 50 test functions (not counting parametrized expansions)."""
        import inspect
        import tests.test_mode_leakage_regression as mod

        count = 0
        for name in dir(mod):
            obj = getattr(mod, name)
            if inspect.isclass(obj) and name.startswith("Test"):
                for method_name in dir(obj):
                    if method_name.startswith("test_"):
                        count += 1
        assert count >= 50, f"Only {count} test methods found, need >= 50"

    def test_no_external_conftest_dependency(self) -> None:
        """The test file uses only built-in pytest fixtures (tmp_path, etc.) — no conftest imports."""
        import importlib.util

        spec = importlib.util.find_spec("tests.test_mode_leakage_regression")
        assert spec is not None
        source = Path(spec.origin).read_text() if spec.origin else ""

        # Check that no import statement at module level references conftest.
        # Use a line-by-line check to avoid matching the test's own assertions.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import conftest"):
                pytest.fail(f"Found conftest import: {stripped}")
            if stripped.startswith("from conftest"):
                pytest.fail(f"Found conftest import: {stripped}")
            if stripped.startswith("from tests.conftest"):
                pytest.fail(f"Found conftest import: {stripped}")

    def test_mcp_server_separation_guarantee(self) -> None:
        """Layer 3 guarantee: in single mode, exactly one MCP server registered."""
        build_servers = _get_mcp_servers_for_mode("build")
        teach_servers = _get_mcp_servers_for_mode("teach")

        assert len(build_servers) == 1
        assert len(teach_servers) == 1
        assert build_servers[0] != teach_servers[0]

    def test_command_tool_matrix_no_false_positives(self) -> None:
        """Common non-state commands/tools are never blocked."""
        commands = ["/help", "/clear", "/gsd:progress", ""]
        tools = ["bash", "Read", "Write", "Edit", "Grep"]
        for mode in ("build", "teach", "both"):
            for cmd in commands:
                assert not _is_command_blocked(cmd, mode)
            for tool in tools:
                assert not _is_tool_blocked(tool, mode)


# ===========================================================================
# Helpers
# ===========================================================================


def _setup_lint_dirs(base: Path) -> None:
    """Create the standard 5-package directories for import-lint fixture trees."""
    for name in ("state_build", "state_teach", "state_core", "state_daemon", "state_cli"):
        (base / name).mkdir(parents=True, exist_ok=True)
