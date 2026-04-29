"""Local fixtures for tests/auth/providers/ — Phase 014 (AUTH-01).

Lives alongside test_anthropic.py to avoid name clashes with the parent
tests/auth/conftest.py. The parent provides oauth_cred / now_frozen /
auth_json_path / clean_state_auth_json_env (autouse) /
_isolate_structlog_for_auth_tests (autouse).

This conftest adds Phase-014-specific fixtures: pinned PKCE verifier,
fake code#state paste string, mock token-endpoint payload, and
monkeypatch helpers for getpass + generate_verifier.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import pytest


# Pinned 43-char base64url-no-pad string. Matches the EXACT length window
# RFC 7636 §4.1 mandates for PKCE verifiers ([43, 128]) and the alphabet
# `[A-Za-z0-9_-]+`. Kept stable so match_json assertions in test_anthropic.py
# can pin the exact body.
#
# String construction: 'fixture-verifier-' (17 chars) + 'a' * 26 = 43 chars.
# secrets.token_urlsafe(32) returns exactly 43 chars; we mirror that length
# so the pinned fixture is interchangeable with real verifier output in
# match_json equality checks.
_FIXTURE_VERIFIER = "fixture-verifier-aaaaaaaaaaaaaaaaaaaaaaaaaa"

# Import-time self-check — fails LOUD at pytest collection if the constant
# ever drifts (not at first-test-run). Both the length AND the alphabet are
# load-bearing: a wrong-length verifier would produce a "verifier too short"
# server-side error in real flows; a non-base64url char (e.g., '+', '/', '=')
# would be normalised by Anthropic's parser and break round-trip equality.
assert len(_FIXTURE_VERIFIER) == 43, (
    f"PKCE fixture verifier must be EXACTLY 43 chars (RFC 7636 §4.1 minimum); "
    f"got {len(_FIXTURE_VERIFIER)}: {_FIXTURE_VERIFIER!r}"
)
assert re.fullmatch(r"[A-Za-z0-9_-]+", _FIXTURE_VERIFIER), (
    f"PKCE fixture verifier must use ONLY base64url-no-pad alphabet "
    f"`[A-Za-z0-9_-]`; got: {_FIXTURE_VERIFIER!r}"
)


@pytest.fixture
def fixture_verifier() -> str:
    """Canonical pinned PKCE verifier; reused as state == verifier (P0-8)."""
    return _FIXTURE_VERIFIER


@pytest.fixture
def fixture_paste(fixture_verifier: str) -> str:
    """Canonical `code#state` paste string the user would type in interactively."""
    return f"fixture-code#{fixture_verifier}"


@pytest.fixture
def fixture_token_response(fixture_verifier: str) -> dict[str, Any]:
    """Canonical 200-OK payload from POST https://platform.claude.com/v1/oauth/token.

    Matches AnthropicTokenResponse(extra="ignore") — Plan 02 will add an
    'unknown_extra_field' to prove forward-compat at row 014-01-11.
    """
    return {
        "access_token": "sk-ant-oat01-FIXTURE-AAAAAAAAAAAAAAAAAAAAAAAAA",
        "refresh_token": "sk-ant-ort01-FIXTURE-BBBBBBBBBBBBBBBBBBBBBBBBB",
        "expires_in": 28_800,
        "token_type": "Bearer",
        "account": {
            "uuid": "u-fixture-account-uuid",
            "email_address": "fixture@example.test",
        },
    }


@pytest.fixture
def mock_getpass(monkeypatch: pytest.MonkeyPatch, fixture_paste: str) -> Callable[[], None]:
    """Patch getpass.getpass IN the provider module to return the canonical paste.

    Returned callable: invoke `mock_getpass()` inside the test body to apply
    the patch. Lazy so individual tests can OVERRIDE the return value via
    `monkeypatch.setattr` BEFORE calling `mock_getpass()` if needed.

    Pitfall 7 defense: tests MUST never let real getpass run under pytest;
    a non-tty falls back to input() and echoes the auth code to test logs.
    """

    def _apply() -> None:
        monkeypatch.setattr(
            "state_core.auth.providers.anthropic.getpass.getpass",
            lambda _prompt="": fixture_paste,
        )

    return _apply


@pytest.fixture
def mock_generate_verifier(
    monkeypatch: pytest.MonkeyPatch, fixture_verifier: str
) -> Callable[[], None]:
    """Patch generate_verifier so PKCE state is deterministic in tests."""

    def _apply() -> None:
        monkeypatch.setattr(
            "state_core.auth.oauth_common.pkce.generate_verifier",
            lambda *_args, **_kwargs: fixture_verifier,
        )
        # Also patch the re-import surface in providers.anthropic, in case
        # the impl imports `from state_core.auth.oauth_common.pkce import generate_verifier`
        # at module load (rebinds the name in the provider's namespace).
        try:
            monkeypatch.setattr(
                "state_core.auth.providers.anthropic.generate_verifier",
                lambda *_args, **_kwargs: fixture_verifier,
                raising=False,
            )
        except AttributeError:
            pass

    return _apply
