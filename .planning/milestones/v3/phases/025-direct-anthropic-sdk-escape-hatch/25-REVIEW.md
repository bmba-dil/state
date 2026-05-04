---
phase: 025
status: findings
reviewed: 2026-05-03
---

# Code Review — Phase 025: Direct Anthropic SDK Escape Hatch

## Summary

3 findings (0 CRITICAL, 0 MAJOR, 3 MINOR, 0 STYLE). No blocking issues. The error hierarchy extraction is clean and the OAuth stealth header wiring is correct. Two findings are about mid-stream transient error classification and a silent `_deps` field; both are low risk for this phase but worth fixing before Phase 026 (ProviderRouter) consumes the error types for retry decisions.

---

### [MINOR] Mid-stream connection errors classified as non-retryable
**File:** `src/state_core/providers/anthropic_client.py:233-238`
**Issue:** The `async for event in response` iteration block catches all exceptions as `StateProviderError`. If a connection drops mid-stream (`anthropic.APIConnectionError`), it wraps as `StateProviderError` instead of `ProviderTransientError`. Phase 026 (ProviderRouter) uses exception type for retry decisions — mid-stream transient errors will be treated as permanent failures.
**Suggestion:** Mirror the setup error mapping inside the iteration catch:
```python
        except anthropic.APIConnectionError as e:
            raise ProviderTransientError(f"stream_connection: {e}") from e
        except Exception as e:
            log.warning("anthropic_client.stream_iter_error", error=str(e))
            raise StateProviderError(f"stream_error: {e}") from e
```

---

### [MINOR] `_deps` stored but never accessed after `__init__`
**File:** `src/state_core/providers/anthropic_client.py:55-57`
**Issue:** `self._deps = deps` stores the `Deps` reference, but `_deps` is never read again — the shared `http_client` reference is held indirectly through `self._sdk`. Future readers may assume `_deps` is dead code and remove it (which would be correct — GC won't collect `deps.http_client` if the SDK holds it). Add a brief comment or remove the assignment.
**Suggestion:** If the intent is to keep `Deps` alive for lifecycle reasoning, document it:
```python
self._deps = deps  # kept alive so callers can assert deps.http_client is not closed
```
Otherwise remove it — `self._sdk` already holds the `http_client` reference.

---

### [MINOR] Broad `except Exception` in `stream()` setup swallows programming errors
**File:** `src/state_core/providers/anthropic_client.py:230-231`
**Issue:** After the specific `APIConnectionError` and `BadRequestError` catches, `except Exception as e` wraps all remaining exceptions (including `TypeError`, `AttributeError`) as `StateProviderError`. A caller passing wrong argument types (e.g., an invalid `thinking` dict) gets a `StateProviderError` instead of a `TypeError`, making it harder to diagnose.
**Suggestion:** Add `anthropic.APIError` to the specific catches before the catch-all, or narrow the catch-all to `anthropic.APIStatusError`:
```python
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise ProviderTransientError(f"server_error {e.status_code}: {e}") from e
            raise StateProviderError(f"stream_setup {e.status_code}: {e}") from e
        # Let TypeError / AttributeError propagate naturally as programming errors
```
