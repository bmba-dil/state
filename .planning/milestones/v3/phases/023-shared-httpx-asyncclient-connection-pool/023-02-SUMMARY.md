---
phase: 023-shared-httpx-asyncclient-connection-pool
plan: 02
subsystem: state_core/state_daemon
tags: [httpx, connection-pool, deps-injection, litellm, prv-06, tdd-green]

# Dependency graph
requires:
  - "023-01 (Wave 0 RED stubs for build_shared_client and Deps)"
provides:
  - "src/state_core/http_client.py — build_shared_client() factory (PRV-06)"
  - "src/state_core/deps.py — Deps Pydantic container with async aclose()"
  - "src/state_daemon/orchestrator.py — startup() wires shared client to litellm.aclient_session"
affects:
  - "Phase 025 — direct Anthropic SDK escape hatch (AsyncAnthropic(http_client=deps.http_client))"
  - "All provider inference traffic now routes through single shared httpx.AsyncClient"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "build_shared_client() factory: env var resolution (STATE_HTTP_PROXY/STATE_CA_BUNDLE/STATE_TLS_VERIFY) with explicit-arg-wins-over-env priority"
    - "Deps Pydantic BaseModel with ConfigDict(arbitrary_types_allowed=True) for httpx.AsyncClient storage"
    - "litellm.aclient_session module-level import in orchestrator.py enables patch('state_daemon.orchestrator.litellm') in tests"
    - "httpx 0.28.1 Limits accessible via client._transport._pool._max_connections (not client._limits)"

key-files:
  created:
    - "src/state_core/http_client.py"
    - "src/state_core/deps.py"
  modified:
    - "src/state_daemon/orchestrator.py"
    - "tests/test_http_client.py"
    - "tests/test_deps.py"

key-decisions:
  - "httpx 0.28.1 does not expose client._limits — used client._transport._pool._max_connections etc. instead; updated test assertions accordingly"
  - "test_build_shared_client_env_ca: mocked ssl.create_default_context to avoid ssl.SSLError from empty PEM file (as prescribed in plan action block)"
  - "test_startup_creates_deps: used AsyncMock for SqliteEventStore.run_repair_now() and StartupReconciler.start() to avoid TypeError on await — original Wave 0 stub used plain MagicMock"
  - "litellm imported at module level in orchestrator.py (not inside startup()) so patch('state_daemon.orchestrator.litellm') works in tests"

requirements-completed:
  - PRV-06

# Metrics
duration: 15min
completed: 2026-05-03
---

# Phase 023 Plan 02: Shared httpx.AsyncClient Connection Pool — Wave 1 GREEN Implementation

**Single daemon-owned httpx.AsyncClient with connection pooling, proxy/TLS env-var support, and dep-injection via Pydantic Deps container wired into orchestrator startup**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-03T04:20:00Z
- **Completed:** 2026-05-03T04:39:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 new, 3 updated)

## Accomplishments

- Created `src/state_core/http_client.py` with `build_shared_client()` factory:
  - `httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0)`
  - Reads `STATE_HTTP_PROXY`, `STATE_CA_BUNDLE`, `STATE_TLS_VERIFY` env vars (explicit args take priority)
  - `trust_env=True`, `follow_redirects=False`, `Timeout(30.0, connect=10.0)`
- Created `src/state_core/deps.py` with Pydantic `Deps` container:
  - `model_config = ConfigDict(arbitrary_types_allowed=True)` for `httpx.AsyncClient` field
  - `async def aclose()` delegates to `http_client.aclose()`
- Updated `src/state_daemon/orchestrator.py`:
  - `import litellm` at module level (required for test patching)
  - `from state_core.deps import Deps` and `from state_core.http_client import build_shared_client`
  - `startup()` creates `Deps(http_client=build_shared_client())` after `assert_redactor_attached()`
  - Assigns `litellm.aclient_session = deps.http_client` (best-effort for non-Anthropic providers)
- All 9 Phase 023 tests pass GREEN (5 `test_http_client.py` + 4 `test_deps.py`)
- Auth providers (`state_core.auth.providers.*`) and `sync_mirror.py` untouched
- No regressions: pre-existing failures (23) remain; new tests add 1 net passing test

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement src/state_core/http_client.py** - `e36831d` (feat)
2. **Task 2: Implement src/state_core/deps.py and wire into orchestrator.py** - `814323d` (feat)

## Files Created/Modified

- `src/state_core/http_client.py` — `build_shared_client()` factory (PRV-06 implementation)
- `src/state_core/deps.py` — `Deps(BaseModel)` container with `aclose()`
- `src/state_daemon/orchestrator.py` — litellm, Deps, build_shared_client wired into startup()
- `tests/test_http_client.py` — updated `_limits` access and mocked `ssl.create_default_context`
- `tests/test_deps.py` — updated `test_startup_creates_deps` with proper `AsyncMock` for async methods

## Decisions Made

- **httpx 0.28.1 _limits attribute absent**: The `AsyncClient` object does not expose `_limits` in httpx 0.28.1. Limits are accessible via `client._transport._pool._max_connections` etc. Updated test assertions to use the correct access path.
- **test_startup_creates_deps AsyncMock fix**: The Wave 0 stub patched `SqliteEventStore` and `StartupReconciler` with plain `MagicMock`, but `startup()` awaits `store.run_repair_now()` and `reconciler.start()`. Updated to use `AsyncMock` for these methods.
- **litellm module-level import**: Required at module level (not inside `startup()` body) so `patch("state_daemon.orchestrator.litellm")` works for test isolation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed httpx 0.28.1 _limits attribute access in test**
- **Found during:** Task 1 test run
- **Issue:** `test_build_shared_client_defaults` accessed `client._limits` which doesn't exist in httpx 0.28.1; raises `AttributeError`
- **Fix:** Updated assertion to `client._transport._pool._max_connections` / `_max_keepalive_connections` / `_keepalive_expiry`
- **Files modified:** `tests/test_http_client.py`
- **Commit:** `e36831d`

**2. [Rule 1 - Bug] Fixed test_startup_creates_deps AsyncMock for async methods**
- **Found during:** Task 2 test run
- **Issue:** Wave 0 stub patched `SqliteEventStore` with plain `MagicMock`; `await store.run_repair_now()` raised `TypeError: object MagicMock can't be used in 'await' expression`
- **Fix:** Created `mock_store` with `run_repair_now = AsyncMock(return_value=[])` and `mock_reconciler` with `start = AsyncMock(return_value=None)`
- **Files modified:** `tests/test_deps.py`
- **Commit:** `814323d`

Both fixes were anticipated in the plan action block (which noted the CA bundle test would need updating and that the executor may need to fix the startup test).

## Issues Encountered

Pre-existing test failures (23) exist on the base commit (confirmed via stash + re-run) and are unrelated to Phase 023 changes. These include `tests/test_cli.py::TestTail::test_tail_empty_store_with_no_follow` and several `tests/test_sync_mirror.py` errors. Phase 023 Wave 1 leaves these untouched.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Wave 1 complete: all 9 Phase 023 tests GREEN, PRV-06 satisfied
- Phase 025 (direct Anthropic SDK escape hatch) can now inject `deps.http_client` via `AsyncAnthropic(http_client=deps.http_client)` — the `test_anthropic_client_injection` smoke test already passes
- `litellm.aclient_session` is set in `startup()` for non-Anthropic provider traffic

---
*Phase: 023-shared-httpx-asyncclient-connection-pool*
*Completed: 2026-05-03*
