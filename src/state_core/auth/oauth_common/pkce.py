"""PKCE (RFC 7636) primitives — stdlib-only, shared across providers.

Phase 014 (Anthropic) consumes this module first; phases 015 (Gemini),
016 (Antigravity), 017 (Copilot) reuse the same primitives so each
provider does not re-implement the recipe.

Cardinal rules (mirrored from 014-RESEARCH.md):

  1. Verifier MUST be base64url-no-pad in the [43, 128]-char window
     (RFC 7636 §4.1). secrets.token_urlsafe(32) yields exactly 43 chars
     of base64url alphabet — perfect, no truncation, no padding to strip.

  2. Challenge MUST be S256 (RFC 7636 §4.2): base64url-no-pad of
     sha256(verifier.encode('ascii')). The `.rstrip(b'=')` is mandatory —
     padded base64 round-trips fine in Python but Anthropic's server
     rejects padded challenges with `invalid_grant`.

  3. Anthropic-specific reuse (P0-8): the SAME verifier is passed as both
     OAuth `state` AND PKCE `code_verifier`. This module just generates
     the string; the reuse decision lives in providers/anthropic.py.

  4. Mode isolation — stdlib ONLY (secrets, hashlib, base64). NO pydantic,
     NO httpx, NO state.build.* / state.teach.* imports.
"""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_verifier(nbytes: int = 32) -> str:
    """Return a URL-safe PKCE verifier string (RFC 7636 §4.1).

    Args:
        nbytes: Number of random bytes to source from `secrets.token_urlsafe`.
                Default 32 → 43-character base64url-no-pad string. RFC 7636
                requires verifier length ∈ [43, 128]; nbytes ∈ [32, 96]
                stays inside that window.

    Returns:
        A base64url-no-pad string consisting of [A-Z a-z 0-9 - _]. Reusable
        verbatim as the OAuth `state` parameter (P0-8 — Anthropic-specific
        single-source-of-truth pattern).

    Notes:
        secrets.token_urlsafe internally uses os.urandom (CSPRNG); 32 bytes
        gives ≥256 bits of entropy. Each call produces an independent value.
    """
    return secrets.token_urlsafe(nbytes)


def build_challenge(verifier: str) -> str:
    """Return the S256 challenge for *verifier* (RFC 7636 §4.2).

    Args:
        verifier: A PKCE verifier string. Must be ASCII; `generate_verifier`
                  output is always ASCII-safe.

    Returns:
        base64url-no-pad of sha256(verifier). NEVER includes '=' padding —
        Anthropic's server rejects padded challenges as `invalid_grant`.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


__all__ = ["generate_verifier", "build_challenge"]
