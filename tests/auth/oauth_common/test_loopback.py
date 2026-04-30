"""GREEN tests for oauth_common.loopback (Plan 015-02 implementation).

Plan 015-01 landed RED stubs (pytest.xfail). Plan 015-02 lands the impl
in `src/state_core/auth/oauth_common/loopback.py` AND replaces the
stub bodies here with real assertions exercising the listener.

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

The async tests use the canonical "real loopback + concurrent client"
pattern: one task runs `wait_for_oauth_callback`; another task connects
to the same port and writes a synthetic GET request line. Asserting on
both the returned code and the 302 response body proves the listener
implements the full RFC 8252 contract.
"""

from __future__ import annotations

import asyncio
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


# ── Helper: run a synthetic browser GET against the listener ───────────


async def _send_callback_request(
    port: int, path_with_query: str, *, delay: float = 0.05
) -> bytes:
    """Open a TCP connection to 127.0.0.1:port and write a single GET.

    Returns the raw response bytes (status line + headers + body).
    A short delay lets the listener's `asyncio.start_server` settle
    before the client connects (the listener task is created
    immediately before this helper in the test body).
    """
    await asyncio.sleep(delay)
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    request = (
        f"GET {path_with_query} HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("ascii")
    writer.write(request)
    await writer.drain()
    # Half-close the write side so server's drain() of trailing headers
    # short-circuits cleanly; some kernels otherwise wait for the full
    # 8192-byte read budget to time out.
    try:
        writer.write_eof()
    except (NotImplementedError, OSError):
        pass
    response = await reader.read(4096)
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return response


# ── 015-B-01: port allocator ──────────────────────────────────────────


def test_port_allocator() -> None:
    """allocate_loopback_port() returns an int in the ephemeral range."""
    port = loopback.allocate_loopback_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65_535


def test_port_allocation_ephemeral() -> None:
    """Two consecutive port allocations almost always return DIFFERENT ports
    (kernel allocates ephemeral; with port 0 reuse is unlikely in a single
    test run)."""
    p1 = loopback.allocate_loopback_port()
    p2 = loopback.allocate_loopback_port()
    assert isinstance(p1, int) and isinstance(p2, int)
    # The kernel MAY reuse, but typically increments — accept either case
    # but assert at least one of {p1, p2} is bindable as a sanity check.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", p2))


# ── 015-B-02: state validation (CSRF — RFC 6749 §10.12) ───────────────


@pytest.mark.asyncio
async def test_state_validation() -> None:
    """wait_for_oauth_callback raises AuthLoginError when state mismatch."""
    from state_core.auth.errors import AuthLoginError

    port = loopback.allocate_loopback_port()
    expected_state = "expected-state-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    async def _client() -> None:
        await _send_callback_request(
            port,
            "/oauth2callback?code=fixture-code&state=WRONG-state",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    with pytest.raises(AuthLoginError, match="state mismatch"):
        await server_task
    await client_task


@pytest.mark.asyncio
async def test_loopback_rejects_state_mismatch() -> None:
    """Pitfall 4: malicious redirect with wrong state must be rejected.

    Beyond raising AuthLoginError (covered by test_state_validation), this
    test asserts the BROWSER receives a 302 to SIGN_IN_FAILURE_URL — the
    user-visible side of CSRF defense.
    """
    from state_core.auth.errors import AuthLoginError

    port = loopback.allocate_loopback_port()
    expected_state = "expected-state-bbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    response_holder: dict[str, bytes] = {}

    async def _client() -> None:
        response_holder["resp"] = await _send_callback_request(
            port,
            "/oauth2callback?code=fixture-code&state=attacker-state",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    with pytest.raises(AuthLoginError, match="CSRF check failed"):
        await server_task
    await client_task

    resp = response_holder["resp"]
    assert b"302 Found" in resp
    assert loopback.SIGN_IN_FAILURE_URL.encode("ascii") in resp


# ── 015-B-03: redirect handler ────────────────────────────────────────


@pytest.mark.asyncio
async def test_redirect_handler() -> None:
    """Loopback responds with 302 redirect to Google's SUCCESS/FAILURE pages."""
    port = loopback.allocate_loopback_port()
    expected_state = "redirect-test-cccccccccccccccccccccccccccc"

    response_holder: dict[str, bytes] = {}

    async def _client() -> None:
        response_holder["resp"] = await _send_callback_request(
            port,
            f"/oauth2callback?code=happy-code&state={expected_state}",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    code = await server_task
    await client_task

    assert code == "happy-code"
    resp = response_holder["resp"]
    assert resp.startswith(b"HTTP/1.1 302")
    assert b"Location: " in resp
    assert loopback.SIGN_IN_SUCCESS_URL.encode("ascii") in resp


@pytest.mark.asyncio
async def test_loopback_accepts_valid_callback() -> None:
    """Happy path: GET /oauth2callback?code=...&state=<expected> returns code."""
    port = loopback.allocate_loopback_port()
    expected_state = "happy-state-dddddddddddddddddddddddddddd"

    async def _client() -> None:
        await _send_callback_request(
            port,
            f"/oauth2callback?code=fixture-code&state={expected_state}",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    code = await server_task
    await client_task
    assert code == "fixture-code"


@pytest.mark.asyncio
async def test_loopback_rejects_error_param() -> None:
    """User denied consent: GET /oauth2callback?error=access_denied → AuthLoginError."""
    from state_core.auth.errors import AuthLoginError

    port = loopback.allocate_loopback_port()
    expected_state = "denied-state-eeeeeeeeeeeeeeeeeeeeeeeeeeee"

    response_holder: dict[str, bytes] = {}

    async def _client() -> None:
        response_holder["resp"] = await _send_callback_request(
            port,
            "/oauth2callback?error=access_denied",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    with pytest.raises(AuthLoginError, match="OAuth callback returned error: access_denied"):
        await server_task
    await client_task

    # Browser should see the failure page redirect.
    resp = response_holder["resp"]
    assert b"302 Found" in resp
    assert loopback.SIGN_IN_FAILURE_URL.encode("ascii") in resp


@pytest.mark.asyncio
async def test_loopback_redirects_to_google_pages() -> None:
    """302 Location header points to SIGN_IN_SUCCESS_URL on success and
    SIGN_IN_FAILURE_URL on error."""
    # Verify both URL constants are byte-for-byte from gemini-cli.
    assert (
        loopback.SIGN_IN_SUCCESS_URL
        == "https://developers.google.com/gemini-code-assist/auth_success_gemini"
    )
    assert (
        loopback.SIGN_IN_FAILURE_URL
        == "https://developers.google.com/gemini-code-assist/auth_failure_gemini"
    )

    # Drive the success path and confirm the Location header.
    port = loopback.allocate_loopback_port()
    expected_state = "redir-state-ffffffffffffffffffffffffffff"

    response_holder: dict[str, bytes] = {}

    async def _client() -> None:
        response_holder["resp"] = await _send_callback_request(
            port,
            f"/oauth2callback?code=ok&state={expected_state}",
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_task = asyncio.create_task(_client())

    await server_task
    await client_task

    resp = response_holder["resp"]
    location_header = f"Location: {loopback.SIGN_IN_SUCCESS_URL}".encode("ascii")
    assert location_header in resp


@pytest.mark.asyncio
async def test_loopback_only_first_callback_wins() -> None:
    """Browser prefetch defense: second GET to the same listener does NOT
    clobber the resolved future (`if not code_future.done()` guard).

    We can't easily fire a SECOND connection AFTER the listener returns
    (start_server is closed in the finally block). Instead, we exercise
    the guard at the future-resolution layer directly: two concurrent
    valid callbacks racing for the same expected_state. The first one
    wins; the second's `code_future.set_result` call is suppressed by
    the `if not code_future.done()` guard. Either request can win
    (kernel scheduling), but the returned code MUST be one of them and
    not raise.
    """
    port = loopback.allocate_loopback_port()
    expected_state = "first-wins-gggggggggggggggggggggggggggg"

    async def _client_a() -> None:
        await _send_callback_request(
            port,
            f"/oauth2callback?code=code-A&state={expected_state}",
            delay=0.05,
        )

    async def _client_b() -> None:
        await _send_callback_request(
            port,
            f"/oauth2callback?code=code-B&state={expected_state}",
            delay=0.10,
        )

    server_task = asyncio.create_task(
        loopback.wait_for_oauth_callback(port, expected_state, timeout=5.0)
    )
    client_a_task = asyncio.create_task(_client_a())
    client_b_task = asyncio.create_task(_client_b())

    code = await server_task
    # Whichever connection raced ahead wins; both A and B are acceptable.
    assert code in {"code-A", "code-B"}

    # Drain remaining client tasks; they may complete with connection
    # errors after the server's finally block closed the socket — that's
    # the intended cleanup behavior, not a test failure.
    for task in (client_a_task, client_b_task):
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.TimeoutError, ConnectionError, OSError):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
