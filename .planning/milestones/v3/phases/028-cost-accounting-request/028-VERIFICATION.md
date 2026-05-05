---
phase: 028-cost-accounting-request
verified: 2026-05-04T10:15:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 028: Cost Accounting Infrastructure Verification Report

**Phase Goal:** Implement cost accounting infrastructure for provider inference calls — compute_cost(), ProviderCostEmitter, aggregate_provider_costs() — delivering PRV-05.

**Verified:** 2026-05-04T10:15:00Z
**Status:** PASSED
**Re-verification:** Initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | compute_cost('claude-sonnet-4-6', 100, 50) returns a positive float | ✓ VERIFIED | Test: test_compute_cost_known_model PASSED |
| 2 | compute_cost('not/a-real-model', 100, 50) returns None (never 0.0) | ✓ VERIFIED | Test: test_compute_cost_unknown_model_returns_none PASSED; semantic verified via exec |
| 3 | ProviderCostEmitter.acompletion() emits state.provider.request before the call | ✓ VERIFIED | Test: test_emitter_emits_request_event PASSED; await store.append() called before client.acompletion() |
| 4 | ProviderCostEmitter.acompletion() emits state.provider.response after the call with token counts | ✓ VERIFIED | Test: test_emitter_emits_response_event PASSED; test_response_event_has_token_and_cost_fields PASSED |
| 5 | Request and response events share the same request_id ULID (correlation key) | ✓ VERIFIED | Test: test_request_response_share_request_id PASSED; ULID generated once per acompletion() call |
| 6 | ProviderCostEmitter re-raises the original exception after emitting error response event | ✓ VERIFIED | Test: test_emitter_reraises_on_provider_error PASSED; bare `raise` preserves traceback at line 156 |
| 7 | aggregate_provider_costs() returns per-scope rollup with call_count, total_tokens, total_cost_usd | ✓ VERIFIED | Test: test_aggregate_single_scope PASSED; test_aggregate_multiple_calls_same_scope PASSED |
| 8 | aggregate_provider_costs(scope_type='step') excludes non-step scope entries | ✓ VERIFIED | Test: test_aggregate_scope_type_filter PASSED; scope_type parameter filters at lines 254-255 |
| 9 | has_unknown_cost=True in rollup when any response event has cost_usd=None | ✓ VERIFIED | Test: test_aggregate_has_unknown_cost_flag PASSED; flag logic at lines 277-278 |
| 10 | state_core.providers.cost_accounting does NOT import state_build.* or state_teach.* | ✓ VERIFIED | Test: test_no_mode_silo_import PASSED; grep confirms zero matches |
| 11 | All 15 tests pass GREEN; full suite >= 865 passing | ✓ VERIFIED | 15/15 tests pass; full suite 865 passed (>= 850 baseline + 15 net-new) |

**Score:** 11/11 must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/state_core/providers/cost_accounting.py` | compute_cost(), ProviderCostEmitter, aggregate_provider_costs() — 220+ lines | ✓ VERIFIED | File exists, 283 lines; all three public symbols implemented and tested |
| `src/state_core/schema.py` extended | "provider" in AggregateType (10th member), PROVIDER_EVENT_TYPES, ProviderRequestData, ProviderResponseData | ✓ VERIFIED | AggregateType has 10 members including "provider"; ProviderRequestData and ProviderResponseData properly defined with frozen=True, extra="forbid" |
| `tests/test_cost_accounting.py` | 15 test functions covering all PRV-05 behaviors | ✓ VERIFIED | All 15 tests present and GREEN; test names match specification exactly |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| compute_cost() | litellm.completion_cost() | ModelResponse mock at lines 47-54 | ✓ WIRED | Mock object constructed with proper Usage, passed to litellm.completion_cost(), returns float \| None |
| ProviderCostEmitter.acompletion() | SqliteEventStore.append() | await self._store.append() at lines 120-131 (request), 176-194 (response) | ✓ WIRED | Request event emitted before client call; response event emitted after; both use same request_id ULID |
| ProviderCostEmitter | ProviderRequestData / ProviderResponseData | model_dump() at lines 129, 153, 192 | ✓ WIRED | Data models instantiated with correct fields, serialized to dict for append() |
| aggregate_provider_costs() | store.read_events() | await store.read_events() at line 243 | ✓ WIRED | Response events filtered from all events at line 244-246; rollup aggregation complete at lines 250-282 |
| cost_accounting module | schema.py imports | From at lines 28-29 | ✓ WIRED | Mode, ProviderRequestData, ProviderResponseData imported and used throughout |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRV-05 | 028-01, 028-02 | Cost accounting per request, aggregated per Step / Slice / Phase / Arc in SQLite | ✓ SATISFIED | compute_cost() computes per-request cost; ProviderCostEmitter emits to SqliteEventStore; aggregate_provider_costs() groups by scope_type:scope_id |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| N/A | N/A | No TODOs/FIXMEs detected | — | — |
| N/A | N/A | No empty implementations (return {}, return [], return null stubs) | — | — |
| src/state_core/providers/cost_accounting.py | 56 | `return None` in compute_cost() | ℹ️ INFO | Intentional sentinel value for unmapped models; never 0.0 (ambiguity prevention) |

### Quality Findings

No duplication detected in Phase 028 files.
No orphaned exports detected.
No missing test files: `src/state_core/providers/cost_accounting.py` is tested by `tests/test_cost_accounting.py`.

**Step 7b: 0 WARN findings, 0 INFO findings**

### Human Verification Required

None required — all observable behaviors verified programmatically.

### Gaps Summary

No gaps detected. All must-haves verified:
- Phase 028 Plan 01 delivered: schema.py extended with "provider" aggregate type and ProviderRequestData/ProviderResponseData models
- Phase 028 Plan 02 delivered: cost_accounting.py fully implements compute_cost(), ProviderCostEmitter, aggregate_provider_costs()
- All 15 tests pass GREEN
- PRV-05 complete: cost accounting infrastructure for provider inference calls delivered
- Mode isolation verified: no state_build.* or state_teach.* imports
- Full suite unaffected: 865 tests passing (baseline 850 + 15 net-new)

---

## Test Execution Summary

**Test Suite Results:**

```
tests/test_cost_accounting.py::test_compute_cost_known_model PASSED
tests/test_cost_accounting.py::test_compute_cost_unknown_model_returns_none PASSED
tests/test_cost_accounting.py::test_emitter_emits_request_event PASSED
tests/test_cost_accounting.py::test_emitter_emits_response_event PASSED
tests/test_cost_accounting.py::test_response_event_has_token_and_cost_fields PASSED
tests/test_cost_accounting.py::test_response_event_cost_none_for_unmapped_model PASSED
tests/test_cost_accounting.py::test_emitter_reraises_on_provider_error PASSED
tests/test_cost_accounting.py::test_request_response_share_request_id PASSED
tests/test_cost_accounting.py::test_aggregate_single_scope PASSED
tests/test_cost_accounting.py::test_aggregate_multiple_calls_same_scope PASSED
tests/test_cost_accounting.py::test_aggregate_multiple_scopes PASSED
tests/test_cost_accounting.py::test_aggregate_scope_type_filter PASSED
tests/test_cost_accounting.py::test_aggregate_has_unknown_cost_flag PASSED
tests/test_cost_accounting.py::test_provider_aggregate_type_in_schema PASSED
tests/test_cost_accounting.py::test_no_mode_silo_import PASSED

15 passed in 0.88s
Full suite: 865 passed, 2 deselected in 52.14s
```

## Implementation Highlights

### 1. Cost Computation (compute_cost)

- Wraps `litellm.completion_cost()` with a mock `ModelResponse` object
- Returns `float | None` — never `0.0` for unmapped models (ambiguity prevention per THREAT-028-1)
- Bare `except Exception` catches litellm's bare Exception for unmapped models (not a litellm subclass)
- Used by both litellm and Anthropic SDK paths via unified interface

### 2. Event Emission (ProviderCostEmitter)

- `acompletion()` method wraps any client's async inference call
- Emits `state.provider.request` BEFORE the call (awaited)
- Emits `state.provider.response` AFTER the call (awaited)
- On error: emits error response event with `error` field set, then **bare `raise`** preserves original traceback (THREAT-028-3)
- Request/response events correlated via ULID request_id
- Uses `time.monotonic()` for latency measurement (clock-drift safe, not `time.time()`)
- Accesses cache token counts as PrivateAttr: `usage._cache_read_input_tokens`, `usage._cache_creation_input_tokens`

### 3. Aggregation (aggregate_provider_costs)

- Single-pass in-memory rollup of `state.provider.response` events
- Groups by `scope_type:scope_id` key
- Per-scope fields: `call_count`, `total_input_tokens`, `total_output_tokens`, `total_tokens`, `total_cost_usd`, `has_unknown_cost`
- `has_unknown_cost=True` flag set when any call has `cost_usd=None` (prevents silent undercounting)
- Optional `scope_type` parameter filters results (e.g., `scope_type="step"` returns only step-scoped entries)

### 4. Schema Integration

- **AggregateType:** "provider" added as 10th member with comment
- **PROVIDER_EVENT_TYPES:** Literal with "state.provider.request" and "state.provider.response"
- **ProviderRequestData:** model, scope_type, scope_id, request_id, prompt_tokens_estimate (optional)
- **ProviderResponseData:** model, scope_type, scope_id, request_id, input_tokens, output_tokens, total_tokens, cost_usd (None for unmapped), latency_ms, cache_read_tokens, cache_creation_tokens, error (on failures)
- All models use Pydantic's `extra="forbid", frozen=True` for strictness

### 5. Mode Isolation

- Verified: no `state_build.*` or `state_teach.*` imports anywhere in cost_accounting.py
- Module imports only from: `litellm`, `litellm.types.utils`, `state_core.*`, `ulid`, `time`, `structlog`
- Enforced by test_no_mode_silo_import using inspect.getsource() (THREAT-028-2)

## Deviations from Plan

None. Both plans executed as specified:

- **Plan 01:** Schema extended with provider aggregate type + 2 data models + 1 event type Literal + 15 RED test stubs
- **Plan 02:** cost_accounting.py fully implemented; all 15 tests turned GREEN

Auto-fixed deviations from Plan 01 / Plan 02 execution (documented in SUMMARYs) were infrastructure/setup only, not source code changes.

---

_Verified: 2026-05-04T10:15:00Z_
_Verifier: Claude (gsd-verifier)_
_Phase: 028-cost-accounting-request_
_Goal: Cost accounting infrastructure for provider inference calls — PRV-05_
_Result: PASSED — all must-haves verified, no gaps_
