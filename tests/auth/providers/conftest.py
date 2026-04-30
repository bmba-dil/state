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


# ── Phase 015 fixtures (Gemini CLI OAuth) ─────────────────────────────

# Public Desktop-App OAuth credentials from gemini-cli (verbatim — P1-3).
# Pinned here so test_google_gemini.py can assert plaintext source-of-truth.
_GEMINI_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
_GEMINI_CLIENT_SECRET = "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"


@pytest.fixture
def fixture_gemini_client_id() -> str:
    return _GEMINI_CLIENT_ID


@pytest.fixture
def fixture_gemini_client_secret() -> str:
    return _GEMINI_CLIENT_SECRET


@pytest.fixture
def fixture_google_state() -> str:
    """Pinned 43-char state string. INDEPENDENT from fixture_verifier — the
    whole point of Phase 015 is state != verifier (NOT P0-8's reuse)."""
    return "fixture-google-state-aaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def fixture_google_verifier() -> str:
    """Pinned PKCE verifier for Google flow — DIFFERENT string from
    fixture_google_state to prove independence."""
    return "fixture-google-verifier-bbbbbbbbbbbbbbbbbbbbb"


@pytest.fixture
def fixture_google_id_token() -> str:
    """Synthetic JWT with parseable payload — header.payload.signature.

    Payload (decoded base64url):
      {"sub": "u-google-fixture-12345",
       "email": "fixture@example.test",
       "email_verified": true,
       "iss": "https://accounts.google.com"}

    Signature is gibberish — we don't verify locally (per Pitfall 8 design
    decision: trust TLS to oauth2.googleapis.com).
    """
    import base64
    import orjson

    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
    payload_dict = {
        "sub": "u-google-fixture-12345",
        "email": "fixture@example.test",
        "email_verified": True,
        "iss": "https://accounts.google.com",
    }
    payload = base64.urlsafe_b64encode(orjson.dumps(payload_dict)).rstrip(b"=").decode()
    sig = "FIXTURE-SIG"  # not a real signature
    return f"{header}.{payload}.{sig}"


@pytest.fixture
def fixture_google_access_token() -> str:
    """ya29.* access token; matches Google's wire shape."""
    return "ya29.FIXTURE-AAAAAAAAAAAAAAAAAAAAAAAAAA-do-not-redact-in-test-only"


@pytest.fixture
def fixture_google_refresh_token() -> str:
    """1//* refresh token; matches Google's wire shape."""
    return "1//FIXTURE-OLD-BBBBBBBBBBBBBBBBBBBBBBBBBB-do-not-redact-in-test-only"


@pytest.fixture
def fixture_google_rotated_refresh_token() -> str:
    """Distinct refresh token returned by a refresh response (P2-2 rotation)."""
    return "1//FIXTURE-ROTATED-CCCCCCCCCCCCCCCCCCCC-do-not-redact-in-test-only"


@pytest.fixture
def fixture_google_token_response(
    fixture_google_access_token: str,
    fixture_google_id_token: str,
    fixture_google_rotated_refresh_token: str,
) -> dict:
    """Canonical 200-OK payload from POST oauth2.googleapis.com/token (login)."""
    return {
        "access_token": fixture_google_access_token,
        "expires_in": 3599,
        "refresh_token": fixture_google_rotated_refresh_token,
        "scope": (
            "https://www.googleapis.com/auth/cloud-platform "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/userinfo.profile"
        ),
        "token_type": "Bearer",
        "id_token": fixture_google_id_token,
    }


@pytest.fixture
def mock_google_state_and_verifier(
    monkeypatch: pytest.MonkeyPatch,
    fixture_google_state: str,
    fixture_google_verifier: str,
) -> Callable[[], None]:
    """Patch generate_verifier in the gemini provider to return DIFFERENT
    pinned strings on first vs. second call — proves state != verifier
    (independent calls)."""

    def _apply() -> None:
        sequence = iter([fixture_google_state, fixture_google_verifier])

        def _next(*_args, **_kwargs) -> str:
            return next(sequence)

        # Patch the import surface inside the gemini provider module.
        try:
            monkeypatch.setattr(
                "state_core.auth.providers.google_gemini.generate_verifier",
                _next,
                raising=False,
            )
        except AttributeError:
            pass
        # Also patch the source so any direct re-imports see the same.
        monkeypatch.setattr(
            "state_core.auth.oauth_common.pkce.generate_verifier",
            _next,
        )

    return _apply


@pytest.fixture
def mock_loopback_callback(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Patch oauth_common.loopback.wait_for_oauth_callback to return a
    pinned authorization code without spinning up a real HTTP listener.

    Tests pass the desired (code, state) tuple via param.
    """

    def _apply(code: str = "fixture-google-code", state: str | None = None) -> None:
        async def _fake(port: int, expected_state: str, *, timeout: float = 300.0) -> str:
            # If test passed a state, simulate state mismatch when it differs.
            effective = state if state is not None else expected_state
            if effective != expected_state:
                from state_core.auth.errors import AuthLoginError
                raise AuthLoginError("OAuth state mismatch (CSRF check failed)")
            return code

        monkeypatch.setattr(
            "state_core.auth.providers.google_gemini.wait_for_oauth_callback",
            _fake,
            raising=False,
        )
        monkeypatch.setattr(
            "state_core.auth.oauth_common.loopback.wait_for_oauth_callback",
            _fake,
            raising=False,
        )

    return _apply


# ── Antigravity-specific fixtures (Phase 016) ────────────────────────────


@pytest.fixture
def mock_authorize_url_antigravity(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the authorize URL printed by AntigravityAuth.login().

    Returns a list that will receive each printed URL containing the Google
    accounts host. Tests assert on the captured URL contents (must contain
    literal `localhost:51121`, `cclog`, `experimentsandconfigs`, etc.).

    Module-late-bind: in Wave 0, `state_core.auth.providers.antigravity`
    does NOT yet exist on disk. The fixture silently no-ops in that case
    so collection succeeds without ImportError.
    """
    captured: list[str] = []

    def fake_print(*args: Any, **kwargs: Any) -> None:
        for a in args:
            if isinstance(a, str) and "https://accounts.google.com" in a:
                captured.append(a)

    # Late import — module may not exist during collection in Wave 0.
    try:
        from state_core.auth.providers import antigravity as _ag  # type: ignore[import-not-found]

        monkeypatch.setattr(_ag, "print", fake_print, raising=False)
    except ImportError:
        # Wave 0: module not yet created — fixture is inert.
        pass

    return captured


@pytest.fixture
def captured_token_post_antigravity() -> dict[str, Any]:
    """Standard 200-OK token response body for Antigravity.

    Returns a JSON-serializable dict matching AntigravityTokenResponse
    shape with a 3-part JWT id_token whose payload base64url-decodes to
    ``{"sub": "test_sub_antigravity", "email": "test@example.com",
    "email_verified": true}``.

    Five Antigravity scopes embedded in the `scope` field (cloud-platform,
    userinfo.email, userinfo.profile, cclog, experimentsandconfigs) — P2-3.
    """
    # Build a valid 3-part JWT with a parseable payload. orjson preserves
    # dict insertion order (3.7+), so id_token encoding is deterministic.
    import base64
    import orjson

    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload_dict = {
        "sub": "test_sub_antigravity",
        "email": "test@example.com",
        "email_verified": True,
    }
    payload = base64.urlsafe_b64encode(orjson.dumps(payload_dict)).rstrip(b"=").decode()
    signature = "sig"  # ignored — no signature verification per RESEARCH §rule 5
    id_token = f"{header}.{payload}.{signature}"

    return {
        "access_token": "ya29.test_access_antigravity",
        "refresh_token": "1//test_refresh_antigravity",
        "expires_in": 3599,
        "scope": (
            "https://www.googleapis.com/auth/cloud-platform "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/userinfo.profile "
            "https://www.googleapis.com/auth/cclog "
            "https://www.googleapis.com/auth/experimentsandconfigs"
        ),
        "token_type": "Bearer",
        "id_token": id_token,
    }
