"""Shared fixtures for auth tests (Phase 011)."""

from __future__ import annotations

import pytest

from state_core.auth.base import ApiKeyCredential, OAuthCredential


@pytest.fixture
def oauth_cred() -> OAuthCredential:
    """Deterministic OAuth credential for round-trip + redaction tests.

    `expires` is far-future (year 2033) so freshness checks against
    `now=time.time()` would always pass — but tests must inject `now`
    explicitly per the determinism rule (RESEARCH §Pattern 3).
    """
    return OAuthCredential(
        access="sk-ant-oat-test-token-do-not-redact-in-test-only",
        refresh="rt-test-refresh-token-do-not-redact-in-test-only",
        expires=2_000_000_000.0,
        provider_id="anthropic",
        account_id="acct-test-12345",
    )


@pytest.fixture
def api_key_cred() -> ApiKeyCredential:
    """Deterministic API-key credential."""
    return ApiKeyCredential(
        key="sk-ant-api03-test-key-do-not-redact-in-test-only",
        provider_id="anthropic",
    )


@pytest.fixture
def now_frozen() -> float:
    """Frozen 'now' value for is_expired tests. Year 2026."""
    return 1_770_000_000.0
