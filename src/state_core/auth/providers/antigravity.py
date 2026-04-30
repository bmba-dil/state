"""Antigravity (Google Cloud Code Assist Companion) OAuth provider.

Phase 016 (M-A2 / AUTH-03 / P2-3 owner). Third concrete AuthMethod
implementation (after Phase 014 Anthropic, Phase 015 Gemini-CLI).
Mirrors NoeFabris/opencode-antigravity-auth's flow byte-for-byte to
unlock the Cloud Code Assist Companion API at cloudcode-pa.googleapis.com/
v1internal — Google's unified gateway for Gemini 3 + Claude Opus +
GPT-OSS via Antigravity rate limits.

⚠️ Terms-of-Service: third-party Antigravity OAuth clients have been
observed to attract Google account moderation. The user has accepted
this risk per .planning/PROJECT.md Key Decision row 14 ('All five auth
methods day one'). This module IS the implementation; the policy
decision lives at the project level.

Module layout (mirrors providers/google_gemini.py):
  * Identity constants (URLs, scopes, plaintext client_id/secret with P1-3 rationale,
    Antigravity-specific outbound headers)
  * Pydantic models (AntigravityTokenResponse, _GoogleIdTokenPayload — duplicated from Phase 015)
  * Helpers (_parse_id_token_payload, _to_credential, _build_authorize_url,
    _exchange_code, _platform_for_client_metadata, _build_client_metadata)
  * AntigravityAuth class (satisfies AuthMethod Protocol) — Plan 03
  * `if __name__ == '__main__'` argparse entry-point — Plan 04

Cardinal rules — IDENTICAL to Phase 015 with these deltas:
  - provider_id = 'google.antigravity' (Pitfall 10)
  - FIXED port 51121 + literal 'localhost' redirect_uri (Pitfalls 4, 5)
  - 5 scopes (Gemini's 3 + cclog + experimentsandconfigs)
  - http_headers emits 4 headers (Bearer + User-Agent + X-Goog-Api-Client + Client-Metadata)
  - is_token returns True for ya29.* — by design (Pitfall 6); provider_id disambiguates

See .planning/milestones/v2/phases/016-antigravity-oauth-provider/
016-RESEARCH.md for full rationale, 12 pitfalls, downstream contracts.
"""

from __future__ import annotations

import base64
import sys
import time

# Expose `print` in module namespace so Plan 04 tests can monkeypatch
# `state_core.auth.providers.antigravity.print` to capture authorize-URL
# print calls without touching builtins.print globally. (Mirrors anthropic.py
# and google_gemini.py.)
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
    AuthError,  # noqa: F401 — re-exported for symmetry with google_gemini.py
    AuthLoginError,
    AuthRefreshError,
)
from state_core.auth.refresh import is_expired_buffered
from state_core.auth.oauth_common.pkce import (  # noqa: F401 — re-export for Plan 04 + tests
    build_challenge,
    generate_verifier,
)
from state_core.auth.oauth_common.loopback import (  # noqa: F401 — re-export for Plan 04 + tests
    SIGN_IN_FAILURE_URL,
    SIGN_IN_SUCCESS_URL,
    wait_for_oauth_callback,
)
# NOTE: the kernel-port-allocation helper from oauth_common.loopback is
# intentionally NOT imported here (Pitfall 4). Antigravity's redirect_uri
# is pinned to localhost:51121 by Google's OAuth-client pre-registration;
# kernel-allocated ports cannot satisfy the exact-match check. The Plan 02
# verification test asserts that helper's symbol name does not appear
# anywhere in this source — keeping the surface clean against future
# refactors that might silently re-introduce dynamic-port logic.

log = structlog.get_logger(__name__)


# ── Identity constants — DO NOT obfuscate (P1-3) ─────────────────────────
# Sources cross-verified 2026-04-30:
#   * NoeFabris/opencode-antigravity-auth src/plugin/constants.ts (archived main)
#   * https://docs.picoclaw.io/docs/providers/antigravity/
#   * https://gist.github.com/taoalpha/22773d2132519e55a4c7427fd3e96d8e
#
# These are PUBLIC distributed-app credentials — Google's Desktop-App
# OAuth pattern relies on PKCE + loopback redirect validation, NOT
# client_secret confidentiality.
#
# !! IMPORTANT — DO NOT obfuscate (P1-3) !!
# Base64-encoding, XOR-encoding, env-var indirection, or any other
# "defensive" transform on these constants is REJECTED:
#   1. AV scanners flag obfuscated literals in source as malicious;
#      corporate users' installs get quarantined.
#   2. Every observed Antigravity OAuth client in the wild ships these
#      plaintext (NoeFabris, PicoClaw, taoalpha — all three independent
#      sources cross-verified 2026-04-30).
#   3. The actual security boundary is PKCE + loopback redirect
#      validation (RFC 8252) — NOT client_secret secrecy.
# See .planning/research/PITFALLS.md P1-3.
#
# ⚠️ Terms-of-Service note: third-party Antigravity OAuth clients have
# been observed to attract Google account moderation. The user has
# accepted this risk per .planning/PROJECT.md Key Decision row 14
# ('All five auth methods day one'). This module IS the implementation;
# the policy decision lives at the project level.

_CLIENT_ID: str = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
_CLIENT_SECRET: str = "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"

# ── URL constants ────────────────────────────────────────────────────────

_AUTHORIZE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
# Google's OAuth 2.0 v2 endpoint — same as Gemini (Phase 015).

_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
# Google's universal token endpoint — same as Gemini.

# ── Loopback redirect (FIXED — pre-registered with Google's OAuth client) ───
# Pitfall 4 (port collision): the redirect_uri is pre-registered against
# Google's OAuth client; kernel-allocated ports cannot be substituted
# (would 400 with redirect_uri_mismatch). Two concurrent state CLIs on
# the same host will surface OSError EADDRINUSE — login() translates that
# to AuthLoginError with explicit remediation copy (Plan 04).
#
# Pitfall 5 (localhost vs the IPv4 loopback literal): Google's OAuth
# server enforces redirect_uri exact-string match. The Antigravity client
# was registered with literal `http://localhost:51121/oauth-callback`.
# Substituting the IP-literal form causes redirect_uri_mismatch 400. The
# asyncio listener binds the IPv4 loopback (loopback.py default); only
# the URL string differs.

_REDIRECT_HOST_LITERAL: str = "localhost"      # NOT the IP-literal — exact-match (Pitfall 5)
_REDIRECT_PORT: int = 51121                    # NOT kernel-allocated (Pitfall 4)
_REDIRECT_PATH: str = "/oauth-callback"

# ── OAuth scopes (5: Gemini's 3 + cclog + experimentsandconfigs) ─────────
# P2-3 owns this list. Drift surfaces as IAM_PERMISSION_DENIED on inference.
# Discovery doc: https://developers.google.com/identity/protocols/oauth2/scopes
#
# cclog                  — Cloud Code Log telemetry attribution. Required
#                          for the loadCodeAssist boot call (v3 provider
#                          routing concern); omitting it 403s.
# experimentsandconfigs  — A/B-test override resolution. Same 403 if
#                          omitted.
# Both are MANDATORY. Cross-verified across NoeFabris/opencode-antigravity-
# auth, PicoClaw provider docs, and taoalpha gist (2026-04-30).

_SCOPES: str = (
    "https://www.googleapis.com/auth/cloud-platform "
    "https://www.googleapis.com/auth/userinfo.email "
    "https://www.googleapis.com/auth/userinfo.profile "
    "https://www.googleapis.com/auth/cclog "
    "https://www.googleapis.com/auth/experimentsandconfigs"
)

# ── Antigravity-specific outbound headers (AUTH-13 regression-test surface) ──
# Cross-source verification (taoalpha gist + PicoClaw docs, 2026-04-30):
# the Cloud Companion API uses the LITERAL string `antigravity` for
# User-Agent (NOT a version-suffixed form). Pitfall 6: mismatched UA →
# quota attribution lands in the wrong bucket → IAM_PERMISSION_DENIED
# (the January 2026 mass-revocation event was correlated with UA drift).

_USER_AGENT_LITERAL: str = "antigravity"
_X_GOOG_API_CLIENT: str = "google-cloud-sdk vscode_cloudshelleditor/0.1"
# Client-Metadata is built per-call so sys.platform monkeypatch works in tests.


# ── Pydantic token-response models ───────────────────────────────────────


class AntigravityTokenResponse(BaseModel):
    """200-OK payload from POST https://oauth2.googleapis.com/token.

    extra="ignore" — forward-compatible with future Google fields.
    Secret-bearing fields use Field(repr=False) (Phase 011 layer 1;
    Phase 020 structlog redactor is layer 2).

    refresh_token may be ABSENT on a refresh response — Google omits it
    when no rotation occurred. Caller (Plan 04 refresh) resolves via
    `parsed.refresh_token or cred.refresh` per P2-2.

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

    NO signature verification (Pitfall 8). Trust boundary is TLS to
    oauth2.googleapis.com. v3 inference routing may add cryptographic
    verification.
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
        id_token: 3-part JWT string from AntigravityTokenResponse.id_token.

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
    resp: AntigravityTokenResponse,
    *,
    original_refresh: str,
    now: float,
) -> OAuthCredential:
    """Convert token-endpoint response → wire-shape OAuthCredential.

    Identical to google_gemini._to_credential except provider_id="google.antigravity".
    Phase 011 invariant: expires is the absolute epoch (now + expires_in).
    NO 5-min buffer subtracted at storage — buffer is applied in
    is_expired_buffered (P0-7 / AUTH-09).

    P2-2: refresh = resp.refresh_token or original_refresh — Google rotates
    silently; caller MUST persist whatever the response returns, falling
    back to the original ONLY when Google omitted the field.

    Args:
        resp: Validated AntigravityTokenResponse.
        original_refresh: The refresh_token we sent (login: empty string;
                          refresh: cred.refresh from the input credential).
                          Empty string is fine for login because Google
                          ALWAYS returns a refresh_token on first
                          authorization_code exchange.
        now: Wall clock at the START of the wire call (caller passes
             time.time() ONCE).

    Returns:
        Frozen OAuthCredential with wire-shape expires + rotation-aware refresh.
        extras may include `project_id` once v3 provider routing fetches it via
        loadCodeAssist; for the login() call path, extras starts with email +
        email_verified only.
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
        provider_id="google.antigravity",
        account_id=account_id,
        extras=extras,
    )


def _build_authorize_url(redirect_uri: str, state: str, challenge: str) -> str:
    """Construct the Google authorize URL with PKCE S256 + loopback redirect.

    state and challenge are TWO INDEPENDENT strings (NOT P0-8's reuse —
    that's Anthropic-only). Caller (Plan 04 login) generates them via two
    separate `generate_verifier()` calls. RFC 6749 §10.12 (CSRF) and
    RFC 7636 (PKCE) are orthogonal defenses; reusing state==verifier
    weakens CSRF on the loopback redirect.

    access_type=offline + prompt=consent are MANDATORY:
      - access_type=offline → Google issues a refresh_token (without it,
        only short-lived access_token).
      - prompt=consent → forces refresh_token issuance even when the user
        has previously consented (without it, repeat-login may skip
        refresh_token).

    Args:
        redirect_uri: f"http://localhost:51121/oauth-callback" — literal
                      `localhost` (NOT the IP-literal — Pitfall 5), FIXED port
                      51121 (NOT kernel-allocated — Pitfall 4).
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


def _platform_for_client_metadata() -> str:
    """Map sys.platform → Client-Metadata `platform` value.

    Antigravity's backend pattern-matches on the literal strings
    MACOS / LINUX / WINDOWS (uppercase, no separator). Computed per-call
    so tests can monkey-patch sys.platform across all three branches.
    """
    p = sys.platform
    if p == "darwin":
        return "MACOS"
    if p.startswith("linux"):
        return "LINUX"
    if p.startswith("win"):                # win32 / cygwin / msys
        return "WINDOWS"
    return "LINUX"                          # defensive fallback


def _build_client_metadata(platform: str) -> str:
    """Compose the Client-Metadata header value as deterministic JSON.

    orjson default key order is insertion-order; we explicitly insert
    ideType → platform → pluginType to match the Antigravity-IDE wire
    format. AUTH-13 (Phase 022) golden-files this string; deterministic
    key order is required for the regression test to bind.
    """
    return orjson.dumps(
        {"ideType": "ANTIGRAVITY", "platform": platform, "pluginType": "GEMINI"},
    ).decode("ascii")


async def _exchange_code(
    code: str,
    verifier: str,
    redirect_uri: str,
) -> AntigravityTokenResponse:
    """POST _TOKEN_URL with authorization_code grant body. Per-call AsyncClient.

    Body is form-urlencoded (Google's documented preference for Desktop apps,
    UNLIKE Anthropic's JSON). data= kwarg in httpx → application/x-www-form-urlencoded.

    OAuth traffic NEVER routes through litellm — CLAUDE.md cardinal rule.
    Direct httpx is the only path. Per-call AsyncClient (no module-level
    singleton — Phase 014/015 pattern; auth calls infrequent, pool-keepalive
    saves nothing, singletons leak across tests).

    Raises:
        AuthLoginError: any 4xx/5xx, network error, or response that fails
                        AntigravityTokenResponse validation.
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
        return AntigravityTokenResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"token exchange response shape: {exc}") from exc


# ── Module exports ───────────────────────────────────────────────────────


__all__ = [
    # Constants (Phase 022 golden-file test imports these)
    "_CLIENT_ID",
    "_CLIENT_SECRET",
    "_AUTHORIZE_URL",
    "_TOKEN_URL",
    "_SCOPES",
    "_REDIRECT_HOST_LITERAL",
    "_REDIRECT_PORT",
    "_REDIRECT_PATH",
    "_USER_AGENT_LITERAL",
    "_X_GOOG_API_CLIENT",
    # Re-exports from oauth_common (test surfaces). NOTE: the kernel-port-
    # allocation helper is intentionally NOT re-exported (Pitfall 4 + the
    # Plan 02 test_fixed_port_51121 source-text assertion).
    "SIGN_IN_SUCCESS_URL",
    "SIGN_IN_FAILURE_URL",
    "wait_for_oauth_callback",
    "generate_verifier",
    "build_challenge",
    # Re-exports from errors (catch surfaces)
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    # Models
    "AntigravityTokenResponse",
    "_GoogleIdTokenPayload",
    # Helpers
    "_parse_id_token_payload",
    "_to_credential",
    "_build_authorize_url",
    "_platform_for_client_metadata",
    "_build_client_metadata",
    "_exchange_code",
]
