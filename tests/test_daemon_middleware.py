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
import tempfile
from pathlib import Path

import pytest


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
        from src.state_daemon.middleware import ModeConfig

        cfg = ModeConfig(mode="build")
        assert cfg.mode == "build"

    def test_modeconfig_invalid_mode_raises(self) -> None:
        """ModeConfig rejects unsupported modes."""
        from src.state_daemon.middleware import ModeConfig

        with pytest.raises(Exception):  # pydantic ValidationError
            ModeConfig(mode="invalid")

    def test_modeconfig_both_mode_allowed(self) -> None:
        """ModeConfig accepts 'both' as a valid mode."""
        from src.state_daemon.middleware import ModeConfig

        cfg = ModeConfig(mode="both")
        assert cfg.mode == "both"

    def test_modeconfig_teach_mode_allowed(self) -> None:
        """ModeConfig accepts 'teach' as a valid mode."""
        from src.state_daemon.middleware import ModeConfig

        cfg = ModeConfig(mode="teach")
        assert cfg.mode == "teach"


class TestLoadModeConfig:
    """Tests for load_mode_config() function."""

    def test_load_existing_valid_config(self) -> None:
        """load_mode_config() reads and validates an existing mode.json."""
        from src.state_daemon.middleware import ModeConfig

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": ""}, b"{}")
        assert isinstance(result, tuple)
        status, body = result
        assert status == 400
        assert json.loads(body)["error"] == "missing_mode_header"

    async def test_invalid_mode_header_returns_400(self) -> None:
        """Invalid X-State-Mode value returns HTTP 400."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="both")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "build"}, b'{"test": 1}')
        # Should be plain bytes (passed through to router)
        assert isinstance(result, bytes)

    async def test_mode_both_allows_teach_request(self) -> None:
        """Active mode 'both' passes through teach requests."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="both")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Kernel mode — always allowed
    # ------------------------------------------------------------------

    async def test_kernel_mode_always_allowed_even_on_mismatch(self) -> None:
        """Kernel mode bypasses mode enforcement entirely."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "build"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    async def test_mode_match_teach_allows_write(self) -> None:
        """Teach mode match passes through writes."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="teach")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/", {"x-state-mode": "teach"}, b'{"test": 1}')
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Mismatch + read → allow
    # ------------------------------------------------------------------

    async def test_mismatch_get_is_allowed(self) -> None:
        """GET request with mismatched mode still passes through."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("GET", "/", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    async def test_mismatch_head_is_allowed(self) -> None:
        """HEAD request with mismatched mode still passes through."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("HEAD", "/", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    async def test_mismatch_post_health_is_read(self) -> None:
        """POST /health is treated as a read operation, allowed even on mismatch."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("POST", "/health", {"x-state-mode": "teach"}, b"")
        assert isinstance(result, bytes)

    # ------------------------------------------------------------------
    # Mismatch + write → 403
    # ------------------------------------------------------------------

    async def test_cross_mode_write_rejected_403(self) -> None:
        """POST with mismatched mode is rejected with HTTP 403."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("PUT", "/", {"x-state-mode": "teach"}, b"{}")
        assert isinstance(result, tuple)
        status, body = result
        assert status == 403
        assert json.loads(body)["error"] == "cross_mode_rejected"

    async def test_cross_mode_patch_rejected_403(self) -> None:
        """PATCH with mismatched mode is rejected with 403."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

        cfg = ModeConfig(mode="build")
        mw = ModeMiddleware(_make_echo_router(), cfg)

        result = await mw("PATCH", "/", {"x-state-mode": "teach"}, b"{}")
        assert isinstance(result, tuple)
        status, _ = result
        assert status == 403

    async def test_cross_mode_delete_rejected_403(self) -> None:
        """DELETE with mismatched mode is rejected with 403."""
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware

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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware
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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware
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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware
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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware
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
        from src.state_daemon.middleware import ModeConfig, ModeMiddleware
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
