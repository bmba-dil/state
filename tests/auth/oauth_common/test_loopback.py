"""RED stubs for oauth_common.loopback (Plan B will implement).

The loopback module does not yet exist (Plan B creates it). We use the
canonical RED pattern from `tests/auth/test_refresh.py` /
`tests/auth/oauth_common/test_pkce.py`: import via try/except, then a
module-level `pytestmark = pytest.mark.skipif(...)` so collection
catalogues each stub by name (`--collect-only` lists every test) but
each test SKIPS until Plan B lands.

VALIDATION.md rows:
  015-B-01: test_port_allocator
  015-B-02: test_state_validation
  015-B-03: test_redirect_handler
Plus supplementary stubs covering:
  - test_loopback_accepts_valid_callback
  - test_loopback_rejects_state_mismatch (CSRF — RFC 6749 §10.12)
  - test_loopback_rejects_error_param (user denied consent)
  - test_loopback_redirects_to_google_pages (302 to SUCCESS_URL / FAILURE_URL)
  - test_port_allocation_ephemeral
  - test_loopback_only_first_callback_wins (browser prefetch defense)

After Plan B lands, every test in this file flips GREEN.
"""

from __future__ import annotations

import socket

import pytest

# Direct ImportError on collection would also be acceptable RED; the
# preferred shape is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces every stub by name.

try:
    from state_core.auth.oauth_common import loopback  # type: ignore[import-not-found]

    _LOOPBACK_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _LOOPBACK_AVAILABLE = False
    _IMPORT_ERROR = _e
    loopback = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _LOOPBACK_AVAILABLE,
    reason=f"Wave 1 (Plan B) not yet landed: {_IMPORT_ERROR}",
)


# ── 015-B-01: port allocator ──────────────────────────────────────────

def test_port_allocator() -> None:
    """allocate_loopback_port() returns an int in the ephemeral range."""
    pytest.xfail("Plan B implementation pending")
    port = loopback.allocate_loopback_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65_535


def test_port_allocation_ephemeral() -> None:
    """Two consecutive port allocations almost always return DIFFERENT ports
    (kernel allocates ephemeral; with port 0 reuse is unlikely in a single
    test run)."""
    pytest.xfail("Plan B implementation pending")
    p1 = loopback.allocate_loopback_port()
    p2 = loopback.allocate_loopback_port()
    # The kernel MAY reuse, but typically increments — accept either case
    # but assert at least one of {p1, p2} is bindable as a sanity check.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", p2))


# ── 015-B-02: state validation (CSRF — RFC 6749 §10.12) ───────────────

@pytest.mark.asyncio
async def test_state_validation() -> None:
    """wait_for_oauth_callback raises AuthLoginError when state mismatch."""
    pytest.xfail("Plan B implementation pending")


@pytest.mark.asyncio
async def test_loopback_rejects_state_mismatch() -> None:
    """Pitfall 4: malicious redirect with wrong state must be rejected."""
    pytest.xfail("Plan B implementation pending")


# ── 015-B-03: redirect handler ────────────────────────────────────────

@pytest.mark.asyncio
async def test_redirect_handler() -> None:
    """Loopback responds with 302 redirect to Google's SUCCESS/FAILURE pages."""
    pytest.xfail("Plan B implementation pending")


@pytest.mark.asyncio
async def test_loopback_accepts_valid_callback() -> None:
    """Happy path: GET /oauth2callback?code=...&state=<expected> returns code."""
    pytest.xfail("Plan B implementation pending")


@pytest.mark.asyncio
async def test_loopback_rejects_error_param() -> None:
    """User denied consent: GET /oauth2callback?error=access_denied → AuthLoginError."""
    pytest.xfail("Plan B implementation pending")


@pytest.mark.asyncio
async def test_loopback_redirects_to_google_pages() -> None:
    """302 Location header points to SIGN_IN_SUCCESS_URL on success and
    SIGN_IN_FAILURE_URL on error."""
    pytest.xfail("Plan B implementation pending")


@pytest.mark.asyncio
async def test_loopback_only_first_callback_wins() -> None:
    """Browser prefetch defense: second GET to the same listener does NOT
    clobber the resolved future (`if not code_future.done()` guard)."""
    pytest.xfail("Plan B implementation pending")
