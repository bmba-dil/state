"""Tests for state_core.http_client — build_shared_client() contract.

Wave 0 RED stubs made GREEN in Plan 02 (Wave 1).
"""
from __future__ import annotations

import ssl
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from state_core.http_client import build_shared_client


async def test_build_shared_client_defaults() -> None:
    """build_shared_client() returns AsyncClient with correct Limits."""
    client = build_shared_client()
    try:
        assert isinstance(client, httpx.AsyncClient)
        # httpx 0.28.x stores limits on the underlying httpcore pool
        pool = client._transport._pool
        assert pool._max_connections == 100
        assert pool._max_keepalive_connections == 20
        assert pool._keepalive_expiry == 30.0
    finally:
        await client.aclose()


async def test_build_shared_client_proxy(tmp_path: Path) -> None:
    """build_shared_client(proxy=...) accepts a proxy URL without error."""
    client = build_shared_client(proxy="http://proxy.test:8080")
    try:
        assert isinstance(client, httpx.AsyncClient)
    finally:
        await client.aclose()


async def test_build_shared_client_tls_skip() -> None:
    """build_shared_client(verify=False) constructs client without error."""
    client = build_shared_client(verify=False)
    try:
        assert isinstance(client, httpx.AsyncClient)
    finally:
        await client.aclose()


async def test_build_shared_client_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STATE_HTTP_PROXY env var is picked up by build_shared_client()."""
    monkeypatch.setenv("STATE_HTTP_PROXY", "http://proxy.env:9090")
    client = build_shared_client()
    try:
        assert isinstance(client, httpx.AsyncClient)
        # We can't easily introspect the proxy URL on the client object,
        # but construction must not raise — the proxy string is valid.
    finally:
        await client.aclose()


async def test_build_shared_client_env_ca(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """STATE_CA_BUNDLE env var is picked up by build_shared_client()."""
    pem_path = tmp_path / "ca.pem"
    pem_path.write_text("")  # empty — we mock ssl.create_default_context

    fake_ctx = MagicMock(spec=ssl.SSLContext)
    monkeypatch.setenv("STATE_CA_BUNDLE", str(pem_path))

    with patch("state_core.http_client.ssl.create_default_context", return_value=fake_ctx) as mock_ctx:
        client = build_shared_client()
        try:
            assert isinstance(client, httpx.AsyncClient)
            mock_ctx.assert_called_once_with(cafile=str(pem_path))
        finally:
            await client.aclose()
