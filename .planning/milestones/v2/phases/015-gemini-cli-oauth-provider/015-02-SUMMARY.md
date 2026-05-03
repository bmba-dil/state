---
phase: 015-gemini-cli-oauth-provider
plan: "02"
subsystem: auth
tags: [oauth, loopback, asyncio, csrf, rfc-8252, gemini, google]

# Dependency graph
requires:
  - phase: 015-01
    provides: state_core.auth.errors (AuthLoginError) + RED stubs in tests/auth/oauth_common/test_loopback.py
provides:
  - asyncio loopback HTTP listener (allocate_loopback_port + wait_for_oauth_callback)
  - SIGN_IN_SUCCESS_URL / SIGN_IN_FAILURE_URL constants (gemini-cli verbatim)
  - browser-prefetch defense pattern (`if not code_future.done()` guard)
  - CSRF gate (state byte-for-byte comparison) with redirect to FAILURE_URL
affects:
  - 015-03 (Gemini provider login() will import wait_for_oauth_callback)
  - 015-04 (Gemini provider integration tests use the live listener)
  - 016-* (Antigravity provider — reuses oauth_common/loopback.py byte-for-byte unchanged)

# Tech tracking
tech-stack:
  added: []  # stdlib only — asyncio.start_server + socket + urllib.parse
  patterns:
    - "RFC 8252 desktop-app loopback redirect (asyncio listener)"
    - "Browser-prefetch defense via `if not code_future.done()` guards"
    - "Listener cleanup in `finally:` so timeout/error/success all release the socket"
    - "Concurrent-client test pattern: server task + client task awaited in parallel"

key-files:
  created:
    - src/state_core/auth/oauth_common/loopback.py
  modified:
    - tests/auth/oauth_common/test_loopback.py

key-decisions:
  - "Plain `!=` for state comparison (not hmac.compare_digest) — 256-bit entropy from secrets.token_urlsafe(32) makes timing attacks infeasible against a one-shot listener"
  - "Accept any GET with code/error params, not just /oauth2callback path — matches gemini-cli reference behavior; attacker collisions on localhost are unlikely"
  - "Drain trailing headers (max 8192 bytes, 1s timeout) so browser keep-alive doesn't leak fds"
  - "Listener uses asyncio.start_server (not socket.SO_REUSEADDR-on-bind) — kernel-allocated ephemeral ports avoid TIME_WAIT collisions"

patterns-established:
  - "loopback module is provider-agnostic: provider-specific URL construction lives in providers/*.py"
  - "test_loopback uses real socket clients (no mock_loopback_callback fixture) — proves the wire-level contract"

requirements-completed: [AUTH-02]

# Metrics
duration: ~3min
completed: 2026-04-30
---

# Phase 015 Plan 02: oauth_common/loopback.py Summary

**asyncio loopback HTTP listener (199 LOC) catching OAuth browser redirects, validating CSRF state byte-for-byte against expected_state, and routing the browser to gemini-cli's polished success/failure pages — shared module reusable by Phase 016 unchanged.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-30T17:35:54Z
- **Completed:** 2026-04-30T17:38:53Z
- **Tasks:** 1
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `allocate_loopback_port()` — kernel-allocated ephemeral port via `socket.bind('127.0.0.1', 0)`, returns int in [1024, 65535]
- `wait_for_oauth_callback(port, expected_state, *, timeout=300.0)` — full asyncio listener with state CSRF gate, error-param rejection, missing-code rejection, browser-prefetch defense, and clean socket teardown via `finally:`
- 9 RED stubs in `tests/auth/oauth_common/test_loopback.py` flipped to GREEN (test_port_allocator, test_port_allocation_ephemeral, test_state_validation, test_loopback_rejects_state_mismatch, test_redirect_handler, test_loopback_accepts_valid_callback, test_loopback_rejects_error_param, test_loopback_redirects_to_google_pages, test_loopback_only_first_callback_wins)
- Module imports verified stdlib-only (asyncio, socket, urllib.parse) + state_core.auth.errors — no third-party deps, no mode-specific imports, no litellm
- Full auth suite: 94 passed / 30 skipped (was 85 / 39 in 015-01) — zero regressions in Phase 014 anthropic suite

## Task Commits

1. **Task 1: Implement allocate_loopback_port + wait_for_oauth_callback in oauth_common/loopback.py** — `06204f1` (feat)

_Note: TDD RED was already landed by Plan 015-01; Plan 015-02 is GREEN-only — single commit covers impl + test-body fill-in._

## Files Created/Modified

- `src/state_core/auth/oauth_common/loopback.py` (created, 199 LOC) — asyncio loopback listener: port allocator, redirect helper, async wait_for_oauth_callback with state CSRF gate, error-param rejection, missing-code rejection, browser-prefetch guard, finally-block cleanup
- `tests/auth/oauth_common/test_loopback.py` (modified) — replaced 9 `pytest.xfail("Plan B implementation pending")` stubs with real assertion bodies driving the listener via concurrent client tasks

## Decisions Made

- **Plain `!=` for state comparison** (not `hmac.compare_digest`): the 43-char base64url-no-pad state token has ~256 bits of entropy from `secrets.token_urlsafe(32)`. Timing attacks against a one-shot listener that closes after the first valid match are infeasible. Documented inline.
- **Accept any GET path, not just `/oauth2callback`**: matches gemini-cli reference. The decision is anchored on the query-param contents (code/error/state), not the path. Path collisions on localhost are vanishingly unlikely.
- **Drain trailing headers with a 1s timeout**: browsers send Connection: keep-alive plus a few hundred bytes of headers we ignore. Reading up to 8192 bytes within 1s prevents fd leaks without blocking the listener.
- **Listener uses asyncio.start_server**: the kernel allocates a fresh ephemeral port per `allocate_loopback_port()` call; SO_REUSEADDR isn't needed because we don't reuse explicit ports.
- **`finally:` block runs server.close() + wait_closed()**: ensures TimeoutError, AuthLoginError, and the happy path all release the listening socket. No outstanding fd leaks across asyncio tasks.

## Deviations from Plan

None — plan executed exactly as written. The verbatim 199-LOC skeleton in `<action>` was the implementation; the only minor adjustments were:

1. Wrapping the trailing-header drain `try/except` to also catch the bare `Exception` class (not just `asyncio.TimeoutError`) so a kernel-side `ConnectionResetError` during browser keep-alive teardown does not leak. This is a hardening tweak inside the planned `try/finally`, not a behavior change.
2. The test helper `_send_callback_request` calls `writer.write_eof()` after sending the request to half-close the write side — this short-circuits the listener's `reader.read(8192)` drain on Linux/macOS so tests complete in ~50 ms instead of timing out at the 1s drain budget.

Both adjustments are within the spirit of the plan (`<behavior>` says "drain trailing headers" — the test helper makes the drain return cleanly).

**Total deviations:** 0 auto-fixed
**Impact on plan:** None.

## Issues Encountered

- Initial `python3 -m pytest` invocation failed because the homebrew system Python lacks the project deps (structlog, pytest-asyncio, etc.). Switched to `.venv/bin/python -m pytest` for all subsequent runs. No code change required — just an environment-discovery step.

## User Setup Required

None — pure stdlib module, no external services.

## Next Phase Readiness

- Plan 015-03 (Gemini provider `login()`) is unblocked — can `from state_core.auth.oauth_common.loopback import allocate_loopback_port, wait_for_oauth_callback` directly.
- Phase 016 (Antigravity) can reuse this module byte-for-byte unchanged — interface guarantees `expected_state` is provider-agnostic.
- Mock fixture `mock_loopback_callback` in `tests/auth/providers/conftest.py` already mirrors the same surface, so Plan 015-03/04 unit tests can swap between mock and real listener without code changes.

## Self-Check: PASSED

- File `src/state_core/auth/oauth_common/loopback.py` exists (199 LOC, within [60, 200] budget)
- Commit `06204f1` exists in `git log`
- All 14 grep-based acceptance criteria satisfied (SUCCESS_URL/FAILURE_URL byte-for-byte, allocate_loopback_port, async wait_for_oauth_callback, AuthLoginError import, asyncio.start_server, prefetch defense guard, expected_state, "OAuth state mismatch" exact message, no httpx/google_auth/requests imports, no state.build/teach imports, no litellm)
- `pytest tests/auth/oauth_common/test_loopback.py -x` exits 0 with 9 PASSED (no SKIPs, no XFAILs)
- `pytest tests/auth -x` exits 0 (94 passed / 30 skipped — Phase 014 anthropic + 015-01 errors module unaffected)
- `python -c "from state_core.auth.oauth_common.loopback import allocate_loopback_port, wait_for_oauth_callback, SIGN_IN_SUCCESS_URL, SIGN_IN_FAILURE_URL; print('ok')"` prints `ok`

---
*Phase: 015-gemini-cli-oauth-provider*
*Completed: 2026-04-30*
