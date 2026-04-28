"""Shared fixtures for auth tests (Phase 011 + Phase 012)."""

from __future__ import annotations

from pathlib import Path

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


# ── Phase 012 fixtures ────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_state_auth_json_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense against Pitfall 8: prevent STATE_AUTH_JSON leakage between tests.

    Autouse — fires for EVERY test in tests/auth/. Uses monkeypatch.delenv
    with raising=False so it is a no-op when the env var is unset.
    monkeypatch automatically restores the prior value at test teardown.
    """
    monkeypatch.delenv("STATE_AUTH_JSON", raising=False)


@pytest.fixture
def auth_json_path(tmp_path: Path) -> Path:
    """Per-test .state/auth.json path under pytest's tmp_path.

    Parent directory is pre-created so callers may write directly without
    needing to call mkdir themselves. Path is unique per-test (pytest-managed).
    """
    p = tmp_path / ".state" / "auth.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def vault_with_one_oauth(oauth_cred: OAuthCredential):  # type: ignore[no-untyped-def]
    """In-memory AuthVault with one anthropic OAuth credential.

    Uses pytest.importorskip so collection survives Plan 02 lag — when
    state_core.auth.store has not yet exposed AuthVault, every test
    consuming this fixture is SKIPPED rather than ERRORED at collect time.
    """
    store = pytest.importorskip("state_core.auth.store")
    return store.AuthVault(providers={"anthropic": [oauth_cred]})
