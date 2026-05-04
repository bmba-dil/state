"""Daemon-owned shared httpx.AsyncClient factory.

Usage (daemon startup only):

    from state_core.http_client import build_shared_client

    client = build_shared_client()   # reads STATE_HTTP_PROXY / STATE_CA_BUNDLE env vars
    # OR
    client = build_shared_client(proxy="http://proxy:8080", verify=False)

The returned client is intended for provider inference traffic only
(litellm + direct Anthropic SDK).  Auth provider OAuth flows use
per-call httpx.AsyncClient() by design — do NOT pass this client to
state_core.auth.providers.*.

Always close the client on daemon shutdown:
    await client.aclose()
"""

from __future__ import annotations

import os
import ssl

import httpx

# Connection pool defaults — tuned for a daemon serving provider inference traffic.
# 100 total connections supports concurrent litellm calls across multiple providers.
# 20 keepalive slots reduce reconnect overhead to Anthropic/Gemini/etc. endpoints.
# 30s keepalive expiry balances idle connection reuse vs. stale-socket risk.
_DEFAULT_MAX_CONNECTIONS: int = 100
_DEFAULT_MAX_KEEPALIVE_CONNECTIONS: int = 20
_DEFAULT_KEEPALIVE_EXPIRY: float = 30.0


def build_shared_client(
    *,
    max_connections: int = _DEFAULT_MAX_CONNECTIONS,
    max_keepalive_connections: int = _DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    keepalive_expiry: float = _DEFAULT_KEEPALIVE_EXPIRY,
    proxy: str | None = None,
    verify: bool | ssl.SSLContext = True,
) -> httpx.AsyncClient:
    """Build the daemon-level shared httpx.AsyncClient.

    Environment variables (lower priority than explicit args):
    - STATE_HTTP_PROXY:  proxy URL (e.g. "http://proxy.corp:8080")
    - STATE_CA_BUNDLE:   path to custom CA PEM file
    - STATE_TLS_VERIFY:  set "false" to disable TLS verification (dev/test only)

    Args:
        max_connections:          Total concurrent connections (default 100).
        max_keepalive_connections: Idle keepalive connections in pool (default 20).
        keepalive_expiry:         Seconds before idle connection is closed (default 30.0).
        proxy:                    Explicit proxy URL.  If None, falls back to
                                  STATE_HTTP_PROXY env var.  trust_env=True also
                                  reads HTTP_PROXY/HTTPS_PROXY/ALL_PROXY.
        verify:                   TLS config: True (system CAs), False (skip),
                                  or ssl.SSLContext (custom CA).  If True and
                                  STATE_CA_BUNDLE env is set, a custom SSLContext
                                  is built from that path.

    Returns:
        A configured httpx.AsyncClient.  Caller is responsible for calling
        ``await client.aclose()`` on shutdown.
    """
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
    )

    # Resolve proxy — explicit arg wins over env var.
    resolved_proxy: str | None = proxy
    if resolved_proxy is None:
        resolved_proxy = os.environ.get("STATE_HTTP_PROXY")

    # Resolve TLS verify — explicit arg wins over env vars.
    resolved_verify: bool | ssl.SSLContext = verify
    if isinstance(verify, bool) and verify:
        # Only apply env-var overrides when verify is still the default True.
        ca_bundle = os.environ.get("STATE_CA_BUNDLE")
        tls_verify_env = os.environ.get("STATE_TLS_VERIFY", "true").lower()
        if ca_bundle:
            resolved_verify = ssl.create_default_context(cafile=ca_bundle)
        elif tls_verify_env == "false":
            resolved_verify = False

    return httpx.AsyncClient(
        limits=limits,
        proxy=resolved_proxy,
        verify=resolved_verify,
        trust_env=True,
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
    )
