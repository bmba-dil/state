---
phase: 028-cost-accounting-request
plan: "02"
subsystem: providers
tags: [litellm, cost-accounting, event-store, tdd, wave-1, pydantic, ulid]

# Dependency graph
requires:
  - phase: 028-01
    provides: ProviderRequestData/ProviderResponseData schema models + 15 RED test stubs

provides:
  - compute_cost(model, input_tokens, output_tokens) -> float | None
  - ProviderCostEmitter.acompletion() emitting state.provider.request + state.provider.response events
  - aggregate_provider_costs(store, scope_type=None) -> dict[str, dict]
  - 15 tests GREEN (all PRV-05 behaviors verified)

affects:
  - 031-provider-parity-matrix-tests (uses ProviderCostEmitter for per-matrix-cell accounting)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "compute_cost() wraps litellm.completion_cost() with mock ModelResponse — unified cost path for both litellm and Anthropic SDK"
    - "ProviderCostEmitter: emit request event -> call client.acompletion() -> emit response event; bare raise preserves traceback"
    - "aggregate_provider_costs(): single-pass in-memory rollup over state.provider.response events from read_events()"
    - "time.monotonic() for latency measurement (not time.time() — clock-drift safe)"
    - "cost_usd=None sentinel (never 0.0) for unmapped models — preserved through event store to aggregator"

key-files:
  created:
    - src/state_core/providers/cost_accounting.py
  modified:
    - tests/test_cost_accounting.py

key-decisions:
  - "compute_cost() uses bare except Exception: return None — litellm raises bare Exception (not a subclass) for unmapped models"
  - "ProviderCostEmitter accesses cache tokens as PrivateAttr directly: usage._cache_read_input_tokens, usage._cache_creation_input_tokens"
  - "aggregate_provider_costs() uses has_unknown_cost=True when any call has cost_usd=None — partial sum (undercounting) rather than error"
  - "test file updated from pytest.fail() stubs to real assertions using tmp_path+monkeypatch+migrate() fixture pattern from test_events.py"

patterns-established:
  - "Wave 0 RED stubs replaced with fixture-based async tests using _isolate_db + store fixtures"
  - "ProviderCostEmitter test pattern: mock client with AsyncMock, read_events() after call, assert event fields"

requirements-completed:
  - PRV-05

# Metrics
duration: 25min
completed: 2026-05-04
---

# Phase 028 Plan 02: Cost Accounting Wave 1 Summary

**ProviderCostEmitter + compute_cost() + aggregate_provider_costs() implement PRV-05 cost accounting — all 15 tests GREEN, full suite 865 passing**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-04T04:00:00Z
- **Completed:** 2026-05-04T04:26:02Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Created `src/state_core/providers/cost_accounting.py` (220 lines) implementing:
  - `compute_cost()`: wraps `litellm.completion_cost()` with a mock `ModelResponse`, returns `None` (never `0.0`) for unmapped models using bare `except Exception`
  - `ProviderCostEmitter`: wraps any `client.acompletion()`, emits `state.provider.request` before the call and `state.provider.response` after, re-raises on error after emitting error event, uses `time.monotonic()` for latency
  - `aggregate_provider_costs()`: single-pass in-memory rollup of `state.provider.response` events, supports `scope_type` filter, tracks `has_unknown_cost` flag
- Updated `tests/test_cost_accounting.py`: replaced 13 `pytest.fail("RED: ...")` stubs with real assertions using the `_isolate_db` + `store` fixture pattern from `test_events.py`
- All 15 tests GREEN; full suite 865 passed (baseline was 850 + 15 net-new = 865)
- Mode isolation confirmed: no `state_build.*` or `state_teach.*` imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement cost_accounting.py (compute_cost, ProviderCostEmitter, aggregate_provider_costs)** - `3a79e2a` (feat)

## Files Created/Modified

- `src/state_core/providers/cost_accounting.py` — Full implementation: compute_cost(), ProviderCostEmitter, aggregate_provider_costs() (220 lines, new file)
- `tests/test_cost_accounting.py` — Updated from RED stubs to GREEN assertions with proper fixture infrastructure

## Decisions Made

- **Bare `except Exception` in compute_cost()**: litellm raises a bare `Exception` (not a litellm subclass) for "model not in cost map" cases (e.g. `gemini/gemini-1.5-pro`). The except must be broad enough to catch these.
- **PrivateAttr cache token access**: `usage._cache_read_input_tokens` and `usage._cache_creation_input_tokens` are litellm `PrivateAttr` fields — they do NOT appear in `model_dump()`. Must be accessed directly as instance attributes.
- **Test fixture pattern**: Tests use the `_isolate_db` autouse fixture (sets `STATE_DB_PATH` env var to tmp_path) + `store` async fixture calling `migrate()`. This matches the established pattern in `test_events.py`.
- **Module docstring scrubbed**: Original docstring mentioned "state_build" and "state_teach" in a prohibition comment — `test_no_mode_silo_import` uses `inspect.getsource()` which includes docstrings, so those strings were replaced with neutral phrasing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Worktree branch base reset required**
- **Found during:** Pre-task setup
- **Issue:** Worktree HEAD was at `80449eec` (an older base) instead of `172f5be3` (target base with 028-01 schema and test stubs). Required `git reset --soft 172f5be3` + `git checkout HEAD -- src/ tests/` to restore working tree.
- **Fix:** Reset branch to correct base and restored source files.
- **Impact:** No scope creep; setup only.

**2. [Rule 1 - Bug] Module docstring contained "state_build" string**
- **Found during:** Test run for test_no_mode_silo_import
- **Issue:** The docstring "It MUST NOT import state_build.* or state_teach.*" caused `inspect.getsource()` to find "state_build" in the source, triggering the mode isolation assertion.
- **Fix:** Replaced with neutral phrasing "No build-mode or teach-mode packages are imported here."
- **Files modified:** `src/state_core/providers/cost_accounting.py`

**3. [Rule 2 - Missing critical functionality] Test stubs needed fixture infrastructure**
- **Found during:** Task 1 test run
- **Issue:** The original `tests/test_cost_accounting.py` Wave 0 stubs used `pytest.fail()` without test infrastructure. Real assertions require `_isolate_db`/`store` fixtures per the `test_events.py` pattern.
- **Fix:** Rewrote test file with complete fixture infrastructure before committing.
- **Files modified:** `tests/test_cost_accounting.py`

## Issues Encountered

- Worktree's `.state/migrations/` was missing `0001_init.sql`, `0002_cache.sql`, `0003_add_mode_column.sql` — copied from main project and ran migrations before tests.
- `uv run python3 -m pytest` initially failed with "No module named pytest" until `uv sync --all-extras` was run to install dev dependencies.

## Self-Check: PASSED

- `src/state_core/providers/cost_accounting.py` exists and is importable
- `uv run python3 -c "from state_core.providers.cost_accounting import compute_cost, ProviderCostEmitter, aggregate_provider_costs; print('OK')"` exits 0
- All 15 tests GREEN: `uv run python3 -m pytest tests/test_cost_accounting.py -v` shows 15 passed, 0 failed
- Full suite: 865 passed (>= 865 requirement met)
- Mode isolation: `grep -n "state_build\|state_teach" src/state_core/providers/cost_accounting.py` returns no matches
- compute_cost returns None for unknown: confirmed
- Task commit `3a79e2a` exists

## PRV-05 Verification

```
compute_cost("claude-sonnet-4-6", 100, 50) = positive float ✓
compute_cost("not/a-real-model", 100, 50) = None ✓
ProviderCostEmitter emits request before call ✓
ProviderCostEmitter emits response after call with input_tokens, output_tokens, cost_usd ✓
request_id shared between request and response events ✓
ProviderCostEmitter re-raises on provider error ✓
aggregate_provider_costs() groups by scope_type:scope_id ✓
aggregate_provider_costs(scope_type="step") filters correctly ✓
has_unknown_cost=True when any cost_usd=None ✓
No state_build.* or state_teach.* imports ✓
```

---
*Phase: 028-cost-accounting-request*
*Completed: 2026-05-04*
