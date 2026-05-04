---
phase: 024-litellm-wrapper
plan: "01"
subsystem: testing
tags: [litellm, pytest, hypothesis, tdd, provider-routing]

# Dependency graph
requires:
  - phase: 023-shared-httpx-asyncclient-connection-pool
    provides: shared httpx.AsyncClient and Deps container that LitellmClient will accept
provides:
  - 11 RED test stubs defining the LitellmClient API contract (import, methods, error hierarchy, streaming)
affects:
  - 024-litellm-wrapper (plan 02 GREEN implementation)
  - 025-direct-anthropic-sdk-escape-hatch

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level import at top of test file causes unconditional ImportError at collection time (RED guarantee)"
    - "pytest.fail('RED stub') in each body ensures explicit failure if import somehow resolves"
    - "Hypothesis @given(st.sampled_from(...)) with litellm.exceptions classes for property-based error taxonomy"

key-files:
  created:
    - tests/test_litellm_client.py
  modified: []

key-decisions:
  - "Use BadGatewayError (not NotFoundError) in the _LITELLM_EXCEPTION_CLASSES list to match the exception class plan specified in 024-01-PLAN.md exactly"
  - "Hypothesis test is async def (asyncio_mode=auto handles it); no @pytest.mark.asyncio needed per project pattern"

patterns-established:
  - "Wave 0 RED stubs: module-level import of non-existent module causes collection-time ImportError — no pytest.skip, no conditional guards"

requirements-completed:
  - PRV-01
  - PRV-07

# Metrics
duration: 8min
completed: 2026-05-03
---

# Phase 024 Plan 01: LitellmClient RED Test Stubs

**11-stub test file defining LitellmClient's full API contract — acompletion, error taxonomy mapping, streaming normalization, and mode-silo import isolation — all failing RED at collection via ImportError on state_core.providers.litellm_client**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-03T00:00:00Z
- **Completed:** 2026-05-03T00:08:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_litellm_client.py` with exactly 11 test stubs (10 async + 1 sync) matching 024-VALIDATION.md test ID map
- All stubs fail at pytest collection with `ModuleNotFoundError: No module named 'state_core.providers.litellm_client'` — unconditional RED
- Hypothesis property test enumerates 10 litellm exception classes (`lexc.BadGatewayError` over `lexc.NotFoundError` per plan spec)
- Zero `pytest.skip` calls; zero conditional imports; module-level import guarantees failure before any test body runs
- Existing 411-test suite unaffected (pre-existing `test_cli.py` sqlite failure unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test stubs for LitellmClient** - `5d1e346` (test)

## Files Created/Modified

- `tests/test_litellm_client.py` - 11 RED stubs defining LitellmClient contract: acompletion, streaming (astream), error taxonomy (StateProviderError hierarchy), shared-client lifecycle (no aclose), mode-silo isolation

## Decisions Made

- Used `lexc.BadGatewayError` as the 10th exception class in `_LITELLM_EXCEPTION_CLASSES` to match the list in 024-01-PLAN.md exactly (the RESEARCH.md example used `NotFoundError` but the plan's `<action>` block specified `BadGatewayError`)
- `test_no_mode_silo_import` is `def` (synchronous) because it only inspects the import graph — no async needed; matches plan's explicit annotation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- `tests/test_litellm_client.py` is complete; Wave 1 executor (plan 02) creates `src/state_core/providers/litellm_client.py` to make all 11 stubs go GREEN
- No blockers; all test names match 024-VALIDATION.md identifiers exactly

---
*Phase: 024-litellm-wrapper*
*Completed: 2026-05-03*
