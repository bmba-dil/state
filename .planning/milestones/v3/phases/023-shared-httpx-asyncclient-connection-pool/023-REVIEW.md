---
phase: 023
status: findings
reviewed: 2026-05-02
finding_count: 4
blocker_count: 0
---

# Code Review — Phase 023: Shared `httpx.AsyncClient`

## Summary

Clean implementation. One major lifecycle gap (deps not stored for shutdown), two minors, one style note. No blockers — safe to proceed. The lifecycle gap is explicitly out-of-scope for Phase 023 (daemon shutdown owned by a later phase).

---

### [MAJOR] `deps` not stored — `http_client.aclose()` unreachable on daemon shutdown
**File:** `src/state_daemon/orchestrator.py:57`
**Issue:** `deps = Deps(http_client=build_shared_client())` is a local variable. `startup()` returns without storing `deps`, so `deps.aclose()` can never be called. The client object is kept alive via `litellm.aclient_session` but will never be explicitly closed on daemon exit — leaving OS socket descriptors open and triggering asyncio `ResourceWarning`.
**Suggestion:** Return `deps` from `startup()` so the daemon process can call `await deps.aclose()` during shutdown, or store it in a module-level slot (e.g. `_deps: Deps | None = None`). Phase 023 scope is the factory + wiring; daemon shutdown lifecycle is out of scope. Mark with a `# TODO(phase-NNN): store deps for shutdown` comment and track as tech debt.

---

### [MINOR] `timeout` not configurable — hardcoded in factory
**File:** `src/state_core/http_client.py:94`
**Issue:** `timeout=httpx.Timeout(30.0, connect=10.0)` is baked into `build_shared_client()` with no parameter or env var escape hatch. Provider inference calls (especially streaming) may need a longer read timeout; CI/unit tests benefit from a shorter connect timeout.
**Suggestion:** Add `timeout: httpx.Timeout | None = None` parameter with the current values as the default, so callers (tests, daemon, future MCP server paths) can override. Low priority — the defaults are reasonable for production.

---

### [MINOR] `STATE_CA_BUNDLE` silently overrides `STATE_TLS_VERIFY=false`
**File:** `src/state_core/http_client.py:82-87`
**Issue:** When both `STATE_CA_BUNDLE` and `STATE_TLS_VERIFY=false` are set, the CA bundle wins (correct security-first behaviour), but the override is silent and undocumented. An operator setting `STATE_TLS_VERIFY=false` while a CA bundle is configured will be confused by TLS still being verified.
**Suggestion:** Add a `log.warning("STATE_TLS_VERIFY=false ignored because STATE_CA_BUNDLE is set")` or document the precedence in the docstring.

---

### [STYLE] Test accesses httpx private transport internals
**File:** `tests/test_http_client.py:23-25`
**Issue:** `client._transport._pool._max_connections` etc. are private httpcore attributes. This test will break if httpx changes its internal transport structure (which it has done across minor versions).
**Suggestion:** Either document the fragility with a comment (`# httpx 0.28.x private API — update if httpx transport internals change`) or switch to a black-box assertion that verifies the client was built with the expected limits by checking that a `Limits` object with those values *could* produce the transport (e.g. use `httpx.Limits` comparison). The executor already noted this deviation — tracking it here closes the loop.

---

## Files Reviewed

| File | Finding Count |
|------|--------------|
| `src/state_core/http_client.py` | 2 (1 minor, 1 style) |
| `src/state_core/deps.py` | 0 |
| `src/state_daemon/orchestrator.py` | 1 (major) |
| `tests/test_http_client.py` | 1 (style) |
| `tests/test_deps.py` | 0 |
