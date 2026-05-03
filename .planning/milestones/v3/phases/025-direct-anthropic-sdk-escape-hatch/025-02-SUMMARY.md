---
phase: 025-direct-anthropic-sdk-escape-hatch
plan: "02"
subsystem: provider-routing
tags: [anthropic-sdk, oauth-stealth, thinking, cache-control, error-hierarchy]
dependency_graph:
  requires:
    - "023-01"  # Deps.http_client — shared httpx.AsyncClient
    - "025-01"  # RED stubs in test_anthropic_client.py
    - "024-02"  # LitellmClient with StateProviderError hierarchy to extract
  provides:
    - "state_core.providers.errors — shared error hierarchy (PRV-01 + PRV-02)"
    - "state_core.providers.anthropic_client.AnthropicClient — direct SDK escape hatch"
  affects:
    - "026-*"  # ProviderRouter selects AnthropicClient for OAuth credentials
    - "028-*"  # cost accounting reads response.usage from AnthropicClient.create()
    - "029-*"  # thinking budget propagation via AnthropicClient.create(thinking=)
    - "030-*"  # cache-control e2e via AnthropicClient.create(cache_control=)
tech_stack:
  added:
    - "anthropic 0.96.0 AsyncAnthropic — direct SDK injection (already pinned)"
  patterns:
    - "AsyncAnthropic(http_client=deps.http_client) — shared transport injection"
    - "X-Api-Key: omit — SDK env-var suppression via default_headers"
    - "inspect.isawaitable() — @required_args decorator compatibility for stream()"
    - "from state_core.providers.errors import — single source of error hierarchy"
key_files:
  created:
    - src/state_core/providers/errors.py
    - src/state_core/providers/anthropic_client.py
  modified:
    - src/state_core/providers/litellm_client.py
decisions:
  - "Use 'User-Agent' (capital U-A) in default_headers to match SDK's key casing so Python dict merge overwrites instead of creating duplicate keys that httpx concatenates"
  - "Use inspect.isawaitable() in stream() to handle SDK's @required_args decorator wrapping — makes mock-based tests work without awaiting non-awaitable async generators"
  - "Stealth system prefix (inject_stealth_system_prefix) applied only for OAuthCredential, not ApiKeyCredential — prefix is part of OAuth stealth identity, not needed for API key path"
  - "AnthropicClient builds SDK instance once in __init__, not per-call — AnthropicAuth.http_headers() is stateless so called once at construction"
metrics:
  duration: "~9 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 025 Plan 02: AnthropicClient GREEN Implementation Summary

**One-liner:** Direct Anthropic SDK escape hatch with OAuth stealth headers, shared httpx transport, thinking/cache passthrough, and extracted shared error hierarchy.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create errors.py and update litellm_client.py import | 415c905 | src/state_core/providers/errors.py, src/state_core/providers/litellm_client.py |
| 2 | Implement AnthropicClient (18 tests GREEN) | 4c100ca | src/state_core/providers/anthropic_client.py |

## What Was Built

### Task 1: errors.py Extraction

Created `src/state_core/providers/errors.py` with the shared exception hierarchy:
- `StateProviderError` — base for all provider errors
- `ProviderTransientError` — retry-able (rate limits, connection errors, 5xx)
- `ProviderAuthError` — authentication failures (401, 403)
- `ProviderBadRequestError` — non-retryable (400, bad params)
- `ProviderResponseError` — invalid/unexpected response shape

Updated `litellm_client.py` to replace the inline definitions with `from state_core.providers.errors import ...`. The import re-exports the names as module attributes, so existing callers (`from state_core.providers.litellm_client import StateProviderError`) continue to work without modification.

### Task 2: AnthropicClient Implementation

Created `src/state_core/providers/anthropic_client.py` implementing `AnthropicClient(cred, deps)`:

**OAuthCredential path:**
- Calls `AnthropicAuth().http_headers(cred)` once in `__init__` via `_build_sdk()`
- Sets `auth_token=cred.access` for Bearer Authorization
- Sets `"User-Agent": stealth["user-agent"]` (capital U-A to match SDK's dict key — prevents httpx concatenation)
- Sets `"X-Api-Key": omit` in `default_headers` to suppress env-var populated api_key (T-025-2)
- Sets `default_query={"beta": "true"}` for all requests
- Sets `max_retries=0` (State owns retry policy via ProviderTransientError)

**ApiKeyCredential path:**
- Standard `api_key=cred.key` construction
- No stealth headers

**create() method:**
- Passes `thinking=` and `cache_control=` through to `messages.create()`
- Applies `inject_stealth_system_prefix()` only for OAuthCredential
- Returns full `Message` object (usage tokens preserved for Phase 028)
- Error mapping: APIConnectionError→ProviderTransientError, 401→ProviderAuthError, 400→ProviderBadRequestError

**stream() method:**
- Uses `messages.create(stream=True)` (not `messages.stream()` context manager)
- Uses `inspect.isawaitable()` to handle SDK's `@required_args` decorator wrapping
- Yields `RawMessageStreamEvent` unchanged

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] User-Agent header casing fix**
- **Found during:** Task 2, test_oauth_stealth_headers
- **Issue:** Using `"user-agent"` (lowercase) in `default_headers` creates a separate Python dict key from the SDK's `"User-Agent"` key, so both survive the merge and httpx concatenates them: `AsyncAnthropic/Python 0.96.0, claude-cli/2.1.121 (external, cli)`
- **Fix:** Changed key to `"User-Agent"` (matching SDK's exact casing) so Python dict `{**obj1, **obj2}` overwrites correctly
- **Files modified:** `src/state_core/providers/anthropic_client.py`
- **Commit:** 4c100ca

**2. [Rule 1 - Bug] inspect.isawaitable() for stream() mock compatibility**
- **Found during:** Task 2, test_stream_thinking_delta_yielded
- **Issue:** The Anthropic SDK's `messages.create` is decorated with `@required_args` which makes `inspect.iscoroutinefunction()` return False. `unittest.mock.patch.object` therefore creates a regular `Mock` (not `AsyncMock`). When the test mocks `create` with `return_value=_fake_stream()`, calling `await self._sdk.messages.create(...)` tries to await an async generator, which raises `TypeError`.
- **Fix:** Use `raw = self._sdk.messages.create(...)` then `response = await raw if inspect.isawaitable(raw) else raw`. This handles both real API calls (coroutine returned) and test mocks (async generator returned directly).
- **Files modified:** `src/state_core/providers/anthropic_client.py`
- **Commit:** 4c100ca

## Issues Encountered

None beyond the two auto-fixed bugs above.

## Verification

```
python3 -m pytest tests/test_anthropic_client.py -v
# 18 passed

python3 -m pytest tests/test_litellm_client.py -v
# 11 passed (no regressions)

grep -n "class AnthropicClient" src/state_core/providers/anthropic_client.py
# 47:class AnthropicClient

grep -n "from state_core.providers.errors import" src/state_core/providers/litellm_client.py
# confirmed (no inline class definitions remain)

grep -rn "aclose|.close()" src/state_core/providers/anthropic_client.py | grep -v "# Never"
# (empty — no aclose calls in implementation)
```

## Self-Check: PASSED
