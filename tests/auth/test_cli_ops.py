"""Phase 022 — AUTH-12 ops-layer unit tests.

Tests for state_core.auth.cli_ops: login(), logout(), status().
These tests replaced the Wave 0 RED stubs in Plan 02 (022-02-PLAN.md).

All tests mock the vault path via STATE_AUTH_JSON env var (tmp_path fixture),
and mock provider login() methods to avoid network calls.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.auth.errors import UnknownApiKeyProviderError
from state_core.auth.store import AuthVault, save_vault


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_oauth_cred(provider_id: str = "anthropic", **kwargs: Any) -> OAuthCredential:
    """Build a deterministic OAuthCredential for testing.

    Callers can override any field via kwargs. Fields not in kwargs use
    safe non-real defaults. Note: if you pass `extras` or `account_id` in kwargs,
    the default for that field is not used (caller takes full ownership).
    """
    defaults: dict[str, Any] = {
        "access": "test-access-token-not-real",
        "refresh": "test-refresh-token-not-real",
        "expires": 2_000_000_000.0,
        "account_id": "test-account-id",
        "extras": {"email_address": "test@example.com", "_source": "vault"},
    }
    defaults.update(kwargs)
    return OAuthCredential(provider_id=provider_id, **defaults)


def _make_api_key_cred(provider_id: str = "openai", **kwargs: Any) -> ApiKeyCredential:
    """Build a deterministic ApiKeyCredential for testing."""
    return ApiKeyCredential(
        provider_id=provider_id,
        key="test-api-key-not-real-1234",
        extras={"_source": "vault"},
        **kwargs,
    )


def _write_vault(vault_path: Path, vault: AuthVault) -> None:
    """Write a vault to disk, creating parent dirs as needed."""
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    save_vault(vault_path, vault)


# ── Tests: login() ───────────────────────────────────────────────────────────


def test_login_anthropic_oauth_returns_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """login('anthropic', code_state='code#state') returns OAuthCredential."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    fake_cred = _make_oauth_cred("anthropic")

    with patch("state_core.auth.providers.anthropic.AnthropicAuth") as MockAuth:
        instance = MockAuth.return_value
        instance.login = AsyncMock(return_value=fake_cred)

        from state_core.auth.cli_ops import login

        result = asyncio.run(login("anthropic", code_state="code#state"))

    assert isinstance(result, OAuthCredential)
    assert result.provider_id == "anthropic"


def test_login_openai_api_key_returns_api_key_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """login('openai', api_key='test-key-not-real') returns ApiKeyCredential."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    from state_core.auth.cli_ops import login

    result = asyncio.run(login("openai", api_key="test-api-key-not-real-1234"))

    assert isinstance(result, ApiKeyCredential)
    assert result.provider_id == "openai"


def test_login_unknown_provider_raises_unknown_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """login('not-a-provider') raises UnknownApiKeyProviderError."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    from state_core.auth.cli_ops import login

    with pytest.raises(UnknownApiKeyProviderError):
        asyncio.run(login("not-a-provider"))


def test_login_emits_auth_logged_in_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """login() writes auth.logged_in to SQLite BEFORE SyncEvent mirror."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    call_order: list[str] = []

    class MockStore:
        def append(
            self,
            aggregate_type: str,
            aggregate_id: str,
            event_type: str,
            data: dict,
            mirror: Any = None,
        ) -> None:
            call_order.append("sqlite")
            # Simulate SyncEvent mirror being called after
            if mirror is not None:
                mirror.send(event_type=event_type, data=data)

    class MockMirror:
        def send(self, **kwargs: Any) -> None:
            call_order.append("sync_event")

    fake_cred = _make_oauth_cred("anthropic")

    with patch("state_core.auth.providers.anthropic.AnthropicAuth") as MockAuth:
        instance = MockAuth.return_value
        instance.login = AsyncMock(return_value=fake_cred)

        from state_core.auth.cli_ops import login

        asyncio.run(
            login(
                "anthropic",
                store=MockStore(),
                mirror=MockMirror(),
            )
        )

    # SQLite write must happen before SyncEvent
    assert call_order == ["sqlite", "sync_event"], (
        f"Expected ['sqlite', 'sync_event'] but got {call_order}. "
        "SQLite must be written FIRST (v1 cardinal rule)."
    )


# ── Tests: logout() ──────────────────────────────────────────────────────────


def test_logout_removes_credential_from_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logout('anthropic') removes cred, returns count=1."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    cred = _make_oauth_cred("anthropic")
    vault = AuthVault(providers={"anthropic": [cred]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import logout
    from state_core.auth.store import load_vault

    count = asyncio.run(logout("anthropic"))

    assert count == 1
    reloaded = load_vault(vault_path)
    assert "anthropic" not in reloaded.providers


def test_logout_all_flag_wipes_provider_array(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logout('anthropic', all_=True) wipes entire providers['anthropic'] array."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    cred1 = _make_oauth_cred("anthropic")
    cred2 = _make_oauth_cred("anthropic", account_id="second-account")
    vault = AuthVault(providers={"anthropic": [cred1, cred2]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import logout
    from state_core.auth.store import load_vault

    count = asyncio.run(logout("anthropic", all_=True))

    assert count == 2
    reloaded = load_vault(vault_path)
    assert "anthropic" not in reloaded.providers


def test_logout_emits_auth_logged_out_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logout() writes auth.logged_out to SQLite BEFORE SyncEvent mirror."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    cred = _make_oauth_cred("anthropic")
    vault = AuthVault(providers={"anthropic": [cred]})
    _write_vault(vault_path, vault)

    call_order: list[str] = []

    class MockStore:
        def append(
            self,
            aggregate_type: str,
            aggregate_id: str,
            event_type: str,
            data: dict,
            mirror: Any = None,
        ) -> None:
            call_order.append("sqlite")
            if mirror is not None:
                mirror.send(event_type=event_type, data=data)

    class MockMirror:
        def send(self, **kwargs: Any) -> None:
            call_order.append("sync_event")

    from state_core.auth.cli_ops import logout

    asyncio.run(
        logout(
            "anthropic",
            store=MockStore(),
            mirror=MockMirror(),
        )
    )

    assert call_order == ["sqlite", "sync_event"], (
        f"Expected ['sqlite', 'sync_event'] but got {call_order}. "
        "SQLite must be written FIRST (v1 cardinal rule)."
    )


def test_logout_no_creds_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logout() with no creds present returns 0 (idempotent)."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    # Empty vault
    vault = AuthVault()
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import logout

    count = asyncio.run(logout("anthropic"))

    assert count == 0


# ── Tests: status() ──────────────────────────────────────────────────────────


def test_status_returns_status_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status() returns StatusReport with .providers list and .summary str."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))
    # Unset all api-key env vars so status() only sees the vault contents.
    # The dev machine may have GEMINI_API_KEY set which would synthesize an
    # extra credential and change the provider count.
    from state_core.auth.providers.api_key import _REGISTRY
    for spec in _REGISTRY.values():
        monkeypatch.delenv(spec.env_var, raising=False)

    cred = _make_oauth_cred("anthropic")
    vault = AuthVault(providers={"anthropic": [cred]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import StatusReport, status

    report = asyncio.run(status())

    assert isinstance(report, StatusReport)
    assert isinstance(report.providers, list)
    assert isinstance(report.summary, str)
    # With env vars cleared and only anthropic in vault, exactly 1 provider
    assert "1 provider(s)" in report.summary


def test_status_provider_id_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status(provider_id='anthropic') returns only anthropic rows."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    anthropic_cred = _make_oauth_cred("anthropic")
    openai_cred = _make_api_key_cred("openai")
    vault = AuthVault(providers={"anthropic": [anthropic_cred], "openai": [openai_cred]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import status

    report = asyncio.run(status(provider_id="anthropic"))

    assert all(r.provider_id == "anthropic" for r in report.rows)
    assert report.total_providers == 1


def test_status_source_column_from_extras(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status() row.source reads extras['_source'] — 'opencode-import', 'vault', or 'env'."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    vault_cred = _make_oauth_cred("anthropic", extras={"email_address": "test@example.com", "_source": "vault"})
    import_cred = _make_oauth_cred(
        "anthropic",
        account_id="import-account",
        extras={"_source": "opencode-import"},
    )
    vault = AuthVault(providers={"anthropic": [vault_cred, import_cred]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import status

    report = asyncio.run(status(provider_id="anthropic"))

    sources = {r.account_label: r.source for r in report.rows}
    # vault_cred has email_address so label is "test@example.com"
    assert sources.get("test@example.com") == "vault"
    # import_cred has account_id "import-account" and no email
    assert sources.get("import-account") == "opencode-import"


def test_status_expired_only_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status(show_expired=True) includes only rows with is_expired=True."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    import time as _time

    now = _time.time()
    # Expired: expires < now - 5 min buffer -> expires < now - 300
    expired_cred = OAuthCredential(
        provider_id="anthropic",
        access="test-access-expired",
        refresh="test-refresh-expired",
        expires=now - 400.0,  # 400s in the past → well past 5-min buffer
        extras={"_source": "vault"},
    )
    # Valid: expires > now + 5 min
    valid_cred = OAuthCredential(
        provider_id="anthropic",
        access="test-access-valid",
        refresh="test-refresh-valid",
        expires=now + 3600.0,
        account_id="valid-account",
        extras={"_source": "vault"},
    )
    vault = AuthVault(providers={"anthropic": [expired_cred, valid_cred]})
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import status

    report = asyncio.run(status(show_expired=True))

    assert all(r.is_expired for r in report.rows), (
        f"show_expired=True should only include expired rows; got: {[r.is_expired for r in report.rows]}"
    )
    assert len(report.rows) == 1


def test_status_ordering_alphabetical_then_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status() rows are ordered: providers alphabetical; within provider,
    vault first, then opencode-import, then env; by expires_at ascending."""
    vault_path = tmp_path / ".state" / "auth.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(vault_path))

    import time as _time

    now = _time.time()

    # Two providers: "anthropic" and "github.copilot" (alphabetical order)
    # For anthropic: opencode-import first in vault, vault second — status should flip to vault first
    anthropic_import = OAuthCredential(
        provider_id="anthropic",
        access="import-access-token",
        refresh="import-refresh-token",
        expires=now + 7200.0,
        account_id="import-user",
        extras={"_source": "opencode-import"},
    )
    anthropic_vault = OAuthCredential(
        provider_id="anthropic",
        access="vault-access-token",
        refresh="vault-refresh-token",
        expires=now + 3600.0,  # expires sooner but vault source takes priority
        account_id="vault-user",
        extras={"_source": "vault"},
    )
    copilot_cred = OAuthCredential(
        provider_id="github.copilot",
        access="copilot-access-token",
        refresh="copilot-refresh-token",
        expires=now + 1800.0,
        extras={"_source": "vault"},
    )
    vault = AuthVault(providers={
        "anthropic": [anthropic_import, anthropic_vault],  # import stored first
        "github.copilot": [copilot_cred],
    })
    _write_vault(vault_path, vault)

    from state_core.auth.cli_ops import status

    report = asyncio.run(status())

    provider_ids = [r.provider_id for r in report.rows]

    # anthropic rows must come before github.copilot (alphabetical)
    anthropic_indices = [i for i, r in enumerate(report.rows) if r.provider_id == "anthropic"]
    copilot_indices = [i for i, r in enumerate(report.rows) if r.provider_id == "github.copilot"]
    assert max(anthropic_indices) < min(copilot_indices), (
        "anthropic rows must precede github.copilot rows (alphabetical)"
    )

    # Within anthropic: vault row should come BEFORE opencode-import row
    anthropic_rows = [r for r in report.rows if r.provider_id == "anthropic"]
    assert anthropic_rows[0].source == "vault", (
        f"First anthropic row should be 'vault', got {anthropic_rows[0].source!r}"
    )
    assert anthropic_rows[1].source == "opencode-import", (
        f"Second anthropic row should be 'opencode-import', got {anthropic_rows[1].source!r}"
    )


def test_cli_ops_import_succeeds() -> None:
    """from state_core.auth.cli_ops import login, logout, status succeeds."""
    # If the import fails, this test will error at module load time.
    from state_core.auth.cli_ops import login, logout, status, StatusReport, StatusRow

    assert callable(login)
    assert callable(logout)
    assert callable(status)
    assert StatusReport is not None
    assert StatusRow is not None
