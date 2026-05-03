---
phase: 023-shared-httpx-asyncclient-connection-pool
plan: 01
subsystem: testing
tags: [httpx, pytest, tdd, red-phase, deps-container, connection-pool]

# Dependency graph
requires: []
provides:
  - "RED test stubs for build_shared_client() API contract (5 tests, tests/test_http_client.py)"
  - "RED test stubs for Deps container and startup wiring (4 tests, tests/test_deps.py)"
affects:
  - "023-02-PLAN (Wave 1 GREEN — implements state_core.http_client to make stubs pass)"
  - "023-03-PLAN (Wave 1 GREEN — implements state_core.deps to make stubs pass)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED stubs: top-level import from not-yet-existing module causes ModuleNotFoundError — all tests fail at collection time without pytest.skip"
    - "asyncio_mode=auto: async test functions collected without @pytest.mark.asyncio decorator"

key-files:
  created:
    - "tests/test_http_client.py"
    - "tests/test_deps.py"
  modified: []

key-decisions:
  - "keepalive_expiry=30.0 used in test assertions (plan spec) rather than 5.0 (research doc example) — GREEN executor must implement build_shared_client() with keepalive_expiry=30.0"
  - "test_anthropic_client_injection does NOT depend on state_core.deps import path — it uses real anthropic.AsyncAnthropic constructor; this test will pass even before Deps is implemented, once it can collect"

patterns-established:
  - "RED stub pattern: import from non-existent module at top level — all tests in file fail with ModuleNotFoundError at collection time"
  - "Deps container test isolation: test_deps.py uses MagicMock/AsyncMock for http_client, never imports actual http_client module"

requirements-completed:
  - PRV-06

# Metrics
duration: 8min
completed: 2026-05-02
---

# Phase 023 Plan 01: Shared httpx.AsyncClient Connection Pool — Wave 0 RED Stubs

**9 failing RED test stubs (5 for build_shared_client, 4 for Deps container) that define the Phase 023 API contract before any implementation exists**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-02T23:26:00Z
- **Completed:** 2026-05-02T23:34:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `tests/test_http_client.py` with 5 async RED stubs covering `build_shared_client()` defaults, proxy parameter, TLS skip, `STATE_HTTP_PROXY` env var, and `STATE_CA_BUNDLE` env var
- Created `tests/test_deps.py` with 4 async RED stubs covering `Deps` construction, `aclose()` delegation, `startup()` litellm wiring, and `AsyncAnthropic(http_client=...)` smoke test
- All 9 tests fail at collection time with `ModuleNotFoundError: No module named 'state_core.http_client'` and `No module named 'state_core.deps'` — correct RED behavior
- No pytest.skip calls, no conditional imports — strict TDD RED discipline maintained

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test stubs for build_shared_client()** - `da9e190` (test)
2. **Task 2: Write RED test stubs for Deps container and startup wiring** - `edde0ad` (test)

_Note: This is a Wave 0 TDD plan — both commits are test-only (RED phase)_

## Files Created/Modified
- `tests/test_http_client.py` - 5 RED async stubs for `state_core.http_client.build_shared_client()` API contract
- `tests/test_deps.py` - 4 RED async stubs for `state_core.deps.Deps` container + orchestrator startup wiring

## Decisions Made
- `keepalive_expiry=30.0` used in `test_build_shared_client_defaults` assertion (per plan spec) — Wave 1 GREEN executor must implement `build_shared_client()` with `keepalive_expiry=30.0`, not 5.0 as in research doc examples
- `test_anthropic_client_injection` does not import `state_core.deps` directly; it tests `anthropic.AsyncAnthropic(http_client=httpx.AsyncClient(...))` — this will pass once collection succeeds after Deps module is created
- `test_startup_creates_deps` patches `state_daemon.orchestrator.build_shared_client` and `state_daemon.orchestrator.litellm` — these don't exist in orchestrator yet; test verifies the GREEN executor wires both into startup()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing failures in `tests/test_cli.py::TestTail` and some `tests/test_sync_mirror.py` tests were confirmed to exist on the base commit (80449ee) and are unrelated to this plan's changes. The 411 passing tests (from the base suite excluding pre-existing failures) remain unaffected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Wave 1 GREEN (Plans 02 + 03) can now implement `src/state_core/http_client.py` and `src/state_core/deps.py` to turn all 9 RED stubs GREEN
- The startup orchestrator test (`test_startup_creates_deps`) requires the GREEN executor to also wire `build_shared_client` and `litellm` imports into `state_daemon/orchestrator.py`
- `test_build_shared_client_env_ca` uses an empty PEM — GREEN executor must update this test to either mock `ssl.create_default_context` or use a valid self-signed cert (marked with `# GREEN: update PEM handling` comment)

---
*Phase: 023-shared-httpx-asyncclient-connection-pool*
*Completed: 2026-05-02*
