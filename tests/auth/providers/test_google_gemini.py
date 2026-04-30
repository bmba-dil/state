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
    pytest.xfail("Plan C implementation pending")
    auth = google_gemini.GoogleGeminiAuth()
    assert auth.is_token("ya29.FOOBAR")
    assert not auth.is_token("sk-ant-oat-FOOBAR")
    assert not auth.is_token("1//refresh-token-FOOBAR")
    assert not auth.is_token("")


# 015-C-02 alias — research §validation row "is_token_ya29_prefix"
def test_is_token_ya29_prefix() -> None:
    """Alias for token_shape_sniffer — explicit ya29.* prefix assertion."""
    pytest.xfail("Plan C implementation pending")


# 015-C-02
def test_is_expired() -> None:
    """is_expired delegates to is_expired_buffered (5-min buffer at AuthMethod layer)."""
    pytest.xfail("Plan C implementation pending")


def test_is_expired_uses_300s_buffer() -> None:
    """P0-7: now >= cred.expires - 300 → True."""
    pytest.xfail("Plan C implementation pending")


# 015-C-03
def test_http_headers() -> None:
    """http_headers returns Bearer + (optional) x-goog-user-project."""
    pytest.xfail("Plan C implementation pending")


def test_http_headers_bearer_and_optional_project() -> None:
    """http_headers omits x-goog-user-project unless extras['project_id'] is set."""
    pytest.xfail("Plan C implementation pending")


# 015-C-04
def test_id_token_parser() -> None:
    """id_token JWT parse extracts sub + email from the middle segment."""
    pytest.xfail("Plan C implementation pending")


def test_id_token_parse_account_email() -> None:
    """account_id == payload['sub']; extras['email'] == payload['email']."""
    pytest.xfail("Plan C implementation pending")


# 015-C-05
def test_build_authorize_url() -> None:
    """Authorize URL contains client_id, redirect_uri, response_type=code,
    scope, state, code_challenge, code_challenge_method=S256, access_type=offline,
    prompt=consent."""
    pytest.xfail("Plan C implementation pending")


def test_authorize_url_shape() -> None:
    """Alias — explicit shape check."""
    pytest.xfail("Plan C implementation pending")


# 015-C-06
def test_exchange_code() -> None:
    """_exchange_code POSTs oauth2.googleapis.com/token with form-urlencoded body."""
    pytest.xfail("Plan C implementation pending")


def test_token_post_form_urlencoded_shape() -> None:
    """Alias — explicit form-urlencoded body shape check."""
    pytest.xfail("Plan C implementation pending")


# ── Wave 3 (Plan D) — orchestration ───────────────────────────────────

# 015-D-01
def test_login_full_flow() -> None:
    """End-to-end login: builds URL → mock loopback returns code → token POST → OAuthCredential."""
    pytest.xfail("Plan D implementation pending")


# 015-D-02 — P2-2 forward
def test_refresh_rotation_persisted() -> None:
    """When Google returns a new refresh_token, persist it (creds.model_copy)."""
    pytest.xfail("Plan D implementation pending")


def test_refresh_persists_rotated_refresh_token() -> None:
    """Alias from research §validation row."""
    pytest.xfail("Plan D implementation pending")


# 015-D-03 — P2-2 inverse
def test_refresh_no_rotation_keeps_old() -> None:
    """When Google omits refresh_token, preserve original (`creds.refresh_token or original`)."""
    pytest.xfail("Plan D implementation pending")


def test_refresh_preserves_unrotated_refresh_token() -> None:
    """Alias from research §validation row."""
    pytest.xfail("Plan D implementation pending")


# 015-D-04
def test_refresh_5min_buffer() -> None:
    """Refresh respects Phase 013's is_expired_buffered (5-min buffer at AuthMethod layer)."""
    pytest.xfail("Plan D implementation pending")


# 015-D-05
def test_refresh_request_headers_match_gemini_cli() -> None:
    """Refresh POST body: form-urlencoded with grant_type=refresh_token,
    refresh_token, client_id, client_secret. Headers: accept: application/json.
    NO Authorization header (refresh uses body credentials, not Bearer)."""
    pytest.xfail("Plan D implementation pending")


# 015-D-06
def test_state_param_csrf_check() -> None:
    """Loopback handler validates state == expected_state; mismatch → AuthLoginError."""
    pytest.xfail("Plan D implementation pending")


def test_state_and_verifier_independent() -> None:
    """state and verifier are TWO independent secrets.token_urlsafe(32) calls
    (NOT P0-8's state == verifier reuse — that's Anthropic-only)."""
    pytest.xfail("Plan D implementation pending")


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
    pytest.xfail("Plan C implementation pending")


def test_client_credentials_plaintext() -> None:
    """P1-3: _CLIENT_ID and _CLIENT_SECRET are plaintext module constants —
    NO base64.b64decode, NO XOR, NO env-var indirection in the source."""
    pytest.xfail("Plan C implementation pending")


def test_provider_id_dotted() -> None:
    """provider_id == 'google.gemini_cli' (dotted, distinct from Phase 016)."""
    pytest.xfail("Plan C implementation pending")


def test_expiry_epoch_timezone_invariant() -> None:
    """Pitfall 7: creds.expiry → epoch is the same regardless of TZ."""
    pytest.xfail("Plan D implementation pending")


def test_refresh_rejects_apikey() -> None:
    """refresh(ApiKeyCredential) raises TypeError (caller programming error)."""
    pytest.xfail("Plan D implementation pending")
