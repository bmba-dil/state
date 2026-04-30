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

  3. Polling deadline math uses time.monotonic(), NOT wall-clock now
     (Pitfall 7). Clock skew during a 15-minute device-code window is
     real; monotonic time is wall-clock-independent.

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
    Plan 03 implementation.

    JSON content-type (NOT form-urlencoded) — GitHub accepts both for the
    device-code endpoint, but JSON keeps body shape consistent across all
    three endpoints in this provider (device-code, poll, mint).

    Per-call AsyncClient (NO module-level singleton — Phase 014/015/016
    pattern). follow_redirects=False is the DoS-by-redirect mitigation.
    """
    url = f"https://{base_domain}/login/device/code"
    body = {"client_id": _CLIENT_ID, "scope": _SCOPE}
    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "user-agent":   _USER_AGENT,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise AuthLoginError(f"device-code request transport: {exc}") from exc

    if resp.status_code >= 400:
        raise AuthLoginError(
            f"device-code request http {resp.status_code}: {resp.text[:500]!r}"
        )
    try:
        return DeviceCodeResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"device-code response shape: {exc}") from exc


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
    reads wall-clock now for deadline math (Pitfall 7).

    See 017-RESEARCH.md §Pattern 2 + §Code Examples (skeleton lines 230-321).
    Plan 03 implementation — RFC 8628 §3.5 state machine.

    Critical anti-pattern guards:
    - Mutate state.interval (NOT a local) — RFC 8628 §3.5 mandates
      persistence across iterations (Pitfall 6 NEW OWNED).
    - Use monotonic() for deadline (NOT wall-clock now) — wall-clock-
      independent (Pitfall 7 NEW OWNED).
    - Sleep BEFORE poll — user needs interval seconds anyway to walk to
      a browser; mirrors opencode reference.
    - Add safety_margin to EVERY sleep — defends client/server clock
      skew (Pitfall 10 NEW OWNED).
    - DO NOT catch asyncio.CancelledError — let it propagate so daemon
      shutdown cleanly cancels the polling task (Pitfall 9 NEW OWNED).
    - DO NOT log full tokens — only token_prefix.
    """
    url = f"https://{base_domain}/login/oauth/access_token"
    body = {
        "client_id":   _CLIENT_ID,
        "device_code": device_code,
        "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
    }
    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "user-agent":   _USER_AGENT,
    }
    state = _PollingState(
        interval=float(initial_interval),
        deadline=monotonic() + float(expires_in),
    )

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
    ) as client:
        while True:
            # Sleep BEFORE each poll — user needs `interval` seconds anyway
            # to walk to a browser. 3-second safety margin (Pitfall 10).
            #
            # asyncio.CancelledError propagates from sleep — daemon shutdown
            # cleanly cancels the polling task (Pitfall 9). DO NOT catch.
            await sleep(state.interval + state.safety_margin)

            try:
                resp = await client.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise AuthLoginError(f"polling transport: {exc}") from exc

            # GitHub returns 200 even for known error codes (RFC 8628 deviation);
            # only 5xx and unexpected non-400 4xx raise.
            if resp.status_code >= 500 or (
                resp.status_code >= 400 and resp.status_code != 400
            ):
                raise AuthLoginError(
                    f"polling http {resp.status_code}: {resp.text[:500]!r}"
                )

            try:
                parsed = DeviceTokenResponse.model_validate_json(resp.content)
            except ValidationError as exc:
                raise AuthLoginError(f"polling response shape: {exc}") from exc

            if parsed.access_token:
                log.info(
                    "github_copilot.poll.success",
                    token_prefix=parsed.access_token[:4],   # gho_ / ghu_ — no full token
                )
                return parsed.access_token

            err = parsed.error
            if err == "authorization_pending":
                # Wall-clock-independent deadline check AFTER each poll
                # (Pitfall 7). Placed here so the first registered response
                # is always consumed before the deadline can fire — matches
                # opencode's order-of-operations.
                if state.remaining(monotonic()) <= 0.0:
                    raise AuthLoginError(
                        f"Device-code authorization expired after "
                        f"{expires_in}s; please re-run login."
                    )
                log.debug(
                    "github_copilot.poll.pending",
                    interval=state.interval,
                )
                continue
            if err == "slow_down":
                # RFC 8628 §3.5: MUST increase by 5s, persist increase
                # across ALL subsequent requests (Pitfall 6 NEW OWNED).
                # If server provided a new interval, prefer it.
                if parsed.interval and parsed.interval > 0:
                    state.interval = float(parsed.interval)
                else:
                    state.interval += _SLOW_DOWN_BUMP_S
                # Wall-clock-independent deadline check (Pitfall 7).
                if state.remaining(monotonic()) <= 0.0:
                    raise AuthLoginError(
                        f"Device-code authorization expired after "
                        f"{expires_in}s; please re-run login."
                    )
                log.info(
                    "github_copilot.poll.slow_down",
                    new_interval=state.interval,
                )
                continue
            if err == "expired_token":
                raise AuthLoginError(
                    "Device code expired; please re-run login."
                )
            if err == "access_denied":
                raise AuthLoginError("User denied authorization.")

            # Unknown error — terminal.
            raise AuthLoginError(
                f"polling unexpected error: {err!r} body={resp.text[:500]!r}"
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
    url = f"{base_api}/copilot_internal/v2/token"
    headers = {
        "accept":                "application/json",
        "authorization":         f"Bearer {oauth_token}",
        "user-agent":             _USER_AGENT,
        "editor-version":         _EDITOR_VERSION,
        "editor-plugin-version":  _EDITOR_PLUGIN_VERSION,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(url, headers=headers)
    except httpx.HTTPError as exc:
        raise AuthRefreshError(
            f"copilot session-token transport: {exc}"
        ) from exc

    # 401/403: oauth token rejected, grant revoked, or Copilot subscription
    # lapsed. Terminal — caller (refresh path) surfaces re-login remediation.
    if resp.status_code in (401, 403):
        raise AuthRefreshError(
            f"Copilot grant rejected (http {resp.status_code}): "
            f"{resp.text[:500]!r}"
        )
    if resp.status_code >= 400:
        raise AuthRefreshError(
            f"copilot session-token http {resp.status_code}: "
            f"{resp.text[:500]!r}"
        )

    try:
        return CopilotSessionResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        # P1-6 / Pitfall 4: 200 with null/missing token → ValidationError
        # because `token: str` is required. Re-raise with grant-revoked
        # message so callers can surface the right remediation.
        raise AuthRefreshError(
            f"Copilot session-token response shape "
            f"(likely grant revoked): {exc}"
        ) from exc


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
        base_domain = (
            normalize_domain(enterprise_url) if enterprise_url else "github.com"
        )
        base_api = (
            f"https://copilot-api.{normalize_domain(enterprise_url)}"
            if enterprise_url
            else "https://api.github.com"
        )

        # Leg 1: device-code request.
        device_resp = await _request_device_code(base_domain=base_domain)

        # Print outside any prompt — user_code must appear even if stdout is piped.
        # Phase 022 will add webbrowser.open(verification_uri_complete) + --no-browser.
        print(
            f"Open this URL in your browser to grant GitHub Copilot access:\n\n"
            f"  {device_resp.verification_uri}\n\n"
            f"And enter the code: {device_resp.user_code}\n\n"
            f"(Code expires in {device_resp.expires_in // 60} minutes; polling "
            f"every {device_resp.interval}s)\n"
        )

        log.info(
            "github_copilot.login.waiting_for_device",
            verification_uri=device_resp.verification_uri,
            expires_in=device_resp.expires_in,
            interval=device_resp.interval,
        )

        # Leg 2: RFC 8628 polling — blocks until success / denial / expiry.
        oauth_token = await _poll_for_token(
            device_code=device_resp.device_code,
            initial_interval=device_resp.interval,
            expires_in=device_resp.expires_in,
            base_domain=base_domain,
        )

        log.info("github_copilot.login.minting_session")

        # Leg 3: eager tid_* mint (Pitfall 14).
        session = await _mint_session_token(oauth_token, base_api=base_api)

        extras: dict[str, Any] = {
            "oauth_token":    oauth_token,           # mirror of cred.refresh (read-clarity)
            "editor_version": _EDITOR_VERSION,        # captured at login (Pitfall 12 forensics)
        }
        if enterprise_url:
            extras["enterprise_url"] = enterprise_url
        if session.sku:
            extras["sku"] = session.sku

        # Two-tier mapping (Pattern 4 — see module docstring + Pitfall 5):
        #   access  = tid_* short-lived Copilot session token
        #   refresh = gho_* / ghu_* long-lived OAuth token
        #   expires = tid_* expiry epoch (server-issued absolute Unix timestamp)
        cred = OAuthCredential(
            access=session.token,
            refresh=oauth_token,
            expires=float(session.expires_at),
            provider_id="github.copilot",
            account_id=None,            # Phase 022 polishes via GET /user
            extras=extras,
        )

        log.info(
            "github_copilot.login.success",
            provider_id=cred.provider_id,
            sku=session.sku,
            expires_at=session.expires_at,
        )
        return cred

    async def refresh(self, cred: Credential) -> Credential:
        """Re-mint the short-lived Copilot session token from stored OAuth token.

        See 017-RESEARCH.md §Pattern 6 (skeleton lines 511-572). Plan 04
        implements. Note: does NOT call GitHub OAuth refresh endpoint
        (legacy OAuth App `Iv1...` doesn't issue refresh_tokens).
        """
        if not isinstance(cred, OAuthCredential):
            raise TypeError(
                f"GitHubCopilotAuth.refresh() requires OAuthCredential, "
                f"got {type(cred).__name__} — Phase 013 should short-circuit "
                f"non-OAuth credentials before reaching this method."
            )

        # GHE base URL substitution from extras (Pitfall 11). At refresh time,
        # the original enterprise_url kwarg is gone — we read it from extras
        # which login() persisted.
        base_api = (
            f"https://copilot-api.{cred.extras['enterprise_url']}"
            if cred.extras.get("enterprise_url")
            else "https://api.github.com"
        )

        log.info(
            "github_copilot.refresh.minting",
            provider_id=cred.provider_id,
            account_id=cred.account_id,
        )

        # Re-mint tid_* via copilot_internal/v2/token using stored gho_*.
        # NOTE: We do NOT call GitHub's OAuth refresh endpoint — the legacy
        # OAuth App Iv1.b507a08c87ecfe98 does not issue refresh_tokens; the
        # gho_* IS the persistent grant. Calling /login/oauth/access_token
        # with grant_type=refresh_token would return unsupported_grant_type.
        session = await _mint_session_token(cred.refresh, base_api=base_api)

        new_extras = dict(cred.extras)
        if session.sku:
            new_extras["sku"] = session.sku

        # model_copy is frozen-model-safe; preserves account_id + non-rotated
        # extras (extras["oauth_token"] still equals the gho_*).
        new_cred = cred.model_copy(
            update={
                "access":  session.token,
                # refresh stays the same — gho_* is long-lived; we are NOT
                # rotating it, only re-minting tid_*.
                "expires": float(session.expires_at),
                "extras":  new_extras,
            }
        )
        log.info(
            "github_copilot.refresh.success",
            provider_id=new_cred.provider_id,
            sku=session.sku,
            expires_at=session.expires_at,
        )
        return new_cred


# ── argparse __main__ entry-point — Plan 04 implements ──────────────────


def _main() -> int:  # pragma: no cover — covered by integration smoke + unit tests
    """argparse entry-point: login + refresh subcommands.

    login subcommand:
        python -m state_core.auth.providers.github_copilot login [--enterprise-url URL]
    refresh subcommand:
        python -m state_core.auth.providers.github_copilot refresh [provider_id] [--idx N]

    login persists the credential via store.save_vault (chmod 0600 atomic);
    refresh drives Phase 013's refresh_credential filelock-guarded path.

    Exit codes:
      0  — success
      1  — AuthLoginError / AuthRefreshError / KeyError
      2  — argparse usage error (provided by argparse itself)
      130 — KeyboardInterrupt (POSIX SIGINT)

    See 017-RESEARCH.md §Pattern 9 + §Code Examples §8 (skeleton lines
    657-688). Plan 04 implements.
    """
    import argparse
    import asyncio
    import sys

    from state_core.auth.refresh import refresh_credential
    from state_core.auth.store import (
        ensure_initialized,
        get_auth_json_path,
        load_vault,
        save_vault,
    )

    parser = argparse.ArgumentParser(
        prog="python -m state_core.auth.providers.github_copilot",
        description="GitHub Copilot device-code OAuth — Phase 017 smoke surface.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    login_parser = sub.add_parser(
        "login",
        help="Run the interactive Copilot device-code login flow.",
    )
    login_parser.add_argument(
        "--enterprise-url",
        default=None,
        help="Optional GHE domain (e.g. company.ghe.com). Defaults to github.com.",
    )

    refresh_parser = sub.add_parser(
        "refresh",
        help="Re-mint the Copilot session token via Phase 013's filelock-guarded path.",
    )
    refresh_parser.add_argument(
        "provider_id",
        nargs="?",
        default="github.copilot",
        help="Provider ID (default: github.copilot).",
    )
    refresh_parser.add_argument(
        "--idx",
        type=int,
        default=0,
        help="Credential index in the provider's array (default: 0).",
    )

    args = parser.parse_args()

    if args.cmd == "login":
        try:
            cred = asyncio.run(
                GitHubCopilotAuth().login(enterprise_url=args.enterprise_url)
            )
        except KeyboardInterrupt:
            print("\nLogin cancelled.", file=sys.stderr)
            return 130
        except AuthLoginError as exc:
            print(f"Login failed: {exc}", file=sys.stderr)
            return 1

        # Persist via Phase 012's atomic-write + chmod 0600. P1-7 array invariant.
        try:
            vault_path = get_auth_json_path()
            ensure_initialized(vault_path)
            vault = load_vault(vault_path)
            vault.providers.setdefault("github.copilot", []).append(cred)
            save_vault(vault_path, vault)
        except Exception as exc:
            print(f"Failed to persist credential to vault: {exc}", file=sys.stderr)
            return 1

        account_label = (
            cred.account_id
            or cred.extras.get("oauth_token", "<unknown>")[:10]
            or "<unknown>"
        )
        print(f"Logged in as {account_label}")
        return 0

    if args.cmd == "refresh":
        try:
            asyncio.run(
                refresh_credential(
                    GitHubCopilotAuth(),
                    args.provider_id,
                    idx=args.idx,
                )
            )
        except KeyboardInterrupt:
            print("\nRefresh cancelled.", file=sys.stderr)
            return 130
        except KeyError as exc:
            print(
                f"No credential for provider_id={args.provider_id!r}: {exc}",
                file=sys.stderr,
            )
            return 1
        except AuthRefreshError as exc:
            print(f"Refresh failed: {exc}", file=sys.stderr)
            return 1

        print(f"Refreshed access_token for {args.provider_id}")
        return 0

    # argparse with required=True should never reach here.
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main())
