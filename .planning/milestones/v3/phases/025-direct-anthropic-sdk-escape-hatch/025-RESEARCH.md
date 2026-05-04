# Phase 025: Direct Anthropic SDK Escape Hatch — Research

**Researched:** 2026-05-03
**Domain:** anthropic SDK 0.96.0, OAuth stealth headers, extended thinking, cache-control, pytest-httpx mocking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per `workflow.skip_discuss`. All implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices — class design, credential-dispatch strategy, stealth header injection pattern, thinking/cache API shape.

### Deferred Ideas (OUT OF SCOPE)
None declared.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-02 | Direct Anthropic SDK escape hatch for extended thinking and fine-grained cache-control breakpoints | `anthropic.AsyncAnthropic(http_client=deps.http_client)` with stealth headers via `default_headers=`; `thinking=ThinkingConfigParam` and `cache_control=CacheControlEphemeralParam` are first-class SDK params on `messages.create()` |
| PRV-08 | Thinking-budget tag propagation (`thinking.budget_tokens`) for Anthropic extended thinking | `ThinkingConfigEnabledParam(type="enabled", budget_tokens=N)` passed as `thinking=` to `client.messages.create()`; must be >= 1024, < max_tokens; adaptive thinking also supported via `ThinkingConfigAdaptiveParam` |
| PRV-09 | Cache-control marker preservation end-to-end (client → provider → response accounting) | `cache_control=CacheControlEphemeralParam(type="ephemeral", ttl="5m"|"1h")` on `messages.create()`; usage accounting in `response.usage.cache_creation_input_tokens` and `response.usage.cache_read_input_tokens` |
</phase_requirements>

---

## Summary

Phase 025 creates `state_core/providers/anthropic_client.py` — a thin async wrapper around `anthropic.AsyncAnthropic` that acts as the escape hatch for direct Anthropic API calls when an OAuth credential (`sk-ant-oat*`) is present. It injects the shared `httpx.AsyncClient` from Phase 023 (`deps.http_client`), applies the stealth headers from Phase 014's `AnthropicAuth.http_headers()`, and exposes extended thinking and cache-control as first-class parameters on its `create()` and `stream()` methods.

The three requirements are tightly coupled: PRV-02 mandates the direct SDK path (not litellm); PRV-08 mandates that `thinking.budget_tokens` flows through correctly; PRV-09 mandates that `cache_control` markers are passed and their response usage tokens are preserved for accounting. All three are satisfied by a single `AnthropicClient` class that wraps `client.messages.create()` and `client.messages.stream()` with the correct params.

Phase 014 already provides everything needed on the auth side: `AnthropicAuth.http_headers(cred)` returns the four stealth headers (`authorization`, `user-agent`, `x-app`, `anthropic-beta`) for `OAuthCredential`; `inject_stealth_system_prefix()` handles the system prompt prefix; `with_beta_param()` is available but not needed here (the SDK's `default_query={"beta": "true"}` is the cleaner approach). Phase 023's `Deps.http_client` is the shared transport. Phase 025 assembles these into `AnthropicClient`.

**Primary recommendation:** Implement `AnthropicClient` as a plain class constructed from `(cred, deps)`. It builds a fresh `AsyncAnthropic` instance per credential (not per call) with `auth_token=`, `http_client=deps.http_client`, `default_headers=` (stealth headers + x-api-key suppression), and `default_query={"beta": "true"}`. Test with `pytest-httpx` `HTTPXMock` intercepting at the `httpx.AsyncHTTPTransport` layer.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | 0.96.0 (pinned `>=0.80.0`) | Direct Anthropic SDK — `AsyncAnthropic`, `messages.create()`, `messages.stream()` | Project pin; PRV-02 requirement; stealth headers not available via litellm path |
| `httpx` | 0.28.1 (already pinned) | Shared transport injected via `http_client=` parameter | Phase 023 provides; same client used by litellm for OpenAI-compatible providers |
| `pydantic` | 2.13.2+ (already pinned) | `AnthropicClient` is a plain class; state error hierarchy extends Phase 024's `StateProviderError` | Project standard |
| `structlog` | 25.1+ (already pinned) | Logging consistent with rest of `state_core.providers` | Project standard |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-httpx` | 0.36.2 | `HTTPXMock` — intercepts `httpx.AsyncHTTPTransport.handle_async_request` at transport layer | Primary test strategy; works because `AsyncAnthropic` uses the shared `httpx.AsyncClient` which pytest-httpx patches |
| `pytest-asyncio` | 1.3.0+ | `asyncio_mode = "auto"` for `async def test_*` functions | Already configured in `pyproject.toml` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest-httpx` HTTPXMock | `unittest.mock.patch` on `AsyncAnthropic.messages.create` | pytest-httpx validates actual HTTP shape (URL, headers, body) including stealth header verification — preferred for PRV-02/PRV-08/PRV-09; mocking the SDK method is simpler but skips transport-level assertions |
| `default_query={"beta": "true"}` | `with_beta_param(url)` on each call | `default_query` is cleaner (SDK applies to every request); `with_beta_param` is a manual URL builder designed for pre-SDK wiring |
| Re-export `StateProviderError` from litellm_client.py | Separate `errors.py` module | Phase 024 has `# TODO(phase-025): extract to errors.py`; Phase 025 should do that extraction so both clients share the hierarchy |

**Installation:** No new packages — `anthropic>=0.80.0` already in `pyproject.toml` and installed at 0.96.0.

---

## Architecture Patterns

### Recommended File Layout
```
src/state_core/providers/
├── __init__.py              # "Provider routing: litellm default, Anthropic SDK escape hatch."
├── errors.py                # NEW — Phase 025: extract StateProviderError hierarchy here (shared by litellm_client + anthropic_client)
├── litellm_client.py        # Phase 024 — update import: from state_core.providers.errors import *
├── anthropic_client.py      # NEW — Phase 025
└── router.py                # stub ProviderRouter — untouched

tests/
├── test_anthropic_client.py # NEW — Wave 0 RED stubs, Wave 1 GREEN
```

### Pattern 1: `AsyncAnthropic` Construction with Stealth Headers

**What:** Build a fresh `AsyncAnthropic` for an OAuth credential, injecting the shared httpx client and stealth headers.
**When to use:** During `AnthropicClient.__init__` or in a factory method (once per credential, not per call).

Key facts from installed SDK 0.96.0 (`_client.py` lines 302-354):

```python
# Source: anthropic 0.96.0 _client.py AsyncAnthropic.__init__
import anthropic
from anthropic import omit  # Omit sentinel for header suppression

def _build_sdk_client(
    cred: OAuthCredential,
    http_client: httpx.AsyncClient,
    stealth_headers: dict[str, str],
) -> anthropic.AsyncAnthropic:
    """Construct AsyncAnthropic for an OAuth credential.

    Critical: pass api_key=None AND suppress X-Api-Key via default_headers omit.
    If ANTHROPIC_API_KEY env var is set, SDK reads it when api_key is None
    (line 332-333 of _client.py). Suppressing with omit in default_headers
    removes it even if env var was read.
    """
    return anthropic.AsyncAnthropic(
        auth_token=cred.access,       # Bearer Authorization header
        api_key=None,                 # Allow env fallback (suppressed below)
        http_client=http_client,      # Phase 023 shared client
        default_headers={
            # Suppress X-Api-Key even if ANTHROPIC_API_KEY is set in env.
            # _merge_mappings in _base_client.py removes keys with Omit values.
            "X-Api-Key": omit,
            # Override SDK default User-Agent with stealth value
            "user-agent": stealth_headers["user-agent"],
            "x-app": stealth_headers["x-app"],
            # anthropic-beta carries the full stealth beta flags
            "anthropic-beta": stealth_headers["anthropic-beta"],
        },
        default_query={"beta": "true"},  # Appends ?beta=true to all requests
        max_retries=0,  # State handles retry policy via ProviderTransientError
    )
```

**SDK header merge order (verified from `_base_client.py` lines 684-693):**
`Accept` / `Content-Type` / `User-Agent` → `auth_headers` (`X-Api-Key` + `Authorization: Bearer`) → `_custom_headers` (our `default_headers`). `_merge_mappings` removes `Omit` values last. So `{"X-Api-Key": omit}` in `default_headers` correctly suppresses the key even if `api_key` was populated from the env var.

**Key: stealth headers source.** Phase 014's `AnthropicAuth.http_headers(cred)` returns exactly:
```python
{
    "authorization": f"Bearer {cred.access}",  # covered by auth_token= param
    "user-agent": "claude-cli/2.1.121 (external, cli)",
    "x-app": "cli",
    "anthropic-beta": "oauth-2025-04-20,interleaved-thinking-2025-05-14,...",
}
```
The `authorization` header is handled by `auth_token=`. The other three go into `default_headers`. **Do not duplicate the `authorization` key** — `auth_token=` already adds `Authorization: Bearer` via the SDK's `_bearer_auth` property.

### Pattern 2: `AnthropicClient` Class Design

**What:** Thin wrapper class, constructed from credential + deps.
**When to use:** This is the escape hatch; one instance per (credential, deps) pair; should be cheap to create.

```python
# Source: project conventions + anthropic 0.96.0 API
from __future__ import annotations

import anthropic
from anthropic import omit
import structlog
from anthropic.types import Message
from anthropic.types.thinking_config_param import ThinkingConfigParam
from anthropic.types.cache_control_ephemeral_param import CacheControlEphemeralParam

from state_core.auth.base import OAuthCredential, ApiKeyCredential, Credential
from state_core.auth.providers.anthropic import AnthropicAuth
from state_core.deps import Deps
from state_core.providers.errors import (
    StateProviderError, ProviderTransientError, ProviderAuthError,
    ProviderBadRequestError, ProviderResponseError,
)

log = structlog.get_logger(__name__)


class AnthropicClient:
    """Direct Anthropic SDK escape hatch for OAuth stealth traffic (PRV-02).

    Use this for all sk-ant-oat* credentials. Never route OAuth traffic
    through litellm (PRV-03 enforcement is Phase 026's job; this class
    accepts any credential and dispatches appropriately).
    """

    def __init__(self, cred: Credential, deps: Deps) -> None:
        self._cred = cred
        self._deps = deps
        self._sdk = self._build_sdk(cred, deps)

    def _build_sdk(self, cred: Credential, deps: Deps) -> anthropic.AsyncAnthropic:
        """Build AsyncAnthropic with correct auth and stealth headers."""
        if isinstance(cred, OAuthCredential):
            stealth = AnthropicAuth().http_headers(cred)
            return anthropic.AsyncAnthropic(
                auth_token=cred.access,
                api_key=None,
                http_client=deps.http_client,
                default_headers={
                    "X-Api-Key": omit,
                    "user-agent": stealth["user-agent"],
                    "x-app": stealth["x-app"],
                    "anthropic-beta": stealth["anthropic-beta"],
                },
                default_query={"beta": "true"},
                max_retries=0,
            )
        elif isinstance(cred, ApiKeyCredential):
            return anthropic.AsyncAnthropic(
                api_key=cred.key,
                http_client=deps.http_client,
                max_retries=0,
            )
        else:
            raise TypeError(f"AnthropicClient: unsupported credential type {type(cred)}")

    async def create(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int,
        thinking: ThinkingConfigParam | None = None,
        cache_control: CacheControlEphemeralParam | None = None,
        system: str | list | None = None,
        **kwargs: object,
    ) -> Message:
        """Non-streaming inference via direct Anthropic SDK (PRV-02)."""
        ...  # See error mapping pattern below

    async def stream(self, ...) -> ...:
        """Streaming inference via direct Anthropic SDK (PRV-02)."""
        ...
```

### Pattern 3: Extended Thinking — PRV-08

**What:** Pass `thinking=` to `messages.create()` using SDK types.
**When to use:** When caller requests extended thinking (budget_tokens > 0).

Verified from `messages.py` line 969 and `thinking_config_enabled_param.py`:

```python
# Source: anthropic 0.96.0 types/thinking_config_enabled_param.py
from anthropic.types.thinking_config_param import ThinkingConfigParam
# ThinkingConfigParam = Union[ThinkingConfigEnabledParam, ThinkingConfigDisabledParam, ThinkingConfigAdaptiveParam]

# For explicit budget:
thinking_config: ThinkingConfigParam = {"type": "enabled", "budget_tokens": 8192}

# For adaptive (recommended by SDK for claude-opus-4-6 and newer):
thinking_config: ThinkingConfigParam = {"type": "adaptive"}

# Note: for claude-opus-4-6 and claude-mythos-preview, SDK warns if type="enabled"
# is used — use "adaptive" instead (verified from messages.py lines 993-995).
# Phase 025 should pass through whatever the caller provides without filtering.

response = await sdk.messages.create(
    model="claude-opus-4-5",
    max_tokens=16000,           # must be > budget_tokens
    messages=messages,
    thinking=thinking_config,   # PRV-08
)

# Thinking blocks in response.content:
for block in response.content:
    if block.type == "thinking":
        # block is ThinkingBlock with .thinking (str) and .signature (str)
        thinking_text = block.thinking
    elif block.type == "redacted_thinking":
        # block is RedactedThinkingBlock with .data (str) — multi-turn continuity
        pass
    elif block.type == "text":
        text = block.text
```

**Budget constraint (from SDK docstring):** `budget_tokens` must be >= 1024 and < `max_tokens`. Caller is responsible for ensuring this constraint; `AnthropicClient` should validate and raise `ProviderBadRequestError` if violated.

### Pattern 4: Cache-Control — PRV-09

**What:** Pass `cache_control=` to `messages.create()` and preserve usage counters in response.
**When to use:** When fine-grained caching is requested.

Verified from `messages.py` lines 959, 1007 and `cache_control_ephemeral_param.py`:

```python
# Source: anthropic 0.96.0 types/cache_control_ephemeral_param.py
from anthropic.types.cache_control_ephemeral_param import CacheControlEphemeralParam

cache_config: CacheControlEphemeralParam = {"type": "ephemeral", "ttl": "5m"}  # or "1h"

response = await sdk.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=messages,
    cache_control=cache_config,  # PRV-09 — top-level cache control
)

# Cache accounting in response.usage (verified from types/usage.py):
# response.usage.cache_creation_input_tokens  — tokens used to populate cache
# response.usage.cache_read_input_tokens      — tokens read from cache
# response.usage.cache_creation               — CacheCreation object with
#     .ephemeral_1h_input_tokens and .ephemeral_5m_input_tokens breakdown
```

**PRV-09 contract:** `AnthropicClient.create()` must return the full `Message` object (not strip `usage`). Callers (Phase 028, cost accounting) read `response.usage.cache_creation_input_tokens` and `response.usage.cache_read_input_tokens`. Do not wrap or truncate the response.

### Pattern 5: Streaming — `AsyncStream[RawMessageStreamEvent]`

**What:** Stream via `client.messages.create(stream=True)` returning `AsyncStream[RawMessageStreamEvent]`.
**When to use:** When caller requests streaming.

Verified from `_streaming.py` and `types/raw_message_stream_event.py`:

```python
# Source: anthropic 0.96.0 _streaming.py and types/raw_message_stream_event.py
from collections.abc import AsyncGenerator
from anthropic.types import RawMessageStreamEvent

async def stream(self, *, model: str, messages: list[dict], max_tokens: int,
                 thinking: ThinkingConfigParam | None = None,
                 cache_control: CacheControlEphemeralParam | None = None,
                 **kwargs: object) -> AsyncGenerator[RawMessageStreamEvent, None]:
    try:
        response = await self._sdk.messages.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            thinking=thinking,
            cache_control=cache_control,
            stream=True,
            **kwargs,
        )
    except anthropic.APIStatusError as e:
        raise _map_sdk_error(e) from e
    except anthropic.APIConnectionError as e:
        raise ProviderTransientError(f"connection: {e}") from e

    async for event in response:
        # event is RawMessageStreamEvent (discriminated union):
        #   RawMessageStartEvent, RawMessageDeltaEvent, RawMessageStopEvent
        #   RawContentBlockStartEvent, RawContentBlockDeltaEvent, RawContentBlockStopEvent
        #
        # For thinking streaming, event type="content_block_delta" with
        #   event.delta.type == "thinking_delta" and event.delta.thinking (str)
        yield event
```

### Pattern 6: Error Mapping

**What:** Map `anthropic` SDK exceptions to the shared `StateProviderError` hierarchy.
**When to use:** Wrap all `messages.create()` calls.

Verified from `anthropic/_exceptions.py`:

```python
# Source: anthropic 0.96.0 _exceptions.py
import anthropic

def _map_sdk_error(e: anthropic.APIStatusError) -> StateProviderError:
    """Map Anthropic SDK HTTP status errors to state hierarchy."""
    status = e.status_code
    if status == 429 or status >= 500:
        return ProviderTransientError(f"transient {status}: {e}")
    if status in (401, 403):
        return ProviderAuthError(f"auth {status}: {e}")
    if status == 400:
        return ProviderBadRequestError(f"bad_request: {e}")
    return StateProviderError(f"provider_error {status}: {e}")
```

Key Anthropic SDK exception classes (from `_exceptions.py`):
- `anthropic.APIConnectionError` — network failure → `ProviderTransientError`
- `anthropic.APITimeoutError` (subclass of `APIConnectionError`) → `ProviderTransientError`
- `anthropic.RateLimitError` (status 429) → `ProviderTransientError`
- `anthropic.AuthenticationError` (status 401) → `ProviderAuthError`
- `anthropic.PermissionDeniedError` (status 403) → `ProviderAuthError`
- `anthropic.BadRequestError` (status 400) → `ProviderBadRequestError`
- `anthropic.APIStatusError` (base for all HTTP status errors) — dispatch on `status_code`

### Pattern 7: `errors.py` Extraction (TODO from Phase 024)

Phase 024's `litellm_client.py` has `# TODO(phase-025): extract StateProviderError hierarchy to state_core/providers/errors.py`. Phase 025 MUST do this extraction:

```python
# src/state_core/providers/errors.py  (NEW in Phase 025)
from __future__ import annotations

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

Then `litellm_client.py` is updated to `from state_core.providers.errors import ...` instead of defining the hierarchy inline. Both `litellm_client.py` and `anthropic_client.py` import from `errors.py`.

### Pattern 8: pytest-httpx Mocking at Transport Layer

**What:** Use `HTTPXMock` to intercept real HTTP calls from `AsyncAnthropic`.
**When to use:** All tests — avoids live API calls, validates actual wire shape.

`pytest-httpx` 0.36.2 patches `httpx.AsyncHTTPTransport.handle_async_request` at the fixture level (verified from `__init__.py`). Since `AsyncAnthropic(http_client=shared_client)` uses the `shared_client`'s transport (which is `httpx.AsyncHTTPTransport`), `HTTPXMock` intercepts all calls.

```python
# Source: pytest-httpx 0.36.2 __init__.py + _httpx_mock.py
import json
import pytest
from pytest_httpx import HTTPXMock
import httpx
import anthropic

@pytest.fixture
def shared_client() -> httpx.AsyncClient:
    """Fixture: shared httpx client (stands in for deps.http_client)."""
    return httpx.AsyncClient()

async def test_create_non_streaming(httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient) -> None:
    """AnthropicClient.create() sends correct stealth headers and returns Message."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        json={
            "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-opus-4-5-20241022",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    )
    # Verify stealth headers are sent:
    # httpx_mock allows `match_headers=` for header assertions
```

**Important:** `httpx_mock.add_response(match_headers={"authorization": "Bearer sk-ant-oat-..."})` can be used to verify stealth header presence. Use `match_headers` to assert `x-app: cli` and `user-agent: claude-cli/2.1.121 (external, cli)`.

### Anti-Patterns to Avoid

- **Calling `AnthropicAuth().http_headers(cred)` for every request:** Call once at `AnthropicClient.__init__` — `AnthropicAuth` is stateless; the headers come from the credential and the constants, which don't change per-call.
- **Passing `auth_token=` AND leaving `api_key=None` without `"X-Api-Key": omit` in default_headers:** If `ANTHROPIC_API_KEY` is set in the environment, `api_key` will be populated from env (SDK line 332-333: `if api_key is None: api_key = os.environ.get(...)`), and both `X-Api-Key` and `Authorization: Bearer` will be sent. The Phase 014 docstring says to pop X-Api-Key; for the SDK this means `"X-Api-Key": omit` in `default_headers`.
- **Using `client.messages.stream()` helper instead of `create(stream=True)`:** The SDK's `messages.stream()` context-manager helper is convenient but returns a `MessageStreamManager` (not `AsyncStream[RawMessageStreamEvent]`). For raw event access (needed to preserve thinking blocks and cache usage in streaming), use `messages.create(stream=True)` which returns `AsyncStream[RawMessageStreamEvent]`.
- **Sharing `AnthropicClient` across different credentials:** `AnthropicClient` is credential-bound (the `AsyncAnthropic` instance is built from one credential's token). Phase 026's `ProviderRouter` is responsible for building the correct `AnthropicClient` for the active credential.
- **Calling `await self._sdk.close()` or `await deps.http_client.aclose()` from this module:** The shared httpx client lifecycle is owned by `Deps`; `AnthropicClient` must never close it.
- **Setting `max_retries` > 0 on `AsyncAnthropic`:** The SDK's built-in retry logic uses `time.sleep` in some paths and conflicts with `ProviderTransientError`-based retry policy. Set `max_retries=0`; callers implement retry via `ProviderTransientError`.
- **Importing `thinking` or `cache_control` types from litellm:** These are anthropic SDK types (`anthropic.types.thinking_config_param`, `anthropic.types.cache_control_ephemeral_param`). Do not import from litellm for the escape hatch path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth Bearer header | Custom `httpx.Auth` class | `AsyncAnthropic(auth_token=cred.access)` + `default_headers` | SDK handles Bearer token in `_bearer_auth` property |
| X-Api-Key suppression | Monkey-patch `auth_headers` | `"X-Api-Key": anthropic.omit` in `default_headers` | `_merge_mappings` in SDK removes Omit values; no monkey-patching needed |
| SSE streaming parser | Custom SSE decoder | `messages.create(stream=True)` returning `AsyncStream[RawMessageStreamEvent]` | SDK handles SSE, JSON delta parsing, thinking block reconstruction |
| Thinking block detection | Type-check raw JSON | `block.type == "thinking"` on `ContentBlock` union | SDK returns discriminated union; type field is reliable |
| Cache usage extraction | Parse raw response JSON | `response.usage.cache_creation_input_tokens` | SDK deserializes into `Usage` Pydantic model |
| ?beta=true URL manipulation | `with_beta_param(url)` on each call | `default_query={"beta": "true"}` on `AsyncAnthropic()` | SDK appends query params to every request automatically |

**Key insight:** Phase 014 already built `with_beta_param()` and `inject_stealth_system_prefix()` for use before Phase 025 existed. Now that Phase 025 wires the SDK directly, `default_query={"beta": "true"}` replaces the need for `with_beta_param()` on inference URLs. `inject_stealth_system_prefix()` is still needed for the system prompt prefix (applies to the message body, not headers).

---

## Common Pitfalls

### Pitfall 1: X-Api-Key Leaked Alongside Bearer When `ANTHROPIC_API_KEY` Env Var Is Set

**What goes wrong:** `AsyncAnthropic(auth_token=cred.access, api_key=None, ...)` — passing `api_key=None` does NOT prevent env fallback. SDK line 332-333: `if api_key is None: api_key = os.environ.get("ANTHROPIC_API_KEY")`. If `ANTHROPIC_API_KEY` is set (common in dev/CI), both `X-Api-Key` and `Authorization: Bearer` are sent. Anthropic server may demote to API-key pricing (not OAuth/subscription pricing).

**Why it happens:** SDK's env-var fallback happens before our `api_key=None` has any effect. The `None` check triggers the env read.

**How to avoid:** Always add `"X-Api-Key": omit` to `default_headers`. The `_merge_mappings` function (SDK `_base_client.py` line 2262-2271) removes any key whose value is `Omit`. This fires AFTER auth_headers are built, so the env-populated api_key is suppressed.

**Warning signs:** Test that passes only when `ANTHROPIC_API_KEY` env var is unset; CI failure when developer has env var set.

### Pitfall 2: Using `client.messages.stream()` Context Manager Instead of `create(stream=True)`

**What goes wrong:** `async with sdk.messages.stream(...) as stream:` returns a `MessageStreamManager` which yields `MessageStreamEvent` (a higher-level abstraction that accumulates deltas). The `thinking` field in `MessageStreamEvent` is the accumulated thinking text, not individual `ThinkingDelta` chunks. PRV-09 cache accounting in streaming requires access to the final `RawMessageStopEvent` or `RawMessageDeltaEvent` which contains `usage`.

**Why it happens:** The SDK has two streaming APIs: the context-manager helper (`messages.stream()`) which accumulates for convenience, and the raw stream (`messages.create(stream=True)`) which yields individual events. The raw stream is needed when callers need each event.

**How to avoid:** Use `await sdk.messages.create(stream=True, ...)` which returns `AsyncStream[RawMessageStreamEvent]`. This yields each raw SSE event including `RawMessageStartEvent` (has `message.usage` partial) and `RawMessageStopEvent` (has final `message.usage`).

**Warning signs:** Callers can't find `usage.cache_read_input_tokens` on streaming responses.

### Pitfall 3: Thinking Budget Must Be < max_tokens and >= 1024

**What goes wrong:** `thinking={"type": "enabled", "budget_tokens": 5000}` with `max_tokens=2048` raises `anthropic.BadRequestError` with body `{"error": {"type": "invalid_request_error", "message": "budget_tokens must be less than max_tokens"}}`.

**Why it happens:** The Anthropic API enforces this constraint server-side. The SDK does not validate it client-side before sending.

**How to avoid:** `AnthropicClient.create()` should validate: `if thinking and thinking.get("type") == "enabled" and thinking["budget_tokens"] >= max_tokens: raise ProviderBadRequestError(...)`. Budget must also be >= 1024.

**Warning signs:** Intermittent 400 errors when callers set low `max_tokens` with extended thinking enabled.

### Pitfall 4: `anthropic-beta` Header Conflicts with SDK's Default anthropic-version Header

**What goes wrong:** The SDK always sends `anthropic-version: 2023-06-01` in `default_headers` (line 421 of `_client.py`). If we also try to override `anthropic-version` in our stealth headers, the `_merge_mappings` order means our value wins if in `_custom_headers`. The `anthropic-beta` flag list is a SEPARATE header — they don't conflict. The risk is accidentally trying to override `anthropic-version` instead of `anthropic-beta`.

**Why it happens:** Confusion between `anthropic-version` (API versioning, always `2023-06-01`) and `anthropic-beta` (feature flags, our stealth values).

**How to avoid:** Only set `anthropic-beta` in `default_headers`; never set `anthropic-version`. The SDK's hardcoded value is correct.

**Warning signs:** Anthropic API returns 400 with "anthropic-version must be 2023-06-01" if someone accidentally overrides it.

### Pitfall 5: `inject_stealth_system_prefix` Must Be Applied Before Calling SDK

**What goes wrong:** The stealth system prefix ("You are Claude Code, Anthropic's official CLI for Claude.") must be prepended to the `system` parameter. Phase 014's `inject_stealth_system_prefix(body)` handles all three shapes (list, string, None). If called on the raw messages dict, it mutates the `system` key.

**Why it happens:** The `inject_stealth_system_prefix` function takes a `body: dict` (the full request body) and mutates `body["system"]`. When using the SDK directly, we don't construct a raw request body — we pass `system=` as a kwarg. 

**How to avoid:** Apply `inject_stealth_system_prefix` to a dict containing the `system` kwarg, then extract `body["system"]` to pass as the SDK param:
```python
body = {"system": kwargs.pop("system", None)}
inject_stealth_system_prefix(body)
system = body["system"]  # now has the prefix prepended
```
This avoids mutating the caller's original args while correctly using Phase 014's helper.

**Warning signs:** OAuth inference calls that lack the "You are Claude Code" prefix get flagged by Anthropic's subscription gate (may result in non-subscription pricing or 403).

### Pitfall 6: SDK Internal Retry Uses `asyncio.sleep` — Set max_retries=0

**What goes wrong:** Leaving `max_retries` at the SDK default (2) causes the SDK to silently retry transient errors before raising. This bypasses state's `ProviderTransientError`-based retry policy and cost accounting (Phase 028 doesn't see retry attempts).

**Why it happens:** `AsyncAnthropic` default `max_retries=2` (visible in `_base_client.py`). SDK retries on 429 and 5xx automatically.

**How to avoid:** Pass `max_retries=0` to `AsyncAnthropic()`. State's retry policy (Phase 028) sits above `AnthropicClient`.

**Warning signs:** Cost accounting shows fewer requests than expected; transient 429s appear to succeed on first attempt (actually succeeded on second attempt internally).

---

## Code Examples

Verified patterns from installed anthropic 0.96.0:

### Full `AnthropicClient` Construction for OAuth

```python
# Source: anthropic 0.96.0 _client.py AsyncAnthropic.__init__ + _base_client.py _merge_mappings
import anthropic
from anthropic import omit
from state_core.auth.base import OAuthCredential
from state_core.auth.providers.anthropic import AnthropicAuth, inject_stealth_system_prefix

def _build_oauth_sdk(cred: OAuthCredential, http_client: httpx.AsyncClient) -> anthropic.AsyncAnthropic:
    stealth = AnthropicAuth().http_headers(cred)
    # stealth keys: "authorization" (skip — auth_token= handles it),
    #               "user-agent", "x-app", "anthropic-beta"
    return anthropic.AsyncAnthropic(
        auth_token=cred.access,
        api_key=None,
        http_client=http_client,
        default_headers={
            "X-Api-Key": omit,            # suppress even if ANTHROPIC_API_KEY env set
            "user-agent": stealth["user-agent"],
            "x-app": stealth["x-app"],
            "anthropic-beta": stealth["anthropic-beta"],
        },
        default_query={"beta": "true"},
        max_retries=0,
    )
```

### Non-Streaming Create with Thinking (PRV-02 + PRV-08)

```python
# Source: anthropic 0.96.0 resources/messages/messages.py async def create (line 2400)
from anthropic.types import Message
from anthropic.types.thinking_config_param import ThinkingConfigParam

async def create(
    self,
    *,
    model: str,
    messages: list[dict],
    max_tokens: int,
    thinking: ThinkingConfigParam | None = None,
    cache_control: CacheControlEphemeralParam | None = None,
    system: str | list | None = None,
    **kwargs: object,
) -> Message:
    # Apply stealth system prefix if OAuth credential
    if isinstance(self._cred, OAuthCredential) and system is not None or True:
        body = {"system": system}
        inject_stealth_system_prefix(body)
        system = body["system"]

    create_kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        **kwargs,
    }
    if thinking is not None:
        create_kwargs["thinking"] = thinking
    if cache_control is not None:
        create_kwargs["cache_control"] = cache_control
    if system is not None:
        create_kwargs["system"] = system

    try:
        return await self._sdk.messages.create(**create_kwargs)
    except anthropic.APIConnectionError as e:
        raise ProviderTransientError(f"connection: {e}") from e
    except anthropic.RateLimitError as e:
        raise ProviderTransientError(f"rate_limit: {e}") from e
    except anthropic.AuthenticationError as e:
        raise ProviderAuthError(f"auth: {e}") from e
    except anthropic.PermissionDeniedError as e:
        raise ProviderAuthError(f"permission: {e}") from e
    except anthropic.BadRequestError as e:
        raise ProviderBadRequestError(f"bad_request: {e}") from e
    except anthropic.APIStatusError as e:
        if e.status_code >= 500:
            raise ProviderTransientError(f"server_error {e.status_code}: {e}") from e
        raise StateProviderError(f"api_error {e.status_code}: {e}") from e
```

### Cache Usage Preservation (PRV-09)

```python
# Source: anthropic 0.96.0 types/usage.py
# After calling create():
response: Message = await client.create(
    model="claude-opus-4-5-20241022",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1024,
    cache_control={"type": "ephemeral", "ttl": "5m"},
)
# PRV-09: preserve usage — caller (Phase 028) reads these:
print(response.usage.input_tokens)
print(response.usage.output_tokens)
print(response.usage.cache_creation_input_tokens)   # tokens written to cache
print(response.usage.cache_read_input_tokens)        # tokens read from cache
print(response.usage.cache_creation)  # CacheCreation with .ephemeral_5m_input_tokens / .ephemeral_1h_input_tokens
```

### pytest-httpx Wire-Level Test

```python
# Source: pytest-httpx 0.36.2 __init__.py — patches httpx.AsyncHTTPTransport
import json
import httpx
import anthropic
import pytest
from pytest_httpx import HTTPXMock
from state_core.auth.base import OAuthCredential
from state_core.providers.anthropic_client import AnthropicClient

FAKE_OAUTH_CRED = OAuthCredential(
    type="oauth",
    access="sk-ant-oat-fake-token",
    refresh="fake-refresh",
    expires=9999999999.0,
    provider_id="anthropic",
)

@pytest.fixture
def shared_client():
    return httpx.AsyncClient()

async def test_create_sends_stealth_headers(
    httpx_mock: HTTPXMock, shared_client: httpx.AsyncClient
) -> None:
    """AnthropicClient.create() sends stealth headers and ?beta=true."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        match_headers={
            "x-app": "cli",
            "authorization": "Bearer sk-ant-oat-fake-token",
        },
        json={
            "id": "msg_01", "type": "message", "role": "assistant",
            "content": [{"type": "text", "text": "Hi"}],
            "model": "claude-opus-4-5-20241022",
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 5, "output_tokens": 2,
                      "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0},
        },
    )
    from state_core.deps import Deps
    deps = Deps(http_client=shared_client)
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    msg = await client.create(
        model="claude-opus-4-5-20241022",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )
    assert msg.content[0].text == "Hi"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `auth_token=` only, relying on env-var not being set | `auth_token=` + `"X-Api-Key": omit` in `default_headers` | anthropic SDK added env fallback | X-Api-Key never leaks even in dev/CI environments |
| Manual `?beta=true` URL construction via `with_beta_param()` | `default_query={"beta": "true"}` on `AsyncAnthropic()` | Phase 025 (now) | Cleaner; SDK applies to every request |
| `thinking.type="enabled"` | `thinking.type="adaptive"` for claude-opus-4-6+ | anthropic 0.96.0 | SDK warns on "enabled" for newer models; "adaptive" is preferred |
| Flat `StateProviderError` in `litellm_client.py` | `errors.py` module shared by both clients | Phase 025 (now) | Both clients share the same error hierarchy |

**Deprecated/outdated:**
- `thinking.type="enabled"` for `claude-opus-4-6` and `claude-mythos-preview` models — SDK warns; use `"adaptive"` instead (SDK source `messages.py` line 993). Pass through caller's value; don't silently rewrite it.
- `messages.stream()` context-manager — useful for accumulation but loses raw event access needed for PRV-09 streaming cache accounting. Use `messages.create(stream=True)` for raw events.

---

## Open Questions

1. **Should `inject_stealth_system_prefix` be applied for API-key credentials (non-OAuth)?**
   - What we know: The prefix is part of the stealth identity — it makes the request look like Claude Code. For API-key credentials, stealth identity is not needed (no subscription pricing benefit).
   - What's unclear: Whether applying the prefix to API-key calls causes any harm or server-side behavior change.
   - Recommendation: For Phase 025, only apply `inject_stealth_system_prefix` for `OAuthCredential`. Document this choice in the module docstring.

2. **Should `AnthropicClient` be constructable without a credential (daemon startup)?**
   - What we know: Phase 026 (ProviderRouter) will build the `AnthropicClient` for the active credential when routing a request. The daemon doesn't know the credential at startup — it's known at request time.
   - What's unclear: Whether Phase 025 should expose a factory method or expect Phase 026 to construct it.
   - Recommendation: `AnthropicClient(cred, deps)` constructor is sufficient for Phase 025. Phase 026 builds it per-request as needed.

3. **`beta=true` query param — is it required for extended thinking requests or all requests?**
   - What we know: Phase 014's `with_beta_param` docstring says "Mirrors milady claude-code-stealth.mjs L79: add beta=true if not already present". This applies to inference URLs broadly in the stealth flow.
   - What's unclear: Whether `?beta=true` is REQUIRED for extended thinking specifically, or just part of the general stealth mimic.
   - Recommendation: `default_query={"beta": "true"}` applies to all SDK requests (safe; consistent with stealth spec). No per-call branching needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| Quick run command | `python3 -m pytest tests/test_anthropic_client.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-02 | `AnthropicClient` constructs `AsyncAnthropic` with `http_client=deps.http_client` | unit | `pytest tests/test_anthropic_client.py::test_uses_shared_http_client -x` | ❌ Wave 0 |
| PRV-02 | `AnthropicClient.create()` sends POST to `https://api.anthropic.com/v1/messages?beta=true` | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_create_posts_to_correct_url -x` | ❌ Wave 0 |
| PRV-02 | `OAuthCredential` → stealth headers present (`x-app: cli`, `user-agent: claude-cli/2.1.121 (external, cli)`, `authorization: Bearer sk-ant-oat...`, `anthropic-beta: ...`) | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_oauth_stealth_headers -x` | ❌ Wave 0 |
| PRV-02 | `X-Api-Key` header absent when `OAuthCredential` used even if `ANTHROPIC_API_KEY` env set | unit (httpx_mock + monkeypatch env) | `pytest tests/test_anthropic_client.py::test_no_x_api_key_with_oauth -x` | ❌ Wave 0 |
| PRV-02 | `ApiKeyCredential` → `X-Api-Key` header present, no stealth headers | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_api_key_credential_headers -x` | ❌ Wave 0 |
| PRV-02 | `AnthropicClient` does NOT close the shared httpx client | unit | `pytest tests/test_anthropic_client.py::test_does_not_close_shared_client -x` | ❌ Wave 0 |
| PRV-02 | `anthropic.APIConnectionError` maps to `ProviderTransientError` | unit | `pytest tests/test_anthropic_client.py::test_connection_error_maps_to_transient -x` | ❌ Wave 0 |
| PRV-02 | `anthropic.AuthenticationError` maps to `ProviderAuthError` | unit | `pytest tests/test_anthropic_client.py::test_auth_error_maps_to_auth_error -x` | ❌ Wave 0 |
| PRV-02 | `anthropic.BadRequestError` maps to `ProviderBadRequestError` | unit | `pytest tests/test_anthropic_client.py::test_bad_request_maps_to_bad_request -x` | ❌ Wave 0 |
| PRV-02 | `StateProviderError` is importable from `state_core.providers.errors` (extracted from litellm_client) | import | `pytest tests/test_anthropic_client.py::test_errors_importable_from_errors_module -x` | ❌ Wave 0 |
| PRV-02 | Mode isolation: `state_core.providers.anthropic_client` does NOT import `state_build.*` or `state_teach.*` | import-graph | `pytest tests/test_anthropic_client.py::test_no_mode_silo_import -x` | ❌ Wave 0 |
| PRV-08 | `thinking={"type": "enabled", "budget_tokens": 8192}` is passed through to `messages.create()` | unit (httpx_mock + match_json) | `pytest tests/test_anthropic_client.py::test_thinking_budget_passed_through -x` | ❌ Wave 0 |
| PRV-08 | `ThinkingBlock` and `RedactedThinkingBlock` in response are preserved in returned `Message` | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_thinking_blocks_preserved -x` | ❌ Wave 0 |
| PRV-08 | `thinking={"type": "adaptive"}` also accepted | unit | `pytest tests/test_anthropic_client.py::test_adaptive_thinking_accepted -x` | ❌ Wave 0 |
| PRV-09 | `cache_control={"type": "ephemeral", "ttl": "5m"}` passed through to `messages.create()` | unit (httpx_mock + match_json) | `pytest tests/test_anthropic_client.py::test_cache_control_passed_through -x` | ❌ Wave 0 |
| PRV-09 | `response.usage.cache_creation_input_tokens` preserved in returned `Message` | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_cache_usage_preserved -x` | ❌ Wave 0 |
| PRV-09 | `response.usage.cache_read_input_tokens` preserved in returned `Message` | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_cache_read_tokens_preserved -x` | ❌ Wave 0 |
| PRV-08+09 | Streaming: `RawContentBlockDeltaEvent` with `delta.type="thinking_delta"` yielded unchanged | unit (httpx_mock streaming) | `pytest tests/test_anthropic_client.py::test_stream_thinking_delta_yielded -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_anthropic_client.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_anthropic_client.py` — all 18 RED stubs listed above
- [ ] `src/state_core/providers/errors.py` — extracted error hierarchy (created in Wave 1 GREEN)
- [ ] `src/state_core/providers/anthropic_client.py` — module (created in Wave 1 GREEN)

*(No framework gaps — pytest infrastructure and `HTTPXMock` pattern already used in `test_sync_mirror.py` and `test_deps.py`.)*

---

## Sources

### Primary (HIGH confidence)
- `anthropic 0.96.0` installed at `.venv/lib/python3.12/site-packages/anthropic/` — verified from source:
  - `_client.py` — `AsyncAnthropic.__init__` signature (lines 302-354), `auth_headers` property (lines 397-412), `default_headers` property (lines 414-422), env-var fallback for `api_key` (lines 332-333)
  - `_base_client.py` — `default_headers` merge order (lines 684-693), `_merge_mappings` removes `Omit` values (lines 2262-2271), `_build_headers` (lines 440-469)
  - `_types.py` — `Omit` class definition (lines 161-182), `omit` sentinel (line 182)
  - `types/thinking_config_enabled_param.py` — `ThinkingConfigEnabledParam` with `budget_tokens` and `display` fields
  - `types/thinking_config_adaptive_param.py` — `ThinkingConfigAdaptiveParam`
  - `types/thinking_config_param.py` — `ThinkingConfigParam = Union[Enabled, Disabled, Adaptive]`
  - `types/thinking_block.py` — `ThinkingBlock.thinking`, `.signature`, `.type`
  - `types/redacted_thinking_block.py` — `RedactedThinkingBlock.data`, `.type`
  - `types/cache_control_ephemeral_param.py` — `CacheControlEphemeralParam` with `ttl` field ("5m" | "1h")
  - `types/usage.py` — `Usage` with `cache_creation_input_tokens`, `cache_read_input_tokens`, `cache_creation: CacheCreation`
  - `types/cache_creation.py` — `CacheCreation.ephemeral_1h_input_tokens`, `.ephemeral_5m_input_tokens`
  - `types/content_block.py` — `ContentBlock` union including `ThinkingBlock`, `RedactedThinkingBlock`
  - `types/raw_message_stream_event.py` — `RawMessageStreamEvent` union members
  - `types/raw_content_block_delta.py` — `RawContentBlockDelta` including `ThinkingDelta`
  - `types/thinking_delta.py` — `ThinkingDelta.thinking`, `.type="thinking_delta"`
  - `resources/messages/messages.py` — `async def create()` signature (lines 2400-2478), `thinking=` param, `cache_control=` param, `MODELS_TO_WARN_WITH_THINKING_ENABLED` (line 79)
  - `__init__.py` — `omit` exported from `anthropic` package (line 6)
- `pytest_httpx 0.36.2` installed at `.venv/lib/python3.12/site-packages/pytest_httpx/` — `__init__.py` (patches `httpx.AsyncHTTPTransport.handle_async_request`), `_httpx_mock.py` (`.add_response()`, `match_headers=` matcher)
- `src/state_core/auth/providers/anthropic.py` — Phase 014 implementation: `AnthropicAuth.http_headers()`, `_USER_AGENT`, `_X_APP`, `_ANTHROPIC_BETA`, `inject_stealth_system_prefix()`, `with_beta_param()`, `OAuthCredential` shape
- `src/state_core/auth/base.py` — `OAuthCredential`, `ApiKeyCredential`, `Credential` discriminated union
- `src/state_core/deps.py` — `Deps.http_client` field, `Deps.aclose()`
- `src/state_core/http_client.py` — `build_shared_client()` confirmed implemented
- `src/state_core/providers/litellm_client.py` — `StateProviderError` hierarchy + `# TODO(phase-025): extract` comment
- `.state-inputs/claude-oauth.md` — Stealth header spec: `user-agent: claude-cli/<version>`, `x-app: cli`, `anthropic-beta: ...` flag list; `?beta=true` on inference URLs

### Secondary (MEDIUM confidence)
- Phase 023 RESEARCH.md — Pattern 3: `AsyncAnthropic(http_client=deps.http_client)` injection shape; Pitfall 1: auth provider OAuth flows must NOT use the shared client
- Phase 024 RESEARCH.md — Pitfall 1: litellm does not use shared httpx client for Anthropic; Phase 025 is the canonical Anthropic path; `# TODO(phase-025)` comment confirmed
- `pyproject.toml` — confirmed `anthropic>=0.80.0` installed at 0.96.0, `pytest-httpx>=0.35` at 0.36.2

### Tertiary (LOW confidence)
- None — all critical claims verified from installed package source or project files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — installed anthropic 0.96.0 verified from source
- Architecture (stealth header injection): HIGH — `_merge_mappings` Omit behavior verified from `_base_client.py`; `AnthropicAuth.http_headers()` shape verified from Phase 014 source
- Thinking API (PRV-08): HIGH — `ThinkingConfigParam` union, `budget_tokens` constraint, `ThinkingBlock` shape all verified from installed types
- Cache-control API (PRV-09): HIGH — `CacheControlEphemeralParam`, `Usage.cache_creation_input_tokens` all verified from installed types
- Streaming shape: HIGH — `AsyncStream[RawMessageStreamEvent]`, `ThinkingDelta` verified from installed types
- Pitfall 1 (X-Api-Key leak): HIGH — SDK env-var fallback behavior verified directly from `_client.py` lines 332-333

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (anthropic SDK is fast-moving; re-verify if bumped past 0.100.0, particularly `ThinkingConfigParam` shape as adaptive thinking matures)
