"""GitHub Copilot device-code OAuth provider — RFC 8628 + two-tier token mint.

Phase 017 (M-A2 / AUTH-04 / P1-5 + P1-6 owner). Fourth concrete AuthMethod
implementation (after Phase 014 Anthropic, Phase 015 Gemini-CLI, Phase 016
Antigravity). FIRST without a loopback HTTP listener — device-code flow
(RFC 8628) replaces PKCE+loopback. Mirrors the canonical copilot.vim flow
byte-for-byte to unlock Copilot inference at api.githubcopilot.com via
the copilot_internal/v2/token mint.

Two-tier token architecture (Pitfall 5):

  * cred.refresh = gho_* long-lived OAuth token (legacy OAuth App
    Iv1.b507a08c87ecfe98 issues these without expiry; revoked only when
    the user revokes Copilot access in GitHub settings).
  * cred.access  = tid_* short-lived Copilot session token (~30 min;
    minted from gho_* via copilot_internal/v2/token).
  * cred.expires = tid_* expiry epoch (server-returned absolute Unix
    time from CopilotSessionResponse.expires_at — NOT now+expires_in
    math; Pitfall 5 mandates the server epoch).
  * cred.extras["oauth_token"] = mirror of cred.refresh, kept for
    read-clarity in downstream code paths that want the OAuth token
    without name-mapping the two-tier semantics.

Module layout (mirrors providers/google_gemini.py):
  * Constants (URLs are inlined into helpers per Pitfall 11 GHE support;
    plaintext _CLIENT_ID with P1-3 + Pitfall 2 rationale; Copilot-stealth
    headers; polling-loop tuning constants)
  * Pydantic models (DeviceCodeResponse, DeviceTokenResponse,
    CopilotSessionResponse) with extra="ignore" for forward-compat
  * _PollingState dataclass (mutable polling state — interval, deadline,
    safety_margin)
  * normalize_domain helper (strip protocol + trailing slash)
  * Async helpers — _request_device_code, _poll_for_token,
    _mint_session_token (Plan 03/04 implements; this plan stubs)
  * GitHubCopilotAuth class — sync methods FULL, async stubbed
  * `if __name__ == "__main__"` block — Plan 04

Cardinal rules (CLAUDE.md / Phase 011 / Phase 017 RESEARCH):

  1. _CLIENT_ID MUST be the legacy OAuth App "Iv1.b507a08c87ecfe98"
     (Pitfall 2). Tokens minted from opencode's GitHub App ID (the
     `Ov23li...` family) are NOT authorized for
     copilot_internal/v2/token — verified hermes-agent #16551,
     cherry-studio #11905, opencode #20759. Plain string literal
     (P1-3 — AV scanners flag obfuscated literals as malicious).

  2. There is no client-secret constant — device-code flow (RFC 8628)
     is for PUBLIC OAuth clients. The user-consent step (entering
     user_code at the verification_uri) is the security boundary, not
     client-secret confidentiality.

  3. Polling deadline math uses time.monotonic(), NOT time.time()
     (Pitfall 7). Wall-clock skew during a 15-minute device-code
     window is real; monotonic time is wall-clock-independent.

  4. RFC 8628 §3.5 slow_down PERSISTS — every slow_down response
     bumps the interval by +5 seconds; the bump is cumulative across
     iterations, NOT reset back to the initial interval (Pitfall 6
     NEW OWNED).

  5. 3-second safety margin on every interval-based sleep (Pitfall 10
     NEW OWNED). Mirrors opencode's OAUTH_POLLING_SAFETY_MARGIN_MS=3000
     against client-server clock skew.

  6. Eager tid_* mint at login (Pitfall 14) — login() returns a
     credential whose `access` is ALREADY a session token, not the
     gho_* OAuth token. Phase 019 routing operates on the session
     token directly without a per-request refresh round-trip.

  7. 5-min buffer (AUTH-09) applies to cred.expires which tracks
     tid_* — the gho_* in cred.refresh has no stored expiry; it's
     checked only when copilot_internal/v2/token returns 401/403
     (Pitfall 5).

  8. NO oauth_common imports (Pitfall 13) — device-code uses neither
     PKCE nor loopback; those are loopback-flow helpers. Importing
     them would be dead code and obscures the architectural split.

  9. OAuth NEVER through litellm — CLAUDE.md cardinal rule. Direct
     httpx is the only path.

 10. No own filelock — Phase 013's refresh_credential wraps refresh()
     in a 10s-budgeted async lock. Acquiring a second lock here
     deadlocks (refresh.py rule 9). Provider's refresh() is pure HTTP.

See .planning/milestones/v2/phases/017-github-copilot-device-code-flow/
017-RESEARCH.md for full rationale, 14 pitfalls, downstream contracts.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

# Re-bind for testability (mirrors anthropic.py / google_gemini.py /
# antigravity.py — Plan 04 tests monkeypatch this module-level binding to
# capture verification_uri + user_code prints).
print = print  # noqa: A001 — intentional re-bind for testability

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from state_core.auth.base import (
    AuthMethod,  # noqa: F401 — runtime_checkable Protocol; isinstance check in tests
    Credential,
    OAuthCredential,
)
from state_core.auth.errors import (
    AuthError,  # noqa: F401 — re-exported for symmetry with google_gemini.py / antigravity.py
    AuthLoginError,
    AuthRefreshError,
)
from state_core.auth.refresh import is_expired_buffered

# Intentionally absent: state_core.auth.oauth_common imports (Pitfall 13 —
#     device-code has no PKCE, no loopback).
# Intentionally absent: litellm (CLAUDE.md cardinal rule — OAuth never via
#     litellm).
# Intentionally absent: filelock import (refresh.py rule 9 — Phase 013 owns
#     coordination via the per-vault async lock).

log = structlog.get_logger(__name__)


# ── Identity constants — DO NOT obfuscate (P1-3) ─────────────────────────
# Sources cross-verified 2026-04-30:
#   * copilot.vim (canonical Copilot-CLI ecosystem reference)
#   * B00TK1D/copilot-api (Python reference implementation)
#   * Alorse/copilot-to-api
#   * litellm github_copilot provider docs
#   * .planning/_archived/gsd2-auth-analysis.md
#
# !! IMPORTANT — DO NOT swap to opencode's `Ov23li...` GitHub App ID !!
# Tokens minted from that GitHub App family are NOT authorized for
# copilot_internal/v2/token (verified hermes-agent#16551, cherry-studio
# #11905, opencode#20759). The legacy OAuth App `Iv1.b507a08c87ecfe98`
# is the ONLY client_id that supports the two-tier mint we need.
# See .planning/research/PITFALLS.md P1-3 + Phase 017 Pitfall 2.

_CLIENT_ID: str = "Iv1.b507a08c87ecfe98"
_SCOPE: str = "read:user"

# NOTE: No client-secret module attribute exists — device-code flow
# (RFC 8628) is a PUBLIC client flow. The user-consent step (entering
# user_code at verification_uri) is the security boundary, not
# client-secret confidentiality. See Pitfall 13.

# ── RFC 8628 endpoints (github.com — GHE overrides via base_domain kwarg) ──
# Device-code request:    POST https://{base_domain}/login/device/code
# Token polling:          POST https://{base_domain}/login/oauth/access_token
# Session-token mint:     POST {base_api}/copilot_internal/v2/token
#     base_api = https://api.github.com (default)
#              | https://copilot-api.{enterprise_domain} (GHE — Pitfall 11)
#
# Endpoints are NOT module-level constants because base_domain / base_api
# vary by enterprise URL (Pitfall 11). Helpers receive them as kwargs and
# format the URL inline. The canonical github.com defaults live in the
# helper signatures.

# ── Copilot-stealth headers (P2-1 analog — see Pitfall 12) ───────────────
# Captured from copilot.vim 1.16.0 + verified across community refs.
# Editor-Version drift: when GitHub upgrades the accepted client allowlist,
# these strings may need to advance. Phase 022's captured-header regression
# (AUTH-13) is the trip-wire.

_USER_AGENT: str = "GithubCopilot/1.155.0"
_EDITOR_VERSION: str = "Neovim/0.6.1"
_EDITOR_PLUGIN_VERSION: str = "copilot.vim/1.16.0"

# ── Polling-loop tuning ──────────────────────────────────────────────────

_POLLING_SAFETY_MARGIN_S: float = 3.0
"""Seconds added to every interval-based sleep to defend against
client-server clock skew (Pitfall 10). Mirrors opencode's
OAUTH_POLLING_SAFETY_MARGIN_MS=3000."""

_SLOW_DOWN_BUMP_S: float = 5.0
"""RFC 8628 §3.5: minimum interval increase on `slow_down` response.
Persistent across iterations (Pitfall 6 — NEW OWNED)."""


# ── Pydantic response models ─────────────────────────────────────────────


class DeviceCodeResponse(BaseModel):
    """200-OK payload from POST {base}/login/device/code.

    Forward-compat: extra='ignore'. GitHub may add fields
    (verification_uri_complete is in the spec; we store it but don't
    depend on it for v2 — Phase 022 may use it for one-click).
    """

    model_config = ConfigDict(extra="ignore")
    device_code: str = Field(repr=False)         # secret-ish (single-use)
    user_code: str                                # human-readable, displayed
    verification_uri: str
    verification_uri_complete: str | None = None
    expires_in: int                               # 900 = 15 minutes
    interval: int                                 # initial poll cadence (seconds)


class DeviceTokenResponse(BaseModel):
    """200-OK payload from POST {base}/login/oauth/access_token (poll endpoint).

    Either access_token is present (success) or error is present
    (authorization_pending / slow_down / expired_token / access_denied /
    other). Pydantic does NOT enforce 'exactly one of'; caller checks
    .access_token first.
    """

    model_config = ConfigDict(extra="ignore")
    access_token: str | None = Field(default=None, repr=False)
    token_type: str | None = None
    scope: str | None = None
    error: str | None = None
    error_description: str | None = None
    interval: int | None = None  # server-suggested new interval on slow_down


class CopilotSessionResponse(BaseModel):
    """200-OK payload from POST {base_api}/copilot_internal/v2/token.

    `token` is REQUIRED — Pydantic ValidationError fires on null/missing,
    which the caller re-raises as AuthRefreshError('grant revoked …')
    (P1-6 — Pitfall 4). The legacy OAuth App keeps issuing 200s with
    empty bodies for revoked grants rather than 401s, so this Pydantic
    requirement IS the grant-revocation detector.
    """

    model_config = ConfigDict(extra="ignore")
    token: str = Field(repr=False)               # tid_* short-lived session token
    expires_at: int                               # Unix timestamp (absolute epoch)
    refresh_in: int | None = None                 # seconds until recommended refresh
    sku: str | None = None                        # free / individual / business / ent
    chat_enabled: bool | None = None              # informational


# ── Polling state ────────────────────────────────────────────────────────


@dataclass
class _PollingState:
    """Mutable state for the RFC 8628 polling loop.

    - interval: current poll cadence (seconds). Mutated on `slow_down`
      (RFC 8628 §3.5 — increase persists for ALL subsequent requests;
      Pitfall 6).
    - deadline: time.monotonic() + expires_in. Wall-clock-independent
      (Pitfall 7).
    - safety_margin: 3-second clock-skew margin added to every sleep
      (Pitfall 10).
    """

    interval: float
    deadline: float
    safety_margin: float = _POLLING_SAFETY_MARGIN_S

    def remaining(self, now_mono: float) -> float:
        """Seconds left before deadline, clamped to ≥ 0."""
        return max(0.0, self.deadline - now_mono)


# ── Helpers ──────────────────────────────────────────────────────────────


def normalize_domain(url: str) -> str:
    """Strip protocol + trailing slash from a GitHub Enterprise URL.

    Mirrors opencode's pattern (state-inputs/opencode/.../copilot.ts:16):
        https://company.ghe.com/  → company.ghe.com
        company.ghe.com           → company.ghe.com

    Used by login(enterprise_url=...) to derive base_domain and base_api.
    """
    return url.replace("https://", "").replace("http://", "").rstrip("/")


# ── Async helpers — Plan 03 (poll loop) + Plan 04 (mint) implement ────────


async def _request_device_code(
    *,
    base_domain: str = "github.com",
) -> DeviceCodeResponse:
    """POST {base_domain}/login/device/code with client_id + scope=read:user.

    See 017-RESEARCH.md §Pattern 1 + §Code Examples (skeleton lines 162-198).
    Plan 03 implements.
    """
    raise NotImplementedError(
        "Plan 03 implements _request_device_code() body — RFC 8628 §3.1"
    )


async def _poll_for_token(
    device_code: str,
    initial_interval: int,
    expires_in: int,
    *,
    base_domain: str = "github.com",
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> str:
    """Poll the token endpoint until success or terminal error.

    Returns the long-lived OAuth token (gho_* or ghu_*). Raises
    AuthLoginError on terminal failure or 15-min monotonic-deadline
    timeout.

    Determinism: monotonic + sleep are injectable. The function NEVER
    reads time.time() for deadline math (Pitfall 7).

    See 017-RESEARCH.md §Pattern 2 + §Code Examples (skeleton lines 230-321).
    Plan 03 implements.
    """
    raise NotImplementedError(
        "Plan 03 implements _poll_for_token() body — RFC 8628 §3.5 state machine"
    )


async def _mint_session_token(
    oauth_token: str,
    *,
    base_api: str = "https://api.github.com",
) -> CopilotSessionResponse:
    """POST {base_api}/copilot_internal/v2/token with Bearer <oauth_token>.

    Returns CopilotSessionResponse with token / expires_at / refresh_in.
    Raises AuthRefreshError on transport / 4xx / 5xx / shape errors.

    Special case (P1-6 / Pitfall 4): a 200 response WITHOUT a `token`
    field signals grant revocation. Pydantic catches this — `token: str`
    is required, ValidationError fires. We re-raise as AuthRefreshError.

    See 017-RESEARCH.md §Pattern 3 + §Code Examples (skeleton lines 338-395).
    Plan 04 implements.
    """
    raise NotImplementedError(
        "Plan 04 implements _mint_session_token() body — copilot_internal/v2/token"
    )


# ── GitHubCopilotAuth — AuthMethod Protocol implementation ───────────────


class GitHubCopilotAuth:
    """GitHub Copilot device-code OAuth provider (RFC 8628 + two-tier mint).

    Implements state_core.auth.base.AuthMethod structurally. Stateless —
    every method is pure-introspection (sync) or constructs its own
    AsyncClient (async, per-call lifecycle, Plans 03/04).

    Self-check available via:
        from state_core.auth.base import AuthMethod
        assert isinstance(GitHubCopilotAuth(), AuthMethod)

    Two-tier token mapping (see module docstring + Pitfall 5):
      * cred.access  = tid_* short-lived Copilot session token (~30 min)
      * cred.refresh = gho_* long-lived OAuth token (indefinite TTL on
                       legacy OAuth App; revoked when user revokes
                       Copilot access in GitHub settings)
      * cred.expires = tid_* expiry epoch (from CopilotSessionResponse.expires_at)
      * cred.extras["oauth_token"] = mirror of cred.refresh (read-clarity)
    """

    provider_id: str = "github.copilot"

    # ── Sync (pure introspection) ──────────────────────────────────────

    def is_token(self, value: str) -> bool:
        """Token-shape sniffer.

        GitHub Copilot tokens come in four relevant shapes (see
        https://github.blog/changelog/2021-03-31-authentication-token-format-updates-...):
            gho_* — OAuth App access tokens (legacy 'Iv1' clients)
            ghu_* — GitHub App user-to-server tokens
            tid_* — Copilot session tokens (minted via copilot_internal/v2/token)
            ghr_* — GitHub OAuth refresh tokens (NOT issued by Iv1; only GitHub
                    Apps with expiring tokens)

        Returns True for any of the four prefixes; provider-level routing
        disambiguates Copilot vs GitHub-OAuth-only via cred.provider_id.
        """
        return any(
            value.startswith(prefix)
            for prefix in ("gho_", "ghu_", "tid_", "ghr_")
        )

    def is_expired(self, cred: Credential, now: float) -> bool:
        """Delegate to Phase 013's is_expired_buffered (5-min buffer per AUTH-09).

        cred.expires tracks the SHORT-lived tid_* expiry epoch — buffer
        applies cleanly. cred.refresh (gho_*) has no stored expiry; it's
        checked only at refresh-call time when copilot_internal/v2/token
        returns 401/403 (Pitfall 5).

        `now` MUST be a parameter — this method NEVER reads the clock
        internally (Phase 011 cardinal rule).
        """
        return is_expired_buffered(cred, now)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Bearer + Copilot-stealth triple for outbound inference requests.

        api.githubcopilot.com (the Copilot inference endpoint that v3
        provider routing targets) requires:
            Authorization:          Bearer <tid_…>           # cred.access
            User-Agent:             GithubCopilot/1.155.0
            Editor-Version:         Neovim/0.6.1
            Editor-Plugin-Version:  copilot.vim/1.16.0

        Returns:
            For OAuthCredential: {authorization, user-agent, editor-version,
                                  editor-plugin-version} — exactly 4 keys.
            For ApiKeyCredential or anything else: {} — caller decides.

        AUTH-13 (Phase 022) golden-files this dict.
        """
        if not isinstance(cred, OAuthCredential):
            return {}
        return {
            "authorization":         f"Bearer {cred.access}",
            "user-agent":             _USER_AGENT,
            "editor-version":         _EDITOR_VERSION,
            "editor-plugin-version":  _EDITOR_PLUGIN_VERSION,
        }

    # ── Async (I/O-bound) — Plan 04 implements ─────────────────────────

    async def login(
        self,
        *,
        enterprise_url: str | None = None,
    ) -> OAuthCredential:
        """Run the device-code login flow + immediately mint a Copilot session token.

        See 017-RESEARCH.md §Pattern 5 (skeleton lines 425-507). Plan 04
        implements.
        """
        raise NotImplementedError(
            "Plan 04 implements GitHubCopilotAuth.login() body — "
            "device-code → poll → mint → OAuthCredential"
        )

    async def refresh(self, cred: Credential) -> Credential:
        """Re-mint the short-lived Copilot session token from stored OAuth token.

        See 017-RESEARCH.md §Pattern 6 (skeleton lines 511-572). Plan 04
        implements. Note: does NOT call GitHub OAuth refresh endpoint
        (legacy OAuth App `Iv1...` doesn't issue refresh_tokens).
        """
        raise NotImplementedError(
            "Plan 04 implements GitHubCopilotAuth.refresh() body — "
            "re-mint tid_* via copilot_internal/v2/token"
        )


# ── argparse __main__ entry-point — Plan 04 implements ──────────────────


def _main() -> int:
    """argparse entry-point: login + refresh subcommands.

    See 017-RESEARCH.md §Pattern 9 + §Code Examples §8 (skeleton lines
    657-688). Plan 04 implements.
    """
    raise NotImplementedError(
        "Plan 04 implements _main() argparse — login + refresh subcommands"
    )


if __name__ == "__main__":
    import sys
    sys.exit(_main())
