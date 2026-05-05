---
phase: 028-cost-accounting-request
status: issues_found
reviewed_at: 2026-05-03
reviewer: gsd:code-review
files_reviewed:
  - src/state_core/providers/cost_accounting.py
  - src/state_core/schema.py
  - tests/test_cost_accounting.py
---

# Code Review — Phase 028: Cost Accounting Request

## Summary

3 issues found (1 MAJOR, 2 MINOR). No CRITICAL issues. The PRV-05 implementation is
structurally sound — correct event emission, re-raise semantics, `None` vs `0.0`
enforcement, and mode isolation. The MAJOR issue is a logic bug in token extraction
that silently produces wrong values when `prompt_tokens` is 0.

---

### [MAJOR] Token extraction uses `or` — treats 0 as falsy
**File:** `src/state_core/providers/cost_accounting.py:166-168`
**Issue:** `getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0)`
— if `prompt_tokens` is `0` (legitimate for a cached-hit call where the prompt is
entirely cache-served), the `or` short-circuits to the Anthropic SDK fallback field
`input_tokens`, producing an incorrect value. Same applies to `output_tokens`
(line 167) and `total_tokens` (line 168 uses `getattr` with default but the comment
says `input_tokens + output_tokens` so the default is reliable here).

```python
# BUG: 0-token prompt falls through to Anthropic SDK alias
input_tokens: int = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0)
```

**Suggestion:** Use `None`-check, not truthiness:
```python
_pt = getattr(usage, "prompt_tokens", None)
input_tokens: int = _pt if _pt is not None else getattr(usage, "input_tokens", 0)

_ct = getattr(usage, "completion_tokens", None)
output_tokens: int = _ct if _ct is not None else getattr(usage, "output_tokens", 0)
```

---

### [MINOR] Error-path response events inflate `call_count` and set `has_unknown_cost`
**File:** `src/state_core/providers/cost_accounting.py:244-280`
**Issue:** `aggregate_provider_costs()` includes error response events (those with
`error != None`) in the per-scope rollup. A failed call increments `call_count` by 1
and sets `has_unknown_cost=True` (since `cost_usd=None` on error). Neither behavior
is documented, and callers have no way to distinguish successful calls from errors
in the rollup.
**Suggestion:** Either (a) add an `error_count` field to the rollup dict, or (b)
filter out error events in the aggregation and document the choice. The docstring
currently says nothing about error events:
```python
# In the rollup loop, skip or count separately:
if data.get("error") is not None:
    entry["error_count"] = entry.get("error_count", 0) + 1
    continue  # exclude errors from cost/token totals
```

---

### [MINOR] `scope_type` is unvalidated `str` — typos persist silently to SQLite
**File:** `src/state_core/schema.py:389, 408`
**Issue:** `ProviderRequestData.scope_type` and `ProviderResponseData.scope_type` are
typed as plain `str`. Valid values are `'step' | 'slice' | 'phase' | 'arc'`, but
nothing enforces this — a caller passing `scope_type="phaze"` will happily write a
malformed event. `aggregate_provider_costs(scope_type="step")` will then silently
miss those events.
**Suggestion:** Introduce a `ScopeType` Literal alongside the other type literals:
```python
ScopeType = Literal["step", "slice", "phase", "arc"]
```
Then update `ProviderRequestData.scope_type: ScopeType` and
`ProviderResponseData.scope_type: ScopeType`. Pydantic's `extra="forbid"` enforces
this at validation time.

---

## Not flagged (acceptable)

- `except Exception: return None` in `compute_cost()` — intentionally broad per
  RESEARCH.md pitfall analysis; litellm raises bare `Exception` for unmapped models.
- `client: Any` in `ProviderCostEmitter.acompletion()` — structural subtyping via
  Protocol would be cleaner but is out of scope for Phase 028.
- `from src.state_core.migrations import migrate` in test file — matches the pattern
  used by `test_database.py` and `test_projector.py`; project-wide convention.
- Double space in module docstring line 13 (`from state_core.*  and stdlib`) — STYLE only.
