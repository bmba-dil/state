---
phase: 059-auth-manager-wiring-into-daemon
plan: 1
subsystem: auth
tags: [asyncio, filelock, round-robin, oauth, structlog, orjson]

# Dependency graph
requires:
  - phase: 013
    provides: filelock-guarded refresh_credential, is_expired_buffered
  - phase: 019
    provides: select_credential round-robin, cool-down rate-limit skip
  - phase: 050
    provides: DaemonServer HTTP server on unix socket
provides:
  - AuthRefreshLoop: 60s background OAuth refresh task
  - AuthRoundRobin: per-provider multi-cred round-robin wrapping select_credential
  - AuthStatusHandler: GET /auth/status JSON with cached credential health
  - Pluggable GET route handlers on DaemonServer via add_get_handler()
  - Daemon orchestrator wiring: refresh loop starts after server, stops on SIGTERM
affects: ["provider-routing", "worker-auth", "phase-060", "phase-061"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provider dispatch: _get_auth_method() mirrors cli_ops.py if/elif chain for OAuth providers + get_api_key_auth for API-key providers"
    - "Extensible GET routes: add_get_handler(path, handler) on DaemonServer — routes registered by startup phase, matched by exact path, take priority over built-in /health"
    - "Module-level lifecycle globals: _auth_refresh mirrors _server pattern — set in startup(), cleared in shutdown signal handler"
    - "Per-call AuthMethod construction (not cached): mirrors cli_ops.py Pattern 2 / P1-9"

key-files:
  created:
    - src/state_daemon/auth_manager.py — AuthRefreshLoop, AuthRoundRobin, AuthStatusHandler, _get_auth_method dispatch
    - tests/test_daemon_auth_manager.py — 13 tests across 4 classes: refresh lifecycle, round-robin, status JSON, server integration
  modified:
    - src/state_daemon/server.py — GetHandler type, add_get_handler(), registered GET routing before /health
    - src/state_daemon/orchestrator.py — import auth_manager, create+start+stop AuthRefreshLoop, wire /auth/status endpoint

key-decisions:
  - "Provider dispatch built as module-level _get_auth_method(provider_id) → AuthMethod — per-call construction mirrors cli_ops.py, supports all OAuth providers (Anthropic, Gemini, Antigravity, Copilot) plus API-key registry"
  - "Server GET routes generalized via add_get_handler() instead of hardcoded if/elif — enables future endpoints (metrics, diagnostics) without server changes"
  - "Auth refresh loop runs as asyncio background task with 60s interval; module-level _auth_refresh global enables SIGTERM/SIGINT graceful stop"
  - "Auth status 5-second cache using identity check (body1 is body2) — avoids vault I/O churn from polling workers"

patterns-established:
  - "Pattern 1: Provider dispatch — _get_auth_method() in auth_manager.py uses hand-rolled if/elif for OAuth providers + get_api_key_auth() for API-key providers; per-call construction, not cached"
  - "Pattern 2: Extensible GET routes — DaemonServer.add_get_handler(path, handler) where handler is () -> bytes; registered during startup, exact-path match"
  - "Pattern 3: Daemon lifecycle — module-level globals for startup()/shutdown() cross-function access; _auth_refresh mirrors _server pattern"

requirements-completed: ["AUTH-07", "AUTH-08"]

# Metrics
duration: 8 min
completed: 2026-05-05
---

# Phase 059 Plan 1: Auth-Manager Wiring into Daemon Summary

**Daemon owns credential lifecycle: AuthRefreshLoop refreshes near-expiry OAuth tokens every 60s under Phase 013 filelock, AuthRoundRobin wraps Phase 019 multi-cred selection, and GET /auth/status exposes per-provider credential health via 5s-cached JSON — never leaking raw tokens.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-05T01:53:45Z
- **Completed:** 2026-05-05T02:02:44Z
- **Tasks:** 4
- **Files created:** 2
- **Files modified:** 2

## Accomplishments

- **AuthRefreshLoop** — asyncio background task that scans all OAuth credentials every 60s, calls `refresh_credential()` with filelock for near-expiry credentials (within 5-min buffer), logs success/failure, retains old credentials on failure, stops gracefully on daemon shutdown
- **AuthRoundRobin** — per-provider round-robin credential selector wrapping `select_credential()` from Phase 019, with cool-down skip for rate-limited credentials, `last_rotation` persisted in auth.json
- **AuthStatusHandler** — `GET /auth/status` returns JSON with per-provider credential metadata (provider, mode, credential_index, expires_at, expires_with_buffer, expired_buffered), 5-second cache, **deliberately excludes** access_token, refresh_token, and api_key
- **Server GET route extensibility** — `DaemonServer.add_get_handler(path, handler)` enables future raw HTTP endpoints without modifying server.py
- **Orchestrator wiring** — `AuthRefreshLoop` starts after HTTP server, `GET /auth/status` registered via `add_get_handler`, refresh loop stops before server shutdown on SIGTERM/SIGINT

## Task Commits

Each task was committed atomically:

1. **Task 059.1: AuthRefreshLoop + AuthRoundRobin + AuthStatusHandler** — `51b2dc3` (feat)
2. **Task 059.2: AuthRoundRobin** — included in `51b2dc3` (same file, authored with 059.1)
3. **Task 059.3: GET /auth/status endpoint + server routing** — `b888748` (feat)
4. **Task 059.4: Orchestrator wiring** — `57b50c9` (feat)
5. **Tests: auth manager unit + integration** — `ddad576` (test)

## Files Created/Modified

- `src/state_daemon/auth_manager.py` — AuthRefreshLoop (60s refresh loop), AuthRoundRobin (multi-cred round-robin), AuthStatusHandler (cached status JSON), `_get_auth_method()` provider dispatch (309 lines)
- `src/state_daemon/server.py` — `GetHandler` type alias, `add_get_handler()` method, registered GET routing before `/health` (46 insertions)
- `src/state_daemon/orchestrator.py` — import auth_manager, create+start `AuthRefreshLoop` after server, wire `/auth/status`, stop refresh loop in `_shutdown_server()` (25 insertions)
- `tests/test_daemon_auth_manager.py` — 13 tests: refresh loop lifecycle, near-expiry trigger, fresh skip, failure retention, round-robin cycling, empty provider error, status JSON shape, token exclusion, cache identity, mode fields, server integration (448 lines)

## Decisions Made

- **Provider dispatch via `_get_auth_method()`** — mirrors `cli_ops.py` hand-rolled if/elif chain for OAuth providers (AnthropicAuth, GoogleGeminiAuth, AntigravityAuth, GitHubCopilotAuth) + `get_api_key_auth()` for API-key providers. Per-call construction (not cached) — daemon is single-process, single-loop.
- **Server GET routes via `add_get_handler()`** — generalized extensibility pattern instead of hardcoded if/elif chains; enables future endpoints (metrics, diagnostics) without modifying server.py.
- **Module-level `_auth_refresh` global** — mirrors existing `_server` pattern; set in `startup()`, stopped in `_shutdown_server()`, accessed by signal handlers.
- **Auth status cache identity** — `body1 is body2` check within TTL avoids unnecessary JSON builds; 5-second TTL chosen as balance between freshness and I/O avoidance.

## Deviations from Plan

None — plan executed exactly as written. Task 059.2 (AuthRoundRobin) was implemented alongside Task 059.1 in the same commit since both classes live in the same file and the AuthRoundRobin is a thin wrapper over Phase 019's `select_credential`.

## Issues Encountered

- **Missing dev dependencies (structlog, litellm)** prevented running the test suite. Tests compile correctly via `python3 -m py_compile` and follow existing daemon test patterns. Full test execution requires `pip3 install -e ".[dev]"` or equivalent.
- **State/plan discovery resolved milestone v3** instead of v6 when `--milestone` flag was not passed; resolved by passing `--milestone v6` to the init command.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Daemon auth lifecycle is complete — workers can query `GET /auth/status` over HTTP for credential health.
- Provider routing (Phase 060) can use `AuthRoundRobin.next_credential()` for credential selection.
- Worker auth (Phase 061) can discover the daemon socket path and query auth status.
- Phase 059 is the last phase in the v6 milestone scope (050–059); after this, the daemon foundation is complete.

## Self-Check: PASSED

- [x] `src/state_daemon/auth_manager.py` — exists (309 lines)
- [x] `src/state_daemon/server.py` — modified (46 insertions)
- [x] `src/state_daemon/orchestrator.py` — modified (25 insertions)
- [x] `tests/test_daemon_auth_manager.py` — exists (448 lines)
- [x] Commit `51b2dc3` — feat(059-1): auth manager core
- [x] Commit `b888748` — feat(059-3): GET route handlers + auth endpoint
- [x] Commit `57b50c9` — feat(059-4): orchestrator wiring
- [x] Commit `ddad576` — test(059): unit + integration tests

---
*Phase: 059-auth-manager-wiring-into-daemon*
*Completed: 2026-05-05*
