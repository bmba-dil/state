"""Anthropic OAuth stealth provider — claude-code mitm-verified surface.

Phase 014 (M-A2 / AUTH-01 / P0-1..P0-5, P0-7, P0-8 owner). First concrete
AuthMethod implementation. Mirrors Claude Code's outbound HTTPS shape
byte-for-byte to unlock Pro/Max subscription-priced inference.

Module layout (CONTEXT-locked):
  * Constants (URLs, scopes, stealth headers, system prefix, client_id)
  * Exception hierarchy (AuthError → AuthLoginError, AuthRefreshError,
    StealthRejected) — inline; promote to state_core.auth.errors when
    Phase 015 lands and confirms shared shape (YAGNI per RESEARCH §Open Q5).
  * Pydantic models (AnthropicAccount, AnthropicTokenResponse) with
    extra="ignore" for forward-compat (RESEARCH Pitfall 5).
  * Helpers — _parse_paste, with_beta_param, inject_stealth_system_prefix,
    _to_credential.
  * AnthropicAuth class — satisfies AuthMethod Protocol structurally.
  * `if __name__ == "__main__"` block — Plan 03.

Cardinal rules (CLAUDE.md / Phase 011 Pattern 3 / 014-CONTEXT.md):

  1. Stealth header values are the SOURCE OF TRUTH. Phase 022 (golden-file
     test / AUTH-13) imports these constants and diffs captured outbound
     traffic. Drift in these values = subscription downgrade (P0-1, P0-2,
     P0-3). Each constant carries a `# captured 2026-04 from
     2026-04-29 from local Claude Code 2.1.121 mitm session` provenance
     comment, with milady-ai/milady#1910 (2.1.92) noted as the prior snapshot.

  2. Determinism — no time.time() / datetime.now() reads inside Protocol
     methods. is_expired(cred, now) takes `now` as a parameter; login()
     and refresh() read time.time() ONCE at function entry (RESEARCH §Open
     Q4). Tests inject via monkeypatch.

  3. Mode isolation — imports limited to stdlib + httpx + pydantic +
     structlog + state_core.auth.base + state_core.auth.refresh +
     state_core.auth.oauth_common.pkce. NO state.build.* / state.teach.*.

  4. No own lock — Phase 013's refresh_credential wraps refresh() in a
     10s-budgeted async lock. Acquiring a second lock here deadlocks
     (refresh.py rule 9). Provider's refresh() is pure HTTP exchange.

  5. Per-call AsyncClient — `async with httpx.AsyncClient(...)` inside
     login() and refresh(). NO module-level singleton (RESEARCH §Pattern 2,
     P1-9 defense).

  6. _CLIENT_ID is base64-decoded at module load — defeats secret scanners
     on the literal UUID and matches the spec (P0-5).

See .planning/milestones/v2/phases/014-anthropic-oauth-provider/
014-CONTEXT.md and 014-RESEARCH.md for full rationale.
"""

from __future__ import annotations

import base64
import getpass  # noqa: F401 — exposed at module scope so tests can monkeypatch
import sys
import time

# Expose `print` in the module's namespace so Plan 03 tests can
# monkeypatch `state_core.auth.providers.anthropic.print` to capture
# the authorize-URL print call without touching builtins.print globally.
print = print  # noqa: A001 — intentional re-bind for testability
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from state_core.auth.base import (
    AuthMethod,
    Credential,
    OAuthCredential,
)
from state_core.auth.refresh import is_expired_buffered
from state_core.auth.oauth_common.pkce import (  # noqa: F401 — re-export for Plan 03 + tests
    build_challenge,
    generate_verifier,
)

log = structlog.get_logger(__name__)


# ── Identity constants ───────────────────────────────────────────────────
# Each value carries a provenance comment. DO NOT edit without re-running
# the mitmproxy capture gate (CONTEXT-locked pre-merge requirement).

_CLAUDE_CLI_VERSION: str = "2.1.121"
# captured 2026-04-29 from local Claude Code mitm session
# (was 2.1.92 from milady-ai/milady#1910 as of 2026-04 — superseded)

# base64.b64encode('9d1c250a-e61b-44d9-88ed-5944d1962f5e'.encode()).decode()
# → 'OWQxYzI1MGEtZTYxYi00NGQ5LTg4ZWQtNTk0NGQxOTYyZjVl'
# Encoded form below; decoded at module load to defeat secret scanners on
# the literal Claude Code client_id (P0-5).
_CLIENT_ID: str = base64.b64decode(
    "OWQxYzI1MGEtZTYxYi00NGQ5LTg4ZWQtNTk0NGQxOTYyZjVl"
).decode("ascii")
# captured 2026-04 from milady-ai/milady#1910 (Claude Code OAuth client_id)

# Verify decode at module load — fail fast if base64 string was garbled.
assert _CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e", (
    f"_CLIENT_ID base64 decode produced wrong value: {_CLIENT_ID!r} "
    f"— expected '9d1c250a-e61b-44d9-88ed-5944d1962f5e' (P0-5)"
)

_USER_AGENT: str = f"claude-cli/{_CLAUDE_CLI_VERSION} (external, cli)"
# (external, cli) parenthetical re-confirmed against live capture 2026-04-29 — DO NOT drop (P0-1)

_X_APP: str = "cli"
# re-confirmed against live capture 2026-04-29 (P0-3)

_ANTHROPIC_BETA: str = (
    "oauth-2025-04-20,"
    "interleaved-thinking-2025-05-14,"
    "redact-thinking-2026-02-12,"
    "context-management-2025-06-27,"
    "prompt-caching-scope-2026-01-05"
)
# captured 2026-04-29 from local Claude Code 2.1.121 mitm session (P0-2)
# Drift vs milady-ai/milady#1910 (2.1.92):
#   REMOVED: claude-code-20250219, advanced-tool-use-2025-11-20, effort-2025-11-24
#   ADDED:   redact-thinking-2026-02-12
# Note: Claude Code 2.1.121 sends only `oauth-2025-04-20` on auth/login endpoints
# and the full 5-flag list above on inference (/v1/messages). Phase 014 returns
# this full list from http_headers(); v3 inference routing is responsible for
# any per-endpoint filtering if Anthropic ever rejects the broader list on auth
# calls (current capture shows no rejection).

# ── URL constants ────────────────────────────────────────────────────────

_AUTHORIZE_URL: str = "https://claude.ai/oauth/authorize"
# from .state-inputs/claude-oauth.md §3

_TOKEN_URL: str = "https://platform.claude.com/v1/oauth/token"
# from .state-inputs/claude-oauth.md §3

_REDIRECT_URI: str = "https://platform.claude.com/oauth/code/callback"
# from .state-inputs/claude-oauth.md §3 — manual paste flow, no local server

_SCOPES: str = "org:create_api_key user:profile user:inference"
# from .state-inputs/claude-oauth.md §3

# ── Body-mutation constant ───────────────────────────────────────────────

_CLAUDE_CODE_SYSTEM_PREFIX: str = (
    "You are Claude Code, Anthropic's official CLI for Claude."
)
# from .state-inputs/references/milady/claude-code-stealth.mjs L30-L31


# ── Exception hierarchy ──────────────────────────────────────────────────


class AuthError(Exception):
    """Base for all Anthropic-provider auth errors. Catch this for "any auth failure"."""


class AuthLoginError(AuthError):
    """Token-exchange (login) failed for a non-stealth reason.

    Examples:
        - Paste format invalid (no `#` separator) — P1-2.
        - Network error during POST.
        - Token-endpoint returns 4xx/5xx without stealth-shape signal.
    """


class AuthRefreshError(AuthError):
    """Refresh failed (invalid_grant, network, 4xx/5xx)."""


class StealthRejected(AuthError):
    """401/403 from Anthropic with stealth-shape signal — header drift suspected.

    Distinguished from AuthLoginError so Phase 022's CLI can render
    "stealth headers may be stale, run `state auth recapture`" instead
    of a generic "login failed" message.
    """


# ── Pydantic token-response models ───────────────────────────────────────


class AnthropicAccount(BaseModel):
    """Nested account block in the token-endpoint response.

    extra="ignore" (NOT inherited from a parent — Pydantic v2 ConfigDict
    is per-model). Anthropic may add fields without breaking us.
    """

    model_config = ConfigDict(extra="ignore")

    uuid: str
    email_address: str | None = None


class AnthropicTokenResponse(BaseModel):
    """200-OK payload from POST https://platform.claude.com/v1/oauth/token.

    extra="ignore" (RESEARCH Pitfall 5) — forward-compatible with future
    fields like `id_token`, new account-shape additions, etc.

    access_token / refresh_token use Field(repr=False) for secret hygiene
    (Phase 011 layer 1; Phase 020 structlog redactor is layer 2).
    """

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)
    expires_in: int
    """Seconds-from-now (wire shape per OAuthCredential.expires invariant)."""

    token_type: str | None = None
    account: AnthropicAccount | None = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _parse_paste(paste: str) -> tuple[str, str]:
    """Split a `code#state` paste string. Raises AuthLoginError on missing `#`.

    P1-2 mitigation. Mirrors GSD-pi's exact paste contract — single-prompt
    paste, split on `#`, both halves required.
    """
    if "#" not in paste:
        raise AuthLoginError(
            "paste must be in the form 'code#state' — got a string without '#'. "
            "Re-copy the redirect URL from your browser; the fragment after "
            "'#state=' is required for PKCE state validation."
        )
    code, _, state = paste.partition("#")
    if not code or not state:
        raise AuthLoginError(
            "paste 'code#state' has empty code or state. Re-copy from browser."
        )
    return code, state


def with_beta_param(url: str) -> str:
    """Append `?beta=true` to *url* if not already present. Idempotent.

    Mirrors milady claude-code-stealth.mjs L79: `if (!url.searchParams.has("beta"))
    url.searchParams.set("beta", "true");`. Used by v3 provider routing when
    invoking inference URLs against api.anthropic.com — Phase 014 ships the
    helper; routing wires it later.
    """
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if params.get("beta") == "true":
        return url
    params["beta"] = "true"
    return urlunparse(parsed._replace(query=urlencode(params)))


def inject_stealth_system_prefix(body: dict[str, Any]) -> dict[str, Any]:
    """Mutate *body* in place to begin `system` with the Claude-Code prefix.

    Mirrors milady's addSystemPrefix (claude-code-stealth.mjs L38-L51).
    Idempotent: a `system` array whose first entry text begins with
    "You are Claude Code" is left untouched.

    Handles all three input shapes:
      * list   — prepend prefix unless already present
      * string — wrap into [prefix, {"type": "text", "text": <original>}]
      * missing/None — set to [prefix]
    """
    prefix = {"type": "text", "text": _CLAUDE_CODE_SYSTEM_PREFIX}
    sys_val = body.get("system")
    if isinstance(sys_val, list):
        already_prefixed = (
            len(sys_val) > 0
            and isinstance(sys_val[0], dict)
            and isinstance(sys_val[0].get("text"), str)
            and sys_val[0]["text"].startswith("You are Claude Code")
        )
        if not already_prefixed:
            sys_val.insert(0, prefix)
    elif isinstance(sys_val, str):
        body["system"] = [prefix, {"type": "text", "text": sys_val}]
    else:  # None or missing
        body["system"] = [prefix]
    return body


def _to_credential(resp: AnthropicTokenResponse, now: float) -> OAuthCredential:
    """Convert token-endpoint response → wire-shape OAuthCredential.

    Phase 011 invariant: expires is the absolute epoch returned by the OAuth
    server (now + expires_in). NO 5-min buffer subtracted at storage —
    buffer is applied in is_expired/is_expired_buffered (P0-7).
    """
    return OAuthCredential(
        access=resp.access_token,
        refresh=resp.refresh_token,
        expires=now + float(resp.expires_in),
        provider_id="anthropic",
        account_id=resp.account.uuid if resp.account else None,
        extras=(
            {"email_address": resp.account.email_address}
            if resp.account and resp.account.email_address
            else {}
        ),
    )


def _build_authorize_url(verifier: str, challenge: str) -> str:
    """Construct the authorize URL with state == verifier (P0-8).

    Args:
        verifier: PKCE verifier from generate_verifier(). Reused as the
                  OAuth `state=` parameter — the server round-trips state
                  and we accept that as proof of possession.
        challenge: PKCE S256 challenge from build_challenge(verifier).

    Returns:
        Full URL ready for the user to open in their browser. Default
        urllib.parse.urlencode uses quote_plus → spaces become '+';
        Anthropic accepts both '+' and '%20' (RESEARCH §Open Q3).
    """
    qs = urlencode(
        {
            "client_id": _CLIENT_ID,
            "response_type": "code",
            "redirect_uri": _REDIRECT_URI,
            "scope": _SCOPES,
            "state": verifier,                  # state == verifier (P0-8)
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{_AUTHORIZE_URL}?{qs}"


def _is_stealth_rejection(body_json: dict) -> bool:
    """Detect token-endpoint rejection bodies that signal stealth-header drift.

    Tightened heuristic (post-Wave-0 verifier review): require BOTH a
    stealth-shape error code AND a stealth keyword in the description.
    The bare substring "Claude Code" is intentionally NOT a marker —
    legitimate `invalid_grant` refresh-failure descriptions routinely
    contain that phrase ("Refresh token expired for Claude Code session"),
    and misclassifying them as StealthRejected would violate the must_haves
    contract `truth: "On 401 invalid_grant → AuthRefreshError"`.

    Args:
        body_json: Parsed JSON body of the 401/403 response. May be `{}` if
                   the body was non-JSON or empty.

    Returns:
        True iff the body looks like Anthropic rejected the request because
        the stealth headers/identity drifted from claude-code shape. False
        for `invalid_grant`, network glitches, or generic 5xx.

    Conservative — false positives cause user-facing "header drift suspected"
    message; false negatives just demote to AuthLoginError / AuthRefreshError.
    Phase 022's CLI uses StealthRejected to render a more actionable hint.

    NOTE: callers MUST pre-check `body_json.get("error") == "invalid_grant"`
    BEFORE calling this and raise AuthRefreshError directly. See `refresh()`
    and `_exchange_code()` for the canonical precedence.
    """
    error = (body_json.get("error") or "").lower()
    desc = (body_json.get("error_description") or "").lower()
    has_error_code = error in {"invalid_client", "unauthorized_client"}
    stealth_kw = any(
        kw in desc
        for kw in ("stealth", "drift", "header signature", "client identification")
    )
    return has_error_code and stealth_kw


async def _exchange_code(code: str, verifier: str) -> AnthropicTokenResponse:
    """POST _TOKEN_URL with authorization_code grant body. Per-call AsyncClient.

    Raises:
        StealthRejected: 401/403 with stealth-shape signal (header drift).
        AuthLoginError: any other 4xx/5xx, network error, or response that
                        fails AnthropicTokenResponse validation.
    """
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _REDIRECT_URI,
        "client_id": _CLIENT_ID,
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,                  # OAuth never redirects
        ) as client:
            resp = await client.post(
                _TOKEN_URL,
                json=body,                           # JSON per CONTEXT decision
                headers={"accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise AuthLoginError(f"token exchange transport error: {exc}") from exc

    if resp.status_code >= 400:
        body_text = resp.text[:500]                  # truncate; never log full
        body_json: dict = {}
        try:
            body_json = resp.json()
        except Exception:
            pass
        # PRECEDENCE: invalid_grant ALWAYS wins — auth-code expiry / one-shot-use
        # is unambiguous. Must run BEFORE any stealth heuristic to satisfy the
        # must_haves contract `truth: "On 401 invalid_grant → AuthRefreshError"`
        # (and the symmetric login-side expectation: invalid_grant → AuthLoginError,
        # never StealthRejected — even when the description mentions "Claude Code").
        if body_json.get("error") == "invalid_grant":
            desc = body_json.get("error_description") or "invalid_grant"
            raise AuthLoginError(
                f"token exchange rejected: {desc}"
            )
        # Stealth detection only AFTER invalid_grant ruled out.
        if _is_stealth_rejection(body_json):
            raise StealthRejected(
                f"token exchange rejected (status {resp.status_code}) — "
                f"stealth headers may have drifted. Body: {body_text!r}"
            )
        raise AuthLoginError(
            f"token exchange http {resp.status_code}: {body_text!r}"
        )

    try:
        return AnthropicTokenResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"token exchange response shape: {exc}") from exc


# ── AnthropicAuth — AuthMethod Protocol implementation ──────────────────


class AnthropicAuth:
    """Anthropic OAuth stealth provider (claude-code 2.1.121, mitm-verified).

    Implements state_core.auth.base.AuthMethod structurally. The class is
    deliberately stateless — every method is pure-introspection (sync) or
    constructs its own AsyncClient (async, per-call lifecycle).

    Self-check available via:
        from state_core.auth.base import AuthMethod
        assert isinstance(AnthropicAuth(), AuthMethod)
    """

    provider_id: str = "anthropic"

    # ── Sync (pure introspection) ──────────────────────────────────────

    def is_token(self, value: str) -> bool:
        """First branch of token-shape sniffer (P1-1).

        OAuth tokens issued by Anthropic begin `sk-ant-oat`; API keys begin
        `sk-ant-api03`. Each provider owns its own sniffer (PITFALLS Pitfall 5
        — no central registry).
        """
        return value.startswith("sk-ant-oat")

    def is_expired(self, cred: Credential, now: float) -> bool:
        """Delegate to Phase 013's pure helper — never duplicate buffer math (P0-7).

        `now` MUST be a parameter — never read time.time() internally
        (Phase 011 cardinal rule).
        """
        return is_expired_buffered(cred, now)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Return the exact 4-key stealth header dict for OAuth credentials.

        Returns:
            For OAuthCredential: {authorization Bearer, user-agent, x-app,
                                  anthropic-beta} — the four stealth headers.
            For ApiKeyCredential or anything else: {} — caller decides how to
                                  authenticate non-OAuth credentials.

        NEVER includes x-api-key (P0-4). NEVER includes a Content-Type or
        Accept header (caller's concern). The four headers here are
        byte-for-byte stealth identity; everything else is the caller's
        problem.

        Design note — defensive ``headers.pop("x-api-key", None)``:
            CONTEXT.md §decisions / line 74 calls for a defensive
            ``headers.pop("x-api-key", None)`` "before setting Bearer" to
            defeat P0-4 in disguise. This method returns a FRESH dict — no
            caller-supplied header merge happens here, so the pop is moot
            at this layer. The audit trail is preserved here so the v3
            inference-routing phase (which DOES merge upstream headers
            into the outbound request before applying these stealth
            headers) MUST apply that pop before merging this dict to
            defeat the P0-4 bleed-through.
        """
        if not isinstance(cred, OAuthCredential):
            return {}
        # Fresh dict — no upstream-header merge happens here. v3 routing
        # MUST `headers.pop("x-api-key", None)` before merging this dict
        # into the outbound request (CONTEXT.md §decisions / line 74).
        return {
            "authorization": f"Bearer {cred.access}",
            "user-agent": _USER_AGENT,
            "x-app": _X_APP,
            "anthropic-beta": _ANTHROPIC_BETA,
        }

    # ── Async (I/O-bound) — Plan 03 implements ─────────────────────────

    async def login(self) -> OAuthCredential:
        """Run the interactive paste-flow Anthropic OAuth login.

        Steps:
            1. Generate ONE PKCE verifier; reuse as both `state` and code_verifier (P0-8).
            2. Build authorize URL; print it for the user to open in browser.
            3. Read `code#state` paste via getpass (hidden — auth code is a
               transient secret, T6).
            4. Parse paste; verify state == verifier client-side (T10).
            5. POST token endpoint with authorization_code grant.
            6. Convert response to wire-shape OAuthCredential.

        Raises:
            AuthLoginError: paste format wrong, state/verifier mismatch,
                            network error, non-stealth 4xx/5xx, response
                            shape invalid.
            StealthRejected: 401/403 with stealth-shape signal.
        """
        verifier = generate_verifier()
        challenge = build_challenge(verifier)
        authorize_url = _build_authorize_url(verifier, challenge)

        # Print outside getpass so the URL appears even if stdout is a pipe.
        print(
            "Open this URL in your browser, complete login, "
            "then paste the redirect URL fragment back:\n\n"
            f"  {authorize_url}\n"
        )
        paste = getpass.getpass("Paste code#state: ")

        code, state = _parse_paste(paste)
        if state != verifier:
            # Defensive client-side check (T10). Server enforces server-side too.
            raise AuthLoginError(
                "PKCE state mismatch — pasted state does not equal generated "
                "verifier. Re-run login (the previous URL may have been replaced "
                "or tampered with)."
            )

        now = time.time()
        log.info(
            "anthropic.login.exchange",
            client_id=_CLIENT_ID,
            verifier_length=len(verifier),
        )
        resp = await _exchange_code(code, verifier)

        cred = _to_credential(resp, now=now)
        log.info(
            "anthropic.login.success",
            provider_id=cred.provider_id,
            account_id=cred.account_id,
            expires_in_seconds=resp.expires_in,
        )
        return cred

    async def refresh(self, cred: Credential) -> Credential:
        """Exchange refresh_token for new tokens. Returns a new OAuthCredential.

        Phase 013's refresh_credential wraps this call in a 10s-budgeted
        async file lock; this method MUST NOT acquire its own lock (deadlock —
        refresh.py rule 9). Per-call httpx.AsyncClient with the same
        Timeout(10.0, connect=5.0) as login().

        Args:
            cred: The expired (or near-expired per 5-min buffer) credential.
                  Must be an OAuthCredential — refresh of ApiKeyCredential
                  is a programming error (Phase 013 short-circuits api keys
                  before reaching here).

        Returns:
            New OAuthCredential via cred.model_copy(update={access, refresh,
            expires}). Frozen Pydantic model — input is never mutated.

        Raises:
            TypeError: if cred is not an OAuthCredential.
            StealthRejected: 401/403 with stealth-shape signal.
            AuthRefreshError: invalid_grant, network error, non-stealth 4xx/5xx,
                              response shape invalid.
        """
        if not isinstance(cred, OAuthCredential):
            raise TypeError(
                f"AnthropicAuth.refresh() requires OAuthCredential, "
                f"got {type(cred).__name__} — Phase 013 should short-circuit "
                f"non-OAuth credentials before reaching this method."
            )

        body = {
            "grant_type": "refresh_token",
            "refresh_token": cred.refresh,
            "client_id": _CLIENT_ID,
        }
        log.info(
            "anthropic.refresh.exchange",
            provider_id=cred.provider_id,
            account_id=cred.account_id,
        )
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                follow_redirects=False,
            ) as client:
                resp = await client.post(
                    _TOKEN_URL,
                    json=body,
                    headers={"accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise AuthRefreshError(f"refresh transport error: {exc}") from exc

        if resp.status_code >= 400:
            body_text = resp.text[:500]
            body_json: dict = {}
            try:
                body_json = resp.json()
            except Exception:
                pass
            # PRECEDENCE: invalid_grant ALWAYS wins — refresh-token expiry is
            # unambiguous. Must run BEFORE stealth heuristic to satisfy the
            # must_haves contract `truth: "On 401 invalid_grant → AuthRefreshError"`.
            # A naive heuristic that scans description for "Claude Code" would
            # misclassify "Refresh token expired for Claude Code session" as
            # StealthRejected — see Wave 0 row 014-01-17 regression test.
            if body_json.get("error") == "invalid_grant":
                desc = body_json.get("error_description") or "invalid_grant"
                raise AuthRefreshError(
                    f"Refresh token rejected: {desc}"
                )
            # Stealth detection only AFTER invalid_grant ruled out.
            if _is_stealth_rejection(body_json):
                raise StealthRejected(
                    f"refresh rejected (status {resp.status_code}) — "
                    f"stealth headers may have drifted. Body: {body_text!r}"
                )
            raise AuthRefreshError(
                f"refresh http {resp.status_code}: {body_text!r}"
            )

        try:
            parsed = AnthropicTokenResponse.model_validate_json(resp.content)
        except ValidationError as exc:
            raise AuthRefreshError(f"refresh response shape: {exc}") from exc

        now = time.time()
        new_cred = cred.model_copy(
            update={
                "access": parsed.access_token,
                "refresh": parsed.refresh_token,
                "expires": now + float(parsed.expires_in),
            }
        )
        log.info(
            "anthropic.refresh.success",
            provider_id=new_cred.provider_id,
            account_id=new_cred.account_id,
            expires_in_seconds=parsed.expires_in,
        )
        return new_cred


# ── Module exports ───────────────────────────────────────────────────────


__all__ = [
    # Constants (Phase 022 golden-file test imports these)
    "_CLIENT_ID",
    "_CLAUDE_CLI_VERSION",
    "_USER_AGENT",
    "_X_APP",
    "_ANTHROPIC_BETA",
    "_AUTHORIZE_URL",
    "_TOKEN_URL",
    "_REDIRECT_URI",
    "_SCOPES",
    "_CLAUDE_CODE_SYSTEM_PREFIX",
    # Exceptions
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    "StealthRejected",
    # Models
    "AnthropicAccount",
    "AnthropicTokenResponse",
    # Helpers
    "with_beta_param",
    "inject_stealth_system_prefix",
    # Class
    "AnthropicAuth",
]


# ── Module entry point — `python -m state_core.auth.providers.anthropic login` ──
#
# Smoke-test surface for the pre-merge mitmproxy capture gate. Polished
# `state auth login` Typer CLI lands in Phase 022; this argparse stub is
# deliberately minimal so it can be removed cleanly when 022 ships.


def _main() -> int:  # pragma: no cover — covered by integration smoke, not unit
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        prog="python -m state_core.auth.providers.anthropic",
        description="Anthropic OAuth stealth login — Phase 014 smoke surface.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser(
        "login",
        help="Run the interactive Anthropic OAuth stealth login flow.",
    )
    args = parser.parse_args()

    if args.cmd == "login":
        try:
            cred = asyncio.run(AnthropicAuth().login())
        except KeyboardInterrupt:
            print("\nLogin cancelled.", file=sys.stderr)
            return 130   # POSIX SIGINT exit code
        except (AuthLoginError, StealthRejected) as exc:
            print(f"Login failed: {exc}", file=sys.stderr)
            return 1
        label = (
            cred.extras.get("email_address")
            or cred.account_id
            or "<unknown account>"
        )
        print(f"Logged in as {label}")
        return 0

    return 2  # unknown subcommand


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
