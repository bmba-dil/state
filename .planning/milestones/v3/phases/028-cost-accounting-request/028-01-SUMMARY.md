---
phase: 028-cost-accounting-request
plan: "01"
subsystem: providers
tags: [pydantic, schema, cost-accounting, event-store, tdd, wave-0]

# Dependency graph
requires:
  - phase: 027-model-profile-resolver
    provides: model_profile.py and hooks.py — same provider package; schema.py already present

provides:
  - "provider" added to AggregateType Literal in schema.py (10th member)
  - PROVIDER_EVENT_TYPES Literal (state.provider.request, state.provider.response)
  - ProviderRequestData Pydantic model (pre-call event payload, extra="forbid", frozen=True)
  - ProviderResponseData Pydantic model (post-call event payload, cost_usd=None semantics)
  - 15 RED test stubs in tests/test_cost_accounting.py covering all PRV-05 behaviors

affects:
  - 028-02 (Wave 1 GREEN — implements cost_accounting.py against these stubs)
  - 031-provider-parity-matrix-tests (uses ProviderCostEmitter for per-matrix-cell accounting)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cost_usd=None (never 0.0) sentinel for unknown/unmapped models — ambiguity prevention"
    - "Wave 0 RED stubs with module-level import error as acceptable RED state"
    - "test_no_mode_silo_import pattern using inspect.getsource() for import-graph verification"

key-files:
  created:
    - tests/test_cost_accounting.py
  modified:
    - src/state_core/schema.py

key-decisions:
  - "cost_usd=None (not 0.0) for unmapped models — 0.0 is ambiguous with genuinely free-tier calls"
  - "Module-level import in test file causes ImportError (not individual pytest.fail) — acceptable as RED state per Wave 0 contract"
  - "test_provider_aggregate_type_in_schema and test_no_mode_silo_import are real assertions not pytest.fail stubs — they provide immediate feedback on correctness"

patterns-established:
  - "PRV-05 test contract: 15 stubs covering compute_cost, ProviderCostEmitter, aggregate_provider_costs"
  - "ProviderRequestData/ProviderResponseData Pydantic models use same extra=forbid/frozen=True convention as AuthImportedData"

requirements-completed:
  - PRV-05

# Metrics
duration: 16min
completed: 2026-05-04
---

# Phase 028 Plan 01: Cost Accounting Wave 0 Summary

**schema.py extended with ProviderRequestData/ProviderResponseData/PROVIDER_EVENT_TYPES and 15 RED test stubs establish the complete PRV-05 test contract for Wave 1**

## Performance

- **Duration:** 16 min
- **Started:** 2026-05-04T03:40:58Z
- **Completed:** 2026-05-04T03:57:46Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `schema.py` with `"provider"` as the 10th `AggregateType` member, `PROVIDER_EVENT_TYPES` Literal, and `ProviderRequestData` / `ProviderResponseData` Pydantic models — all using the project-standard `extra="forbid", frozen=True` convention
- Created `tests/test_cost_accounting.py` with 15 test stubs covering all PRV-05 behavioral requirements (compute_cost, ProviderCostEmitter, aggregate_provider_costs)
- Security tests T-028-1 (cost_usd=None for unmapped models), T-028-2 (mode isolation), T-028-3 (re-raise after error event) wired as real assertions / pytest.fail stubs
- Baseline 850 tests unaffected by schema additions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend schema.py with provider event types and data models** - `d3278ff` (feat)
2. **Task 2: Write 15 RED test stubs for cost_accounting module** - `4f55579` (test)

## Files Created/Modified

- `src/state_core/schema.py` — Added "provider" to AggregateType, PROVIDER_EVENT_TYPES Literal, ProviderRequestData and ProviderResponseData Pydantic models (55 lines added)
- `tests/test_cost_accounting.py` — 15 RED test stubs (126 lines, new file)

## Decisions Made

- **cost_usd=None not 0.0 for unmapped models**: Conflating "no cost data" with "zero cost" is a silent data corruption. The test contract (test_compute_cost_unknown_model_returns_none, test_aggregate_has_unknown_cost_flag) enforces this distinction throughout Wave 1 implementation.
- **Module-level import causes ImportError (not per-test ImportError)**: Intentional — the entire test file goes ERROR until Wave 1 creates cost_accounting.py. This is cleaner than wrapping each test in a try/except import guard.
- **test_provider_aggregate_type_in_schema is a real assertion**: Does not use pytest.fail() since AggregateType was extended in the same plan (Task 1). Goes GREEN immediately after Task 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree .state/migrations missing first 3 SQL files**
- **Found during:** Pre-task baseline verification
- **Issue:** Worktree's `.state/migrations/` was missing `0001_init.sql`, `0002_cache.sql`, `0003_add_mode_column.sql`, causing `test_tail_empty_store_with_no_follow` and others to fail with "no such table: events"
- **Fix:** Copied the 3 missing migration files from main project; migrated `.state/events.sqlite`
- **Files modified:** `.state/migrations/0001_init.sql`, `0002_cache.sql`, `0003_add_mode_column.sql` (copied, not tracked)
- **Verification:** Baseline restored to 850 passed before any task changes
- **Committed in:** Not committed (infrastructure setup, not source change)

---

**Total deviations:** 1 auto-fixed (1 blocking — worktree infrastructure setup)
**Impact on plan:** Baseline restoration was required before task execution; no scope creep.

## Issues Encountered

- Worktree branch was created from an older commit than `c0b7e4f` (target base). Required `git reset --soft c0b7e4fbcc9a0a8b3daccc205db50f0f2b1b72f1` followed by `git checkout HEAD -- src/ tests/` to restore the working tree.
- Worktree `.state/events.sqlite` was empty (no tables), causing test failures until migrations ran.

## Self-Check: PASSED

- `src/state_core/schema.py` contains "provider" in AggregateType, ProviderRequestData, ProviderResponseData, PROVIDER_EVENT_TYPES
- `tests/test_cost_accounting.py` exists with 15 test functions (confirmed with grep -c)
- Task 1 commit `d3278ff` exists
- Task 2 commit `4f55579` exists
- `uv run python3 -c "from state_core.schema import AggregateType, ProviderRequestData, ProviderResponseData, PROVIDER_EVENT_TYPES; assert 'provider' in AggregateType.__args__; print('schema OK')"` exits 0
- Baseline 850 tests pass excluding test_cost_accounting.py

## Next Phase Readiness

- Wave 1 (Plan 02) has a complete test contract: 15 stubs to turn GREEN
- `src/state_core/providers/cost_accounting.py` must implement: `compute_cost()`, `ProviderCostEmitter.acompletion()`, `aggregate_provider_costs()`
- Schema symbols (ProviderRequestData, ProviderResponseData, PROVIDER_EVENT_TYPES) are ready for import in cost_accounting.py

---
*Phase: 028-cost-accounting-request*
*Completed: 2026-05-04*
