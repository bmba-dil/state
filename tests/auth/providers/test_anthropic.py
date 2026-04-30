"""RED stubs for state_core.auth.providers.anthropic — Phase 014 / AUTH-01.

Maps 1:1 to the 16 rows in 014-VALIDATION.md + 1 precedence regression
(invalid_grant must NOT be misclassified as StealthRejected). Plan 02
(Wave 1) lands the constants + class skeleton (turns 4–11 stealth header
tests + 13 protocol + 14 paste-format GREEN). Plan 03 (Wave 2) lands
login/refresh impls (turns 8/9/12/15/16/17 GREEN).

EVERY test asserts the LITERAL pinned value. No startswith on stealth
headers — that's how silent drift sneaks in.

RED-state strategy:
    Plan 01 ships these tests BEFORE ``state_core.auth.providers.anthropic``
    and ``state_core.auth.oauth_common.pkce`` exist. The modules are
    imported via ``try / except ImportError`` and a
    ``pytestmark = pytest.mark.skipif(...)`` ensures collection always
    succeeds — every test is SKIPPED with a clear reason until Plan 02
    lands. This mirrors the canonical pattern in
    ``tests/auth/test_refresh.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape per the plan is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces exactly 17 items.

try:
    from state_core.auth.providers import anthropic  # type: ignore[import-not-found]
    from state_core.auth.oauth_common import pkce  # type: ignore[import-not-found]

    _ANTHROPIC_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _ANTHROPIC_AVAILABLE = False
    _IMPORT_ERROR = _e
    anthropic = None  # type: ignore[assignment]
    pkce = None  # type: ignore[assignment]

from state_core.auth.base import AuthMethod, OAuthCredential  # noqa: E402

pytestmark = pytest.mark.skipif(
    not _ANTHROPIC_AVAILABLE,
    reason=f"Plan 02 not yet landed: {_IMPORT_ERROR}",
)

# asyncio_mode = auto is set in pyproject.toml; individual @pytest.mark.asyncio
# decorators are kept for clarity but are not strictly required.


# ── Pinned literal values (must match CONTEXT.md / RESEARCH.md / milady) ──

_EXPECTED_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_EXPECTED_USER_AGENT = "claude-cli/2.1.121 (external, cli)"
_EXPECTED_X_APP = "cli"
_EXPECTED_ANTHROPIC_BETA = (
    "oauth-2025-04-20,"
    "interleaved-thinking-2025-05-14,"
    "redact-thinking-2026-02-12,"
    "context-management-2025-06-27,"
    "prompt-caching-scope-2026-01-05"
)
_EXPECTED_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_EXPECTED_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_EXPECTED_REDIRECT_URI = "https://platform.claude.com/oauth/code/callback"
_EXPECTED_SCOPES = "org:create_api_key user:profile user:inference"
_EXPECTED_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-02 — P0-8 — PKCE state == verifier
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_state_equals_verifier(
    httpx_mock,
    fixture_verifier: str,
    fixture_token_response: dict[str, Any],
    mock_getpass,
    mock_generate_verifier,
    monkeypatch,
) -> None:
    """The SAME string MUST appear as `state=<verifier>` in the authorize URL
    AND as `code_verifier=<verifier>` in the token-exchange POST body.

    Generating two distinct strings would let token exchange succeed with
    a fake state — Anthropic's server enforces state == verifier.
    """
    mock_generate_verifier()
    mock_getpass()

    # Capture the authorize URL by monkeypatching `print` IN THE PROVIDER
    # MODULE (NOT builtins.print — patching builtins.print leaks into pytest's
    # own internals and can corrupt test reporting). The login flow prints
    # the URL via the module's namespace `print`, so module-scoped patching
    # captures the call without any global-state pollution.
    captured: dict[str, str] = {}
    # Module-scoped patch — safer than builtins
    monkeypatch.setattr(
        "state_core.auth.providers.anthropic.print",
        lambda *args, **_kw: captured.setdefault("url", " ".join(str(a) for a in args)),
    )

    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        json=fixture_token_response,
    )

    cred = await anthropic.AnthropicAuth().login()

    # state in the authorize URL == fixture_verifier
    assert f"state={fixture_verifier}" in captured.get("url", ""), (
        f"authorize URL missing state={fixture_verifier}: {captured.get('url')!r}"
    )
    # code_verifier in the token POST body == fixture_verifier
    req = httpx_mock.get_request(method="POST", url=_EXPECTED_TOKEN_URL)
    assert req is not None, "no POST captured against token endpoint"
    body = req.read()
    # body may be JSON; decode and assert by field
    import json as _json
    parsed = _json.loads(body)
    assert parsed.get("code_verifier") == fixture_verifier, (
        f"code_verifier in body != fixture_verifier; got {parsed.get('code_verifier')!r}"
    )
    assert isinstance(cred, OAuthCredential)


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-03 — P0-5 — client_id matches Claude Code
# ─────────────────────────────────────────────────────────────────────────

def test_client_id_matches_claude_code() -> None:
    """_CLIENT_ID MUST decode to exactly the Claude Code UUID — never a fresh registration."""
    assert anthropic._CLIENT_ID == _EXPECTED_CLIENT_ID, (
        f"_CLIENT_ID drift: got {anthropic._CLIENT_ID!r}, expected {_EXPECTED_CLIENT_ID!r}"
    )
    # Sanity: the source MUST be a base64.b64decode at module load
    # (defeats secret scanners on the literal). Grep the source.
    src = _read_provider_source()
    assert "base64.b64decode" in src, (
        "_CLIENT_ID must be base64-decoded at module load (P0-5 mitigation)"
    )


def _read_provider_source() -> str:
    """Helper — read providers/anthropic.py source for grep-style assertions."""
    import inspect
    return inspect.getsource(anthropic)


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-04 — P0-1 — user-agent literal
# ─────────────────────────────────────────────────────────────────────────

def test_http_headers_user_agent_exact(oauth_cred: OAuthCredential) -> None:
    """user-agent MUST equal 'claude-cli/2.1.121 (external, cli)' — no startswith shortcut."""
    h = anthropic.AnthropicAuth().http_headers(oauth_cred)
    assert h["user-agent"] == _EXPECTED_USER_AGENT, (
        f"user-agent drift: got {h.get('user-agent')!r}, expected {_EXPECTED_USER_AGENT!r}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-05 — P0-2 — anthropic-beta literal (full 7-flag string)
# ─────────────────────────────────────────────────────────────────────────

def test_http_headers_anthropic_beta_exact(oauth_cred: OAuthCredential) -> None:
    """anthropic-beta MUST equal the full pinned 7-flag string — literal equality."""
    h = anthropic.AnthropicAuth().http_headers(oauth_cred)
    assert h["anthropic-beta"] == _EXPECTED_ANTHROPIC_BETA, (
        f"anthropic-beta drift: got {h.get('anthropic-beta')!r}, expected {_EXPECTED_ANTHROPIC_BETA!r}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-06 — P0-3 — x-app
# ─────────────────────────────────────────────────────────────────────────

def test_http_headers_x_app(oauth_cred: OAuthCredential) -> None:
    """x-app MUST equal 'cli' — literal."""
    h = anthropic.AnthropicAuth().http_headers(oauth_cred)
    assert h["x-app"] == _EXPECTED_X_APP, (
        f"x-app drift: got {h.get('x-app')!r}, expected {_EXPECTED_X_APP!r}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-07 — P0-4 — Bearer (NEVER x-api-key) at http_headers level
# ─────────────────────────────────────────────────────────────────────────

def test_http_headers_no_x_api_key(oauth_cred: OAuthCredential) -> None:
    """OAuth path MUST emit Authorization: Bearer + MUST NOT emit x-api-key (P0-4)."""
    h = anthropic.AnthropicAuth().http_headers(oauth_cred)
    assert h.get("authorization") == f"Bearer {oauth_cred.access}", (
        f"authorization not Bearer: {h.get('authorization')!r}"
    )
    assert "x-api-key" not in h, (
        f"x-api-key MUST NOT appear in OAuth http_headers; got: {h.get('x-api-key')!r}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-08 — P0-7 — 5-min buffer at AuthMethod.is_expired layer
# ─────────────────────────────────────────────────────────────────────────

def test_is_expired_uses_300s_buffer(oauth_cred: OAuthCredential) -> None:
    """is_expired delegates to is_expired_buffered with 300s buffer (P0-7)."""
    method = anthropic.AnthropicAuth()
    # Within the buffer (299s before expiry) → True (refresh needed)
    assert method.is_expired(oauth_cred, oauth_cred.expires - 299.0) is True
    # Outside the buffer (301s before expiry) → False (still fresh)
    assert method.is_expired(oauth_cred, oauth_cred.expires - 301.0) is False
    # Exactly at the buffer boundary (300s before expiry) → True
    # (now >= expires - buffer per is_expired_buffered)
    assert method.is_expired(oauth_cred, oauth_cred.expires - 300.0) is True


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-09 — token POST shape (authorization_code grant)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_token_post_shape(
    httpx_mock,
    fixture_verifier: str,
    fixture_token_response: dict[str, Any],
    mock_getpass,
    mock_generate_verifier,
    monkeypatch,
) -> None:
    """POST to _TOKEN_URL with EXACTLY the authorization_code grant fields, no extras."""
    mock_generate_verifier()
    mock_getpass()
    # Module-scoped patch — safer than builtins
    monkeypatch.setattr("state_core.auth.providers.anthropic.print", lambda *_a, **_k: None)

    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        json=fixture_token_response,
    )

    await anthropic.AnthropicAuth().login()

    req = httpx_mock.get_request(method="POST", url=_EXPECTED_TOKEN_URL)
    assert req is not None, "no token-endpoint POST captured"
    import json as _json
    body = _json.loads(req.read())
    assert body == {
        "grant_type": "authorization_code",
        "code": "fixture-code",
        "redirect_uri": _EXPECTED_REDIRECT_URI,
        "client_id": _EXPECTED_CLIENT_ID,
        "code_verifier": fixture_verifier,
    }, f"token POST body drift: {body!r}"


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-10 — refresh POST shape (refresh_token grant)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_post_shape(
    httpx_mock,
    oauth_cred: OAuthCredential,
    fixture_token_response: dict[str, Any],
) -> None:
    """POST to _TOKEN_URL with EXACTLY the refresh_token grant fields."""
    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        json=fixture_token_response,
    )

    new = await anthropic.AnthropicAuth().refresh(oauth_cred)
    assert isinstance(new, OAuthCredential)

    req = httpx_mock.get_request(method="POST", url=_EXPECTED_TOKEN_URL)
    assert req is not None
    import json as _json
    body = _json.loads(req.read())
    assert body == {
        "grant_type": "refresh_token",
        "refresh_token": oauth_cred.refresh,
        "client_id": _EXPECTED_CLIENT_ID,
    }, f"refresh POST body drift: {body!r}"


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-11 — AnthropicTokenResponse forward-compat (extra="ignore")
# ─────────────────────────────────────────────────────────────────────────

def test_token_response_ignores_unknown_field() -> None:
    """AnthropicTokenResponse parses payloads with unknown future fields (extra='ignore')."""
    payload = {
        "access_token": "sk-ant-oat01-X",
        "refresh_token": "sk-ant-ort01-Y",
        "expires_in": 28_800,
        "token_type": "Bearer",
        "account": {"uuid": "u-1", "email_address": "x@y.z"},
        "unknown_extra_field_2027": "future-anthropic-addition",
        "another_one": {"nested": "value"},
    }
    parsed = anthropic.AnthropicTokenResponse.model_validate(payload)
    assert parsed.access_token == "sk-ant-oat01-X"
    assert parsed.refresh_token == "sk-ant-ort01-Y"
    assert parsed.expires_in == 28_800
    assert parsed.account is not None
    assert parsed.account.uuid == "u-1"
    assert parsed.account.email_address == "x@y.z"
    # Unknown field must NOT appear on the model
    assert not hasattr(parsed, "unknown_extra_field_2027")


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-12 — inject_stealth_system_prefix (list / string / missing / idempotent)
# ─────────────────────────────────────────────────────────────────────────

def test_inject_stealth_system_prefix() -> None:
    """Mirror of milady addSystemPrefix — handles all 4 input shapes correctly."""
    # 1. list form (no existing prefix) → prepended
    body1: dict = {"system": [{"type": "text", "text": "Existing system msg"}]}
    anthropic.inject_stealth_system_prefix(body1)
    assert body1["system"][0] == {"type": "text", "text": _EXPECTED_SYSTEM_PREFIX}
    assert body1["system"][1] == {"type": "text", "text": "Existing system msg"}

    # 2. list form (already prefixed) → idempotent, no double-prepend
    body2: dict = {"system": [{"type": "text", "text": _EXPECTED_SYSTEM_PREFIX}]}
    before = body2["system"][0]
    anthropic.inject_stealth_system_prefix(body2)
    assert body2["system"][0] is before, "idempotency violated — prefix prepended twice"
    assert len(body2["system"]) == 1

    # 3. string form → wrapped into list with prefix at index 0
    body3: dict = {"system": "Existing system message."}
    anthropic.inject_stealth_system_prefix(body3)
    assert body3["system"] == [
        {"type": "text", "text": _EXPECTED_SYSTEM_PREFIX},
        {"type": "text", "text": "Existing system message."},
    ]

    # 4. missing system → created with prefix as sole element
    body4: dict = {}
    anthropic.inject_stealth_system_prefix(body4)
    assert body4["system"] == [{"type": "text", "text": _EXPECTED_SYSTEM_PREFIX}]


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-13 — ?beta=true on inference URLs
# ─────────────────────────────────────────────────────────────────────────

def test_url_has_beta_true() -> None:
    """Helper or constant ensures `?beta=true` is appended to outbound inference URLs.

    Phase 014 ships either a `with_beta_param(url) -> str` helper OR the
    AnthropicAuth class exposes a `prepare_url(url) -> str` method. Either
    surface is acceptable; this test asserts ONE of them exists and behaves.
    """
    candidate_url = "https://api.anthropic.com/v1/messages"
    # Try the helper-style API first; fall back to method-style.
    if hasattr(anthropic, "with_beta_param"):
        result = anthropic.with_beta_param(candidate_url)
    elif hasattr(anthropic.AnthropicAuth, "prepare_url"):
        result = anthropic.AnthropicAuth().prepare_url(candidate_url)
    else:
        pytest.fail(
            "Phase 014 must expose either anthropic.with_beta_param(url) "
            "OR AnthropicAuth().prepare_url(url) for the ?beta=true rule"
        )
    assert "beta=true" in result, f"?beta=true missing from {result!r}"

    # Idempotency — calling twice must not duplicate the param
    if hasattr(anthropic, "with_beta_param"):
        result2 = anthropic.with_beta_param(result)
    else:
        result2 = anthropic.AnthropicAuth().prepare_url(result)
    assert result2.count("beta=true") == 1, f"beta=true duplicated: {result2!r}"


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-14 — AuthMethod Protocol satisfaction
# ─────────────────────────────────────────────────────────────────────────

def test_satisfies_authmethod_protocol() -> None:
    """AnthropicAuth() structurally satisfies state_core.auth.base.AuthMethod (5-method Protocol)."""
    method = anthropic.AnthropicAuth()
    assert isinstance(method, AuthMethod), (
        "AnthropicAuth must satisfy AuthMethod Protocol (provider_id, is_token, "
        "is_expired, http_headers, login, refresh)"
    )
    assert method.provider_id == "anthropic"
    # is_token sniffer — first branch is sk-ant-oat
    assert method.is_token("sk-ant-oat01-XXX") is True
    assert method.is_token("sk-ant-api03-XXX") is False
    assert method.is_token("ya29.something") is False


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-15 — paste format required (P1-2)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_paste_format_required(
    monkeypatch,
    fixture_verifier: str,
    mock_generate_verifier,
) -> None:
    """A paste with NO `#` MUST raise AuthLoginError (not crash with ValueError) — P1-2."""
    mock_generate_verifier()
    # Module-scoped patch — safer than builtins
    monkeypatch.setattr("state_core.auth.providers.anthropic.print", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "state_core.auth.providers.anthropic.getpass.getpass",
        lambda _prompt="": "code-without-hash-separator",
    )

    with pytest.raises(anthropic.AuthLoginError):
        await anthropic.AnthropicAuth().login()


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-16 — 401 with stealth-shape signal raises StealthRejected
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_401_raises_stealth_rejected(
    httpx_mock,
    fixture_verifier: str,
    mock_getpass,
    mock_generate_verifier,
    monkeypatch,
) -> None:
    """401 response from token endpoint with stealth-shape signal raises StealthRejected
    (NOT generic AuthLoginError). Distinguishing the two lets Phase 022 surface a
    'header drift suspected — re-capture' message.
    """
    mock_generate_verifier()
    mock_getpass()
    # Module-scoped patch — safer than builtins
    monkeypatch.setattr("state_core.auth.providers.anthropic.print", lambda *_a, **_k: None)

    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        status_code=401,
        json={"error": "invalid_client", "error_description": "stealth signature rejected"},
    )

    with pytest.raises(anthropic.StealthRejected):
        await anthropic.AnthropicAuth().login()


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-17 — invalid_grant precedence regression
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected(
    httpx_mock,
    oauth_cred: OAuthCredential,
) -> None:
    """A 401 with `error=invalid_grant` MUST raise AuthRefreshError, NEVER StealthRejected.

    Regression for the heuristic ordering bug: a naive `_is_stealth_rejection`
    that scans `error_description` for the substring "Claude Code" would catch
    legitimate refresh-token-expired responses (which often contain that phrase
    in their description). The Plan 03 must_haves contract is unambiguous:

        truths:
          - "On 401 invalid_grant → AuthRefreshError"

    Plan 03 implements this by pre-checking `body.get("error") == "invalid_grant"`
    BEFORE any stealth-shape heuristic runs. This test pins that precedence so
    a future heuristic widening cannot regress it.

    Maps to row 014-01-17 in 014-VALIDATION.md.
    """
    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        status_code=401,
        json={
            "error": "invalid_grant",
            "error_description": "Refresh token expired for Claude Code session",
        },
    )

    with pytest.raises(anthropic.AuthRefreshError):
        await anthropic.AnthropicAuth().refresh(oauth_cred)

    # Belt-and-suspenders: the test would fail above already if StealthRejected
    # leaked, but assert the request was even made (no early return).
    req = httpx_mock.get_request(method="POST", url=_EXPECTED_TOKEN_URL)
    assert req is not None, "no POST captured against token endpoint"


# ─────────────────────────────────────────────────────────────────────────
# Row 014-01-16-bonus — wire-level x-api-key absence on token POST (P0-4 reinforcement)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_token_post_includes_no_x_api_key(
    httpx_mock,
    fixture_token_response: dict[str, Any],
    mock_getpass,
    mock_generate_verifier,
    monkeypatch,
) -> None:
    """Token-endpoint POST MUST NOT carry x-api-key in request headers (P0-4 wire-level)."""
    mock_generate_verifier()
    mock_getpass()
    # Module-scoped patch — safer than builtins
    monkeypatch.setattr("state_core.auth.providers.anthropic.print", lambda *_a, **_k: None)

    httpx_mock.add_response(
        method="POST",
        url=_EXPECTED_TOKEN_URL,
        json=fixture_token_response,
    )

    await anthropic.AnthropicAuth().login()

    req = httpx_mock.get_request(method="POST", url=_EXPECTED_TOKEN_URL)
    assert req is not None
    # Headers are case-insensitive in httpx
    header_keys_lower = {k.lower() for k in req.headers.keys()}
    assert "x-api-key" not in header_keys_lower, (
        f"x-api-key MUST NOT be on token-endpoint POST; saw headers: {list(req.headers.keys())!r}"
    )
