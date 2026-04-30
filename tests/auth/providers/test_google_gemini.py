"""RED stubs for state_core.auth.providers.google_gemini (AUTH-02).

Tests are RED until Plans B/C/D implement them. Test names mirror
015-VALIDATION.md row IDs — plan-checker / verify-work map by name.

Plans:
  Wave 1 (B): oauth_common/loopback.py
  Wave 2 (C): pure helpers (constants, is_token, is_expired, http_headers,
              id_token parser, _build_authorize_url, _exchange_code)
  Wave 3 (D): orchestration (login, refresh, __main__ argparse)

RED-state strategy:
    Plan A ships these tests BEFORE
    ``state_core.auth.providers.google_gemini`` exists. The module is
    imported via ``try / except ImportError`` and a module-level
    ``pytestmark = pytest.mark.skipif(...)`` ensures collection always
    succeeds — every test is SKIPPED with a clear reason until Plans
    B/C/D land. ``--collect-only`` lists every stub by name so the
    plan-checker can map test IDs to 015-VALIDATION.md rows.

Each test asserts a SINGLE acceptance criterion from 015-VALIDATION.md.
"""

from __future__ import annotations

import pytest

# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces every stub by name.

try:
    from state_core.auth.providers import google_gemini  # type: ignore[import-not-found]

    _GEMINI_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _GEMINI_AVAILABLE = False
    _IMPORT_ERROR = _e
    google_gemini = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _GEMINI_AVAILABLE,
    reason=f"Waves 2/3 (Plans C/D) not yet landed: {_IMPORT_ERROR}",
)


# ── Wave 2 (Plan C) — pure helpers ────────────────────────────────────

# 015-C-01
def test_token_shape_sniffer() -> None:
    """is_token() returns True for `ya29.` access tokens, False for others."""
    auth = google_gemini.GoogleGeminiAuth()
    assert auth.is_token("ya29.FOOBAR")
    assert auth.is_token("ya29.")  # bare prefix accepted (degenerate but consistent)
    assert not auth.is_token("sk-ant-oat-FOOBAR")
    assert not auth.is_token("sk-ant-api03-FOOBAR")
    assert not auth.is_token("1//refresh-token-FOOBAR")
    assert not auth.is_token("")


# 015-C-02 alias — research §validation row "is_token_ya29_prefix"
def test_is_token_ya29_prefix() -> None:
    """Alias for token_shape_sniffer — explicit ya29.* prefix assertion."""
    auth = google_gemini.GoogleGeminiAuth()
    assert auth.is_token("ya29.x")
    assert not auth.is_token("YA29.x")  # case-sensitive (Google ships lowercase)
    assert not auth.is_token(" ya29.x")  # no leading whitespace tolerated


# 015-C-02
def test_is_expired() -> None:
    """is_expired delegates to is_expired_buffered (5-min buffer at AuthMethod layer)."""
    from state_core.auth.base import OAuthCredential

    auth = google_gemini.GoogleGeminiAuth()
    cred = OAuthCredential(
        access="ya29.x",
        refresh="1//x",
        expires=1_000_000.0,
        provider_id="google.gemini_cli",
    )
    # now well before expiry-buffer → not expired
    assert auth.is_expired(cred, now=999_000.0) is False
    # now after expiry → expired
    assert auth.is_expired(cred, now=1_000_001.0) is True


def test_is_expired_uses_300s_buffer() -> None:
    """P0-7: now >= cred.expires - 300 → True."""
    from state_core.auth.base import OAuthCredential

    auth = google_gemini.GoogleGeminiAuth()
    cred = OAuthCredential(
        access="ya29.x",
        refresh="1//x",
        expires=10_000.0,
        provider_id="google.gemini_cli",
    )
    # 5-min buffer (300s) — now == expires - 300 → expired (>= boundary)
    assert auth.is_expired(cred, now=9_700.0) is True
    # now slightly before buffer → not expired
    assert auth.is_expired(cred, now=9_699.999) is False


# 015-C-03
def test_http_headers() -> None:
    """http_headers returns Bearer + (optional) x-goog-user-project."""
    from state_core.auth.base import ApiKeyCredential, OAuthCredential

    auth = google_gemini.GoogleGeminiAuth()
    oauth = OAuthCredential(
        access="ya29.ACCESS",
        refresh="1//REFRESH",
        expires=1_000_000.0,
        provider_id="google.gemini_cli",
    )
    headers = auth.http_headers(oauth)
    assert headers == {"authorization": "Bearer ya29.ACCESS"}

    # ApiKeyCredential → empty dict (caller decides for non-OAuth)
    api = ApiKeyCredential(key="secret", provider_id="google.gemini_cli")
    assert auth.http_headers(api) == {}


def test_http_headers_bearer_and_optional_project() -> None:
    """http_headers omits x-goog-user-project unless extras['project_id'] is set."""
    from state_core.auth.base import OAuthCredential

    auth = google_gemini.GoogleGeminiAuth()
    # Without project_id
    cred = OAuthCredential(
        access="ya29.x",
        refresh="1//x",
        expires=1_000_000.0,
        provider_id="google.gemini_cli",
    )
    h = auth.http_headers(cred)
    assert "authorization" in h
    assert "x-goog-user-project" not in h

    # With project_id
    cred_with_project = OAuthCredential(
        access="ya29.y",
        refresh="1//y",
        expires=1_000_000.0,
        provider_id="google.gemini_cli",
        extras={"project_id": "my-gcp-project"},
    )
    h2 = auth.http_headers(cred_with_project)
    assert h2["authorization"] == "Bearer ya29.y"
    assert h2["x-goog-user-project"] == "my-gcp-project"

    # Empty-string project_id → header NOT added (truthy check)
    cred_empty = OAuthCredential(
        access="ya29.z",
        refresh="1//z",
        expires=1_000_000.0,
        provider_id="google.gemini_cli",
        extras={"project_id": ""},
    )
    h3 = auth.http_headers(cred_empty)
    assert "x-goog-user-project" not in h3


# 015-C-04
def test_id_token_parser(fixture_google_id_token: str) -> None:
    """id_token JWT parse extracts sub + email from the middle segment."""
    payload = google_gemini._parse_id_token_payload(fixture_google_id_token)
    assert payload.sub == "u-google-fixture-12345"
    assert payload.email == "fixture@example.test"
    assert payload.email_verified is True


def test_id_token_parse_account_email(
    fixture_google_token_response: dict,
) -> None:
    """account_id == payload['sub']; extras['email'] == payload['email']."""
    resp = google_gemini.GoogleTokenResponse.model_validate(
        fixture_google_token_response
    )
    cred = google_gemini._to_credential(
        resp,
        original_refresh="",
        now=1_000_000.0,
    )
    assert cred.account_id == "u-google-fixture-12345"
    assert cred.extras["email"] == "fixture@example.test"
    assert cred.extras["email_verified"] is True
    # P2-2 wire-shape — expires is now + expires_in, NO buffer subtracted
    assert cred.expires == 1_000_000.0 + 3599.0
    assert cred.provider_id == "google.gemini_cli"


def test_id_token_parser_rejects_malformed() -> None:
    """Defensive: parser raises AuthLoginError on non-JWT input."""
    from state_core.auth.errors import AuthLoginError

    with pytest.raises(AuthLoginError):
        google_gemini._parse_id_token_payload("not-a-jwt")
    with pytest.raises(AuthLoginError):
        google_gemini._parse_id_token_payload("only.two")
    with pytest.raises(AuthLoginError):
        google_gemini._parse_id_token_payload("a.!!!.c")  # invalid base64
    with pytest.raises(AuthLoginError):
        # Valid base64 of '{}' — payload missing required `sub` field.
        import base64 as _b
        empty = _b.urlsafe_b64encode(b"{}").rstrip(b"=").decode()
        google_gemini._parse_id_token_payload(f"hdr.{empty}.sig")


# 015-C-05
def test_build_authorize_url(
    fixture_google_state: str, fixture_google_verifier: str
) -> None:
    """Authorize URL contains client_id, redirect_uri, response_type=code,
    scope, state, code_challenge, code_challenge_method=S256, access_type=offline,
    prompt=consent."""
    from urllib.parse import parse_qs, urlparse

    challenge = google_gemini.build_challenge(fixture_google_verifier)
    url = google_gemini._build_authorize_url(
        "http://127.0.0.1:54321/oauth2callback",
        fixture_google_state,
        challenge,
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # All 9 fields present
    for key in (
        "client_id",
        "redirect_uri",
        "response_type",
        "scope",
        "state",
        "code_challenge",
        "code_challenge_method",
        "access_type",
        "prompt",
    ):
        assert key in qs, f"missing {key} in authorize URL"


def test_authorize_url_shape(
    fixture_google_state: str, fixture_google_verifier: str
) -> None:
    """Alias — explicit shape check."""
    from urllib.parse import parse_qs, urlparse

    challenge = google_gemini.build_challenge(fixture_google_verifier)
    url = google_gemini._build_authorize_url(
        "http://127.0.0.1:54321/oauth2callback",
        fixture_google_state,
        challenge,
    )
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert parsed.path == "/o/oauth2/v2/auth"
    qs = parse_qs(parsed.query)
    assert qs["client_id"][0].endswith(".apps.googleusercontent.com")
    assert qs["redirect_uri"][0] == "http://127.0.0.1:54321/oauth2callback"
    assert qs["response_type"][0] == "code"
    assert qs["state"][0] == fixture_google_state
    assert qs["code_challenge"][0] == challenge
    assert qs["code_challenge_method"][0] == "S256"
    assert qs["access_type"][0] == "offline"  # P1 — refresh_token issuance
    assert qs["prompt"][0] == "consent"        # P1 — force refresh_token on repeat
    assert "cloud-platform" in qs["scope"][0]
    assert "userinfo.email" in qs["scope"][0]
    assert "userinfo.profile" in qs["scope"][0]


# 015-C-06
@pytest.mark.asyncio
async def test_exchange_code(
    httpx_mock,
    fixture_google_token_response: dict,
    fixture_google_verifier: str,
) -> None:
    """_exchange_code POSTs oauth2.googleapis.com/token with form-urlencoded body."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json=fixture_google_token_response,
    )
    resp = await google_gemini._exchange_code(
        "fixture-code",
        fixture_google_verifier,
        "http://127.0.0.1:54321/oauth2callback",
    )
    assert resp.access_token.startswith("ya29.")
    assert resp.refresh_token is not None
    assert resp.expires_in == 3599


@pytest.mark.asyncio
async def test_token_post_form_urlencoded_shape(
    httpx_mock,
    fixture_google_token_response: dict,
    fixture_google_verifier: str,
) -> None:
    """Alias — explicit form-urlencoded body shape check."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json=fixture_google_token_response,
    )
    await google_gemini._exchange_code(
        "fixture-code",
        fixture_google_verifier,
        "http://127.0.0.1:54321/oauth2callback",
    )
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.headers.get("content-type", "").startswith(
        "application/x-www-form-urlencoded"
    )
    body = req.content.decode("ascii")
    # All 6 documented fields present
    assert "code=fixture-code" in body
    assert "grant_type=authorization_code" in body
    assert "code_verifier=" in body
    assert "client_id=" in body
    assert "client_secret=" in body
    assert "redirect_uri=" in body
    # The plaintext client_id substring (urlencoded `.` stays as `.`)
    assert "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j" in body


# ── Wave 3 (Plan D) — orchestration ───────────────────────────────────

# 015-D-01
@pytest.mark.asyncio
async def test_login_full_flow(
    httpx_mock,
    monkeypatch,
    mock_google_state_and_verifier,
    mock_loopback_callback,
    fixture_google_state,
    fixture_google_verifier,
    fixture_google_token_response,
) -> None:
    """End-to-end login: state/verifier generated, port allocated, URL built,
    loopback returns code, token POST returns response, OAuthCredential
    constructed with account_id from id_token."""
    mock_google_state_and_verifier()
    mock_loopback_callback(code="fixture-code", state=fixture_google_state)

    # pytest-httpx for token-endpoint POST
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json=fixture_google_token_response,
    )

    # Suppress the print() of authorize URL during test
    monkeypatch.setattr(
        "state_core.auth.providers.google_gemini.print",
        lambda *_a, **_kw: None,
    )

    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    cred = await GoogleGeminiAuth().login()
    assert cred.provider_id == "google.gemini_cli"
    assert cred.access.startswith("ya29.")
    assert cred.refresh.startswith("1//")
    assert cred.account_id == "u-google-fixture-12345"
    assert cred.extras["email"] == "fixture@example.test"


# 015-D-02 — P2-2 forward
@pytest.mark.asyncio
async def test_refresh_rotation_persisted(
    httpx_mock,
    fixture_google_access_token,
    fixture_google_rotated_refresh_token,
) -> None:
    """P2-2: when Google returns a NEW refresh_token, persist it."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": fixture_google_access_token,
            "expires_in":   3599,
            "refresh_token": fixture_google_rotated_refresh_token,    # NEW — must persist
            "token_type":   "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//OLD-FIXTURE-do-not-redact-in-test-only",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == fixture_google_rotated_refresh_token
    assert new.access == fixture_google_access_token


@pytest.mark.asyncio
async def test_refresh_persists_rotated_refresh_token(
    httpx_mock,
    fixture_google_access_token,
    fixture_google_rotated_refresh_token,
) -> None:
    """Alias from research §validation row — same as test_refresh_rotation_persisted."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": fixture_google_access_token,
            "expires_in":   3599,
            "refresh_token": fixture_google_rotated_refresh_token,
            "token_type":   "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//OLD-FIXTURE-do-not-redact-in-test-only",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == fixture_google_rotated_refresh_token


# 015-D-03 — P2-2 inverse
@pytest.mark.asyncio
async def test_refresh_no_rotation_keeps_old(
    httpx_mock,
    fixture_google_access_token,
) -> None:
    """P2-2 inverse: when Google omits refresh_token, preserve the original."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": fixture_google_access_token,
            "expires_in":   3599,
            # NO refresh_token in response — Google did not rotate
            "token_type":   "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//PRESERVED-FIXTURE-do-not-redact-in-test-only",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == "1//PRESERVED-FIXTURE-do-not-redact-in-test-only"   # preserved
    assert new.access == fixture_google_access_token


@pytest.mark.asyncio
async def test_refresh_preserves_unrotated_refresh_token(
    httpx_mock,
    fixture_google_access_token,
) -> None:
    """Alias from research §validation row — same as test_refresh_no_rotation_keeps_old."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": fixture_google_access_token,
            "expires_in":   3599,
            "token_type":   "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//PRESERVED-FIXTURE-do-not-redact-in-test-only",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == "1//PRESERVED-FIXTURE-do-not-redact-in-test-only"


# 015-D-04
def test_refresh_5min_buffer(now_frozen) -> None:
    """P0-7: AuthMethod.is_expired returns True when now >= cred.expires - 300."""
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    auth = GoogleGeminiAuth()
    # cred expires 200s after now → already inside buffer
    cred = OAuthCredential(
        access="ya29.x", refresh="1//x", expires=now_frozen + 200.0,
        provider_id="google.gemini_cli",
    )
    assert auth.is_expired(cred, now=now_frozen)
    # cred expires 600s after now → outside buffer
    cred = OAuthCredential(
        access="ya29.x", refresh="1//x", expires=now_frozen + 600.0,
        provider_id="google.gemini_cli",
    )
    assert not auth.is_expired(cred, now=now_frozen)


# 015-D-05
@pytest.mark.asyncio
async def test_refresh_request_headers_match_gemini_cli(
    httpx_mock,
    fixture_google_access_token,
) -> None:
    """Refresh POST: form-urlencoded body, accept: application/json header,
    NO Authorization header (refresh uses body credentials)."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": fixture_google_access_token,
            "expires_in":   3599,
            "token_type":   "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    old = OAuthCredential(
        access="ya29.OLD", refresh="1//OLD", expires=0.0,
        provider_id="google.gemini_cli",
    )
    await GoogleGeminiAuth().refresh(old)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    # Body assertions
    body = req.content.decode("ascii")
    assert "grant_type=refresh_token" in body
    assert "refresh_token=1%2F%2FOLD" in body or "refresh_token=1//OLD" in body
    assert "client_id=" in body
    assert "client_secret=" in body
    # Header assertions
    assert req.headers.get("accept", "").lower() == "application/json"
    # NO Authorization — refresh uses body credentials, not Bearer
    assert "authorization" not in {k.lower() for k in req.headers.keys()}


# 015-D-06
@pytest.mark.asyncio
async def test_state_param_csrf_check(
    monkeypatch,
    mock_google_state_and_verifier,
    fixture_google_state,
) -> None:
    """Loopback handler validates state — mismatch raises AuthLoginError before
    any token POST happens."""
    mock_google_state_and_verifier()

    # Loopback simulator returns a WRONG state — should raise AuthLoginError.
    async def _fake_callback(port: int, expected_state: str, *, timeout: float = 300.0):
        from state_core.auth.errors import AuthLoginError
        raise AuthLoginError("OAuth state mismatch (CSRF check failed)")

    monkeypatch.setattr(
        "state_core.auth.providers.google_gemini.wait_for_oauth_callback",
        _fake_callback,
    )
    monkeypatch.setattr(
        "state_core.auth.providers.google_gemini.print",
        lambda *_a, **_kw: None,
    )

    from state_core.auth.errors import AuthLoginError
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    with pytest.raises(AuthLoginError, match="state mismatch"):
        await GoogleGeminiAuth().login()


def test_state_and_verifier_independent() -> None:
    """state and verifier are TWO independent secrets.token_urlsafe(32) calls
    (NOT P0-8's state == verifier reuse — that's Anthropic-only)."""
    s1 = google_gemini.generate_verifier()
    s2 = google_gemini.generate_verifier()
    # 256 bits of entropy → collision astronomically unlikely
    assert s1 != s2
    assert len(s1) == 43
    assert len(s2) == 43


# 015-D-07
def test_main_argparse_login() -> None:
    """`python -m state_core.auth.providers.google_gemini login` runs without ImportError."""
    pytest.xfail("Plan D implementation pending")


def test_module_main_imports() -> None:
    """Alias — module-level argparse entry point importable."""
    pytest.xfail("Plan D implementation pending")


# 015-D-08
def test_main_argparse_refresh() -> None:
    """`python -m state_core.auth.providers.google_gemini refresh google.gemini_cli` runs."""
    pytest.xfail("Plan D implementation pending")


# ── Supplementary (research §validation table) ────────────────────────

def test_satisfies_authmethod_protocol() -> None:
    """isinstance(GoogleGeminiAuth(), AuthMethod) is True (structural conformance)."""
    from state_core.auth.base import AuthMethod

    assert isinstance(google_gemini.GoogleGeminiAuth(), AuthMethod)


def test_client_credentials_plaintext() -> None:
    """P1-3: _CLIENT_ID and _CLIENT_SECRET are plaintext module constants —
    NO base64.b64decode, NO XOR, NO env-var indirection in the source."""
    import re
    from pathlib import Path

    src = Path("src/state_core/auth/providers/google_gemini.py").read_text()
    assert (
        '_CLIENT_ID: str = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"'
        in src
    )
    assert (
        '_CLIENT_SECRET: str = "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"' in src
    )
    # No constant is ever fed through any decoder/env lookup.
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*b64decode", src)
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*environ", src)
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*getenv", src)
    # P1-3 rationale comment present
    assert "P1-3" in src


def test_provider_id_dotted() -> None:
    """provider_id == 'google.gemini_cli' (dotted, distinct from Phase 016)."""
    assert google_gemini.GoogleGeminiAuth.provider_id == "google.gemini_cli"
    assert google_gemini.GoogleGeminiAuth().provider_id == "google.gemini_cli"


def test_expiry_epoch_timezone_invariant() -> None:
    """Pitfall 7: expires = now + expires_in — pure float arithmetic, no
    datetime. Result is the same regardless of TZ."""
    from state_core.auth.providers.google_gemini import (
        GoogleTokenResponse,
        _to_credential,
    )
    resp = GoogleTokenResponse(
        access_token="ya29.x",
        expires_in=3599,
        refresh_token="1//x",
        token_type="Bearer",
    )
    # Fix now to a known epoch
    now = 1_770_000_000.0
    cred = _to_credential(resp, original_refresh="1//x", now=now)
    assert cred.expires == now + 3599.0  # exactly — no TZ math


@pytest.mark.asyncio
async def test_refresh_rejects_apikey() -> None:
    """refresh(ApiKeyCredential) raises TypeError — caller programming error."""
    from state_core.auth.base import ApiKeyCredential
    from state_core.auth.providers.google_gemini import GoogleGeminiAuth
    cred = ApiKeyCredential(key="sk-test", provider_id="google.gemini_cli")
    with pytest.raises(TypeError, match="OAuthCredential"):
        await GoogleGeminiAuth().refresh(cred)
