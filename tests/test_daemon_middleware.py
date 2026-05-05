"""Tests for state_daemon.middleware — ModeConfig loading, mode validation,
and ModeMiddleware enforcement of X-State-Mode header.

Covers: load_mode_config() with valid/missing/invalid files,
get_current_mode(), is_valid_mode(), ModeMiddleware for all
mode combinations (read/write), missing/invalid headers,
kernel mode bypass, and integration with JsonRpcRouter.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from src.state_core.schema import ModeConfig


# ---------------------------------------------------------------------------
# Helpers — copied pattern from test_daemon_server.py
# ---------------------------------------------------------------------------


async def _read_response(reader: asyncio.StreamReader) -> tuple[int, dict[str, str], bytes]:
    """Read a full HTTP response from a stream reader.

    Returns (status_code, headers_dict, body_bytes).
    """
    status_line = await reader.readline()
    _, status_str, _ = status_line.decode().strip().split(" ", 2)
    status = int(status_str)

    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        decoded = line.decode().strip()
        if ": " in decoded:
            key, _, value = decoded.partition(": ")
            headers[key.lower()] = value

    content_length = int(headers.get("content-length", "0"))
    body = b""
    if content_length > 0:
        body = await reader.readexactly(content_length)

    return status, headers, body


def _raw_request(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> bytes:
    """Build a raw HTTP/1.1 request."""
    lines = [f"{method} {path} HTTP/1.1"]
    hdrs = headers or {}
    if body:
        hdrs["Content-Length"] = str(len(body))
    for key, value in hdrs.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    lines.append("")
    return "\r\n".join(lines).encode() + body


# ===========================================================================
# Task 053.1 — ModeConfig loading and mode validation
# ===========================================================================


class TestModeConfig:
    """Unit tests for ModeConfig model and config loading."""

    def test_modeconfig_default_model(self) -> None:
        """ModeConfig can be constructed with a valid mode."""

        cfg = ModeConfig(mode="build")
        assert cfg.mode == "build"

    def test_modeconfig_invalid_mode_raises(self) -> None:
        """ModeConfig rejects unsupported modes."""

        with pytest.raises(Exception):  # pydantic ValidationError
            ModeConfig(mode="invalid")

    def test_modeconfig_both_mode_allowed(self) -> None:
        """ModeConfig accepts 'both' as a valid mode."""

        cfg = ModeConfig(mode="both")
        assert cfg.mode == "both"

    def test_modeconfig_teach_mode_allowed(self) -> None:
        """ModeConfig accepts 'teach' as a valid mode."""

        cfg = ModeConfig(mode="teach")
        assert cfg.mode == "teach"


class TestLoadModeConfig:
    """Tests for load_mode_config() function."""

    def test_load_existing_valid_config(self) -> None:
        """load_mode_config() reads and validates an existing mode.json."""

        # Reset cache to isolate test
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".state"), exist_ok=True)
            cfg_path = os.path.join(tmpdir, ".state", "mode.json")
            with open(cfg_path, "w") as f:
                json.dump({"mode": "teach"}, f)

            cfg = mod.load_mode_config(tmpdir)
            assert isinstance(cfg, ModeConfig)
            assert cfg.mode == "teach"

    def test_load_missing_creates_default(self) -> None:
        """load_mode_config() creates a default 'both' config when file missing."""
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = mod.load_mode_config(tmpdir)
            assert cfg.mode == "both"

            # Verify the file was created
            cfg_path = os.path.join(tmpdir, ".state", "mode.json")
            assert os.path.isfile(cfg_path)
            with open(cfg_path) as f:
                assert json.load(f) == {"mode": "both"}

    def test_load_invalid_json_raises(self) -> None:
        """load_mode_config() raises ValueError on invalid JSON."""
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".state"), exist_ok=True)
            cfg_path = os.path.join(tmpdir, ".state", "mode.json")
            with open(cfg_path, "w") as f:
                f.write("not json{")

            with pytest.raises(ValueError, match="Invalid JSON"):
                mod.load_mode_config(tmpdir)

    def test_load_invalid_mode_value_raises(self) -> None:
        """load_mode_config() raises ValueError on unsupported mode value."""
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".state"), exist_ok=True)
            cfg_path = os.path.join(tmpdir, ".state", "mode.json")
            with open(cfg_path, "w") as f:
                json.dump({"mode": "nonsense"}, f)

            with pytest.raises(ValueError, match="Invalid mode config"):
                mod.load_mode_config(tmpdir)


class TestCurrentMode:
    """Tests for get_current_mode()."""

    def test_get_current_mode_defaults_to_both(self) -> None:
        """get_current_mode() returns 'both' before load_mode_config() called."""
        import src.state_daemon.middleware as mod

        mod._config = None
        assert mod.get_current_mode() == "both"

    def test_get_current_mode_after_load(self) -> None:
        """get_current_mode() returns the loaded mode after load_mode_config()."""
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = mod.load_mode_config(tmpdir)
            assert mod.get_current_mode() == cfg.mode

    def test_get_current_mode_with_custom_config(self) -> None:
        """get_current_mode() reflects the loaded build config."""
        import src.state_daemon.middleware as mod

        mod._config = None

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".state"), exist_ok=True)
            with open(os.path.join(tmpdir, ".state", "mode.json"), "w") as f:
                json.dump({"mode": "build"}, f)
            mod.load_mode_config(tmpdir)
            assert mod.get_current_mode() == "build"


class TestIsValidMode:
    """Tests for is_valid_mode()."""

    @pytest.mark.parametrize(
        "mode,expected",
        [
            ("build", True),
            ("teach", True),
            ("both", True),
            ("kernel", True),
            ("invalid", False),
            ("", False),
            ("BUILD", False),
            ("Build", False),
        ],
    )
    def test_is_valid_mode(self, mode: str, expected: bool) -> None:
        """is_valid_mode() returns True only for recognised mode strings."""
        from src.state_daemon.middleware import is_valid_mode

        assert is_valid_mode(mode) == expected


# ===========================================================================
# Task 053.2 — ModeMiddleware enforcement
# ===========================================================================


def _make_echo_router():
    """Create a simple router that echoes the body as JSON."""
    async def _router(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
        return json.dumps({"echo": body.decode()}).encode()

    return _router


class TestModeMiddleware:
    """Tests for ModeMiddleware callable — mode enforcement rules."""

    # ------------------------------------------------------------------
    # Missing / invalid header → 400
    # ------------------------------------------------------------------

    async def test_missing_mode_header_returns_400(self) -> None:
        """Missing X-State-Mode header returns HTTP 400."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {}, b'{"test": 1}')
        assert isinstance(result, tuple)
        status, body = result
        assert status == 400
        data = json.loads(body)
        assert data["error"] == "missing_mode_header"

    async def test_empty_mode_header_returns_400(self) -> None:
        """Empty X-State-Mode header returns HTTP 400."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": ""}, b"{}")
        assert isinstance(result, tuple)
        status, body = result
        assert status == 400
        assert json.loads(body)["error"] == "missing_mode_header"

    async def test_invalid_mode_header_returns_400(self) -> None:
        """Invalid X-State-Mode value returns HTTP 400."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "fakemode"}, b"{}")
        assert isinstance(result, tuple)
        status, body = result
        assert status == 400
        assert json.loads(body)["error"] == "invalid_mode_header"

    # ------------------------------------------------------------------
    # Mode "both" — everything allowed
    # ------------------------------------------------------------------

    async def test_mode_both_allows_build_request(self) -> None:
        """Active mode 'both' passes through build requests."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="both")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "build"}, b'{"test": 1}')
        # Should be plain bytes (passed through to router)
        assert isinstance(result, bytes)

    async def test_mode_both_allows_teach_request(self) -> None:
        """Active mode 'both' passes through teach requests."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="both")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Kernel mode — always allowed
    # ------------------------------------------------------------------

    async def test_kernel_mode_always_allowed_even_on_mismatch(self) -> None:
        """Kernel mode bypasses mode enforcement entirely."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        # kernel with POST (write) — should pass through
        result = await mw("POST", "/", {"x-state-mode": "kernel"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Mode match → allow
    # ------------------------------------------------------------------

    async def test_mode_match_allows_write(self) -> None:
        """When request mode matches active mode, writes are allowed."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "build"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    async def test_mode_match_teach_allows_write(self) -> None:
        """Teach mode match passes through writes."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="teach")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Mismatch + read → allow
    # ------------------------------------------------------------------

    async def test_mismatch_get_is_allowed(self) -> None:
        """GET request with mismatched mode still passes through."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("GET", "/", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    async def test_mismatch_head_is_allowed(self) -> None:
        """HEAD request with mismatched mode still passes through."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("HEAD", "/", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    async def test_mismatch_post_health_is_read(self) -> None:
        """POST /health is treated as a read operation, allowed even on mismatch."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/health", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Mismatch + write → 403
    # ------------------------------------------------------------------

    async def test_cross_mode_write_rejected_403(self) -> None:
        """POST with mismatched mode is rejected with HTTP 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, tuple)
        status, body = result
        assert status == 403
        data = json.loads(body)
        assert data["error"] == "cross_mode_rejected"
        assert data["request_mode"] == "teach"
        assert data["active_mode"] == "build"

    async def test_cross_mode_put_rejected_403(self) -> None:
        """PUT with mismatched mode is rejected with 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("PUT", "/", {"x-state-mode": "teach"}, b"{}")
        assert isinstance(result, tuple)
        status, body = result
        assert status == 403
        assert json.loads(body)["error"] == "cross_mode_rejected"

    async def test_cross_mode_patch_rejected_403(self) -> None:
        """PATCH with mismatched mode is rejected with 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("PATCH", "/", {"x-state-mode": "teach"}, b"{}")
        assert isinstance(result, tuple)
        status, _ = result
        assert status == 403

    async def test_cross_mode_delete_rejected_403(self) -> None:
        """DELETE with mismatched mode is rejected with 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("DELETE", "/", {"x-state-mode": "teach"}, b"{}")
        assert isinstance(result, tuple)
        status, _ = result
        assert status == 403

    # ------------------------------------------------------------------
    # Rejection payload format
    # ------------------------------------------------------------------

    async def test_rejection_payload_contains_all_fields(self) -> None:
        """403 rejection includes error, request_mode, and active_mode."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b"{}")
        _, body = result
        data = json.loads(body)

        assert "error" in data
        assert "request_mode" in data
        assert "active_mode" in data
        assert data["error"] == "cross_mode_rejected"
        assert data["request_mode"] == "teach"
        assert data["active_mode"] == "build"

    async def test_400_rejection_payload(self) -> None:
        """400 rejection includes error, request_mode, and active_mode."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "garbage"}, b"{}")
        status, body = result
        assert status == 400
        data = json.loads(body)
        assert data["error"] == "invalid_mode_header"
        assert data["request_mode"] == "garbage"


# ===========================================================================
# Task 053.3 — Integration: DaemonServer + ModeMiddleware
# ===========================================================================


@pytest.fixture
def integration_socket_path() -> str:
    """Temp socket path for server+middleware integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "mw-daemon.sock")


def _make_jsonrpc_router():
    """Create a JsonRpcRouter with a 'ping' method for integration tests."""
    from src.state_daemon.router import JsonRpcRouter

    router = JsonRpcRouter()

    async def _ping(params: object) -> str:
        return "pong"

    router.add_method("ping", _ping)
    return router


def _jsonrpc_body(method: str, req_id: int = 1) -> bytes:
    """Minimal JSON-RPC 2.0 request body."""
    return json.dumps({"jsonrpc": "2.0", "method": method, "id": req_id}).encode()


class TestIntegration:
    """Integration tests: DaemonServer wired with ModeMiddleware."""

    async def test_matching_mode_allows_rpc_call(self, integration_socket_path: str) -> None:
        """Build-mode RPC with build header passes through middleware."""
        from src.state_daemon.middleware import ModeMiddleware
        from src.state_daemon.server import DaemonServer

        cfg = ModeConfig(mode="build")
        router = _make_jsonrpc_router()
        mw = ModeMiddleware(router, cfg)
        srv = DaemonServer(integration_socket_path, mw)
        await srv.start()

        try:
            reader, writer = await asyncio.open_unix_connection(integration_socket_path)
            writer.write(
                _raw_request(
                    "POST",
                    "/",
                    {
                        "Content-Type": "application/json",
                        "X-State-Mode": "build",
                    },
                    _jsonrpc_body("ping"),
                )
            )
            await writer.drain()
            status, _, resp_body = await _read_response(reader)
            assert status == 200
            data = json.loads(resp_body)
            assert data["result"] == "pong"
            writer.close()
            await writer.wait_closed()
        finally:
            await srv.stop()

    async def test_cross_mode_write_rejected_by_server(self, integration_socket_path: str) -> None:
        """POST with mismatched mode header gets 403 from server."""
        from src.state_daemon.middleware import ModeMiddleware
        from src.state_daemon.server import DaemonServer

        cfg = ModeConfig(mode="build")
        router = _make_jsonrpc_router()
        mw = ModeMiddleware(router, cfg)
        srv = DaemonServer(integration_socket_path, mw)
        await srv.start()

        try:
            reader, writer = await asyncio.open_unix_connection(integration_socket_path)
            writer.write(
                _raw_request(
                    "POST",
                    "/",
                    {
                        "Content-Type": "application/json",
                        "X-State-Mode": "teach",
                    },
                    _jsonrpc_body("ping"),
                )
            )
            await writer.drain()
            status, _, resp_body = await _read_response(reader)
            assert status == 403
            data = json.loads(resp_body)
            assert data["error"] == "cross_mode_rejected"
            writer.close()
            await writer.wait_closed()
        finally:
            await srv.stop()

    async def test_read_with_mismatched_mode_passes_through(self, integration_socket_path: str) -> None:
        """GET /health with mismatched mode still succeeds."""
        from src.state_daemon.middleware import ModeMiddleware
        from src.state_daemon.server import DaemonServer

        cfg = ModeConfig(mode="build")
        router = _make_jsonrpc_router()
        mw = ModeMiddleware(router, cfg)
        srv = DaemonServer(integration_socket_path, mw)
        await srv.start()

        try:
            reader, writer = await asyncio.open_unix_connection(integration_socket_path)
            writer.write(
                _raw_request(
                    "GET",
                    "/health",
                    {"X-State-Mode": "teach"},
                )
            )
            await writer.drain()
            status, _, resp_body = await _read_response(reader)
            assert status == 200
            data = json.loads(resp_body)
            assert data == {"status": "ok"}
            writer.close()
            await writer.wait_closed()
        finally:
            await srv.stop()

    async def test_missing_header_returns_400(self, integration_socket_path: str) -> None:
        """No X-State-Mode header returns 400."""
        from src.state_daemon.middleware import ModeMiddleware
        from src.state_daemon.server import DaemonServer

        cfg = ModeConfig(mode="build")
        router = _make_jsonrpc_router()
        mw = ModeMiddleware(router, cfg)
        srv = DaemonServer(integration_socket_path, mw)
        await srv.start()

        try:
            reader, writer = await asyncio.open_unix_connection(integration_socket_path)
            writer.write(
                _raw_request(
                    "POST",
                    "/",
                    {"Content-Type": "application/json"},
                    _jsonrpc_body("ping"),
                )
            )
            await writer.drain()
            status, _, resp_body = await _read_response(reader)
            assert status == 400
            data = json.loads(resp_body)
            assert data["error"] == "missing_mode_header"
            writer.close()
            await writer.wait_closed()
        finally:
            await srv.stop()

    async def test_teach_mode_allows_teach_rpc(self, integration_socket_path: str) -> None:
        """Teach-mode RPC with teach header passes through."""
        from src.state_daemon.middleware import ModeMiddleware
        from src.state_daemon.server import DaemonServer

        cfg = ModeConfig(mode="teach")
        router = _make_jsonrpc_router()
        mw = ModeMiddleware(router, cfg)
        srv = DaemonServer(integration_socket_path, mw)
        await srv.start()

        try:
            reader, writer = await asyncio.open_unix_connection(integration_socket_path)
            writer.write(
                _raw_request(
                    "POST",
                    "/",
                    {
                        "Content-Type": "application/json",
                        "X-State-Mode": "teach",
                    },
                    _jsonrpc_body("ping"),
                )
            )
            await writer.drain()
            status, _, resp_body = await _read_response(reader)
            assert status == 200
            data = json.loads(resp_body)
            assert data["result"] == "pong"
            writer.close()
            await writer.wait_closed()
        finally:
            await srv.stop()


# ===========================================================================
# Task 098-02 — validate_daemon_path() subtree enforcement
# ===========================================================================


class TestValidateDaemonPath:
    """validate_daemon_path() — daemon subtree enforcement (layer 2 of 6)."""

    def test_build_path_allowed_in_build_mode(self) -> None:
        """A path under .state/build/ is allowed when mode=build."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/build/events.sqlite", "build")

    def test_build_path_rejected_in_teach_mode(self) -> None:
        """A path under .state/build/ is rejected when mode=teach."""
        from src.state_core.schema import validate_subtree_path

        with pytest.raises(ValueError, match="teach"):
            validate_subtree_path(".state/build/events.sqlite", "teach")

    def test_teach_path_allowed_in_teach_mode(self) -> None:
        """A path under .state/teach/ is allowed when mode=teach."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/teach/concepts.db", "teach")

    def test_teach_path_rejected_in_build_mode(self) -> None:
        """A path under .state/teach/ is rejected when mode=build."""
        from src.state_core.schema import validate_subtree_path

        with pytest.raises(ValueError, match="build"):
            validate_subtree_path(".state/teach/concepts.db", "build")

    def test_shared_root_allowed_in_build_mode(self) -> None:
        """Shared root files (.state/events.sqlite) are always allowed."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/events.sqlite", "build")
        validate_subtree_path(".state/mode.json", "build")

    def test_shared_root_allowed_in_teach_mode(self) -> None:
        """Shared root files are always allowed even in teach mode."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/events.sqlite", "teach")
        validate_subtree_path(".state/mode.json", "teach")

    def test_exact_dir_name_rejected(self) -> None:
        """.state/build (no trailing /) is treated as the build subtree."""
        from src.state_core.schema import validate_subtree_path

        with pytest.raises(ValueError):
            validate_subtree_path(".state/build", "teach")

    def test_path_input_accepted(self) -> None:
        """validate_subtree_path accepts pathlib.Path input."""
        from pathlib import Path as Pt
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(Pt(".state/build/foo"), "build")
        with pytest.raises(ValueError):
            validate_subtree_path(Pt(".state/build/foo"), "teach")

    def test_both_mode_allows_all(self) -> None:
        """Both mode allows both subtrees."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/build/foo", "both")
        validate_subtree_path(".state/teach/bar", "both")

    def test_both_mode_allows_shared_root(self) -> None:
        """Both mode allows shared root entries too."""
        from src.state_core.schema import validate_subtree_path

        validate_subtree_path(".state/events.sqlite", "both")
        validate_subtree_path(".state/mode.json", "both")

    def test_middleware_validate_path_method(self) -> None:
        """ModeMiddleware.validate_path() uses the middleware's config."""
        from src.state_core.schema import ModeConfig as Mc
        from src.state_daemon.middleware import ModeMiddleware

        async def _noop(method, path, headers, body):
            return b""

        mw = ModeMiddleware(_noop, Mc(mode="build"))
        mw.validate_path(".state/build/foo")
        with pytest.raises(ValueError):
            mw.validate_path(".state/teach/bar")

    def test_unloaded_config_permissive(self) -> None:
        """Without load_mode_config(), validate_daemon_path() uses 'both' default."""
        # Reset cached config to simulate fresh daemon boot
        import src.state_daemon.middleware as mod
        mod._config = None

        from src.state_daemon.middleware import validate_daemon_path

        # Default "both" mode allows both subtrees
        validate_daemon_path(".state/build/foo")
        validate_daemon_path(".state/teach/bar")


# ===========================================================================
# Task 101-01.1 — Event-type prefix sets + _extract_event_type() helper
# ===========================================================================


class TestEventPrefixSets:
    """Tests for TEACH_ONLY_EVENT_PREFIXES and BUILD_ONLY_EVENT_PREFIXES."""

    def test_teach_only_prefixes_is_frozenset(self) -> None:
        """TEACH_ONLY_EVENT_PREFIXES is a frozenset with correct values."""
        from src.state_core.schema import TEACH_ONLY_EVENT_PREFIXES

        assert isinstance(TEACH_ONLY_EVENT_PREFIXES, frozenset)
        assert TEACH_ONLY_EVENT_PREFIXES == {"state.concept.", "state.drill."}

    def test_build_only_prefixes_is_frozenset(self) -> None:
        """BUILD_ONLY_EVENT_PREFIXES is a frozenset with correct values."""
        from src.state_core.schema import BUILD_ONLY_EVENT_PREFIXES

        assert isinstance(BUILD_ONLY_EVENT_PREFIXES, frozenset)
        assert BUILD_ONLY_EVENT_PREFIXES == {
            "state.arc.", "state.phase.", "state.slice.", "state.step."
        }

    def test_frozensets_are_hashable(self) -> None:
        """Frozensets can be used as dict keys or set members."""
        from src.state_core.schema import TEACH_ONLY_EVENT_PREFIXES, BUILD_ONLY_EVENT_PREFIXES

        # Verify they are hashable (can be dict keys and set members)
        d = {TEACH_ONLY_EVENT_PREFIXES: "teach", BUILD_ONLY_EVENT_PREFIXES: "build"}
        assert d[TEACH_ONLY_EVENT_PREFIXES] == "teach"
        assert d[BUILD_ONLY_EVENT_PREFIXES] == "build"

        s = {TEACH_ONLY_EVENT_PREFIXES, BUILD_ONLY_EVENT_PREFIXES}
        assert len(s) == 2


class TestExtractEventType:
    """Tests for _extract_event_type() JSON-RPC body parser."""

    def test_extracts_event_type_from_state_emit(self) -> None:
        """_extract_event_type returns 'state.concept.introduced' for valid body."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({
            "method": "state.emit",
            "params": {"type": "state.concept.introduced"},
        }).encode()
        result = _extract_event_type(body)
        assert result == "state.concept.introduced"

    def test_returns_none_for_non_state_emit(self) -> None:
        """_extract_event_type returns None for non-state.emit methods."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({"method": "ping", "id": 1}).encode()
        result = _extract_event_type(body)
        assert result is None

    def test_returns_none_for_malformed_json(self) -> None:
        """_extract_event_type returns None for malformed JSON (no crash)."""
        from src.state_daemon.middleware import _extract_event_type

        result = _extract_event_type(b"not json")
        assert result is None

    def test_returns_empty_string_for_missing_type(self) -> None:
        """_extract_event_type returns '' when params.type is missing."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({"method": "state.emit"}).encode()
        result = _extract_event_type(body)
        assert result == ""

    def test_returns_none_for_non_dict_payload(self) -> None:
        """_extract_event_type returns None when JSON is not a dict."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps([1, 2, 3]).encode()
        result = _extract_event_type(body)
        assert result is None

    def test_returns_empty_string_for_null_type(self) -> None:
        """_extract_event_type returns '' when params exists but type is None."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({
            "method": "state.emit",
            "params": {"type": None},
        }).encode()
        result = _extract_event_type(body)
        assert result == ""

    def test_returns_empty_string_for_missing_params(self) -> None:
        """_extract_event_type returns '' when params key is missing from state.emit."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({"method": "state.emit", "id": 1}).encode()
        result = _extract_event_type(body)
        assert result == ""

    def test_returns_empty_string_for_non_dict_params(self) -> None:
        """_extract_event_type returns '' when params is not a dict (state.emit with bad params)."""
        from src.state_daemon.middleware import _extract_event_type

        body = json.dumps({
            "method": "state.emit",
            "params": "string_not_dict",
        }).encode()
        result = _extract_event_type(body)
        assert result == ""


def _state_emit_body(event_type: str) -> bytes:
    """Build a JSON-RPC 2.0 state.emit request body."""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": "state.emit",
        "params": {"type": event_type},
        "id": 1,
    }).encode()


# ===========================================================================
# Task 101-01.2 — Event-type validation in ModeMiddleware.__call__
# ===========================================================================


class TestEventTypeMiddleware:
    """Tests for ModeMiddleware event-type-level validation."""

    # ------------------------------------------------------------------
    # Build mode rejects teach-only events
    # ------------------------------------------------------------------

    async def test_build_mode_rejects_concept_event(self) -> None:
        """Build mode + state.concept.introduced → HTTP 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, tuple)
        status, resp_body = result
        assert status == 403
        data = json.loads(resp_body)
        assert data["error"] == "cross_mode_event_rejected"
        assert data["event_type"] == "state.concept.introduced"

    async def test_build_mode_rejects_drill_event(self) -> None:
        """Build mode + state.drill.prepared → HTTP 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.drill.prepared")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, tuple)
        status, resp_body = result
        assert status == 403
        data = json.loads(resp_body)
        assert data["error"] == "cross_mode_event_rejected"

    async def test_build_mode_allows_step_event(self) -> None:
        """Build mode + state.step.executed → HTTP 200 (passes through)."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.step.executed")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Teach mode rejects build-only events
    # ------------------------------------------------------------------

    async def test_teach_mode_rejects_arc_event(self) -> None:
        """Teach mode + state.arc.created → HTTP 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="teach")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.arc.created")
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        assert isinstance(result, tuple)
        status, resp_body = result
        assert status == 403
        data = json.loads(resp_body)
        assert data["error"] == "cross_mode_event_rejected"

    async def test_teach_mode_rejects_slice_event(self) -> None:
        """Teach mode + state.slice.planned → HTTP 403."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="teach")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.slice.planned")
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        assert isinstance(result, tuple)
        status, resp_body = result
        assert status == 403
        data = json.loads(resp_body)
        assert data["error"] == "cross_mode_event_rejected"

    async def test_teach_mode_allows_concept_event(self) -> None:
        """Teach mode + state.concept.observed → HTTP 200 (passes through)."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="teach")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.observed")
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Both mode and kernel bypass event-type checks
    # ------------------------------------------------------------------

    async def test_both_mode_allows_teach_event(self) -> None:
        """Active mode 'both' allows teach events even with build header."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="both")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    async def test_kernel_mode_bypasses_event_check(self) -> None:
        """Kernel request mode bypasses event-type checks entirely."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "kernel"}, body)
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Non-state.emit methods and malformed bodies skip check
    # ------------------------------------------------------------------

    async def test_non_state_emit_method_skips_check(self) -> None:
        """Non-state.emit JSON-RPC passes through event-type check."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = json.dumps({
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1,
        }).encode()
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    async def test_malformed_json_body_passes_through(self) -> None:
        """Malformed JSON body passes through (router's concern)."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "build"}, b"not json")
        assert isinstance(result, bytes)

    async def test_get_request_skips_event_check(self) -> None:
        """GET requests skip event-type check entirely."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.introduced")
        result = await mw("GET", "/", {"x-state-mode": "build"}, body)
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Rejection payload verification
    # ------------------------------------------------------------------

    async def test_rejection_payload_includes_event_type(self) -> None:
        """403 event rejection payload includes event_type field."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        _, resp_body = result
        data = json.loads(resp_body)

        assert data["error"] == "cross_mode_event_rejected"
        assert data["event_type"] == "state.concept.introduced"
        assert data["request_mode"] == "build"
        assert data["active_mode"] == "build"

    # ------------------------------------------------------------------
    # Existing header-only rejection still works
    # ------------------------------------------------------------------

    async def test_cross_mode_header_rejection_still_works(self) -> None:
        """Existing behavior: teach header with build active → 403 'cross_mode_rejected'."""
        from src.state_daemon.middleware import ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        body = _state_emit_body("state.step.executed")
        result = await mw("POST", "/", {"x-state-mode": "teach"}, body)
        assert isinstance(result, tuple)
        status, resp_body = result
        assert status == 403
        data = json.loads(resp_body)
        assert data["error"] == "cross_mode_rejected"
        # Header-only rejection does NOT include event_type
        assert "event_type" not in data

    async def test_error_codes_are_distinct(self) -> None:
        """Header rejection = 'cross_mode_rejected', event-type rejection = 'cross_mode_event_rejected'."""
        from src.state_daemon.middleware import ModeMiddleware

        # Test 1: Header mismatch → "cross_mode_rejected"
        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)
        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        status, resp_body = result
        assert json.loads(resp_body)["error"] == "cross_mode_rejected"

        # Test 2: Header match but event mismatch → "cross_mode_event_rejected"
        body = _state_emit_body("state.concept.introduced")
        result = await mw("POST", "/", {"x-state-mode": "build"}, body)
        status, resp_body = result
        assert json.loads(resp_body)["error"] == "cross_mode_event_rejected"


# ===========================================================================
# Task 103-01 — Daemon mode reload via load_mode_config
# ===========================================================================


class TestModeReload:
    """Daemon mode reload via load_mode_config."""

    def test_reload_updates_config(self, tmp_path: Path) -> None:
        """load_mode_config() re-reads mode.json and updates global _config."""
        import src.state_daemon.middleware as mod

        mod._config = None

        state_dir = tmp_path / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        # Write initial mode
        (state_dir / "mode.json").write_text(json.dumps({"mode": "build"}))
        # Load it
        cfg = mod.load_mode_config(str(tmp_path))
        assert cfg.mode == "build"
        assert mod.get_current_mode() == "build"

        # Simulate mode set: overwrite mode.json
        (state_dir / "mode.json").write_text(json.dumps({"mode": "teach"}))
        # Reload — should pick up new mode
        cfg2 = mod.load_mode_config(str(tmp_path))
        assert cfg2.mode == "teach"
        assert mod.get_current_mode() == "teach"

    def test_reload_handles_missing_file(self, tmp_path: Path) -> None:
        """load_mode_config() creates default 'both' when file is missing."""
        import src.state_daemon.middleware as mod

        mod._config = None

        state_dir = tmp_path / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        # No mode.json initially
        cfg = mod.load_mode_config(str(tmp_path))
        assert cfg.mode == "both"
        assert mod.get_current_mode() == "both"
        # Default mode.json should have been created
        assert (state_dir / "mode.json").exists()


# ===========================================================================
# Task 104-01 — Mode activation event emission from daemon SIGHUP handler
# ===========================================================================


class TestModeActivatedEvent:
    """Tests for state.mode.activated event emission via _emit_mode_event()."""

    async def _setup_store(self, tmp_path: Path, monkeypatch) -> "SqliteEventStore":
        """Create an isolated event store with migrations applied.

        Returns a SqliteEventStore ready for appending and reading events.
        """
        from src.state_core.events import SqliteEventStore
        from src.state_core.migrations import migrate

        db_path = str(tmp_path / ".state" / "events.sqlite")
        monkeypatch.setenv("STATE_DB_PATH", db_path)

        # Copy migrations to temp dir so migrate() can find them
        migrations_src = Path.cwd() / ".state" / "migrations"
        migrations_dst = tmp_path / ".state" / "migrations"
        if migrations_src.exists():
            shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

        # Run migrations to create the events table
        await migrate()

        return SqliteEventStore()

    @pytest.mark.asyncio
    async def test_emit_mode_event_writes_to_store(self, tmp_path: Path, monkeypatch) -> None:
        """_emit_mode_event() appends a state.mode.activated event to the store."""
        store = await self._setup_store(tmp_path, monkeypatch)

        # Patch the module-level _event_store so _emit_mode_event can use it
        import src.state_daemon.orchestrator as orch
        orch._event_store = store

        # Call the emitter directly
        await orch._emit_mode_event("build", "teach")

        # Read back the event
        events = await store.read_events()
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "state.mode.activated"
        assert event["aggregate_type"] == "mode"
        assert event["aggregate_id"] == "mode-teach"
        assert event["mode"] == "kernel"

        # Verify data payload
        import json as _json
        data = _json.loads(event["data"]) if isinstance(event["data"], str) else event["data"]
        assert data["old_mode"] == "build"
        assert data["new_mode"] == "teach"

    @pytest.mark.asyncio
    async def test_emit_mode_event_aggregate_id_per_new_mode(self, tmp_path: Path, monkeypatch) -> None:
        """aggregate_id follows the pattern 'mode-{new_mode}'."""
        store = await self._setup_store(tmp_path, monkeypatch)

        import src.state_daemon.orchestrator as orch
        orch._event_store = store

        await orch._emit_mode_event("teach", "build")
        await orch._emit_mode_event("build", "both")

        events = await store.read_events()
        assert len(events) == 2
        assert events[0]["aggregate_id"] == "mode-build"
        assert events[1]["aggregate_id"] == "mode-both"

    @pytest.mark.asyncio
    async def test_emit_mode_event_mode_is_kernel(self, tmp_path: Path, monkeypatch) -> None:
        """Event is emitted with mode='kernel' for cross-mode visibility."""
        store = await self._setup_store(tmp_path, monkeypatch)

        import src.state_daemon.orchestrator as orch
        orch._event_store = store

        await orch._emit_mode_event("build", "teach")

        events = await store.read_events()
        assert events[0]["mode"] == "kernel"

    @pytest.mark.asyncio
    async def test_emit_mode_event_no_store_is_noop(self) -> None:
        """_emit_mode_event() is a no-op when _event_store is None."""
        import src.state_daemon.orchestrator as orch

        orch._event_store = None

        # Should not raise — just log warning
        await orch._emit_mode_event("build", "teach")

    @pytest.mark.asyncio
    async def test_emit_mode_event_preserves_fields(self, tmp_path: Path, monkeypatch) -> None:
        """_emit_mode_event() preserves all required fields in the event."""
        store = await self._setup_store(tmp_path, monkeypatch)

        import src.state_daemon.orchestrator as orch
        orch._event_store = store

        await orch._emit_mode_event("build", "teach")

        events = await store.read_events()
        event = events[0]

        # Verify all required envelope fields are present
        assert "id" in event
        assert "seq" in event
        assert "ts" in event
        assert "aggregate_type" in event
        assert "aggregate_id" in event
        assert "type" in event
        assert "data" in event
        assert "mode" in event
