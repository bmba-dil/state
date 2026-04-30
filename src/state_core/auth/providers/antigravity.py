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
# Pitfall 5 (localhost vs 127.0.0.1): Google's OAuth server enforces
# redirect_uri exact-string match. The Antigravity client was registered
# with literal `http://localhost:51121/oauth-callback`. Substituting
# `127.0.0.1` causes redirect_uri_mismatch 400. The asyncio listener
# binds 127.0.0.1 (loopback.py default); only the URL string differs.

_REDIRECT_HOST_LITERAL: str = "localhost"      # NOT '127.0.0.1' — exact-match (Pitfall 5)
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
