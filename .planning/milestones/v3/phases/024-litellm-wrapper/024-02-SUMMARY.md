---
phase: 024-litellm-wrapper
plan: "02"
subsystem: provider-routing
tags: [litellm, pytest, hypothesis, tdd, provider-routing, streaming, error-hierarchy]

# Dependency graph
requires:
  - phase: 023-shared-httpx-asyncclient-connection-pool
    provides: shared httpx.AsyncClient and Deps container; litellm.aclient_session set in orchestrator.startup()
  - phase: 024-01
    provides: 11 RED test stubs defining LitellmClient API contract
provides:
  - src/state_core/providers/litellm_client.py — LitellmClient with acompletion() + astream(); StateProviderError hierarchy
  - All 11 Phase 024 tests GREEN (PRV-01 + PRV-07 satisfied)
affects:
  - 025-direct-anthropic-sdk-escape-hatch (shares StateProviderError hierarchy)
  - 026-provider-router (routes non-Anthropic traffic through LitellmClient)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level import litellm at top of litellm_client.py — stable patch target for tests"
    - "Patch state_core.providers.litellm_client.litellm (whole module) not litellm.acompletion directly (litellm lazy __getattr__)"
    - "PermissionDeniedError requires httpx.Response positional arg — use _make_exc() helper in tests"
    - "async for chunk in response (never sync for) — CustomStreamWrapper has both __iter__ and __aiter__"
    - "astream() is async def generator — has yield inside async def; AsyncGenerator return annotation correct"
    - "Never call aclose() on shared httpx client — lifecycle owned by Deps/orchestrator"

key-files:
  created:
    - src/state_core/providers/litellm_client.py
  modified:
    - tests/test_litellm_client.py

key-decisions:
  - "StateProviderError hierarchy defined in litellm_client.py (not separate errors.py) — TODO(phase-025) comment for future extraction"
  - "LitellmClient is a plain class (not Pydantic BaseModel) — no constructor args needed; aclient_session set globally by orchestrator"
  - "PermissionDeniedError handled via _make_exc() helper in test — requires httpx.Response positional arg unlike other exception classes"
  - "Exception catch-all in acompletion/astream catches any unmapped litellm exception, wraps in StateProviderError (T-024-3)"

patterns-established:
  - "Wave 1 GREEN: implement the module that satisfies Wave 0 RED stubs; update test bodies in same wave"

requirements-completed:
  - PRV-01
  - PRV-07

# Metrics
duration: 25min
completed: 2026-05-03
---

# Phase 024 Plan 02: LitellmClient GREEN Implementation

**litellm async wrapper for non-Anthropic provider traffic — LitellmClient.acompletion() and astream() with StateProviderError hierarchy, all 11 Wave 0 RED stubs turned GREEN**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-03T06:10:00Z
- **Completed:** 2026-05-03T06:34:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `src/state_core/providers/litellm_client.py` with:
  - Module-level `import litellm` and `import litellm.exceptions as lexc` (stable patch targets)
  - `LitellmClient.acompletion()` — calls `litellm.acompletion`, maps all exception types to state hierarchy
  - `LitellmClient.astream()` — calls `litellm.acompletion(stream=True)`, uses `async for` to yield `ModelResponseStream` chunks unchanged
  - `StateProviderError` base + 4 leaf classes: `ProviderTransientError`, `ProviderAuthError`, `ProviderBadRequestError`, `ProviderResponseError`
  - Never calls `aclose()` on shared httpx client (T-024-2)
  - No `state_build.*` or `state_teach.*` imports (T-024-4)
  - Docstring: OAuth stealth MUST NOT route through this module (T-024-1)
  - `TODO(phase-025)` comment for future `errors.py` extraction
- Updated `tests/test_litellm_client.py`: replaced all 11 `pytest.fail("RED stub")` bodies with real assertions; all 11 pass GREEN
- Full suite: 25 failed / 645 passed — 11 fewer failures than baseline (our 11 tests flipped pass); no regressions introduced

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement src/state_core/providers/litellm_client.py** - `48f9245` (feat)
2. **Task 2: Fill GREEN test bodies and verify all 11 pass** - `509c43b` (feat)

## Files Created/Modified

- `src/state_core/providers/litellm_client.py` — new file, 222 lines; LitellmClient + StateProviderError hierarchy
- `tests/test_litellm_client.py` — updated, +117/-16 lines; all 11 stubs converted to real tests

## Decisions Made

- **StateProviderError in litellm_client.py:** Defined the hierarchy in the same module rather than a separate `errors.py`. Keeps the wave minimal; `TODO(phase-025)` comment documents the planned extraction when Phase 025's direct Anthropic SDK path needs to share the same error types.
- **LitellmClient as plain class:** No Pydantic BaseModel — no constructor args needed. The shared `httpx.AsyncClient` is injected globally into `litellm.aclient_session` by orchestrator.startup(); LitellmClient reads it implicitly on each call.
- **_make_exc() helper in tests:** `PermissionDeniedError.__init__` requires a positional `response: httpx.Response` arg unlike the other 9 exception classes in `_LITELLM_EXCEPTION_CLASSES`. Added `_make_exc()` factory that creates a real `httpx.Response(403)` for this case; all other classes use `(message, llm_provider, model)` positional args.
- **No LiteLLMUnknownProvider in _LITELLM_EXCEPTION_CLASSES:** The test file's Hypothesis list covers the 10 most common exception classes. `LiteLLMUnknownProvider` has a different constructor signature `(model, custom_llm_provider=None)` and is still covered by the `acompletion` implementation's `except` clause — it's just not exercised by the Hypothesis property test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Added _make_exc() helper for PermissionDeniedError constructor**

- **Found during:** Task 2 (implementing Hypothesis test body)
- **Issue:** `PermissionDeniedError.__init__` requires a 4th positional `response: httpx.Response` argument. Using `exc_class("fixture", "openai", "gpt-4o")` as specified in the plan's template raises `TypeError: PermissionDeniedError.__init__() missing 1 required positional argument: 'response'`.
- **Fix:** Added `_make_exc(exc_class)` factory function that handles `PermissionDeniedError` specially (creates an `httpx.Response(403)` with a proper `httpx.Request`), falls through to `(message, llm_provider, model)` positional args for all other classes.
- **Files modified:** `tests/test_litellm_client.py`
- **Commit:** `509c43b`

## Issues Encountered

None.

## Next Phase Readiness

- `src/state_core/providers/litellm_client.py` is complete; Phase 025 (direct Anthropic SDK escape hatch) can import `StateProviderError` and its subclasses from this module until `errors.py` is extracted
- `tests/test_litellm_client.py` is fully GREEN (11/11); no blockers for Phase 025 or 026

---
*Phase: 024-litellm-wrapper*
*Completed: 2026-05-03*
