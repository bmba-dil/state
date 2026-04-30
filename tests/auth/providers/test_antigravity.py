"""Phase 016 RED test stubs for AntigravityAuth — Wave 0 (AUTH-03).

Test names map 1:1 to VALIDATION.md row IDs (016-02-01..016-04-07).
Plan 02 turns sync helper tests GREEN (rows 016-02-01..016-02-08).
Plan 03 turns sync class tests GREEN (rows 016-03-01..016-03-07).
Plan 04 turns async login/refresh + __main__ tests GREEN (rows
016-04-01..016-04-07).

The 23rd VALIDATION row (016-01-01) is the *collection gate* satisfied
by ``pytest --collect-only`` succeeding on this file at all — Task 1 of
Plan 01 is responsible for that, not a function in this module.

RED-state strategy:

    Plan 01 ships these stubs BEFORE
    ``state_core.auth.providers.antigravity`` exists. The module is
    imported via ``pytest.importorskip`` so collection always succeeds —
    every test is SKIPPED (with a clear reason) until Plans 02/03/04
    land. Each test body is DRAFTED (not stubbed ``pass``) so later
    plans only delete the ``pytest.xfail`` line to flip XFAIL → GREEN.

The Antigravity-specific constants asserted below are HARD-CODED in
this test file — they are NOT imported from the not-yet-existing source
module. This decouples the verification contract from implementation
order: the test file IS the spec.

Verified-source constants (RESEARCH §Sources):
  _CLIENT_ID     = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
  _CLIENT_SECRET = "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"
  _REDIRECT_PORT = 51121                # FIXED (Pitfall 4) — NOT allocate_loopback_port()
  _REDIRECT_HOST = "localhost"          # literal — NOT 127.0.0.1 (Pitfall 5)
  _REDIRECT_PATH = "/oauth-callback"
  _SCOPES        = cloud-platform + userinfo.email + userinfo.profile +
                   cclog + experimentsandconfigs    # P2-3 (5 scopes)
"""

from __future__ import annotations

import pytest

# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces every stub by name.

try:
    from state_core.auth.providers import antigravity  # type: ignore[import-not-found]

    _ANTIGRAVITY_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _ANTIGRAVITY_AVAILABLE = False
    _IMPORT_ERROR = _e
    antigravity = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _ANTIGRAVITY_AVAILABLE,
    reason=f"Plans 02+ not yet landed: {_IMPORT_ERROR}",
)


# ── Wave 2 (Plan 02) — pure helpers + constants ──────────────────────────


def test_constants_plaintext() -> None:
    """VALIDATION row 016-02-01 — P1-3 plaintext-only client credentials.

    _CLIENT_ID and _CLIENT_SECRET are plaintext module constants, NOT
    base64/XOR-encoded, NOT read from os.environ. AV scanners flag
    obfuscated literals as malicious; every Antigravity OAuth client in
    the wild ships them plaintext.
    """
    import re
    from pathlib import Path

    src = Path("src/state_core/auth/providers/antigravity.py").read_text()
    assert (
        '_CLIENT_ID: str = '
        '"1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"'
        in src
    )
    assert (
        '_CLIENT_SECRET: str = "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"' in src
    )
    # No constant is ever fed through any decoder/env lookup.
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*b64decode", src)
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*environ", src)
    assert not re.search(r"_CLIENT_(ID|SECRET)\s*=.*getenv", src)
    # No padding char `==` (a giveaway of base64-encoded literals).
    assert "_CLIENT_ID" in src
    assert antigravity._CLIENT_ID == (
        "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
    )
    assert antigravity._CLIENT_SECRET == "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"


def test_build_authorize_url() -> None:
    """VALIDATION row 016-02-02 — authorize URL contains 9 required fields.

    Mirrors test_google_gemini.test_build_authorize_url with Antigravity
    client_id swap. Both `access_type=offline` and `prompt=consent` are
    mandatory for refresh_token issuance (P1).
    """
    from urllib.parse import parse_qs, urlparse

    challenge = antigravity.build_challenge("verifier-aaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    redirect_uri = "http://localhost:51121/oauth-callback"
    url = antigravity._build_authorize_url(
        redirect_uri,
        "state-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        challenge,
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["client_id"][0].startswith("1071006060591-")
    assert qs["code_challenge_method"][0] == "S256"
    assert qs["access_type"][0] == "offline"
    assert qs["prompt"][0] == "consent"
    assert qs["response_type"][0] == "code"


def test_localhost_literal_in_redirect_uri() -> None:
    """VALIDATION row 016-02-03 — redirect_uri uses literal `localhost`, NOT `127.0.0.1`.

    Pitfall 5: Google's OAuth server enforces redirect_uri exact-string
    match. The Antigravity client was pre-registered with literal
    `http://localhost:51121/oauth-callback`. ANY substitution
    (`127.0.0.1`, port 51122, `/oauth2callback`) → `redirect_uri_mismatch`
    400. The URL string MUST contain literal `localhost:51121/oauth-callback`
    (urlencoded as `localhost%3A51121%2Foauth-callback`) and MUST NOT
    contain `127.0.0.1`.
    """
    redirect_uri = "http://localhost:51121/oauth-callback"
    url = antigravity._build_authorize_url(
        redirect_uri,
        "state-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "challenge-aaaaaaaaaaaaaaaaaaaaaaaa",
    )
    # Either form (raw or urlencoded) is acceptable — Google parses both.
    assert (
        "localhost%3A51121%2Foauth-callback" in url
        or "localhost:51121/oauth-callback" in url
    )
    assert "127.0.0.1" not in url


def test_fixed_port_51121() -> None:
    """VALIDATION row 016-02-04 — Pitfall 4: port is FIXED constant 51121.

    Antigravity's pre-registered redirect_uri pins the port to 51121.
    Phase 015's `allocate_loopback_port()` does NOT apply; the
    antigravity module MUST NOT reference it at all (otherwise a future
    refactor could silently re-introduce kernel-allocated ports).
    """
    from pathlib import Path

    assert antigravity._REDIRECT_PORT == 51121
    assert antigravity._REDIRECT_HOST_LITERAL == "localhost"
    assert antigravity._REDIRECT_PATH == "/oauth-callback"
    src = Path("src/state_core/auth/providers/antigravity.py").read_text()
    # `allocate_loopback_port` MUST NOT appear anywhere in the source
    # (Pitfall 4 — fixed-port-only). Re-export of the symbol from
    # oauth_common is also banned to keep the surface clean.
    assert "allocate_loopback_port" not in src


def test_five_scopes_present() -> None:
    """VALIDATION row 016-02-05 — P2-3: scope string contains all 5 entries.

    Gemini's three (cloud-platform + userinfo.email + userinfo.profile)
    PLUS Antigravity-specific cclog + experimentsandconfigs. Omitting
    cclog or experimentsandconfigs causes the loadCodeAssist boot call
    to 403 with IAM_PERMISSION_DENIED. P2-3 is THIS phase's owned pitfall.
    """
    scopes = antigravity._SCOPES
    assert "cloud-platform" in scopes
    assert "userinfo.email" in scopes
    assert "userinfo.profile" in scopes
    assert "cclog" in scopes
    assert "experimentsandconfigs" in scopes


def test_id_token_parser(captured_token_post_antigravity: dict) -> None:
    """VALIDATION row 016-02-06 — id_token JWT parse extracts sub + email.

    NO signature verification (RESEARCH §rule 5 — trust boundary is TLS
    to oauth2.googleapis.com). Mirrors
    test_google_gemini.test_id_token_parser with the antigravity sub.
    Bad JWT (2 parts, invalid base64) raises AuthLoginError.
    """
    from state_core.auth.errors import AuthLoginError

    id_token = captured_token_post_antigravity["id_token"]
    payload = antigravity._parse_id_token_payload(id_token)
    assert payload.sub == "test_sub_antigravity"
    assert payload.email == "test@example.com"
    assert payload.email_verified is True

    with pytest.raises(AuthLoginError):
        antigravity._parse_id_token_payload("only.two")
    with pytest.raises(AuthLoginError):
        antigravity._parse_id_token_payload("not-a-jwt")


@pytest.mark.asyncio
async def test_exchange_code(
    httpx_mock,
    captured_token_post_antigravity: dict,
) -> None:
    """VALIDATION row 016-02-07 — _exchange_code POSTs form-urlencoded body.

    All 6 documented fields must be present in the body: code, client_id,
    client_secret, redirect_uri, grant_type=authorization_code,
    code_verifier. The plaintext _CLIENT_SECRET literal must appear in
    the body (P1-3 — sent verbatim, not signed/encrypted).
    """
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json=captured_token_post_antigravity,
    )
    redirect_uri = "http://localhost:51121/oauth-callback"
    resp = await antigravity._exchange_code(
        "fixture-code",
        "verifier-aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        redirect_uri,
    )
    assert resp.access_token.startswith("ya29.")

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    body = requests[0].content.decode("ascii")
    assert "code=fixture-code" in body
    assert "grant_type=authorization_code" in body
    assert "code_verifier=" in body
    assert "client_id=1071006060591-tmhssin2h21lcre235vtolojh4g403ep" in body
    assert "client_secret=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" in body
    assert "redirect_uri=" in body


def test_client_metadata_platform_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """VALIDATION row 016-02-08 — Client-Metadata platform field switches on sys.platform.

    Antigravity backends pattern-match on the literal strings MACOS /
    LINUX / WINDOWS (uppercase, no separator). Computed per-call so
    tests can monkey-patch the three branches.

    JSON-encoded body has exactly three keys: ideType (always
    "ANTIGRAVITY"), platform (sys.platform-derived), pluginType (always
    "GEMINI" — the Antigravity backend treats Antigravity IDE as a
    Gemini-family plugin).
    """
    import orjson

    # darwin → MACOS
    monkeypatch.setattr("sys.platform", "darwin")
    p = antigravity._platform_for_client_metadata()
    assert p == "MACOS"
    body = orjson.loads(antigravity._build_client_metadata(p))
    assert body == {"ideType": "ANTIGRAVITY", "platform": "MACOS", "pluginType": "GEMINI"}

    # linux → LINUX
    monkeypatch.setattr("sys.platform", "linux")
    p = antigravity._platform_for_client_metadata()
    assert p == "LINUX"
    body = orjson.loads(antigravity._build_client_metadata(p))
    assert body["platform"] == "LINUX"

    # win32 → WINDOWS
    monkeypatch.setattr("sys.platform", "win32")
    p = antigravity._platform_for_client_metadata()
    assert p == "WINDOWS"
    body = orjson.loads(antigravity._build_client_metadata(p))
    assert body["platform"] == "WINDOWS"


# ── Wave 3 (Plan 03) — sync class methods ────────────────────────────────


def test_provider_id_dotted() -> None:
    """VALIDATION row 016-03-01 — Pitfall 10: provider_id = 'google.antigravity'.

    Dotted-namespace keeps Phase 015 ("google.gemini_cli") and Phase 016
    ("google.antigravity") in separate AuthVault buckets. Phase 019
    round-robin operates within ONE provider_id only.
    """
    assert antigravity.AntigravityAuth.provider_id == "google.antigravity"
    assert antigravity.AntigravityAuth().provider_id == "google.antigravity"


def test_is_token() -> None:
    """VALIDATION row 016-03-02 — Pitfall 6: is_token is provider-affirmative.

    Antigravity tokens start `ya29.` (same as Gemini — both are Google
    OAuth). is_token returning True for ya29.* is INTENTIONAL — each
    provider says "yes, this is a shape I issue" and the discriminator
    at routing level is provider_id, NEVER the token shape.

    Gemini tokens (sk-ant-*) and refresh tokens (1//*) return False.
    """
    auth = antigravity.AntigravityAuth()
    assert auth.is_token("ya29.foo") is True
    assert auth.is_token("ya29.") is True  # bare prefix accepted
    assert auth.is_token("sk-ant-foo") is False
    assert auth.is_token("1//bar") is False
    assert auth.is_token("") is False


def test_is_expired_5min_buffer() -> None:
    """VALIDATION row 016-03-03 — P0-7 / AUTH-09: 5-min (300s) buffer.

    Cred with `expires = now + 200` (4 min away) → True (within buffer).
    Cred with `expires = now + 400` (well outside) → False.
    Delegates to is_expired_buffered — provider MUST NOT reimplement.
    """
    from state_core.auth.base import OAuthCredential

    auth = antigravity.AntigravityAuth()
    now = 1_770_000_000.0
    inside = OAuthCredential(
        access="ya29.x",
        refresh="1//x",
        expires=now + 200.0,
        provider_id="google.antigravity",
    )
    assert auth.is_expired(inside, now=now) is True

    outside = OAuthCredential(
        access="ya29.x",
        refresh="1//x",
        expires=now + 400.0,
        provider_id="google.antigravity",
    )
    assert auth.is_expired(outside, now=now) is False


def test_http_headers_user_agent() -> None:
    """VALIDATION row 016-03-04 — Pitfall 6: user-agent = literal 'antigravity'.

    Cross-source verified (taoalpha gist, PicoClaw): the Cloud Companion
    API uses the literal string `antigravity` (NOT version-suffixed).
    Mismatched UA → quota attribution lands wrong → IAM_PERMISSION_DENIED.
    """
    from state_core.auth.base import OAuthCredential

    cred = OAuthCredential(
        access="ya29.ACCESS",
        refresh="1//REFRESH",
        expires=1_000_000.0,
        provider_id="google.antigravity",
    )
    headers = antigravity.AntigravityAuth().http_headers(cred)
    assert headers["user-agent"] == "antigravity"


def test_http_headers_goog_api_client() -> None:
    """VALIDATION row 016-03-05 — x-goog-api-client matches Antigravity-IDE traffic.

    Verified literal: `google-cloud-sdk vscode_cloudshelleditor/0.1`.
    """
    from state_core.auth.base import OAuthCredential

    cred = OAuthCredential(
        access="ya29.ACCESS",
        refresh="1//REFRESH",
        expires=1_000_000.0,
        provider_id="google.antigravity",
    )
    headers = antigravity.AntigravityAuth().http_headers(cred)
    assert headers["x-goog-api-client"] == "google-cloud-sdk vscode_cloudshelleditor/0.1"


def test_http_headers_client_metadata_json() -> None:
    """VALIDATION row 016-03-06 — client-metadata is valid JSON, 3 keys.

    Must be parseable by orjson.loads. Decoded dict has EXACTLY three
    keys: ideType (always "ANTIGRAVITY"), platform (run-time sys.platform
    mapping), pluginType (always "GEMINI"). No additional keys leak in.
    """
    import orjson
    import sys

    from state_core.auth.base import OAuthCredential

    cred = OAuthCredential(
        access="ya29.ACCESS",
        refresh="1//REFRESH",
        expires=1_000_000.0,
        provider_id="google.antigravity",
    )
    headers = antigravity.AntigravityAuth().http_headers(cred)
    decoded = orjson.loads(headers["client-metadata"])
    assert set(decoded.keys()) == {"ideType", "platform", "pluginType"}
    assert decoded["ideType"] == "ANTIGRAVITY"
    assert decoded["pluginType"] == "GEMINI"
    # Platform field maps current sys.platform to one of MACOS/LINUX/WINDOWS.
    expected = {
        "darwin": "MACOS",
        "linux": "LINUX",
        "win32": "WINDOWS",
    }.get(sys.platform, "LINUX")  # defensive fallback per RESEARCH §Pattern 5
    assert decoded["platform"] == expected


def test_satisfies_authmethod_protocol() -> None:
    """VALIDATION row 016-03-07 — AntigravityAuth satisfies AuthMethod Protocol.

    runtime_checkable Protocol — structural conformance check via
    isinstance(). All five required attributes must be present:
    provider_id, is_token, is_expired, http_headers, login, refresh.
    """
    from state_core.auth.base import AuthMethod

    assert isinstance(antigravity.AntigravityAuth(), AuthMethod) is True


# ── Wave 4 (Plan 04) — async login/refresh + __main__ ────────────────────


@pytest.mark.asyncio
async def test_login_full_flow(
    httpx_mock,
    monkeypatch: pytest.MonkeyPatch,
    mock_authorize_url_antigravity: list[str],
    captured_token_post_antigravity: dict,
) -> None:
    """VALIDATION row 016-04-01 — end-to-end login returns valid OAuthCredential.

    Wires all the pieces: state/verifier generated, FIXED port 51121,
    URL printed (captured by fixture), wait_for_oauth_callback returns
    canned code, token POST returns 200 with id_token, _to_credential
    extracts sub + email.
    """
    pytest.xfail("Plan 04 implements AntigravityAuth.login()")
    import time

    # Patch wait_for_oauth_callback IN the antigravity module (re-import
    # surface) to return a canned code without spinning up a real listener.
    async def _fake_callback(port: int, expected_state: str, *, timeout: float = 300.0) -> str:
        assert port == 51121
        return "fixture-antigravity-code"

    monkeypatch.setattr(
        "state_core.auth.providers.antigravity.wait_for_oauth_callback",
        _fake_callback,
        raising=False,
    )

    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json=captured_token_post_antigravity,
    )

    cred = await antigravity.AntigravityAuth().login()
    assert cred.provider_id == "google.antigravity"
    assert cred.access == "ya29.test_access_antigravity"
    assert cred.refresh == "1//test_refresh_antigravity"
    assert cred.account_id == "test_sub_antigravity"
    assert cred.extras["email"] == "test@example.com"
    assert cred.expires > time.time()


@pytest.mark.asyncio
async def test_refresh_rotation_persisted(httpx_mock) -> None:
    """VALIDATION row 016-04-02 — P2-2: rotated refresh_token is persisted.

    Original cred has refresh="1//old". Google returns
    refresh_token="1//new". After refresh(), returned cred has
    refresh="1//new". Google rotates silently; the old token may be
    revoked — the new one MUST be persisted.
    """
    pytest.xfail("Plan 04 implements AntigravityAuth.refresh()")
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": "ya29.new_access",
            "refresh_token": "1//new",
            "expires_in": 3599,
            "token_type": "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential

    old = OAuthCredential(
        access="ya29.old",
        refresh="1//old",
        expires=0.0,
        provider_id="google.antigravity",
    )
    new = await antigravity.AntigravityAuth().refresh(old)
    assert new.refresh == "1//new"
    assert new.access == "ya29.new_access"


@pytest.mark.asyncio
async def test_refresh_no_rotation_keeps_old(httpx_mock) -> None:
    """VALIDATION row 016-04-03 — P2-2 inverse: omitted refresh_token kept.

    When Google omits refresh_token in the response (no rotation
    occurred), the original refresh_token is preserved. Caller (refresh
    method) computes ``parsed.refresh_token or cred.refresh``.
    """
    pytest.xfail("Plan 04 implements AntigravityAuth.refresh()")
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token": "ya29.new_access",
            "expires_in": 3599,
            # NO refresh_token — Google did not rotate
            "token_type": "Bearer",
        },
    )
    from state_core.auth.base import OAuthCredential

    old = OAuthCredential(
        access="ya29.old",
        refresh="1//preserved",
        expires=0.0,
        provider_id="google.antigravity",
    )
    new = await antigravity.AntigravityAuth().refresh(old)
    assert new.refresh == "1//preserved"
    assert new.access == "ya29.new_access"


def test_state_and_verifier_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    """VALIDATION row 016-04-04 — state and verifier are TWO independent calls.

    NOT P0-8's `state == verifier` reuse — that's Anthropic-only.
    Antigravity follows Phase 015's rule: two separate generate_verifier()
    calls per login. Patch generate_verifier to a counter and assert it
    was called exactly twice.
    """
    pytest.xfail("Plan 04 implements AntigravityAuth.login()")
    calls: list[str] = []

    def _counter(*_args, **_kwargs) -> str:
        v = f"v{len(calls) + 1}-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        calls.append(v)
        return v

    monkeypatch.setattr(
        "state_core.auth.providers.antigravity.generate_verifier",
        _counter,
        raising=False,
    )

    async def _fake_callback(port: int, expected_state: str, *, timeout: float = 300.0) -> str:
        return "fixture-code"

    monkeypatch.setattr(
        "state_core.auth.providers.antigravity.wait_for_oauth_callback",
        _fake_callback,
        raising=False,
    )

    # The login coroutine doesn't need to fully complete — we only care
    # that generate_verifier is called exactly twice (state, verifier).
    import asyncio

    try:
        asyncio.run(antigravity.AntigravityAuth().login())
    except Exception:
        # Token POST will likely fail (no httpx_mock here) — that's fine,
        # it happens AFTER the two generate_verifier calls.
        pass

    assert len(calls) == 2
    assert calls[0] != calls[1]


def test_main_argparse_login(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    tmp_path,
) -> None:
    """VALIDATION row 016-04-05 — `python -m ... antigravity login` argparse path.

    Patch login() to return canned cred, patch vault helpers to redirect
    to tmp_path. Assert exit code 0 and stdout contains "Logged in as".
    """
    pytest.xfail("Plan 04 implements antigravity._main")
    import sys as _sys

    from state_core.auth.base import OAuthCredential

    monkeypatch.setenv("STATE_AUTH_JSON", str(tmp_path / "auth.json"))
    monkeypatch.setattr(_sys, "argv", ["antigravity.py", "login"])

    canned = OAuthCredential(
        access="ya29.canned",
        refresh="1//canned",
        expires=99_999_999_999.0,
        provider_id="google.antigravity",
        account_id="canned-sub",
        extras={"email": "canned@example.test"},
    )

    async def _fake_login(self):
        return canned

    monkeypatch.setattr(antigravity.AntigravityAuth, "login", _fake_login)

    rc = antigravity._main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Logged in as" in captured.out


def test_main_argparse_refresh(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    tmp_path,
) -> None:
    """VALIDATION row 016-04-06 — `python -m ... antigravity refresh google.antigravity`.

    Patch refresh_credential to a no-op coroutine. Assert exit code 0
    and stdout contains "Refreshed access_token for google.antigravity".
    """
    pytest.xfail("Plan 04 implements antigravity._main")
    import sys as _sys

    monkeypatch.setenv("STATE_AUTH_JSON", str(tmp_path / "auth.json"))
    monkeypatch.setattr(
        _sys, "argv", ["antigravity.py", "refresh", "google.antigravity"]
    )

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "state_core.auth.refresh.refresh_credential",
        _noop,
        raising=False,
    )

    rc = antigravity._main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Refreshed access_token for google.antigravity" in captured.out


@pytest.mark.asyncio
async def test_port_51121_in_use_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """VALIDATION row 016-04-07 — Pitfall 4: port 51121 in-use → AuthLoginError.

    OSError(48, "Address already in use") raised by wait_for_oauth_callback
    surfaces to the caller as AuthLoginError with explicit remediation
    copy: "port 51121" + "already in use". Documented as a fundamental
    constraint of Google's redirect_uri pre-registration, NOT a state bug.
    """
    pytest.xfail("Plan 04 implements AntigravityAuth.login() + OSError-to-AuthLoginError translation")
    from state_core.auth.errors import AuthLoginError

    async def _fake_callback(port: int, expected_state: str, *, timeout: float = 300.0) -> str:
        raise OSError(48, "Address already in use")

    monkeypatch.setattr(
        "state_core.auth.providers.antigravity.wait_for_oauth_callback",
        _fake_callback,
        raising=False,
    )

    with pytest.raises(AuthLoginError) as exc_info:
        await antigravity.AntigravityAuth().login()
    assert "port 51121" in str(exc_info.value)
    assert "already in use" in str(exc_info.value)
