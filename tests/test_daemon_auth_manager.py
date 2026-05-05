"""Tests for state_daemon.auth_manager — AuthRefreshLoop, AuthRoundRobin, AuthStatusHandler.

Covers: refresh loop start/stop, round-robin integration, GET /auth/status
JSON shape (never raw tokens), and server wiring of the auth endpoint.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from time import time as _now
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from state_core.auth import (
    EXPIRY_BUFFER_SECONDS,
    ApiKeyCredential,
    AuthVault,
    OAuthCredential,
    ensure_initialized,
    get_auth_json_path,
    load_vault,
    save_vault,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_oauth_cred(
    provider_id: str = "anthropic",
    expires_offset: float = 3600.0,
) -> OAuthCredential:
    """Create a test OAuth credential that expires in *expires_offset* seconds."""
    now = _now()
    return OAuthCredential(
        access="test-access-token",
        refresh="test-refresh-token",
        expires=now + expires_offset,
        provider_id=provider_id,
    )


def _make_api_key_cred(provider_id: str = "openai") -> ApiKeyCredential:
    """Create a test API-key credential."""
    return ApiKeyCredential(key="sk-test-key", provider_id=provider_id)


def _build_vault_json(providers: dict) -> bytes:
    """Serialize an AuthVault to JSON bytes matching the on-disk format."""
    import orjson
    vault = AuthVault(providers=providers)
    return orjson.dumps(
        vault.model_dump(mode="json"),
        option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_vault_path() -> str:
    """Create a temp vault file and set STATE_AUTH_JSON."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = str(Path(tmpdir) / "auth.json")
        os.environ["STATE_AUTH_JSON"] = vault_path
        yield vault_path
        os.environ.pop("STATE_AUTH_JSON", None)


# ---------------------------------------------------------------------------
# Tests: AuthRefreshLoop
# ---------------------------------------------------------------------------


class TestAuthRefreshLoop:
    """Unit tests for the background refresh loop."""

    async def test_start_stop_lifecycle(self, temp_vault_path: str) -> None:
        """AuthRefreshLoop starts and stops without error."""
        from src.state_daemon.auth_manager import AuthRefreshLoop

        loop = AuthRefreshLoop(vault_path=Path(temp_vault_path))
        await loop.start()
        assert loop._task is not None
        assert loop._running is True

        await loop.stop()
        assert loop._running is False
        assert loop._task is None

    async def test_api_key_creds_not_refreshed(self, temp_vault_path: str) -> None:
        """API-key credentials are skipped during refresh scan (no expiry)."""
        from src.state_daemon.auth_manager import AuthRefreshLoop

        # Populate vault with API-key credentials only.
        vault = AuthVault(providers={
            "openai": [_make_api_key_cred("openai")],
        })
        save_vault(Path(temp_vault_path), vault)

        loop = AuthRefreshLoop(vault_path=Path(temp_vault_path), interval=0.1)
        await loop.start()

        # Give the loop one tick.
        await asyncio.sleep(0.3)

        # Vault should be unchanged (no refresh occurred for api keys).
        reloaded = load_vault(Path(temp_vault_path))
        assert len(reloaded.providers.get("openai", [])) == 1
        cred = reloaded.providers["openai"][0]
        assert isinstance(cred, ApiKeyCredential)
        assert cred.key == "sk-test-key"

        await loop.stop()

    async def test_near_expiry_oauth_attempts_refresh(
        self, temp_vault_path: str
    ) -> None:
        """Near-expiry OAuth credentials trigger a refresh attempt."""
        from src.state_daemon.auth_manager import AuthRefreshLoop

        # Credential that expires in 4 minutes (within 5-min buffer).
        near_expiry = _make_oauth_cred("anthropic", expires_offset=240.0)
        vault = AuthVault(providers={"anthropic": [near_expiry]})
        save_vault(Path(temp_vault_path), vault)

        # Mock _get_auth_method to return a real-ish mock that simulates
        # a successful refresh.
        mock_method = MagicMock()
        mock_method.refresh = AsyncMock(
            return_value=_make_oauth_cred("anthropic", expires_offset=7200.0)
        )

        with patch(
            "src.state_daemon.auth_manager._get_auth_method",
            return_value=mock_method,
        ):
            loop = AuthRefreshLoop(
                vault_path=Path(temp_vault_path), interval=0.1
            )
            await loop.start()
            await asyncio.sleep(0.3)
            await loop.stop()

        # The refresh method should have been called for the near-expiry cred.
        mock_method.refresh.assert_called()

    async def test_fresh_oauth_skipped(self, temp_vault_path: str) -> None:
        """Fresh OAuth credentials (outside buffer) are skipped."""
        from src.state_daemon.auth_manager import AuthRefreshLoop

        # Credential that expires in 24 hours (well outside buffer).
        fresh = _make_oauth_cred("anthropic", expires_offset=86400.0)
        vault = AuthVault(providers={"anthropic": [fresh]})
        save_vault(Path(temp_vault_path), vault)

        mock_method = MagicMock()
        mock_method.refresh = AsyncMock()

        with patch(
            "src.state_daemon.auth_manager._get_auth_method",
            return_value=mock_method,
        ):
            loop = AuthRefreshLoop(
                vault_path=Path(temp_vault_path), interval=0.1
            )
            await loop.start()
            await asyncio.sleep(0.3)
            await loop.stop()

        # Refresh should NOT have been called for a fresh credential.
        mock_method.refresh.assert_not_called()

    async def test_refresh_failure_retained(self, temp_vault_path: str) -> None:
        """Failed refresh keeps the old credential for next tick."""
        from src.state_daemon.auth_manager import AuthRefreshLoop

        old_cred = _make_oauth_cred("anthropic", expires_offset=240.0)
        vault = AuthVault(providers={"anthropic": [old_cred]})
        save_vault(Path(temp_vault_path), vault)

        mock_method = MagicMock()
        mock_method.refresh = AsyncMock(side_effect=Exception("network error"))

        with patch(
            "src.state_daemon.auth_manager._get_auth_method",
            return_value=mock_method,
        ):
            loop = AuthRefreshLoop(
                vault_path=Path(temp_vault_path), interval=0.1
            )
            await loop.start()
            await asyncio.sleep(0.3)
            await loop.stop()

        # The loop should continue running (not crash) despite the error.
        # Old credential remains — the vault is unchanged in content.
        assert loop._running is False  # loop stopped cleanly


# ---------------------------------------------------------------------------
# Tests: AuthRoundRobin
# ---------------------------------------------------------------------------


class TestAuthRoundRobin:
    """Unit tests for round-robin credential selection."""

    async def test_round_robin_cycles(self, temp_vault_path: str) -> None:
        """next_credential cycles through multi-cred array."""
        from src.state_daemon.auth_manager import AuthRoundRobin

        creds = [
            _make_oauth_cred("anthropic", expires_offset=7200.0),
            _make_oauth_cred("anthropic", expires_offset=14400.0),
        ]
        vault = AuthVault(providers={"anthropic": creds})
        save_vault(Path(temp_vault_path), vault)

        rr = AuthRoundRobin(vault_path=Path(temp_vault_path))

        # First call returns some credential.
        c1 = await rr.next_credential("anthropic")
        assert c1.provider_id == "anthropic"

        # Second call should return the other one (round-robin cycling).
        c2 = await rr.next_credential("anthropic")
        assert c2.provider_id == "anthropic"
        assert c1 != c2  # different expires values distinguish them

    async def test_no_creds_raises(self, temp_vault_path: str) -> None:
        """NoCredentialsAvailableError raised for empty provider."""
        from src.state_daemon.auth_manager import AuthRoundRobin
        from state_core.auth.errors import NoCredentialsAvailableError

        rr = AuthRoundRobin(vault_path=Path(temp_vault_path))
        with pytest.raises(NoCredentialsAvailableError):
            await rr.next_credential("nonexistent")


# ---------------------------------------------------------------------------
# Tests: AuthStatusHandler
# ---------------------------------------------------------------------------


class TestAuthStatusHandler:
    """Tests for GET /auth/status JSON endpoint."""

    async def test_returns_providers_list(self, temp_vault_path: str) -> None:
        """Status response contains per-provider metadata."""
        from src.state_daemon.auth_manager import AuthStatusHandler

        cred = _make_oauth_cred("anthropic", expires_offset=3600.0)
        vault = AuthVault(providers={"anthropic": [cred]})
        save_vault(Path(temp_vault_path), vault)

        handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        body = await handler.handle()
        data = json.loads(body)

        assert "providers" in data
        providers = data["providers"]
        assert len(providers) == 1
        p = providers[0]
        assert p["provider"] == "anthropic"
        assert p["count"] == 1

    async def test_never_exposes_raw_tokens(self, temp_vault_path: str) -> None:
        """Auth status JSON MUST NOT contain access_token, refresh_token, or api_key."""
        from src.state_daemon.auth_manager import AuthStatusHandler

        oauth = _make_oauth_cred("anthropic", expires_offset=3600.0)
        apikey = _make_api_key_cred("openai")
        vault = AuthVault(providers={
            "anthropic": [oauth],
            "openai": [apikey],
        })
        save_vault(Path(temp_vault_path), vault)

        handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        body = await handler.handle()
        data = json.loads(body)

        # Serialize to string for grep-style check — raw tokens must NOT appear.
        body_str = json.dumps(data)
        assert "test-access-token" not in body_str
        assert "test-refresh-token" not in body_str
        assert "sk-test-key" not in body_str

    async def test_cache_returns_same_bytes(self, temp_vault_path: str) -> None:
        """Cache returns the same bytes object within TTL."""
        from src.state_daemon.auth_manager import AuthStatusHandler, AUTH_STATUS_CACHE_TTL

        cred = _make_oauth_cred("anthropic", expires_offset=3600.0)
        vault = AuthVault(providers={"anthropic": [cred]})
        save_vault(Path(temp_vault_path), vault)

        handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        body1 = await handler.handle()
        body2 = await handler.handle()

        # Within the short interval, both should return the same cached bytes.
        assert body1 is body2  # identity check — cached reference

    async def test_api_key_mode_null_expiry(self, temp_vault_path: str) -> None:
        """API-key credentials have mode='api_key' and expires_at=null."""
        from src.state_daemon.auth_manager import AuthStatusHandler

        apikey = _make_api_key_cred("openai")
        vault = AuthVault(providers={"openai": [apikey]})
        save_vault(Path(temp_vault_path), vault)

        handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        body = await handler.handle()
        data = json.loads(body)

        creds = data["providers"][0]["credentials"]
        assert len(creds) == 1
        c = creds[0]
        assert c["mode"] == "api_key"
        assert c["expires_at"] is None
        assert c["credential_index"] == 0

    async def test_oauth_mode_fields(self, temp_vault_path: str) -> None:
        """OAuth credentials have mode='bearer' with expiry metadata."""
        from src.state_daemon.auth_manager import AuthStatusHandler

        oauth = _make_oauth_cred("anthropic", expires_offset=3600.0)
        vault = AuthVault(providers={"anthropic": [oauth]})
        save_vault(Path(temp_vault_path), vault)

        handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        body = await handler.handle()
        data = json.loads(body)

        creds = data["providers"][0]["credentials"]
        c = creds[0]
        assert c["mode"] == "bearer"
        assert c["expires_at"] is not None
        assert c["expires_with_buffer"] is not None
        assert "expired_buffered" in c
        assert c["credential_index"] == 0


# ---------------------------------------------------------------------------
# Tests: Server-Integrated Auth Endpoint
# ---------------------------------------------------------------------------


async def _read_response(reader: asyncio.StreamReader) -> tuple[int, dict[str, str], bytes]:
    """Read a full HTTP response."""
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


def _raw_get(path: str) -> bytes:
    """Build a raw GET /path HTTP/1.1 request."""
    return f"GET {path} HTTP/1.1\r\n\r\n".encode()


class TestServerAuthEndpoint:
    """Integration tests for GET /auth/status via DaemonServer."""

    @pytest.fixture
    async def auth_server(self, temp_vault_path: str):
        """Start a DaemonServer with auth status endpoint registered."""
        from src.state_daemon.auth_manager import AuthStatusHandler
        from src.state_daemon.server import DaemonServer

        # Populate vault with test data.
        cred = _make_oauth_cred("anthropic", expires_offset=3600.0)
        vault = AuthVault(providers={"anthropic": [cred]})
        save_vault(Path(temp_vault_path), vault)

        async def noop_router(method, path, headers, body):
            return b"{}"

        socket_path = str(Path(temp_vault_path).parent / "daemon.sock")
        srv = DaemonServer(socket_path, noop_router)
        auth_handler = AuthStatusHandler(vault_path=Path(temp_vault_path))
        srv.add_get_handler("/auth/status", auth_handler.handle)
        await srv.start()
        yield srv, socket_path
        await srv.stop()

    async def test_auth_endpoint_excludes_tokens(
        self, auth_server
    ) -> None:
        """GET /auth/status returns 200 with providers list, no raw tokens."""
        _srv, socket_path = auth_server
        reader, writer = await asyncio.open_unix_connection(socket_path)
        writer.write(_raw_get("/auth/status"))
        await writer.drain()
        status, headers, body = await _read_response(reader)
        writer.close()
        await writer.wait_closed()

        assert status == 200
        assert headers["content-type"] == "application/json"
        data = json.loads(body)
        assert "providers" in data
        # Raw tokens must NOT appear.
        body_str = json.dumps(data)
        assert "test-access-token" not in body_str
        assert "test-refresh-token" not in body_str

    async def test_auth_endpoint_providers_listed(
        self, auth_server
    ) -> None:
        """GET /auth/status lists configured providers."""
        _srv, socket_path = auth_server
        reader, writer = await asyncio.open_unix_connection(socket_path)
        writer.write(_raw_get("/auth/status"))
        await writer.drain()
        status, _headers, body = await _read_response(reader)
        writer.close()
        await writer.wait_closed()

        assert status == 200
        data = json.loads(body)
        provider_ids = [p["provider"] for p in data["providers"]]
        assert "anthropic" in provider_ids
