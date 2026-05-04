# Phase 024: litellm wrapper (`state_core.providers.litellm_client`) - Research

**Researched:** 2026-05-02
**Domain:** litellm acompletion API, streaming normalization, error taxonomy, pytest-httpx mocking
**Confidence:** HIGH

## Summary

Phase 024 adds `src/state_core/providers/litellm_client.py` — a thin async wrapper around `litellm.acompletion` that handles non-Anthropic provider traffic. The shared `httpx.AsyncClient` is already wired to `litellm.aclient_session` by Phase 023's `orchestrator.startup()`, so this phase only needs to call `acompletion`, normalize streaming chunks, and map litellm exceptions to state's own hierarchy. No new infrastructure is required.

The installed version is **litellm 1.83.0** (pinned `>=1.80.0`). The `acompletion` function returns `Union[ModelResponse, CustomStreamWrapper]` — non-streaming returns a Pydantic `ModelResponse`, streaming returns `CustomStreamWrapper` which is both sync- and async-iterable. Streaming chunks are `ModelResponseStream` objects with a `choices: List[StreamingChoices]` field; each `StreamingChoices` has a `delta: Delta` with `content`, `role`, and optional `reasoning_content`. The litellm exception hierarchy (25 classes) maps cleanly onto four state categories: transient/retryable, auth/permanent, bad-request/permanent, and upstream-unavailable.

**Primary recommendation:** Implement `LitellmClient` as a plain class (not a Pydantic model) with `acompletion()` and `astream()` methods. Keep the litellm import at module level so patch paths are stable in tests. Define `StateProviderError` hierarchy in the same module; keep it shallow (4 leaf classes is enough for PRV-01 and PRV-07).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per `workflow.skip_discuss`. All implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices — including class design, exception taxonomy depth, streaming normalization shape, and test structure.

### Deferred Ideas (OUT OF SCOPE)
None declared.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-01 | litellm >= 1.80.0 as default provider abstraction for non-stealth traffic | `acompletion` signature verified at litellm 1.83.0; `aclient_session` already set by Phase 023 |
| PRV-07 | Streaming tokens flow through `chat.params` / `chat.headers` hook without mutation loss | `CustomStreamWrapper` is `AsyncIterable[ModelResponseStream]`; `delta.content` and `delta.tool_calls` are the canonical streaming fields |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.83.0 (pinned >=1.80.0) | Unified provider abstraction; `acompletion` async entry point | Project pin; PRV-01 requirement |
| httpx | 0.28.1 | Shared transport (already injected via `litellm.aclient_session`) | Phase 023 provides; no new work |
| pydantic | 2.13.2+ | `ModelResponse` return type from litellm is Pydantic v2; state error models | Project standard |
| structlog | 25.1+ | Logging in `litellm_client.py`, consistent with all other state_core modules | Project standard |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-httpx | 0.36.2 | Mock HTTP responses at the httpx transport layer | When testing paths that go through the shared `AsyncClient` |
| unittest.mock (stdlib) | n/a | Patch `litellm.acompletion` directly (avoids real HTTP) | Preferred for unit tests; avoids needing to construct HTTP fixtures |
| hypothesis | 6.152.1 | Property tests on error taxonomy (all litellm exception types are handled) | Cover the full exception surface without writing 25 explicit cases |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `unittest.mock.patch("litellm.acompletion")` | `pytest-httpx httpx_mock` | Mock at litellm API level is faster and more stable; httpx mock works but requires constructing valid OpenAI-wire JSON |
| Flat `StateProviderError` subclasses | Custom error codes on one exception | Shallow class hierarchy is simpler to match on; codes-on-one-class makes callers use string comparison |

**Installation:** No new packages required. All libraries already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended File Layout
```
src/state_core/providers/
├── __init__.py              # already exists: "Provider routing: litellm default, Anthropic SDK escape hatch."
├── litellm_client.py        # NEW — Phase 024 (this phase)
└── router.py                # stub ProviderRouter — untouched by Phase 024
```

```
tests/
├── test_litellm_client.py   # NEW — Wave 0 RED stubs, Wave 1 GREEN
```

### Pattern 1: Module-level litellm import with `AsyncMock` patch path

Import `litellm` at module level (not inside the function body) so tests can patch `state_core.providers.litellm_client.litellm` reliably. This is the same pattern as `state_daemon/orchestrator.py`:

```python
# src/state_core/providers/litellm_client.py
from __future__ import annotations

import litellm                     # module-level: patch target is stable
import litellm.exceptions as lexc
import structlog
from litellm.types.utils import ModelResponse, ModelResponseStream

log = structlog.get_logger(__name__)
```

### Pattern 2: `acompletion` call — pass-through with session already set

`litellm.aclient_session` is assigned in `orchestrator.startup()` before any inference call. The wrapper does not need to pass the client explicitly — litellm's openai/azure/common_utils path reads `litellm.aclient_session` automatically.

```python
# Source: verified from litellm 1.83.0 llms/openai/common_utils.py L216-217
# `_get_async_http_client` returns litellm.aclient_session if set.

async def acompletion(
    self,
    model: str,
    messages: list[dict],
    *,
    stream: bool = False,
    **kwargs,
) -> ModelResponse | CustomStreamWrapper:
    return await litellm.acompletion(
        model=model,
        messages=messages,
        stream=stream,
        **kwargs,
    )
```

### Pattern 3: Streaming normalization — `async for` over `CustomStreamWrapper`

`litellm.acompletion(stream=True)` returns `CustomStreamWrapper` which implements `__aiter__` / `__anext__` yielding `ModelResponseStream`. Each chunk has `choices: List[StreamingChoices]`; each `StreamingChoices` has `delta: Delta`. The canonical streaming content fields are:

- `chunk.choices[0].delta.content` — text token (may be `None` for non-text chunks)
- `chunk.choices[0].delta.tool_calls` — tool call delta (may be `None`)
- `chunk.choices[0].delta.reasoning_content` — thinking tokens for compatible providers
- `chunk.choices[0].finish_reason` — `None` until last chunk; `"stop"`, `"tool_calls"`, etc. on last

PRV-07 requires that chunks flow through without mutation loss. The wrapper must yield each `ModelResponseStream` unchanged (or as a thin `StreamChunk` dataclass that preserves all fields). Simplest compliant approach: yield `ModelResponseStream` directly from an `AsyncGenerator`.

```python
# Source: verified from litellm 1.83.0 streaming_handler.py __anext__ return type
from collections.abc import AsyncGenerator

async def astream(
    self,
    model: str,
    messages: list[dict],
    **kwargs,
) -> AsyncGenerator[ModelResponseStream, None]:
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        stream=True,
        **kwargs,
    )
    async for chunk in response:
        yield chunk
```

### Pattern 4: Error taxonomy — map litellm exceptions to state hierarchy

litellm 1.83.0 has 25 exception classes, all in `litellm.exceptions`. They share a common base `litellm.exceptions.APIError` (which inherits from `openai.lib._old_api.APIError`). The practical mapping for state's purposes:

```python
# litellm.exceptions -> state exception (PRV-01 error surface)
#
# Transient (caller should retry with backoff):
#   RateLimitError (429), ServiceUnavailableError, BadGatewayError,
#   InternalServerError, APIConnectionError, Timeout
#
# Auth (caller must refresh credentials and retry once):
#   AuthenticationError (401), PermissionDeniedError (403)
#
# Bad request (caller must not retry, fix request):
#   BadRequestError (400), ContextWindowExceededError (400),
#   UnsupportedParamsError, InvalidRequestError, LiteLLMUnknownProvider
#
# Validation (caller must fix response handling):
#   APIResponseValidationError, JSONSchemaValidationError

class StateProviderError(Exception):
    """Base for all state provider errors."""

class ProviderTransientError(StateProviderError):
    """Retry-able; caller should back off."""

class ProviderAuthError(StateProviderError):
    """Auth failure; caller should refresh credentials."""

class ProviderBadRequestError(StateProviderError):
    """Non-retryable request error."""

class ProviderResponseError(StateProviderError):
    """Unexpected or invalid provider response."""
```

### Anti-Patterns to Avoid

- **Importing litellm inside the function body:** breaks `patch("state_core.providers.litellm_client.litellm")` — import must be at module level.
- **Catching `Exception` as a single broad handler:** loses the retry/no-retry signal; always map to specific state errors first, then fall through to `StateProviderError`.
- **Calling `await client.aclose()` on the shared client in this module:** the shared client's lifecycle is owned by `Deps`/`orchestrator`; `litellm_client.py` must never close it.
- **Importing from `state.build.*` or `state.teach.*`:** `state_core.providers` is shared kernel — mode isolation rules apply.
- **OAuth-path traffic through litellm:** the "OAuth stealth never routes through litellm" rule is enforced at Phase 026 (bypass guard). Phase 024 simply wraps `acompletion` and need not validate this; tests should NOT attempt to call real auth flows through `LitellmClient`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Streaming chunk parsing | Custom SSE parser | `litellm.acompletion(stream=True)` returns `CustomStreamWrapper` | litellm handles SSE, JSON parsing, delta accumulation across all providers |
| Provider-specific error codes | Custom HTTP status mapping | `litellm.exceptions` hierarchy (already maps all provider-specific codes) | litellm 1.83.0 maps Anthropic/OpenAI/Gemini/Azure codes to the same exception class |
| Retry logic | Custom `asyncio.sleep` + counter loop | Caller responsibility (Phase 027/028 concern) — `LitellmClient` only raises `ProviderTransientError` | Retry policy depends on cost accounting context not available in this layer |
| Context-window token counting | Custom token counter | litellm has `get_max_tokens()` / `token_counter()` | `ContextWindowExceededError` is raised automatically by litellm when the model rejects oversized input |

---

## Common Pitfalls

### Pitfall 1: `litellm.aclient_session` is best-effort for non-OpenAI-compatible providers

**What goes wrong:** Anthropic's native endpoint (used by Phase 025) and some HuggingFace/custom endpoints do NOT use `_get_async_http_client` from `llms/openai/common_utils.py`. Only OpenAI-compatible providers (openai, azure, google via openai-compat, github copilot) pick up `aclient_session`.

**Why it happens:** litellm routes Anthropic via a dedicated `llms/anthropic/` handler that constructs its own client. The `aclient_session` path is in `llms/openai/common_utils.py`.

**How to avoid:** Document in the module docstring that `aclient_session` is best-effort. Phase 025 (direct Anthropic SDK escape hatch) injects `deps.http_client` via `AsyncAnthropic(http_client=deps.http_client)` separately.

**Warning signs:** If a test verifies connection-pool reuse by counting `AsyncClient.send()` calls, it will fail for Anthropic model strings — that is expected and intentional.

### Pitfall 2: `CustomStreamWrapper` is a sync-AND-async iterable — use `async for`, not `for`

**What goes wrong:** `CustomStreamWrapper` has both `__iter__` and `__aiter__`. Using sync `for chunk in response` works in some contexts but bypasses `__anext__`'s `await fetch_stream()` lazy-initialization path, causing a `StopIteration` or `RuntimeError`.

**How to avoid:** Always use `async for chunk in response`. The `astream()` wrapper method must be an `async def` with `async for`.

### Pitfall 3: Mock `litellm.acompletion` at the module-level import, not at `litellm` package level

**What goes wrong:** `patch("litellm.acompletion")` patches the function in the `litellm` package's namespace. If `litellm_client.py` imports `import litellm`, the attribute lookup `litellm.acompletion` still finds the unpatched function at call time (it goes through `litellm.__getattr__` lazy-load).

**How to avoid:** In tests, patch `state_core.providers.litellm_client.litellm` as a whole, then set `.acompletion` on the mock (as `AsyncMock`). This mirrors the working pattern in `test_deps.py`:
```python
with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
    mock_litellm.acompletion = AsyncMock(return_value=fake_response)
    ...
```

### Pitfall 4: `ModelResponse` has `choices` not `message` at the top level

**What goes wrong:** Code accesses `response.message.content` (OpenAI SDK style) instead of `response.choices[0].message.content`.

**How to avoid:** `ModelResponse.model_fields` are: `id`, `created`, `model`, `object`, `system_fingerprint`, `choices`. Access content as `response.choices[0].message.content`.

### Pitfall 5: litellm's `__version__` attribute raises `AttributeError`

**What goes wrong:** `litellm.__version__` raises `AttributeError: module 'litellm' has no attribute '__version__'` in 1.83.0. The version is in `litellm._version.version`.

**How to avoid:** If version logging is needed: `from litellm._version import version as litellm_version`. Or skip version logging — it is not required for PRV-01 or PRV-07.

### Pitfall 6: `litellm.exceptions` import path vs `litellm` namespace

**What goes wrong:** `litellm.RateLimitError` may not resolve via `litellm.__getattr__` lazy loading; the canonical import is `import litellm.exceptions as lexc`.

**How to avoid:** Always use `import litellm.exceptions as lexc` and reference `lexc.RateLimitError` etc. Verified at litellm 1.83.0.

---

## Code Examples

### Non-streaming call

```python
# Source: verified against litellm 1.83.0 acompletion signature
from litellm.types.utils import ModelResponse

async def acompletion(
    self,
    model: str,
    messages: list[dict],
    **kwargs,
) -> ModelResponse:
    try:
        result = await litellm.acompletion(model=model, messages=messages, **kwargs)
        return result  # type: ignore[return-value]
    except lexc.RateLimitError as e:
        raise ProviderTransientError(f"rate_limit: {e}") from e
    except lexc.AuthenticationError as e:
        raise ProviderAuthError(f"auth: {e}") from e
    except lexc.BadRequestError as e:
        raise ProviderBadRequestError(f"bad_request: {e}") from e
    except lexc.APIConnectionError as e:
        raise ProviderTransientError(f"connection: {e}") from e
    except Exception as e:
        raise StateProviderError(f"provider_error: {e}") from e
```

### Streaming call — yield normalized chunks

```python
# Source: verified from CustomStreamWrapper.__anext__ return type: ModelResponseStream
# delta.content is the text token; delta.tool_calls for tool streaming
from collections.abc import AsyncGenerator
from litellm.types.utils import ModelResponseStream

async def astream(
    self,
    model: str,
    messages: list[dict],
    **kwargs,
) -> AsyncGenerator[ModelResponseStream, None]:
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
    except lexc.BadRequestError as e:
        raise ProviderBadRequestError(f"bad_request: {e}") from e
    except Exception as e:
        raise StateProviderError(f"provider_error: {e}") from e

    async for chunk in response:
        yield chunk
```

### Test: mock non-streaming response

```python
# Pattern consistent with test_deps.py: patch at litellm_client module's litellm binding
from unittest.mock import AsyncMock, MagicMock, patch
from litellm.types.utils import ModelResponse

async def test_acompletion_non_streaming() -> None:
    fake_response = MagicMock(spec=ModelResponse)
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "hello"

    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_response)
        from state_core.providers.litellm_client import LitellmClient
        client = LitellmClient()
        result = await client.acompletion("gpt-4o", [{"role": "user", "content": "hi"}])
    assert result.choices[0].message.content == "hello"
```

### Test: mock streaming response (async generator helper)

```python
async def _fake_stream(chunks):
    for chunk in chunks:
        yield chunk

async def test_astream_yields_chunks() -> None:
    from litellm.types.utils import ModelResponseStream

    fake_chunk = MagicMock(spec=ModelResponseStream)
    fake_stream = _fake_stream([fake_chunk])

    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_stream)
        from state_core.providers.litellm_client import LitellmClient
        client = LitellmClient()
        chunks = []
        async for chunk in client.astream("gpt-4o", [{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
    assert chunks == [fake_chunk]
```

### Test: error taxonomy with hypothesis

```python
# Verify all litellm exception types are handled (no uncaught exception leaks)
from hypothesis import given, settings
import hypothesis.strategies as st
import litellm.exceptions as lexc

_LITELLM_EXCEPTION_CLASSES = [
    lexc.RateLimitError,
    lexc.AuthenticationError,
    lexc.BadRequestError,
    lexc.ContextWindowExceededError,
    lexc.APIConnectionError,
    lexc.Timeout,
    lexc.InternalServerError,
    lexc.ServiceUnavailableError,
    lexc.PermissionDeniedError,
    lexc.NotFoundError,
]

@given(st.sampled_from(_LITELLM_EXCEPTION_CLASSES))
@settings(max_examples=len(_LITELLM_EXCEPTION_CLASSES))
async def test_all_litellm_exceptions_map_to_state_errors(exc_class) -> None:
    with patch("state_core.providers.litellm_client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            side_effect=exc_class("fixture", status_code=400, llm_provider="openai", model="gpt-4o")
        )
        from state_core.providers.litellm_client import LitellmClient, StateProviderError
        client = LitellmClient()
        with pytest.raises(StateProviderError):
            await client.acompletion("gpt-4o", [])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `litellm.completion` (sync) | `litellm.acompletion` (async) | litellm ~0.x → 1.x | `acompletion` is the correct entry point for daemon's asyncio loop |
| `client_session` (sync httpx client) | `aclient_session` (async httpx client) | litellm ~1.x | `aclient_session = None` is the module-level default; Phase 023 assigns `deps.http_client` |
| litellm raised `openai.error.*` | litellm raises `litellm.exceptions.*` | litellm ~1.0 | All exceptions now in `litellm.exceptions`; the underlying base class `OpenAIError` is legacy artifact |

**Deprecated/outdated:**
- `litellm.__version__`: raises `AttributeError` in 1.83.0; use `litellm._version.version` if needed.
- `litellm.client_session` (sync version): exists but irrelevant for async daemon; use `litellm.aclient_session`.

---

## Open Questions

1. **Anthropic model string routing**
   - What we know: When model string is `"anthropic/claude-*"` or `"claude-*"`, litellm's handler chooses `llms/anthropic/` path which does NOT use `litellm.aclient_session`. Phase 025 provides a direct Anthropic SDK path.
   - What's unclear: Should `LitellmClient` detect Anthropic model strings and raise `NotImplementedError` / redirect to Phase 025's client, or silently route through litellm (which will work but won't use the shared httpx client)?
   - Recommendation: For Phase 024 scope (PRV-01 only), let litellm route Anthropic strings silently. Add a `# NOTE:` docstring comment that Anthropic via litellm does not use the shared httpx client; Phase 025 is the canonical Anthropic path. This avoids a cross-phase dependency in Phase 024.

2. **`StateProviderError` hierarchy location**
   - What we know: The project has no existing provider error hierarchy; `state_core/providers/__init__.py` is nearly empty.
   - What's unclear: Should the hierarchy go in `litellm_client.py` or a separate `state_core/providers/errors.py`?
   - Recommendation: Define in `litellm_client.py` for Phase 024 (keeps the wave minimal). A future phase can extract to `errors.py` if the Anthropic escape hatch (Phase 025) needs to share the same hierarchy. Document the intent in a `# TODO(phase-025)` comment.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ with `asyncio_mode = "auto"` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/test_litellm_client.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-01 | `LitellmClient.acompletion()` calls `litellm.acompletion` and returns `ModelResponse` | unit | `pytest tests/test_litellm_client.py::test_acompletion_returns_model_response -x` | ❌ Wave 0 |
| PRV-01 | `LitellmClient` does NOT close the shared httpx client | unit | `pytest tests/test_litellm_client.py::test_client_does_not_close_shared_httpx -x` | ❌ Wave 0 |
| PRV-01 | All litellm exception types map to `StateProviderError` subclasses | property | `pytest tests/test_litellm_client.py::test_all_litellm_exceptions_map_to_state_errors -x` | ❌ Wave 0 |
| PRV-01 | `RateLimitError` maps to `ProviderTransientError` | unit | `pytest tests/test_litellm_client.py::test_rate_limit_maps_to_transient -x` | ❌ Wave 0 |
| PRV-01 | `AuthenticationError` maps to `ProviderAuthError` | unit | `pytest tests/test_litellm_client.py::test_auth_error_maps_to_auth_error -x` | ❌ Wave 0 |
| PRV-01 | `BadRequestError` maps to `ProviderBadRequestError` | unit | `pytest tests/test_litellm_client.py::test_bad_request_maps_to_bad_request -x` | ❌ Wave 0 |
| PRV-07 | `LitellmClient.astream()` yields `ModelResponseStream` chunks unchanged | unit | `pytest tests/test_litellm_client.py::test_astream_yields_chunks_unchanged -x` | ❌ Wave 0 |
| PRV-07 | `delta.content` is accessible on each yielded chunk | unit | `pytest tests/test_litellm_client.py::test_astream_chunk_delta_content -x` | ❌ Wave 0 |
| PRV-07 | `delta.tool_calls` survives streaming normalization | unit | `pytest tests/test_litellm_client.py::test_astream_chunk_delta_tool_calls -x` | ❌ Wave 0 |
| PRV-07 | Exception in stream mid-flight maps to `StateProviderError` | unit | `pytest tests/test_litellm_client.py::test_astream_exception_maps_correctly -x` | ❌ Wave 0 |
| both | Import graph: `state_core.providers.litellm_client` does NOT import `state_build.*` or `state_teach.*` | import-graph | `pytest tests/test_litellm_client.py::test_no_mode_silo_import -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_litellm_client.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_litellm_client.py` — all 11 RED stubs listed above
- [ ] `src/state_core/providers/litellm_client.py` — module (created in Wave 1 GREEN)

*(No framework gaps — pytest infrastructure and test helpers from Phase 023 carry over.)*

---

## Sources

### Primary (HIGH confidence)
- litellm 1.83.0 installed at `.venv/lib/python3.12/site-packages/litellm/` — `acompletion` signature, `aclient_session` attribute, `CustomStreamWrapper.__anext__` return type, `ModelResponseStream` fields, `StreamingChoices.delta`, `Delta` fields, `exceptions` hierarchy
- `litellm/llms/openai/common_utils.py` L212-226 — `_get_async_http_client` uses `litellm.aclient_session` if set (verified direct source read)
- `litellm/llms/base.py` L62-76 — `create_aclient_session` / cleanup pattern for non-openai providers
- Phase 023 SUMMARY.md — confirms `litellm.aclient_session = deps.http_client` is set in `orchestrator.startup()`
- `src/state_core/http_client.py`, `src/state_core/deps.py` — confirmed Deps and build_shared_client shapes
- `pyproject.toml` — confirmed installed versions: litellm>=1.80.0, pytest-httpx>=0.35, hypothesis>=6.120
- `tests/test_deps.py` — confirmed `patch("state_daemon.orchestrator.litellm")` pattern works for module-level import

### Secondary (MEDIUM confidence)
- pytest-httpx 0.36.2 `HTTPXMock.add_response` signature — verified from installed package source
- hypothesis 6.152.1 `@given` / `@settings` pattern — confirmed from installed package

### Tertiary (LOW confidence)
- None — all critical claims verified from installed package source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from installed litellm 1.83.0 and project pyproject.toml
- Architecture: HIGH — `acompletion` signature and `aclient_session` path verified from venv source
- Pitfalls: HIGH — discovered from direct inspection of litellm internals (lazy `__getattr__`, `CustomStreamWrapper` dual-iteration, missing `__version__`)
- Error taxonomy: HIGH — all 25 exception classes enumerated from `litellm.exceptions`, status_code attributes confirmed

**Research date:** 2026-05-02
**Valid until:** 2026-06-02 (litellm moves fast; re-verify if litellm is bumped past 1.85.0)
