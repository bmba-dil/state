---
wave: 1
depends_on: ["013", "050"]
files_modified:
  - src/state_daemon/auth_manager.py
  - src/state_daemon/orchestrator.py
  - tests/test_daemon_auth_manager.py
autonomous: true
---

# Plan 059-1: Auth-Manager Wiring into Daemon

**Goal:** The daemon owns the auth credential lifecycle — a background refresh loop, multi-cred round-robin, and `GET /auth/status` HTTP endpoint exposing credential health without leaking raw tokens.

**Requirements:** AUTH-07, AUTH-08

### Tasks

#### 059.1 Auth Refresh Background Task

**Acceptance:** `AuthRefreshLoop` refreshes near-expiry credentials periodically; stops on daemon shutdown.
**Estimated effort:** Medium
**Dependencies:** 013 (filelock refresh)

**Details:**
- `AuthRefreshLoop` class in `src/state_daemon/auth_manager.py`:
  - On start: load `.state/auth.json` via vault (Phase 012), verify chmod 0600.
  - Background asyncio task: every 60s check all credentials for expiry.
  - For each near-expiry credential (within 5-min buffer): call `refresh_credential()` with filelock (Phase 013).
  - On successful refresh: log info with provider and new expiry.
  - On refresh failure: log warning, keep old credential, retry on next tick.
  - Graceful stop: cancel background task on daemon shutdown.
- Test: unit tests with mocked auth vault and filelock, verify refresh is called for near-expiry creds.

**Files:**
- `src/state_daemon/auth_manager.py` — new file

#### 059.2 Multi-Cred Round-Robin Manager

**Acceptance:** `AuthRoundRobin` tracks rotation state per provider; `next_credential(provider)` returns the next credential in round-robin order.
**Estimated effort:** Small
**Dependencies:** 019 (multi-cred round-robin)

**Details:**
- `AuthRoundRobin` wraps Phase 019's round-robin logic for daemon use.
- `next_credential(provider: str) -> Credential`: returns the next credential per provider.
- Tracks `last_used_index` per provider in memory (reloaded from auth.json on daemon start).
- Falls back to next credential on rate-limit (429 detection handled by provider router, Phase 026).
- Test: unit tests for round-robin cycling, index tracking.

**Files:**
- `src/state_daemon/auth_manager.py` — extend with round-robin

#### 059.3 HTTP Auth Status Endpoint

**Acceptance:** `GET /auth/status` returns JSON with per-provider credential status (provider, mode, expiry_with_buffer, credential_index) — never raw tokens.
**Estimated effort:** Small
**Dependencies:** 059.1, 050.3

**Details:**
- Register `GET /auth/status` as a raw HTTP handler (not JSON-RPC).
- Response format: `{"providers": [{"provider": "anthropic-oauth", "mode": "bearer", "expires_at": "...", "credential_index": 0, "count": 1}, ...]}`.
- Deliberately exclude: `access_token`, `refresh_token`, `api_key`, `client_secret`.
- Cache auth status for 5 seconds to avoid I/O on every request.
- Test: integration test that verifies endpoint excludes raw tokens.

**Files:**
- `src/state_daemon/auth_manager.py` — status handler
- `src/state_daemon/server.py` — register endpoint

#### 059.4 Orchestrator Wiring

**Acceptance:** Auth refresh loop starts with daemon; stops on shutdown; auth status endpoint is reachable.
**Estimated effort:** Small
**Dependencies:** 059.3

**Details:**
- In `orchestrator.startup()`:
  - Create `AuthRefreshLoop` after server starts.
  - Start the background refresh task.
  - Register `on_shutdown` callback to stop refresh loop.
- Wire auth status endpoint into the server.
- Test: integration test that starts daemon, hits /auth/status, verifies providers listed.

**Files:**
- `src/state_daemon/orchestrator.py` — wire auth manager

### Integration Notes

- Auth manager is the daemon's ownership of credential lifecycle — workers query auth status over HTTP, never read auth.json directly.
- The refresh loop uses the existing filelock infrastructure from Phase 013.
- Token redactor (Phase 020) ensures no raw tokens appear in logs.

### must_haves

1. Daemon periodically refreshes near-expiry credentials.
2. Multi-cred round-robin selects next credential per provider.
3. `GET /auth/status` returns credential health without raw tokens.
4. Auth refresh loop stops gracefully on daemon shutdown.
5. Auth status is cached for 5s to avoid I/O churn.
