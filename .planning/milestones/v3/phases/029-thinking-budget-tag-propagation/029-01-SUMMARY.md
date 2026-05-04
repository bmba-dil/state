---
phase: 029-thinking-budget-tag-propagation
plan: "01"
subsystem: testing
tags: [pytest, pytest-asyncio, pytest-httpx, thinking-budget, anthropic, tdd, wave-0]

# Dependency graph
requires:
  - phase: 025-direct-anthropic-sdk-escape-hatch
    provides: AnthropicClient.create() with thinking param support + HTTPXMock test pattern
  - phase: 027-model-profile-resolver
    provides: ModelProfile enum, ResolvedProfile model, resolve_profile() function
  - phase: 028-cost-accounting-request
    provides: ProviderBadRequestError class
provides:
  - 10 RED test stubs covering PRV-08 end-to-end (thinking_budget module contract)
  - HTTPXMock wire-capture test pattern for thinking budget propagation
  - Mode isolation import guard test
affects: [029-02-thinking-budget-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD Wave 0 RED stubs: tests fail with ImportError until Wave 1 creates the target module"
    - "HTTPXMock wire-capture: intercept at httpx transport layer, not mock at method level"
    - "Mode isolation test: inspect.getsource() to assert no state_build/state_teach imports"

key-files:
  created:
    - tests/test_thinking_budget_propagation.py
  modified: []

key-decisions:
  - "Wire-capture tests use HTTPXMock (transport-layer intercept) not unittest.mock.patch, consistent with test_anthropic_client.py pattern"
  - "FAKE_OAUTH_CRED is an inline module-level constant (not a fixture), following test_anthropic_client.py style"
  - "test_no_mode_silo_import uses inspect.getsource() for reliable source-level assertion without subprocess"

patterns-established:
  - "Wave 0 RED stubs: module-level imports trigger ImportError immediately on collection, not during test run"
  - "Constraint validation tests: construct ResolvedProfile directly with boundary values rather than going through resolve_profile()"

requirements-completed:
  - PRV-08

# Metrics
duration: 8min
completed: 2026-05-04
---

# Phase 029 Plan 01: Thinking Budget Tag Propagation — Wave 0 RED Stubs Summary

**10 RED test stubs for PRV-08 thinking-budget propagation contract: unit constraints, HTTPXMock wire-capture, and mode isolation guard**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-04T12:24:00Z
- **Completed:** 2026-05-04T12:32:43Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_thinking_budget_propagation.py` with exactly 10 named test stubs
- All 10 tests fail with `ModuleNotFoundError: No module named 'state_core.providers.thinking_budget'` (correct RED state)
- Test file is syntactically valid Python (AST parse confirmed)
- Wire-capture tests (7-9) use HTTPXMock pattern inherited from `test_anthropic_client.py`
- Mode isolation test (10) uses `inspect.getsource()` to guard against state_build/state_teach cross-imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Write 10 RED test stubs for thinking_budget propagation (PRV-08)** - `e1c3574` (test)

## Files Created/Modified

- `tests/test_thinking_budget_propagation.py` - 10 RED test stubs for PRV-08 thinking budget propagation contract

## Decisions Made

- Used `inspect.getsource(_thinking_budget_module)` for mode isolation test — reliable source-level check without subprocess overhead, consistent with threat model guidance
- Wire-capture tests use `Deps(http_client=httpx.AsyncClient())` inline (not a fixture) to keep tests self-contained
- Test 5 (`test_budget_ge_max_tokens_raises`) uses `budget == max_tokens` (equals boundary) not `budget > max_tokens`, per the Anthropic API requirement that `budget_tokens < max_tokens` (strictly less than)

## Deviations from Plan

None — plan executed exactly as written. The FAKE_OAUTH_CRED constant uses `access="sk-ant-oat-fake"` (as specified in the plan action block) rather than the longer `"sk-ant-oat-fake-token"` string used in test_anthropic_client.py. This is intentional per plan specification.

## Issues Encountered

None. The worktree branch was initially based on an older commit (80449ee) rather than the target base (d2f0477). This was corrected via `git reset --soft d2f0477316f48125dead1ed20b84974035f1c794` before execution began.

## Next Phase Readiness

- Wave 0 complete: 10 RED stubs establish the contract for `thinking_budget.py`
- Plan 02 (Wave 1) implements `src/state_core/providers/thinking_budget.py` to turn all 10 tests GREEN
- Test names in `tests/test_thinking_budget_propagation.py` are the canonical contract Wave 1 must satisfy

---
*Phase: 029-thinking-budget-tag-propagation*
*Completed: 2026-05-04*
