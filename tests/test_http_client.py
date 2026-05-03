"""RED stubs for state_core.http_client — build_shared_client() contract.

All tests fail with ModuleNotFoundError until Plan 02 (Wave 1) creates
src/state_core/http_client.py.  Do NOT add pytest.skip() or conditional
imports — the tests MUST fail red until the implementation lands.
"""
from __future__ import annotations

import os
import ssl
from pathlib import Path

import httpx
import pytest

from state_core.http_client import build_shared_client


async def test_build_shared_client_defaults() -> None:
    """build_shared_client() returns AsyncClient with correct Limits."""
    client = build_shared_client()
    try:
        assert isinstance(client, httpx.AsyncClient)
        limits = client._limits  # httpx exposes limits on _limits attribute
        assert limits.max_connections == 100
        assert limits.max_keepalive_connections == 20
        assert limits.keepalive_expiry == 30.0
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
    """STATE_CA_BUNDLE env var pointing to a PEM file is picked up."""
    # Create a minimal (self-signed) PEM file so ssl.create_default_context
    # can load it without error.  We use Python's ssl module to generate
    # a context first to verify our build_shared_client path at least
    # reaches ssl.create_default_context(cafile=...).
    #
    # For the RED phase this test simply imports build_shared_client
    # (which fails), so the PEM content doesn't matter yet.
    pem_path = tmp_path / "ca.pem"
    pem_path.write_text("")  # empty — real validation in GREEN phase
    monkeypatch.setenv("STATE_CA_BUNDLE", str(pem_path))
    # We expect this to raise ssl.SSLError for empty PEM in GREEN,
    # but the module import (which fails here) is the RED gate.
    # The GREEN task will update this test to use a real PEM or mock ssl.
    client = build_shared_client()  # GREEN: update PEM handling
    try:
        assert isinstance(client, httpx.AsyncClient)
    finally:
        await client.aclose()
