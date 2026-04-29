"""RED stubs for state_core.auth.oauth_common.pkce — Phase 014 / AUTH-01.

Plan 01 (Wave 0) ships these RED. Plan 02 (Wave 1) ships pkce.py and
turns them GREEN. Plan 03 (Wave 2) is unaffected by this file.

The PKCE primitives are SHARED with phases 015 (Gemini), 016 (Antigravity),
017 (Copilot) — extracting them here unblocks those phases at parallel run.

RED-state strategy:
    Plan 01 ships these tests BEFORE ``state_core.auth.oauth_common.pkce`` exists.
    The module is imported via ``try / except ImportError`` and a
    ``pytestmark = pytest.mark.skipif(...)`` ensures collection always
    succeeds — every test is SKIPPED with a clear reason until Plan 02
    lands the production module. This mirrors the canonical pattern in
    ``tests/auth/test_refresh.py``.
"""

from __future__ import annotations

import pytest

# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape per the plan is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces exactly the right number of items.

try:
    from state_core.auth.oauth_common import pkce  # type: ignore[import-not-found]

    _PKCE_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _PKCE_AVAILABLE = False
    _IMPORT_ERROR = _e
    pkce = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _PKCE_AVAILABLE,
    reason=f"Plan 02 not yet landed: {_IMPORT_ERROR}",
)


def test_verifier_format() -> None:
    """generate_verifier() returns a base64url-no-pad string in RFC 7636's [43, 128] window.

    AUTH-01 / row 014-01-01.
    """
    verifier = pkce.generate_verifier()
    # RFC 7636 §4.1 — verifier MUST be 43–128 unreserved chars.
    assert 43 <= len(verifier) <= 128, f"verifier length {len(verifier)} outside [43,128]"
    # base64url-no-pad alphabet: A-Z a-z 0-9 - _
    assert all(c.isalnum() or c in "-_" for c in verifier), (
        f"verifier contains non-base64url chars: {verifier!r}"
    )
    # NO padding (urlsafe_b64encode + rstrip('=') is the canonical recipe).
    assert "=" not in verifier, "PKCE verifier must NOT contain '=' padding"

    # Must also be high-entropy (not all the same byte). secrets.token_urlsafe
    # gives ≥256 bits at nbytes=32 — sanity-check uniqueness across calls.
    assert pkce.generate_verifier() != pkce.generate_verifier(), (
        "two consecutive verifiers must differ (high-entropy RNG)"
    )
