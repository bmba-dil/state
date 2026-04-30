"""Asyncio loopback HTTP listener for OAuth Desktop-App pattern (RFC 8252).

Phase 015 (M-A2 / AUTH-02): the localhost callback server that catches
the browser's redirect from Google's OAuth consent flow, validates state
(CSRF — RFC 6749 §10.12), extracts the auth code, redirects the browser
to a polished success/failure page, and returns the code to the caller.

This module is SHARED with Phase 016 (Antigravity) byte-for-byte —
DO NOT add provider-specific behavior here. Provider-specific URL
construction (authorize URL, scopes, client_id) lives in providers/*.py.

Cardinal rules:

  1. Mode isolation — imports limited to stdlib (asyncio, socket,
     urllib.parse) + state_core.auth.errors. NO state.build.* /
     state.teach.* / google-auth / httpx imports.

  2. Browser-prefetch defense — `if not code_future.done()` guards
     EVERY future-resolution. Browsers (Chrome, Safari) prefetch the
     redirect target; the second GET must not clobber the first valid
     resolution.

  3. CSRF — qs["state"] == expected_state is the gate. Mismatch raises
     AuthLoginError; the offending request is redirected to FAILURE_URL.
     Comparison is plain `!=` because the 43-char base64url-no-pad
     token has 256 bits of entropy (secrets.token_urlsafe(32)) — timing
     attacks are infeasible.

  4. Listener cleanup — the server.close() + wait_closed() pair runs
     in a `finally:` block, so TimeoutError, AuthLoginError, and the
     happy path all release the socket.

  5. Determinism — the module never reads the wall clock; the only
     time-aware call is `asyncio.wait_for(timeout=...)` driven by the
     caller-supplied budget.

Reference: gemini-cli `packages/core/src/code_assist/oauth2.ts` (state
validation, success/failure URL constants verbatim; loopback skeleton
adapted to asyncio.start_server from the TypeScript http.createServer
pattern).
"""

from __future__ import annotations

import asyncio
import socket
from urllib.parse import parse_qs, urlparse

from state_core.auth.errors import AuthLoginError

# Public Google sign-in result pages — gemini-cli verbatim.
# These are NOT secrets — they are PUBLIC URLs Google ships in the
# distributable gemini-cli package. We pin them so the browser lands
# on the same polished UX.
SIGN_IN_SUCCESS_URL: str = "https://developers.google.com/gemini-code-assist/auth_success_gemini"
SIGN_IN_FAILURE_URL: str = "https://developers.google.com/gemini-code-assist/auth_failure_gemini"


def allocate_loopback_port() -> int:
    """Bind 127.0.0.1:0, read assigned port, close. Return the port int.

    The TOCTOU window between this socket closing and the caller binding
    `wait_for_oauth_callback` is acceptable on single-user dev machines
    (matches gemini-cli reference). For concurrent-CLI safety, the kernel
    allocates a fresh ephemeral port per call so collisions are vanishingly
    rare.

    Returns:
        Port in [1024, 65535] — kernel-allocated ephemeral.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _respond_redirect(writer: asyncio.StreamWriter, url: str) -> None:
    """Write a minimal HTTP/1.1 302 response with Location: *url*.

    No content-type, no body — Google's success/failure pages own the UX.
    """
    response = (
        "HTTP/1.1 302 Found\r\n"
        f"Location: {url}\r\n"
        "Connection: close\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    )
    writer.write(response.encode("ascii"))


async def wait_for_oauth_callback(
    port: int,
    expected_state: str,
    *,
    timeout: float = 300.0,
) -> str:
    """Listen on 127.0.0.1:{port}, accept ONE OAuth callback, return the code.

    The handler validates `state` byte-for-byte against *expected_state*
    (CSRF — RFC 6749 §10.12). On mismatch, redirects the browser to
    SIGN_IN_FAILURE_URL and raises AuthLoginError.

    Browsers prefetch the redirect target; the future-result pattern
    (`if not code_future.done()`) ensures only the first valid GET wins.

    Args:
        port: Port already allocated by `allocate_loopback_port()` (or
              fixed via STATE_OAUTH_CALLBACK_PORT env — caller's concern).
        expected_state: The OAuth `state` parameter we sent in the authorize
                        URL — independent of the PKCE code_verifier (Pitfall 4).
        timeout: User-attention budget (default 5 min). Caller may shorten.

    Returns:
        The OAuth `code` from `?code=...` query string.

    Raises:
        AuthLoginError: state mismatch, error= query param, missing code,
                        or malformed request.
        asyncio.TimeoutError: user did not complete the flow within *timeout*.
    """
    code_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            try:
                request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            except asyncio.TimeoutError:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                return

            parts = request_line.decode("ascii", errors="replace").split(" ")
            if len(parts) < 2:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                return

            url = urlparse(parts[1])
            qs = parse_qs(url.query)
            err = qs.get("error", [None])[0]
            code = qs.get("code", [None])[0]
            state = qs.get("state", [None])[0]

            if err:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError(f"OAuth callback returned error: {err}")
                    )
                return

            if state != expected_state:
                # CSRF — RFC 6749 §10.12. Plain `!=` is sufficient because
                # the 43-char base64url-no-pad token has ~256 bits of
                # entropy (secrets.token_urlsafe(32)); timing attacks are
                # infeasible against a one-shot listener.
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError("OAuth state mismatch (CSRF check failed)")
                    )
                return

            if not code:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError("OAuth callback missing code param")
                    )
                return

            _respond_redirect(writer, SIGN_IN_SUCCESS_URL)
            if not code_future.done():
                code_future.set_result(code)
        finally:
            # Drain trailing headers (browser sends Connection: keep-alive
            # plus a few hundred bytes of headers we ignore).
            try:
                await asyncio.wait_for(reader.read(8192), timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                pass
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle, "127.0.0.1", port)
    try:
        return await asyncio.wait_for(code_future, timeout=timeout)
    finally:
        server.close()
        await server.wait_closed()


__all__ = [
    "SIGN_IN_FAILURE_URL",
    "SIGN_IN_SUCCESS_URL",
    "allocate_loopback_port",
    "wait_for_oauth_callback",
]
