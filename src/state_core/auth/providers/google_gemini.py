"""Gemini CLI OAuth provider — Google Desktop-App OAuth pattern (RFC 8252).

Phase 015 (M-A2 / AUTH-02 / P1-3 + P2-2 owner). Second concrete AuthMethod
implementation (after Phase 014 Anthropic). Mirrors gemini-cli's free-tier
OAuth flow byte-for-byte to unlock Cloud-Platform-priced Gemini inference
via cloudcode-pa.googleapis.com (v3 inference routing wires the call;
this phase only owns auth).

Module layout (mirrors providers/anthropic.py):
  * Constants (URLs, scopes, plaintext client_id/secret with P1-3 rationale)
  * Pydantic models (GoogleTokenResponse, _GoogleIdTokenPayload) with
    extra="ignore" for forward-compat
  * Helpers — _parse_id_token_payload, _to_credential,
    _build_authorize_url, _exchange_code
  * GoogleGeminiAuth class — satisfies AuthMethod Protocol structurally
  * `if __name__ == "__main__"` block — Plan D

Cardinal rules (CLAUDE.md / Phase 011 / Phase 015 RESEARCH):

  1. PLAINTEXT _CLIENT_SECRET (P1-3): Google's Desktop-App OAuth pattern
     relies on PKCE + loopback redirect validation, NOT client_secret
     confidentiality. AV scanners flag obfuscated literals as malicious;
     gemini-cli ships plaintext for the same reason. NEVER base64/XOR/
     env-var.

  2. P2-2 refresh-token rotation: persist `creds.refresh_token or
     original_refresh_token` on EVERY refresh — Google rotates silently;
     the old token gets revoked. _to_credential takes original_refresh as
     a kwarg specifically to make rotation explicit.

  3. state ≠ verifier: Phase 014's `state == code_verifier` reuse (P0-8)
     is ANTHROPIC-SPECIFIC. Phase 015 MUST generate two independent
     `secrets.token_urlsafe(32)` strings — Google does not require reuse
     and reusing weakens RFC 6749 §10.12 CSRF on the loopback redirect.

  4. provider_id = "google.gemini_cli" (Pitfall 9): dotted-namespace
     keeps Phase 016's "google.antigravity" in a separate AuthVault
     bucket. Phase 019 round-robin operates within ONE provider_id only.

  5. id_token parsing without signature verification (Pitfall 8): the
     trust boundary is TLS to oauth2.googleapis.com. We extract sub +
     email from the JWT payload (stdlib base64 + orjson — zero extra
     deps). v3 inference routing can add cryptographic verification.

  6. Determinism — no time.time() / datetime.now() in pure helpers.
     `now` is a parameter on _to_credential; login() and refresh()
     read time.time() ONCE at function entry (Plan D).

  7. Mode isolation — imports limited to stdlib + httpx + pydantic +
     structlog + state_core.auth.{base, refresh, errors, oauth_common.*}.
     NO state.build.* / state.teach.* / litellm.

  8. No own filelock — Phase 013's refresh_credential wraps refresh()
     in a 10s-budgeted async lock. Acquiring a second lock here
     deadlocks (refresh.py rule 9). Provider's refresh() is pure HTTP.

  9. Per-call AsyncClient — `async with httpx.AsyncClient(...)` inside
     login() and refresh() (Plan D). NO module-level singleton.

 10. OAuth NEVER through litellm — CLAUDE.md cardinal rule. Direct
     httpx is the only path.

See .planning/milestones/v2/phases/015-gemini-cli-oauth-provider/
015-RESEARCH.md for full rationale, 9 pitfalls, downstream contracts.

Reference: `state-inputs gemini-cli oauth2.ts` (current main branch as of
2026-04-30 retrieval). Constants are PUBLIC distributed-app credentials —
not secrets in the cryptographic sense.
"""

from __future__ import annotations

import base64
import sys
import time

# Expose `print` in module namespace so Plan D tests can monkeypatch
# `state_core.auth.providers.google_gemini.print` to capture authorize-URL
# print calls without touching builtins.print globally. (Mirrors anthropic.py.)
print = print  # noqa: A001 — intentional re-bind for testability

from typing import Any
from urllib.parse import urlencode

import httpx
import orjson
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from state_core.auth.base import (
    AuthMethod,  # noqa: F401 — runtime_checkable Protocol; isinstance check in tests
    Credential,
    OAuthCredential,
)
from state_core.auth.errors import (
    AuthError,  # noqa: F401 — re-exported for symmetry with anthropic.py
    AuthLoginError,
    AuthRefreshError,
)
from state_core.auth.refresh import is_expired_buffered
from state_core.auth.oauth_common.pkce import (  # noqa: F401 — re-export for Plan D + tests
    build_challenge,
    generate_verifier,
)
from state_core.auth.oauth_common.loopback import (  # noqa: F401 — re-export for Plan D + tests
    SIGN_IN_FAILURE_URL,
    SIGN_IN_SUCCESS_URL,
    allocate_loopback_port,
    wait_for_oauth_callback,
)

log = structlog.get_logger(__name__)


# ── Identity constants ───────────────────────────────────────────────────
# From gemini-cli `packages/core/src/code_assist/oauth2.ts` (current main
# branch as of 2026-04-30 retrieval). These are PUBLIC distributed-app
# credentials — Google's Desktop-App OAuth pattern relies on PKCE +
# loopback redirect validation, not client_secret confidentiality.
#
# !! IMPORTANT — DO NOT obfuscate (P1-3) !!
# Base64-encoding, XOR-encoding, env-var indirection, or any other
# "defensive" transform on these constants is REJECTED:
#   1. AV scanners flag obfuscated literals in source as malicious;
#      corporate users' installs get quarantined.
#   2. Google's own gemini-cli ships them plaintext.
#   3. The actual security boundary is PKCE + loopback redirect
#      validation (RFC 8252) — NOT client_secret secrecy.
# See .planning/research/PITFALLS.md P1-3.

_CLIENT_ID: str = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
_CLIENT_SECRET: str = "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"

# ── URL constants ────────────────────────────────────────────────────────

_AUTHORIZE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
# Google's OAuth 2.0 v2 endpoint — https://developers.google.com/identity/protocols/oauth2/native-app

_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
# Google's token endpoint — same source

_SCOPES: str = (
    "https://www.googleapis.com/auth/cloud-platform "
    "https://www.googleapis.com/auth/userinfo.email "
    "https://www.googleapis.com/auth/userinfo.profile"
)
# Three Cloud-Platform scopes (space-separated, NOT comma) from gemini-cli
# OAUTH_SCOPE array. The cloud-platform scope is what unlocks Gemini
# free-tier via cloudcode-pa.googleapis.com (v3 inference routing).


# ── Pydantic token-response models ───────────────────────────────────────


class GoogleTokenResponse(BaseModel):
    """200-OK payload from POST https://oauth2.googleapis.com/token.

    extra="ignore" — forward-compatible with future Google fields.
    Secret-bearing fields use Field(repr=False) (Phase 011 layer 1;
    Phase 020 structlog redactor is layer 2).

    refresh_token may be ABSENT on a refresh response — Google omits it
    when no rotation occurred. Caller (Plan D refresh) resolves via
    `creds.refresh_token or original_refresh` per P2-2.

    id_token may be ABSENT if scope omits openid (we always request
    userinfo.email which implicitly grants openid, so it should be
    present — but defensively typed as Optional).
    """

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(repr=False)
    expires_in: int
    """Seconds-from-now (wire shape per OAuthCredential.expires invariant)."""

    refresh_token: str | None = Field(default=None, repr=False)
    scope: str | None = None
    token_type: str | None = None
    id_token: str | None = Field(default=None, repr=False)


class _GoogleIdTokenPayload(BaseModel):
    """Subset of OpenID Connect ID-Token claims we extract for account_id.

    NO signature verification — see module docstring rule 5. Trust
    boundary is TLS to oauth2.googleapis.com.
    """

    model_config = ConfigDict(extra="ignore")

    sub: str
    """Stable user identifier — Google's account UUID. Goes into
    OAuthCredential.account_id."""

    email: str | None = None
    """User's email at issue time. Stored in extras["email"] when present."""

    email_verified: bool | None = None
    """Whether Google has verified the email."""


# ── Helpers ──────────────────────────────────────────────────────────────


def _parse_id_token_payload(id_token: str) -> _GoogleIdTokenPayload:
    """Parse the middle segment of a Google id_token JWT — NO signature check.

    JWT format (RFC 7519): <header_b64url>.<payload_b64url>.<signature_b64url>.
    Each segment is base64url-no-pad. Python's b64decode requires padding;
    we pad with '=' to length % 4 == 0.

    Args:
        id_token: 3-part JWT string from GoogleTokenResponse.id_token.

    Returns:
        _GoogleIdTokenPayload with sub, optional email, optional email_verified.

    Raises:
        AuthLoginError: not a 3-part JWT, payload not valid base64url,
                        payload not valid JSON, payload missing required `sub`.
    """
    parts = id_token.split(".")
    if len(parts) != 3:
        raise AuthLoginError(
            f"id_token not a 3-part JWT: got {len(parts)} parts"
        )
    payload_b64 = parts[1]
    pad = "=" * (-len(payload_b64) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + pad)
        payload_json = orjson.loads(payload_bytes)
    except Exception as exc:
        raise AuthLoginError(f"id_token payload parse: {exc}") from exc
    try:
        return _GoogleIdTokenPayload.model_validate(payload_json)
    except ValidationError as exc:
        raise AuthLoginError(f"id_token payload shape: {exc}") from exc


def _to_credential(
    resp: GoogleTokenResponse,
    *,
    original_refresh: str,
    now: float,
) -> OAuthCredential:
    """Convert token-endpoint response → wire-shape OAuthCredential.

    Phase 011 invariant: expires is the absolute epoch (now + expires_in).
    NO 5-min buffer subtracted at storage — buffer is applied in
    is_expired_buffered (P0-7).

    P2-2: refresh = resp.refresh_token or original_refresh — Google rotates
    silently; caller MUST persist whatever the response returns, falling
    back to the original ONLY when Google omitted the field.

    Args:
        resp: Validated GoogleTokenResponse.
        original_refresh: The refresh_token we sent (login: empty string;
                          refresh: cred.refresh from the input credential).
                          Empty string is fine for login because Google
                          ALWAYS returns a refresh_token on first
                          authorization_code exchange.
        now: Wall clock at the START of the wire call (caller passes
             time.time() ONCE).

    Returns:
        Frozen OAuthCredential with wire-shape expires + rotation-aware refresh.
    """
    if resp.id_token:
        payload = _parse_id_token_payload(resp.id_token)
        account_id: str | None = payload.sub
        extras: dict[str, Any] = {}
        if payload.email:
            extras["email"] = payload.email
        if payload.email_verified is not None:
            extras["email_verified"] = payload.email_verified
    else:
        account_id = None
        extras = {}

    return OAuthCredential(
        access=resp.access_token,
        refresh=resp.refresh_token or original_refresh,
        expires=now + float(resp.expires_in),
        provider_id="google.gemini_cli",
        account_id=account_id,
        extras=extras,
    )


def _build_authorize_url(redirect_uri: str, state: str, challenge: str) -> str:
    """Construct the Google authorize URL with PKCE S256 + loopback redirect.

    state and challenge are TWO INDEPENDENT strings (NOT P0-8's reuse —
    that's Anthropic-only). Caller (Plan D login) generates them via two
    separate `generate_verifier()` calls.

    access_type=offline + prompt=consent are MANDATORY:
      - access_type=offline → Google issues a refresh_token (without it,
        only short-lived access_token).
      - prompt=consent → forces refresh_token issuance even when the user
        has previously consented (without it, repeat-login may skip
        refresh_token).

    Args:
        redirect_uri: f"http://127.0.0.1:{port}/oauth2callback" — port from
                      allocate_loopback_port().
        state: CSRF token from generate_verifier() — independent of verifier.
        challenge: PKCE S256 challenge from build_challenge(verifier).

    Returns:
        Full URL ready for the user to open in their browser.
    """
    qs = urlencode(
        {
            "client_id":             _CLIENT_ID,
            "redirect_uri":          redirect_uri,
            "response_type":         "code",
            "scope":                 _SCOPES,
            "state":                 state,
            "code_challenge":        challenge,
            "code_challenge_method": "S256",
            "access_type":           "offline",
            "prompt":                "consent",
        }
    )
    return f"{_AUTHORIZE_URL}?{qs}"


async def _exchange_code(
    code: str,
    verifier: str,
    redirect_uri: str,
) -> GoogleTokenResponse:
    """POST _TOKEN_URL with authorization_code grant body. Per-call AsyncClient.

    Body is form-urlencoded (Google's documented preference for Desktop apps,
    UNLIKE Anthropic's JSON). data= kwarg in httpx → application/x-www-form-urlencoded.

    Raises:
        AuthLoginError: any 4xx/5xx, network error, or response that fails
                        GoogleTokenResponse validation.
    """
    body = {
        "code":          code,
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(
                _TOKEN_URL,
                data=body,
                headers={"accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise AuthLoginError(f"token exchange transport error: {exc}") from exc

    if resp.status_code >= 400:
        body_text = resp.text[:500]
        raise AuthLoginError(
            f"token exchange http {resp.status_code}: {body_text!r}"
        )

    try:
        return GoogleTokenResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"token exchange response shape: {exc}") from exc


# ── GoogleGeminiAuth — AuthMethod Protocol implementation ───────────────


class GoogleGeminiAuth:
    """Google Gemini CLI OAuth provider (Desktop-App OAuth pattern, RFC 8252).

    Implements state_core.auth.base.AuthMethod structurally. Stateless —
    every method is pure-introspection (sync) or constructs its own
    AsyncClient (async, per-call lifecycle, Plan D).

    Self-check available via:
        from state_core.auth.base import AuthMethod
        assert isinstance(GoogleGeminiAuth(), AuthMethod)
    """

    provider_id: str = "google.gemini_cli"

    # ── Sync (pure introspection) ──────────────────────────────────────

    def is_token(self, value: str) -> bool:
        """First branch of token-shape sniffer (P1-1 / Pitfall 5).

        Google access tokens begin `ya29.`. Refresh tokens begin `1//`.
        We sniff on access tokens since http_headers consumes them.
        Each provider owns its own sniffer — no central registry.
        """
        return value.startswith("ya29.")

    def is_expired(self, cred: Credential, now: float) -> bool:
        """Delegate to Phase 013 — never duplicate buffer math (P0-7).

        `now` MUST be a parameter — this method never reads the clock
        internally (Phase 011 cardinal rule).
        """
        return is_expired_buffered(cred, now)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Bearer for inference; x-goog-user-project IFF extras["project_id"] set.

        cloudcode-pa.googleapis.com (v3 inference routing target) expects:
            Authorization: Bearer <ya29.…>
            x-goog-user-project: <project_id>      # optional, for quota
            Content-Type: application/json          # caller's concern

        Returns:
            For OAuthCredential: {authorization, optional x-goog-user-project}.
            For ApiKeyCredential or anything else: {} — caller decides.
        """
        if not isinstance(cred, OAuthCredential):
            return {}
        headers = {"authorization": f"Bearer {cred.access}"}
        project = cred.extras.get("project_id")
        if project:
            headers["x-goog-user-project"] = project
        return headers

    # ── Async (I/O-bound) — Plan D implements ──────────────────────────

    async def login(self) -> OAuthCredential:
        """Run the loopback OAuth login flow.

        Steps:
            1. Generate state and verifier as TWO INDEPENDENT strings (NOT P0-8
               reuse — that's Anthropic-only). RFC 6749 §10.12 CSRF + RFC 7636 PKCE
               are orthogonal defenses.
            2. Allocate a kernel-ephemeral loopback port.
            3. Build authorize URL (access_type=offline + prompt=consent for
               refresh_token issuance).
            4. Print URL — supports headless SSH copy-paste fallback (Phase 022
               adds polished webbrowser.open + --no-browser).
            5. Await wait_for_oauth_callback — blocks until browser redirects.
               AuthLoginError raised on state mismatch / error param / missing code.
            6. Exchange code for tokens via _exchange_code.
            7. Convert response to OAuthCredential — id_token sub → account_id,
               id_token email → extras["email"].

        Returns:
            OAuthCredential with provider_id="google.gemini_cli", access_token
            beginning "ya29.", refresh_token beginning "1//", expires=now+expires_in
            (wire shape; AUTH-09's 5-min buffer applied at is_expired layer).

        Raises:
            AuthLoginError: state CSRF mismatch, error= callback param, missing
                            code, network error, 4xx/5xx, response shape invalid,
                            id_token parse failure.
            asyncio.TimeoutError: user did not complete the flow within 5 minutes
                                  (default wait_for_oauth_callback timeout).
        """
        # CSRF token (state) and PKCE verifier are TWO INDEPENDENT strings.
        # NOT Phase 014's state==verifier reuse (P0-8 — Anthropic-only).
        # Two separate generate_verifier() calls → two 43-char base64url-no-pad
        # strings, each from a fresh os.urandom(32) draw. Collision probability
        # is 2^-256 per call — vanishingly rare.
        state = generate_verifier()
        verifier = generate_verifier()
        challenge = build_challenge(verifier)

        port = allocate_loopback_port()
        redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"
        authorize_url = _build_authorize_url(redirect_uri, state, challenge)

        # Print outside any getpass — URL must appear even if stdout is piped.
        # Phase 022 will add `webbrowser.open(authorize_url)` and a `--no-browser`
        # flag. For 015, print-only supports SSH copy-paste fallback.
        print(
            "Open this URL in your browser to grant Gemini CLI access:\n\n"
            f"  {authorize_url}\n\n"
            f"Waiting for the OAuth callback on http://127.0.0.1:{port}/ ...\n"
        )

        log.info(
            "google_gemini.login.waiting_for_callback",
            port=port,
            client_id_suffix=_CLIENT_ID.split("-")[0],   # NEVER full client_id in logs
        )

        code = await wait_for_oauth_callback(port, expected_state=state, timeout=300.0)

        now = time.time()
        log.info(
            "google_gemini.login.exchange",
            verifier_length=len(verifier),
        )

        resp = await _exchange_code(code, verifier, redirect_uri)
        cred = _to_credential(resp, original_refresh="", now=now)

        log.info(
            "google_gemini.login.success",
            provider_id=cred.provider_id,
            account_id=cred.account_id,
            expires_in_seconds=resp.expires_in,
        )
        return cred

    async def refresh(self, cred: Credential) -> Credential:
        """Refresh access_token using refresh_token. Plan D implements the body."""
        raise NotImplementedError(
            "Plan D (015-D) implements GoogleGeminiAuth.refresh()"
        )


# ── Module exports ───────────────────────────────────────────────────────


__all__ = [
    # Constants (Phase 022 golden-file test imports these)
    "_CLIENT_ID",
    "_CLIENT_SECRET",
    "_AUTHORIZE_URL",
    "_TOKEN_URL",
    "_SCOPES",
    # Re-exports from oauth_common (test surfaces)
    "SIGN_IN_SUCCESS_URL",
    "SIGN_IN_FAILURE_URL",
    "allocate_loopback_port",
    "wait_for_oauth_callback",
    "generate_verifier",
    "build_challenge",
    # Re-exports from errors (catch surfaces)
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    # Models
    "GoogleTokenResponse",
    "_GoogleIdTokenPayload",
    # Helpers
    "_parse_id_token_payload",
    "_to_credential",
    "_build_authorize_url",
    "_exchange_code",
    # Class
    "GoogleGeminiAuth",
]


# ── Module entry point — `python -m state_core.auth.providers.google_gemini` ──
# Plan D fills in the argparse + asyncio.run wiring.

def _main() -> int:  # pragma: no cover — Plan D implements
    raise NotImplementedError(
        "Plan D (015-D) implements `python -m state_core.auth.providers.google_gemini` argparse entry-point"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
