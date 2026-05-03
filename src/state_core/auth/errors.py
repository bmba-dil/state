"""Shared exception hierarchy for auth providers (Phase 015 — promoted from
providers/anthropic.py to satisfy YAGNI second-consumer threshold).

Cardinal rules (CLAUDE.md / Phase 011):
  1. Mode isolation — imports limited to stdlib only (NO state_core.auth.*,
     NO state.build.*, NO state.teach.*). This module is the FOUNDATION of
     the auth-provider exception graph; cycles forbidden.
  2. Secret hygiene — exception messages MUST NOT include access tokens,
     refresh tokens, or client secrets. Provider implementations are
     responsible for slicing/redacting before raising. (Phase 020's
     structlog redactor is the second defense layer.)

History:
  Phase 014 defined these inline in providers/anthropic.py with a note
  ('promote to state_core.auth.errors only when phase 015 lands and confirms
  it wants the same hierarchy'). Phase 015 confirmed — second consumer with
  identical needs (login + refresh exception types, no stealth-specific
  branch). StealthRejected stays inline in providers/anthropic.py — it is
  TRULY Anthropic-specific (header-drift heuristic on the stealth flow,
  not portable to Gemini/Antigravity/Copilot).

Downstream consumers:
  * Phase 014 providers/anthropic.py — re-imports + adds StealthRejected
  * Phase 015 providers/google_gemini.py — direct import
  * Phase 016 providers/antigravity.py — will import (when shipped)
  * Phase 017 providers/github_copilot.py — will import (when shipped)
  * Phase 018 providers/api_key.py — get_api_key_auth raises UnknownApiKeyProviderError
  * Phase 022 CLI — catches AuthError as the broad "any auth failure" net
"""

from __future__ import annotations


class AuthError(Exception):
    """Base for all auth errors across providers. Catch this for 'any auth failure'.

    Subclasses distinguish login vs. refresh failure modes; provider-
    specific exceptions (e.g., StealthRejected for Anthropic) inherit
    from this class to preserve catch-AuthError semantics.
    """


class AuthLoginError(AuthError):
    """Login failed for a non-provider-specific reason.

    Examples:
        - Paste format invalid (Anthropic P1-2)
        - Authorize URL state mismatch (CSRF — RFC 6749 §10.12)
        - Loopback callback returned error param (user denied consent)
        - Network error during token-endpoint POST
        - 4xx/5xx without provider-specific signal
        - Pydantic ValidationError on response shape
        - id_token JWT parse failure
    """


class AuthRefreshError(AuthError):
    """Refresh failed.

    Examples:
        - 401 invalid_grant (refresh-token expired/revoked — caller re-logins)
        - Network error during token-endpoint POST
        - 4xx/5xx without provider-specific signal
        - Pydantic ValidationError on response shape
        - google.auth.exceptions.RefreshError (Gemini)
    """


class UnknownApiKeyProviderError(AuthError):
    """Raised when get_api_key_auth() is called with an unknown provider_id.

    Phase 018 (M-A2 / AUTH-05): the registry-driven PlainApiKeyAuth factory
    (state_core.auth.providers.api_key.get_api_key_auth) raises this when
    the requested provider_id is not present in _REGISTRY.

    Message contract (T-018-2 — secret hygiene):
        The exception message includes the offending provider_id (a public
        string) but NEVER the api key. Callers passing a key alongside the
        provider_id MUST NOT include the key in any subsequent log/raise
        chain — Phase 020's redactor is the second defense layer, not the
        first.

    Attributes:
        provider_id: The unknown provider_id the caller requested.

    Example:
        >>> raise UnknownApiKeyProviderError("not-a-real-provider")
        UnknownApiKeyProviderError: Unknown api_key provider_id: 'not-a-real-provider'
    """

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"Unknown api_key provider_id: {provider_id!r}")


class NoCredentialsAvailableError(AuthError):
    """Raised when no credential is available for *provider_id*.

    Phase 019 (M-A2 / AUTH-08): the round-robin selection path raises
    this when the provider's credential array is empty (no login) or
    when every credential is currently cool-down-marked.

    Message contract (T-019-3 — secret hygiene, ASVS V8.3.1):
        The exception message includes the offending provider_id (a public
        string), the reason ("empty" | "all_cooled_down"), and optionally
        the earliest cool-down expiry epoch. NEVER includes credential
        bytes (Credential.key, OAuthCredential.access, refresh).
        Phase 020's redactor is the second defense layer, not the first.

    Attributes:
        provider_id: The provider whose credential array is empty/exhausted.
        reason: One of "empty" (no creds in vault, env synth also empty)
            or "all_cooled_down" (every cred is currently 429-marked).
        earliest_available_at: Epoch seconds when the soonest-expiring
            cool-down clears. None when reason is "empty" (no cool-down
            to wait for); set to a float when reason is "all_cooled_down".
            Phase 022 status command renders this to the user; v3 retry
            policy uses it to compute back-off.

    Example:
        >>> raise NoCredentialsAvailableError(
        ...     "anthropic", reason="empty"
        ... )
        NoCredentialsAvailableError: No credential available for 'anthropic' (reason=empty)

        >>> raise NoCredentialsAvailableError(
        ...     "openai", reason="all_cooled_down", earliest_available_at=1_770_000_060.0
        ... )
        NoCredentialsAvailableError: No credential available for 'openai' (reason=all_cooled_down), earliest at epoch=1770000060.0
    """

    def __init__(
        self,
        provider_id: str,
        *,
        reason: str,
        earliest_available_at: float | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.reason = reason
        self.earliest_available_at = earliest_available_at
        msg = f"No credential available for {provider_id!r} (reason={reason})"
        if earliest_available_at is not None:
            msg += f", earliest at epoch={earliest_available_at}"
        super().__init__(msg)


__all__ = [
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    "NoCredentialsAvailableError",
    "UnknownApiKeyProviderError",
]
