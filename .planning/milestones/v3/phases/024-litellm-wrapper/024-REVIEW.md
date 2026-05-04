---
phase: 024
status: findings
reviewed: 2026-05-03
finding_count: 7
blocker_count: 0
---

# Phase 024: Code Review Report

**Reviewed:** 2026-05-03T01:39:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 024 delivers a clean, well-structured thin wrapper around `litellm.acompletion`. The exception hierarchy is sound, the patch targets in tests are correct, T-024-2 (no `aclose()`) and T-024-4 (no mode-silo import) are satisfied, and all 11 tests pass. No blockers.

Three findings require attention before the phase is closed: one is a Warning (logic gap in `astream()` setup exception mapping that breaks retry semantics for streaming callers), and two are Warnings (mypy strict failures that will break CI under the project's declared `strict = true` + `warn_unused_ignores = true` config). The remaining four findings are Info-level.

---

## Warnings

### WR-01: Wrong `type: ignore` suppression tag — mypy strict fails at line 131

**File:** `src/state_core/providers/litellm_client.py:131`

**Issue:** The comment `# type: ignore[return-value]` suppresses `[return-value]` but the actual mypy error is `[no-any-return]` (litellm returns `Any`; the function declares `ModelResponse`). Under the project's `warn_unused_ignores = true` config, this produces two errors simultaneously — the original unsuppressed `[no-any-return]` and a new `[unused-ignore]` for the wrong tag. Both will fail `mypy --strict` in CI.

Confirmed with `mypy src/state_core/providers/litellm_client.py`:
```
litellm_client.py:131: error: Unused "type: ignore" comment  [unused-ignore]
litellm_client.py:131: error: Returning Any from function declared to return "ModelResponse"  [no-any-return]
litellm_client.py:131: note: Error code "no-any-return" not covered by "type: ignore" comment
```

**Fix:** Replace the wrong tag with the correct one, or cast the result:

```python
# Option A — correct suppress tag:
return result  # type: ignore[no-any-return]

# Option B — explicit cast (preferred; makes the intent clear):
from typing import cast
return cast(ModelResponse, result)
```

---

### WR-02: Missing type arguments on `list[dict]` — mypy strict fails at lines 100 and 171

**File:** `src/state_core/providers/litellm_client.py:100` and `:171`

**Issue:** Both `acompletion()` and `astream()` declare `messages: list[dict]`. Under `mypy --strict` (`[type-arg]` rule), `dict` requires type arguments. Confirmed:

```
litellm_client.py:100: error: Missing type arguments for generic type "dict"  [type-arg]
litellm_client.py:171: error: Missing type arguments for generic type "dict"  [type-arg]
```

**Fix:** Use the OpenAI-idiomatic message type or `Any`-keyed dict:

```python
from typing import Any

# Both method signatures:
messages: list[dict[str, Any]],
```

---

### WR-03: `astream()` setup does not map transient errors — retry semantics broken for streaming

**File:** `src/state_core/providers/litellm_client.py:203-213`

**Issue:** `astream()` has two setup `except` blocks: one for `BadRequestError` variants (mapped to `ProviderBadRequestError`) and a catch-all `except Exception` (mapped to `StateProviderError` base). This means transient errors that occur at streaming setup time — `RateLimitError`, `APIConnectionError`, `Timeout`, `InternalServerError`, `ServiceUnavailableError`, `BadGatewayError` — are wrapped in the *base* `StateProviderError` rather than `ProviderTransientError`.

Any caller with retry logic of the form `except ProviderTransientError: retry()` will silently skip retrying a rate-limit hit that occurs during stream initialization. The non-streaming `acompletion()` maps these correctly to `ProviderTransientError`.

The docstring documents this gap ("StateProviderError: Any other exception at setup or during iteration") but the gap is a semantic inconsistency that will surprise callers.

**Fix:** Expand the setup exception handlers to mirror `acompletion()`:

```python
except (
    lexc.RateLimitError,
    lexc.APIConnectionError,
    lexc.Timeout,
    lexc.InternalServerError,
    lexc.ServiceUnavailableError,
    lexc.BadGatewayError,
) as e:
    log.warning("provider.stream_transient_error", model=model, error_type=type(e).__name__)
    raise ProviderTransientError(f"transient: {e}") from e
except (
    lexc.AuthenticationError,
    lexc.PermissionDeniedError,
) as e:
    log.warning("provider.stream_auth_error", model=model, error_type=type(e).__name__)
    raise ProviderAuthError(f"auth: {e}") from e
except (
    lexc.BadRequestError,
    lexc.ContextWindowExceededError,
    lexc.UnsupportedParamsError,
    lexc.InvalidRequestError,
) as e:
    log.warning("provider.stream_bad_request", model=model, error_type=type(e).__name__)
    raise ProviderBadRequestError(f"bad_request: {e}") from e
except Exception as e:
    log.warning("provider.stream_setup_error", model=model, error_type=type(e).__name__)
    raise StateProviderError(f"provider_error: {e}") from e
```

---

## Info

### IN-01: Three litellm exception types fall to catch-all in `acompletion()` — semantically imprecise

**File:** `src/state_core/providers/litellm_client.py:163-166`

**Issue:** `NotFoundError` (404 model-not-found), `UnprocessableEntityError` (422), and `BudgetExceededError` are present in the installed litellm 1.83.0 but absent from any named `except` clause in `acompletion()`. They fall to `except Exception -> StateProviderError` (base class). T-024-3 is satisfied (no raw litellm leak), but callers cannot distinguish them from a generic unknown error. `NotFoundError` and `UnprocessableEntityError` are non-retryable bad-request semantics; `BudgetExceededError` resembles a rate-limit condition.

**Fix:** Add explicit mappings if call-site retry/error-handling logic needs to distinguish these. This is intentionally left as Info since the catch-all is T-024-3 compliant and the semantic gap is acceptable for Phase 024 scope.

```python
# Suggested additions to the ProviderBadRequestError handler:
except (
    lexc.BadRequestError,
    lexc.ContextWindowExceededError,
    lexc.UnsupportedParamsError,
    lexc.InvalidRequestError,
    lexc.LiteLLMUnknownProvider,
    lexc.NotFoundError,           # 404 model-not-found
    lexc.UnprocessableEntityError, # 422
) as e:
    ...
```

---

### IN-02: Missing test for `astream()` setup exception paths

**File:** `tests/test_litellm_client.py`

**Issue:** `test_astream_exception_maps_correctly` only covers mid-stream iteration errors. There is no test verifying that a `BadRequestError` raised during stream *setup* (the `await litellm.acompletion(stream=True, ...)` call, before any chunk is yielded) maps to `ProviderBadRequestError`. This path exists in the implementation at lines 203-210 but is untested.

**Fix:** Add a test:

```python
async def test_astream_setup_bad_request_maps_to_bad_request_error() -> None:
    """BadRequestError at stream setup maps to ProviderBadRequestError."""
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=lexc.BadRequestError("bad_request", "openai", "gpt-4o")
        )
        client = LitellmClient()
        with pytest.raises(ProviderBadRequestError):
            async for _ in client.astream("gpt-4o", []):
                pass
```

---

### IN-03: `_fake_stream` helper missing type annotations — mypy strict failure in test file

**File:** `tests/test_litellm_client.py:37-41`

**Issue:** `_fake_stream` has no return type annotation and no parameter type annotations. Under `mypy --strict` this produces `[no-untyped-def]` for both the parameter types and the return type. Also `_make_exc` at line 108 produces `[no-any-return]` (returns `Exception` but the instance construction returns `Any`).

```
tests/test_litellm_client.py:37: error: Function is missing a return type annotation  [no-untyped-def]
tests/test_litellm_client.py:37: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests/test_litellm_client.py:116: error: Returning Any from function declared to return "Exception"  [no-any-return]
```

**Fix:**

```python
from collections.abc import AsyncGenerator
from typing import Any

async def _fake_stream(
    chunks: list[Any],
    *,
    raise_after: Exception | None = None,
) -> AsyncGenerator[Any, None]:
    for chunk in chunks:
        yield chunk
    if raise_after is not None:
        raise raise_after

def _make_exc(exc_class: type[Exception]) -> Exception:
    if exc_class is lexc.PermissionDeniedError:
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(403, request=request)
        return exc_class("permission_denied", "openai", "gpt-4o", response)  # type: ignore[call-arg]
    return exc_class("fixture", "openai", "gpt-4o")  # type: ignore[call-arg]
```

---

### IN-04: `LiteLLMUnknownProvider` is redundant in `acompletion()` except tuple

**File:** `src/state_core/providers/litellm_client.py:149-155`

**Issue:** `LiteLLMUnknownProvider` is a direct subclass of `litellm.BadRequestError` (confirmed via MRO). Since `lexc.BadRequestError` appears earlier in the same `except` tuple, listing `lexc.LiteLLMUnknownProvider` explicitly is redundant — it would be caught by the `BadRequestError` arm regardless. This is harmless but adds noise to the exception list.

**Fix:** Remove the redundant entry:

```python
except (
    lexc.BadRequestError,
    lexc.ContextWindowExceededError,
    lexc.UnsupportedParamsError,
    lexc.InvalidRequestError,
    # LiteLLMUnknownProvider removed: it IS-A BadRequestError, already caught above
) as e:
```

Alternatively, keep the explicit listing with a comment explaining it is a documentation aid.

---

## Requirement Checklist

| Requirement | Status | Notes |
|---|---|---|
| PRV-01: litellm as default provider abstraction | Pass | Exception hierarchy is complete for common cases |
| PRV-07: streaming normalization (chunks yielded unchanged) | Pass | `async for chunk in response: yield chunk` — no mutation |
| T-024-1: OAuth/Anthropic traffic must not route through this module | Pass | Module has no Anthropic-specific imports; routing is Phase 026's responsibility |
| T-024-2: Must never call `aclose()` on shared httpx client | Pass | No `aclose()` calls anywhere in the module; test verifies |
| T-024-3: All litellm exceptions caught and mapped | Pass | Catch-all ensures no raw litellm exception leaks; 3 exception types fall to base class (IN-01) |
| T-024-4: No imports from `state_build.*` or `state_teach.*` | Pass | Confirmed via `sys.modules` check in `test_no_mode_silo_import` |
| Patch target correctness | Pass | `patch("state_core.providers.litellm_client.litellm")` matches `import litellm` at module level |
| mypy strict compliance | **Fail** | 4 errors in implementation, 3 in tests (WR-01, WR-02, IN-03) |

---

_Reviewed: 2026-05-03T01:39:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
