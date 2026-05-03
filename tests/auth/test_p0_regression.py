"""Phase 022 — AUTH-13 P0 pitfall regression suite.

One named test per P0 pitfall. All 9 tests use pytest-httpx mocks or
direct constant/behavior assertions. No live network calls.

P0 pitfall reference: .planning/research/PITFALLS.md (rows P0-1..P0-8, P0-13).
Capture date: see individual golden JSON files.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
from pathlib import Path

import filelock
import pytest

from state_core.auth.providers.anthropic import (
    _CLIENT_ID,
    _USER_AGENT,
    _ANTHROPIC_BETA,
    AnthropicAuth,
)
from state_core.auth.store import AuthVaultPermissionError, load_vault
from state_core.auth.refresh import RefreshLockTimeout, is_expired_buffered
from state_core.auth.base import OAuthCredential

GOLDEN_DIR = Path(__file__).parent / "golden"


def test_p0_1_user_agent_stealth(fake_oauth_cred: OAuthCredential) -> None:
    """P0-1: Outbound user-agent on Anthropic stealth calls matches
    'claude-cli/<version> (external, cli)'.

    Pitfall reference: .planning/research/PITFALLS.md P0-1
    Method: AnthropicAuth().http_headers(cred) is the AUTH-13 hook.
    """
    cred = fake_oauth_cred.model_copy(update={"provider_id": "anthropic"})
    headers = AnthropicAuth().http_headers(cred)
    assert "user-agent" in headers, "Missing user-agent header on Anthropic stealth call"
    assert headers["user-agent"] == _USER_AGENT, (
        f"P0-1 FAIL: user-agent {headers['user-agent']!r} != expected {_USER_AGENT!r}\n"
        "See .planning/research/PITFALLS.md P0-1"
    )
    assert "(external, cli)" in headers["user-agent"], (
        "P0-1 FAIL: '(external, cli)' suffix missing from user-agent\n"
        "See .planning/research/PITFALLS.md P0-1"
    )


def test_p0_2_anthropic_beta_full_string(fake_oauth_cred: OAuthCredential) -> None:
    """P0-2: anthropic-beta header matches the full pinned string.

    Pitfall reference: .planning/research/PITFALLS.md P0-2
    Note: claude-code-20250219 was REMOVED in Claude Code 2.1.121 (2026-04-29 capture).
    The current pinned string is verified against the _ANTHROPIC_BETA constant.
    """
    cred = fake_oauth_cred.model_copy(update={"provider_id": "anthropic"})
    headers = AnthropicAuth().http_headers(cred)
    assert "anthropic-beta" in headers, (
        "P0-2 FAIL: anthropic-beta header missing from Anthropic stealth call\n"
        "See .planning/research/PITFALLS.md P0-2"
    )
    assert headers["anthropic-beta"] == _ANTHROPIC_BETA, (
        f"P0-2 FAIL: anthropic-beta {headers['anthropic-beta']!r} != pinned {_ANTHROPIC_BETA!r}\n"
        "See .planning/research/PITFALLS.md P0-2"
    )
    # The pinned string must contain the OAuth flag (always required on auth endpoints)
    assert "oauth-2025-04-20" in headers["anthropic-beta"], (
        "P0-2 FAIL: Missing oauth-2025-04-20 in anthropic-beta\n"
        "See .planning/research/PITFALLS.md P0-2"
    )


def test_p0_3_x_app_cli(fake_oauth_cred: OAuthCredential) -> None:
    """P0-3: x-app: cli header present on Anthropic stealth calls.

    Pitfall reference: .planning/research/PITFALLS.md P0-3
    """
    cred = fake_oauth_cred.model_copy(update={"provider_id": "anthropic"})
    headers = AnthropicAuth().http_headers(cred)
    assert "x-app" in headers, (
        "P0-3 FAIL: x-app header missing from Anthropic stealth call\n"
        "See .planning/research/PITFALLS.md P0-3"
    )
    assert headers["x-app"] == "cli", (
        f"P0-3 FAIL: x-app {headers['x-app']!r} != 'cli'\n"
        "See .planning/research/PITFALLS.md P0-3"
    )


def test_p0_4_bearer_not_x_api_key(fake_oauth_cred: OAuthCredential) -> None:
    """P0-4: Authorization: Bearer present AND x-api-key NOT present.

    Pitfall reference: .planning/research/PITFALLS.md P0-4
    Golden: tests/auth/golden/anthropic/login_token_exchange.json

    Note: AnthropicAuth.http_headers() returns lowercase 'authorization' key.
    """
    cred = fake_oauth_cred.model_copy(update={"provider_id": "anthropic"})
    headers = AnthropicAuth().http_headers(cred)

    # Positive: Authorization: Bearer must be present (check case-insensitively)
    auth_val = headers.get("Authorization") or headers.get("authorization", "")
    assert auth_val, (
        "P0-4 FAIL: Authorization header missing\nSee .planning/research/PITFALLS.md P0-4"
    )
    assert auth_val.startswith("Bearer "), (
        f"P0-4 FAIL: Authorization value {auth_val!r} does not start with 'Bearer '\n"
        "See .planning/research/PITFALLS.md P0-4"
    )

    # Negative: x-api-key MUST NOT be present (P0-4 — using x-api-key instead of Bearer)
    lower_keys = {k.lower() for k in headers}
    assert "x-api-key" not in lower_keys, (
        "P0-4 FAIL: x-api-key header present on Anthropic stealth call — should use Bearer\n"
        "See .planning/research/PITFALLS.md P0-4"
    )


def test_p0_5_client_id_base64_decoded() -> None:
    """P0-5: _CLIENT_ID decoded from base64 equals '9d1c250a-e61b-44d9-88ed-5944d1962f5e'.

    Pitfall reference: .planning/research/PITFALLS.md P0-5
    This test asserts providers/anthropic.py runtime-assertion is correct.
    """
    assert _CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e", (
        f"P0-5 FAIL: _CLIENT_ID is {_CLIENT_ID!r}, "
        "expected '9d1c250a-e61b-44d9-88ed-5944d1962f5e'\n"
        "See .planning/research/PITFALLS.md P0-5"
    )


@pytest.mark.slow
def test_p0_6_filelock_acquire_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_oauth_cred: OAuthCredential,
) -> None:
    """P0-6: refresh_credential raises RefreshLockTimeout when lock cannot
    be acquired within the timeout.

    Pitfall reference: .planning/research/PITFALLS.md P0-6
    Technique: monkeypatch filelock.AsyncFileLock.__aenter__ to raise filelock.Timeout.

    Note: refresh_credential signature is (method, provider_id, idx, *, vault_path, ...)
    refresh_credential does a "quick check" (reads vault outside lock) before acquiring
    the lock. We must:
      1. Pre-populate vault with an EXPIRED credential so quick-check passes
      2. Then monkeypatch the lock's __aenter__ so the lock acquisition raises Timeout
    """
    from state_core.auth.refresh import refresh_credential
    from state_core.auth.store import AuthVault, save_vault

    vault_path = tmp_path / "auth.json"

    # Pre-populate vault with an expired credential so quick-check proceeds to lock
    expired_cred = fake_oauth_cred.model_copy(update={
        "provider_id": "anthropic",
        "expires": 0.0,  # expired in 1970 — always needs refresh
    })
    vault = AuthVault(providers={"anthropic": [expired_cred]})
    save_vault(vault_path, vault)

    # Monkeypatch AsyncFileLock.__aenter__ to raise filelock.Timeout immediately
    async def _raise_timeout(self: filelock.AsyncFileLock) -> filelock.AsyncFileLock:
        raise filelock.Timeout(str(self.lock_file))

    monkeypatch.setattr(filelock.AsyncFileLock, "__aenter__", _raise_timeout)

    # refresh_credential must propagate RefreshLockTimeout when lock is unavailable
    with pytest.raises(RefreshLockTimeout):
        asyncio.run(
            refresh_credential(
                method=AnthropicAuth(),
                provider_id="anthropic",
                idx=0,
                vault_path=vault_path,
                now=1.0,  # far past expires=0.0, so quick-check sees it expired
            )
        )


def test_p0_7_five_minute_expiry_buffer(fake_oauth_cred: OAuthCredential) -> None:
    """P0-7: is_expired_buffered returns True when now >= expires - 300s.

    Pitfall reference: .planning/research/PITFALLS.md P0-7
    Contract: 5-minute buffer applied by is_expired_buffered (Phase 013).
    """
    # Use fixed expires = 10000.0 to avoid time.time() dependency
    cred = fake_oauth_cred.model_copy(update={
        "provider_id": "anthropic",
        "expires": 10000.0,
    })

    # At exactly expires - 300: should be considered expired (buffer kicks in)
    assert is_expired_buffered(cred, now=10000.0 - 300.0) is True, (
        "P0-7 FAIL: is_expired_buffered returned False at expires - 300s\n"
        "See .planning/research/PITFALLS.md P0-7"
    )

    # At expires - 301: NOT yet expired (1 second before the buffer kicks in)
    assert is_expired_buffered(cred, now=10000.0 - 301.0) is False, (
        "P0-7 FAIL: is_expired_buffered returned True at expires - 301s\n"
        "See .planning/research/PITFALLS.md P0-7"
    )

    # At expiry itself: definitely expired
    assert is_expired_buffered(cred, now=10000.0) is True, (
        "P0-7 FAIL: is_expired_buffered returned False at actual expiry time\n"
        "See .planning/research/PITFALLS.md P0-7"
    )


def test_p0_8_pkce_state_equals_verifier() -> None:
    """P0-8: In Anthropic flow, the OAuth 'state' parameter byte-equals
    the PKCE code_verifier (they share the same value per claude-oauth.md / P0-8).

    Gemini uses TWO INDEPENDENT verifiers (state != verifier there).

    Pitfall reference: .planning/research/PITFALLS.md P0-8
    Technique: inspect _build_authorize_url source + verify state=verifier assignment.
    """
    from state_core.auth.providers.anthropic import _build_authorize_url
    from state_core.auth.oauth_common.pkce import generate_verifier, build_challenge
    from urllib.parse import urlparse, parse_qs

    # Generate a fixed verifier and challenge pair
    verifier = generate_verifier()
    challenge = build_challenge(verifier)

    # Build the authorize URL — Anthropic uses verifier as state (P0-8)
    url = _build_authorize_url(verifier, challenge)

    # Parse the URL and extract query params
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Assert state == verifier (the P0-8 contract)
    state_values = params.get("state", [])
    assert state_values, (
        "P0-8 FAIL: 'state' parameter missing from Anthropic authorize URL\n"
        "See .planning/research/PITFALLS.md P0-8"
    )
    assert state_values[0] == verifier, (
        f"P0-8 FAIL: state {state_values[0]!r} != verifier {verifier!r}\n"
        "Anthropic flow must reuse PKCE verifier as state (claude-oauth.md spec)\n"
        "See .planning/research/PITFALLS.md P0-8"
    )

    # Also assert code_challenge is present (PKCE S256 contract)
    challenge_values = params.get("code_challenge", [])
    assert challenge_values, (
        "P0-8 FAIL: code_challenge missing from authorize URL\n"
        "See .planning/research/PITFALLS.md P0-8"
    )
    assert challenge_values[0] == challenge, (
        f"P0-8 FAIL: code_challenge {challenge_values[0]!r} != expected {challenge!r}\n"
        "See .planning/research/PITFALLS.md P0-8"
    )


def test_p0_13_chmod_0600_verified_on_read(tmp_path: Path) -> None:
    """P0-13: load_vault raises AuthVaultPermissionError when auth.json
    has mode != 0o600.

    Pitfall reference: .planning/research/PITFALLS.md P0-13
    """
    vault_file = tmp_path / "auth.json"
    # Write a valid-shape vault (minimal)
    vault_file.write_text('{"schema_version": 1, "providers": {}}')
    os.chmod(vault_file, 0o644)  # intentionally wrong mode

    with pytest.raises(AuthVaultPermissionError) as exc_info:
        load_vault(vault_file)

    # Error message should reference both actual and expected mode
    error_msg = str(exc_info.value)
    assert "0o644" in error_msg or "644" in error_msg, (
        f"P0-13 FAIL: error message {error_msg!r} does not mention actual mode 0o644"
    )
    assert "0o600" in error_msg or "600" in error_msg, (
        f"P0-13 FAIL: error message {error_msg!r} does not mention expected mode 0o600"
    )
