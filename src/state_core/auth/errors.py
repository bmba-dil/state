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


__all__ = [
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
]
